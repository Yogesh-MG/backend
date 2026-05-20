"""
POS app views.

Endpoints:
  POST /api/pos/login/              — PIN-based POS login
  POST /api/pos/shift/open/         — Open shift
  POST /api/pos/shift/close/        — Close shift
  GET  /api/pos/shift/summary/      — Current shift summary
  GET  /api/pos/products/           — POS product catalog
  POST /api/pos/orders/             — Walk-in order
  GET  /api/pos/customers/lookup/   — Customer lookup by phone
  POST /api/pos/customers/          — Register walk-in customer
  POST /api/pos/wastage/            — Log wastage
  GET  /api/pos/wastage/            — Get wastage for current shift
  GET  /api/pos/settings/           — POS terminal settings
  GET  /api/pos/companies/          — List B2B companies
  POST /api/pos/companies/          — Register B2B company
"""
from decimal import Decimal

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import F

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.inventory.models import InventoryBatch
from apps.wallet.models import Wallet
from .models import (
    PosEmployee, PosCustomer, PosShift,
    PosTransaction, PosTransactionItem, PosTender, PosWastageLog,
    PosSettings, CompanyProfile, PosInvoiceCounter,
)
from .serializers import (
    PosProductSerializer, PosCustomerSerializer,
    PosOrderCreateSerializer, PosTransactionSerializer,
    PosShiftSerializer, PosShiftSummarySerializer,
    PosWastageSerializer, PosSettingsSerializer,
    PosCompanyProfileSerializer,
)
from .permissions import IsPosOperator


def _set_auth_cookies(response, access_token, refresh_token):
    """Reuse cookie-setting pattern from accounts."""
    from django.conf import settings as s
    kw = dict(
        secure=s.JWT_AUTH_COOKIE_SECURE,
        httponly=s.JWT_AUTH_COOKIE_HTTP_ONLY,
        samesite=s.JWT_AUTH_COOKIE_SAMESITE,
        path=s.JWT_AUTH_COOKIE_PATH,
    )
    response.set_cookie(key=s.JWT_AUTH_COOKIE, value=access_token, max_age=3600, **kw)
    response.set_cookie(key=s.JWT_AUTH_REFRESH_COOKIE, value=refresh_token, max_age=86400, **kw)


@method_decorator(csrf_exempt, name='dispatch')
class PosLoginView(APIView):
    """
    POST /api/pos/login/
    PIN-based login for POS terminals.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        employee_id = request.data.get('employee_id', '')
        pin = request.data.get('pin', '')

        if not employee_id or not pin:
            return Response(
                {'error': 'employee_id and pin are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            employee = PosEmployee.objects.select_related('user').get(
                employee_id=employee_id, pin=pin, is_active=True,
            )
        except PosEmployee.DoesNotExist:
            return Response(
                {'error': 'Invalid employee ID or PIN'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = employee.user
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response({
            'message': 'POS login successful',
            'access': access_token,
            'refresh': refresh_token,
            'employee_name': user.get_full_name() or user.username,
        })
        _set_auth_cookies(response, access_token, refresh_token)
        return response


@method_decorator(csrf_exempt, name='dispatch')
class PosShiftOpenView(APIView):
    """POST /api/pos/shift/open/"""
    permission_classes = [IsPosOperator]

    def post(self, request):
        employee_id = request.data.get('employee_id', '')
        opening_cash = request.data.get('opening_cash', 0)

        try:
            employee = PosEmployee.objects.get(
                user=request.user, employee_id=employee_id,
            )
        except PosEmployee.DoesNotExist:
            # Fallback: use user's employee record
            try:
                employee = request.user.pos_employee
            except PosEmployee.DoesNotExist:
                return Response(
                    {'error': 'POS employee record not found'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Check for already-open shift
        open_shift = PosShift.objects.filter(employee=employee, is_open=True).first()
        if open_shift:
            return Response({
                'message': 'Shift already open',
                'shift_id': str(open_shift.id),
            })

        shift = PosShift.objects.create(
            employee=employee,
            opening_cash=Decimal(str(opening_cash)),
        )

        return Response({
            'message': 'Shift opened',
            'shift_id': str(shift.id),
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class PosShiftCloseView(APIView):
    """POST /api/pos/shift/close/"""
    permission_classes = [IsPosOperator]

    def post(self, request):
        closing_cash = request.data.get('closing_cash', 0)
        notes = request.data.get('notes', '')

        try:
            employee = request.user.pos_employee
        except PosEmployee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        shift = PosShift.objects.filter(employee=employee, is_open=True).first()
        if not shift:
            return Response({'error': 'No open shift found'}, status=status.HTTP_404_NOT_FOUND)

        shift.closing_cash = Decimal(str(closing_cash))
        shift.notes = notes
        shift.is_open = False
        shift.closed_at = timezone.now()
        shift.save()

        serializer = PosShiftSummarySerializer(shift)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class PosShiftSummaryView(APIView):
    """GET /api/pos/shift/summary/"""
    permission_classes = [IsPosOperator]

    def get(self, request):
        try:
            employee = request.user.pos_employee
        except PosEmployee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        shift = PosShift.objects.filter(employee=employee).order_by('-started_at').first()
        if not shift:
            return Response({'error': 'No shift found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PosShiftSummarySerializer(shift)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class PosProductsView(APIView):
    """
    GET /api/pos/products/
    Derives POS catalog from inventory batches with stock > 0.
    """
    permission_classes = [IsPosOperator]

    def get(self, request):
        category = request.query_params.get('category')
        search = request.query_params.get('search')

        batches = InventoryBatch.objects.filter(
            stock_level__gt=0,
        ).select_related(
            'variant', 'variant__product', 'variant__product__category',
        )

        if category:
            batches = batches.filter(variant__product__category__slug=category)
        if search:
            batches = batches.filter(variant__product__name__icontains=search)

        products = []
        for batch in batches:
            product = batch.variant.product
            products.append({
                'pid': str(batch.id),
                'name': f"{product.name} ({batch.variant.unit})",
                'price': float(batch.price),
                'weighed': 'kg' in batch.variant.unit.lower() or 'g' in batch.variant.unit.lower(),
                'category': product.category.name if product.category else '',
                'stock': batch.stock_level,
                'low_stock_threshold': 5,
                'member_eligible': True,
            })

        serializer = PosProductSerializer(products, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class PosCustomerLookupView(APIView):
    """GET /api/pos/customers/lookup/?phone=..."""
    permission_classes = [IsPosOperator]

    def get(self, request):
        phone = request.query_params.get('phone', '')
        if not phone:
            return Response({'error': 'phone parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Check if it's a known B2B company phone
        company = CompanyProfile.objects.filter(contact_phone=phone).first()
        if company:
            return Response({
                'type': 'B2B',
                'id': str(company.id),
                'name': company.name,
                'phone': company.contact_phone,
                'email': company.email,
                'is_b2b': True,
                'company': PosCompanyProfileSerializer(company).data
            })

        # 2. Check if it's a regular customer
        try:
            customer = PosCustomer.objects.get(phone=phone)
            data = PosCustomerSerializer(customer).data
            data['type'] = 'RETAIL'
            data['is_b2b'] = customer.is_b2b_contact
            return Response(data)
        except PosCustomer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)


@method_decorator(csrf_exempt, name='dispatch')
class PosCustomerCreateView(APIView):
    """POST /api/pos/customers/"""
    permission_classes = [IsPosOperator]

    def post(self, request):
        name = request.data.get('name', '')
        phone = request.data.get('phone', '')
        email = request.data.get('email', '')
        is_b2b = request.data.get('is_b2b', False)

        if not name or not phone:
            return Response({'error': 'name and phone required'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # If B2B, create/update company profile first
            company = None
            if is_b2b:
                company_name = request.data.get('company_name', name)
                gstin = request.data.get('gstin', '')
                pan = request.data.get('pan', '')
                address = request.data.get('address', '')

                if not gstin:
                    return Response({'error': 'GSTIN required for B2B registration'}, status=status.HTTP_400_BAD_REQUEST)

                company, _ = CompanyProfile.objects.update_or_create(
                    gstin=gstin,
                    defaults={
                        'name': company_name,
                        'pan': pan,
                        'address': address,
                        'email': email,
                        'contact_phone': phone
                    }
                )

            customer, created = PosCustomer.objects.get_or_create(
                phone=phone,
                defaults={
                    'name': name,
                    'email': email,
                    'is_b2b_contact': is_b2b
                },
            )

            if not created and not is_b2b:
                return Response(
                    {'error': 'Customer with this phone already exists'},
                    status=status.HTTP_409_CONFLICT,
                )

            data = PosCustomerSerializer(customer).data
            if is_b2b and company:
                data['is_b2b'] = True
                data['company'] = PosCompanyProfileSerializer(company).data
            
            return Response(data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class PosSettingsView(APIView):
    """GET /api/pos/settings/"""
    permission_classes = [IsPosOperator]

    def get(self, request):
        settings_obj = PosSettings.get()
        serializer = PosSettingsSerializer(settings_obj)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class PosCompanyListView(APIView):
    """GET /api/pos/companies/ — List B2B companies"""
    permission_classes = [IsPosOperator]

    def get(self, request):
        companies = CompanyProfile.objects.all().order_by('name')
        serializer = PosCompanyProfileSerializer(companies, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class PosCompanyCreateView(APIView):
    """POST /api/pos/companies/ — Register B2B company"""
    permission_classes = [IsPosOperator]

    def post(self, request):
        serializer = PosCompanyProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.save()
        return Response(PosCompanyProfileSerializer(company).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class PosOrderCreateView(APIView):
    """POST /api/pos/orders/"""
    permission_classes = [IsPosOperator]

    def post(self, request):
        serializer = PosOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            employee = request.user.pos_employee
        except PosEmployee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        shift = PosShift.objects.filter(employee=employee, is_open=True).first()
        if not shift:
            return Response({'error': 'No open shift'}, status=status.HTTP_400_BAD_REQUEST)

        # Resolve customer
        customer = None
        customer_id = data.get('customer_id')
        is_anonymous = data.get('is_anonymous', False)
        if customer_id and not is_anonymous:
            try:
                customer = PosCustomer.objects.get(id=customer_id)
            except (PosCustomer.DoesNotExist, Exception):
                pass

        # ── PRIDE Limit Validation ──
        # If customer is a PRIDE member, validate member_discount against their limit
        pride_limit_used = Decimal('0.00')
        if customer and customer.user and customer.is_pride:
            try:
                wallet = Wallet.objects.select_for_update().get(user=customer.user)
                gross_subtotal = sum(
                    Decimal(str(item['unit_price'])) * Decimal(str(item['quantity']))
                    for item in data['items']
                )
                # The limit caps how much MRP can be discounted
                max_discountable = min(gross_subtotal, wallet.accumulated_pride_limit)
                max_member_discount = (max_discountable * Decimal('0.30')).quantize(Decimal('0.01'))
                submitted_member_discount = Decimal(str(data.get('member_discount', 0)))

                if submitted_member_discount > max_member_discount:
                    return Response({
                        'error': f'PRIDE discount exceeds available limit. '
                                 f'Max discount: ₹{max_member_discount}, '
                                 f'Submitted: ₹{submitted_member_discount}, '
                                 f'Remaining limit: ₹{wallet.accumulated_pride_limit}'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Deduct the MRP value that was discounted from the limit
                if max_discountable > 0:
                    pride_limit_used = max_discountable
                    wallet.accumulated_pride_limit -= max_discountable
                    wallet.save(update_fields=['accumulated_pride_limit'])
            except Wallet.DoesNotExist:
                pass

        # Resolve discount applied by
        discount_applied_by = None
        discount_by_id = data.get('discount_applied_by_id')
        if discount_by_id:
            try:
                discount_applied_by = PosEmployee.objects.get(employee_id=discount_by_id)
            except PosEmployee.DoesNotExist:
                pass

        # Resolve company for B2B
        company = None
        company_id = data.get('company_id')
        is_b2b = data.get('is_b2b', False)
        if is_b2b and company_id:
            try:
                company = CompanyProfile.objects.get(id=company_id)
            except CompanyProfile.DoesNotExist:
                pass

        # Determine payment method
        tenders = data.get('tenders', [])
        method = tenders[0]['method'] if len(tenders) == 1 else 'Split'

        # Generate invoice number for B2B
        invoice_number = ""
        if is_b2b:
            invoice_number = PosInvoiceCounter.next_invoice_number()

        rounding_adjustment = Decimal(str(data.get('rounding_adjustment', 0)))

        with transaction.atomic():
            txn = PosTransaction.objects.create(
                shift=shift,
                customer=customer,
                method=method,
                subtotal=data['subtotal'],
                member_discount=data.get('member_discount', 0),
                pride_limit_used=pride_limit_used,
                manual_discount_percentage=data.get('manual_discount_percentage', 0),
                manual_discount_amount=data.get('manual_discount_amount', 0),
                discount_reason=data.get('discount_reason', ''),
                discount_applied_by=discount_applied_by,
                surcharge=data.get('surcharge', 0),
                rounding_adjustment=rounding_adjustment,
                total=data['total'],
                receipt_delivery=data.get('receipt_delivery', ''),
                is_anonymous=is_anonymous,
                is_b2b=is_b2b,
                company=company,
                invoice_number=invoice_number,
            )

            # Create items
            for item in data['items']:
                PosTransactionItem.objects.create(
                    transaction=txn,
                    pid=item['pid'],
                    name=item['name'],
                    unit_price=Decimal(str(item['unit_price'])),
                    weighed=item.get('weighed', False),
                    quantity=Decimal(str(item['quantity'])),
                    member_eligible=item.get('member_eligible', False),
                    gst_rate=Decimal(str(item.get('gst_rate', 18.0))),
                )

                # Deduct Stock from InventoryBatch
                try:
                    InventoryBatch.objects.filter(id=item['pid']).update(
                        stock_level=F('stock_level') - Decimal(str(item['quantity']))
                    )
                except Exception:
                    pass

            # Create tenders
            for tender in tenders:
                tender_method = tender['method']
                tender_amount = Decimal(str(tender['amount']))
                
                PosTender.objects.create(
                    transaction=txn,
                    method=tender_method,
                    amount=tender_amount,
                )
                
                # If tender is Wallet and customer is registered with a user, deduct from their actual wallet balance
                if tender_method.lower() == 'wallet' and customer and customer.user and tender_amount > 0:
                    try:
                        wallet_obj = Wallet.objects.select_for_update().get(user=customer.user)
                        if wallet_obj.balance < tender_amount:
                            raise serializers.ValidationError(
                                f"Insufficient customer wallet balance. Required: ₹{tender_amount}, Available: ₹{wallet_obj.balance}"
                            )
                        
                        balance_before = wallet_obj.balance
                        wallet_obj.balance -= tender_amount
                        wallet_obj.save(update_fields=['balance'])
                        
                        # Create wallet transaction record for ledger consistency
                        from apps.wallet.models import WalletTransaction
                        WalletTransaction.objects.create(
                            wallet=wallet_obj,
                            amount=-tender_amount,
                            reason='ORDER_PAYMENT',
                            balance_before=balance_before,
                            balance_after=wallet_obj.balance,
                            notes=f"POS walk-in purchase (Txn Ref: {txn.id})"
                        )
                    except Wallet.DoesNotExist:
                        raise serializers.ValidationError(
                            f"Customer phone {customer.phone} is registered, but has no wallet to deduct ₹{tender_amount} from."
                        )

            # Update shift totals
            shift.txn_count += 1
            shift.total_sales += txn.total
            if method == 'Cash' or any(t['method'] == 'Cash' for t in tenders):
                cash_amount = sum(
                    Decimal(str(t['amount'])) for t in tenders if t['method'] == 'Cash'
                )
                shift.cash_sales += cash_amount
            # Track rounding loss
            if rounding_adjustment > 0:
                shift.rounding_loss += rounding_adjustment
            shift.save()

        return Response(PosTransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class PosWastageView(APIView):
    """
    POST /api/pos/wastage/ — Log wastage
    GET  /api/pos/wastage/ — Get wastage for current shift
    """
    permission_classes = [IsPosOperator]

    def get(self, request):
        try:
            employee = request.user.pos_employee
        except PosEmployee.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        shift = PosShift.objects.filter(employee=employee).order_by('-started_at').first()
        if not shift:
            return Response([], status=status.HTTP_200_OK)

        logs = shift.wastage_logs.all()
        serializer = PosWastageSerializer(logs, many=True)
        return Response(serializer.data)

    def post(self, request):
        try:
            employee = request.user.pos_employee
        except PosEmployee.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        shift = PosShift.objects.filter(employee=employee, is_open=True).first()
        if not shift:
            return Response({'error': 'No open shift'}, status=status.HTTP_400_BAD_REQUEST)

        pid = request.data.get('pid', '')
        name = request.data.get('name', '')
        quantity = request.data.get('quantity', 0)
        weighed = request.data.get('weighed', False)
        unit_price = request.data.get('unit_price', 0)
        reason = request.data.get('reason', 'Spoiled')

        log = PosWastageLog.objects.create(
            shift=shift,
            pid=pid,
            name=name,
            quantity=Decimal(str(quantity)),
            weighed=weighed,
            unit_price=Decimal(str(unit_price)),
            reason=reason,
        )

        # Deduct Stock for wastage
        try:
            InventoryBatch.objects.filter(id=pid).update(
                stock_level=F('stock_level') - Decimal(str(quantity))
            )
        except Exception:
            pass

        return Response({
            'message': 'Wastage logged',
            'id': str(log.id),
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class PosOrderLookupView(APIView):
    """
    GET /api/pos/orders/lookup/
    Look up a past transaction by receipt_id or list transactions by phone.
    Query params:
      - receipt_id: UUID (or prefix) of a single transaction
      - phone: customer phone number to list their last 5 transactions
    """
    permission_classes = [IsPosOperator]

    def get(self, request):
        receipt_id = request.query_params.get('receipt_id', '').strip()
        phone = request.query_params.get('phone', '').strip()

        # Phone-based history search (no-receipt returns)
        if phone:
            customer = PosCustomer.objects.filter(phone=phone).first()
            if not customer:
                return Response(
                    {'error': 'Customer not found'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            txns = PosTransaction.objects.filter(
                customer=customer, transaction_type='SALE'
            ).prefetch_related('items', 'tenders').order_by('-created_at')[:5]
            serializer = PosTransactionSerializer(txns, many=True)
            data = serializer.data
            for item, txn in zip(data, txns):
                item['transaction_type'] = txn.transaction_type
                item['customer_name'] = txn.customer.name if txn.customer else ''
            return Response(data)

        if not receipt_id:
            return Response(
                {'error': 'receipt_id or phone parameter required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Try full UUID first, then fallback to prefix match
            if len(receipt_id) >= 8:
                txn = PosTransaction.objects.prefetch_related('items', 'tenders').filter(id__istartswith=receipt_id).first()
            else:
                txn = PosTransaction.objects.prefetch_related('items', 'tenders').get(id=receipt_id)
            
            if not txn:
                raise PosTransaction.DoesNotExist()
        except (PosTransaction.DoesNotExist, Exception):
            return Response(
                {'error': 'Transaction not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Don't allow looking up RETURN transactions for another return
        if txn.transaction_type == 'RETURN':
            return Response(
                {'error': 'Cannot return a return transaction'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PosTransactionSerializer(txn)
        data = serializer.data
        data['transaction_type'] = txn.transaction_type
        data['customer_name'] = txn.customer.name if txn.customer else ''
        return Response(data)


@method_decorator(csrf_exempt, name='dispatch')
class PosRefundView(APIView):
    """
    POST /api/pos/orders/refund/
    Process a return/refund for a previous transaction.

    Payload:
      {
        "original_transaction_id": "uuid",
        "manager_pin": "1234",
        "items": [{"pid": "...", "quantity": 1.0}],  // items being returned
        "refund_method": "Cash"  // how the refund is paid out
      }

    Business rules:
      - Manager PIN must match an employee with is_manager=True
      - Creates a RETURN PosTransaction with negative totals
      - Restocks returned items in InventoryBatch
      - Deducts from shift totals
    """
    permission_classes = [IsPosOperator]

    def post(self, request):
        original_id = request.data.get('original_transaction_id', '')
        manager_pin = request.data.get('manager_pin', '')
        return_items = request.data.get('items', [])
        refund_method = request.data.get('refund_method', 'Cash')

        # ── Validate inputs ──
        if not original_id or not manager_pin or not return_items:
            return Response(
                {'error': 'original_transaction_id, manager_pin, and items are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Verify manager PIN ──
        try:
            manager = PosEmployee.objects.get(
                pin=manager_pin, is_manager=True, is_active=True,
            )
        except PosEmployee.DoesNotExist:
            return Response(
                {'error': 'Invalid manager PIN'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Fetch original transaction ──
        try:
            original_txn = PosTransaction.objects.prefetch_related(
                'items', 'tenders'
            ).get(id=original_id, transaction_type='SALE')
        except (PosTransaction.DoesNotExist, Exception):
            return Response(
                {'error': 'Original sale transaction not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Get current employee & shift ──
        try:
            employee = request.user.pos_employee
        except PosEmployee.DoesNotExist:
            return Response(
                {'error': 'Employee not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        shift = PosShift.objects.filter(employee=employee, is_open=True).first()
        if not shift:
            return Response(
                {'error': 'No open shift'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Build return items & calculate refund total ──
        original_items = {item.pid: item for item in original_txn.items.all()}
        refund_subtotal = Decimal('0')
        validated_items = []

        for ri in return_items:
            pid = ri.get('pid', '')
            qty = Decimal(str(ri.get('quantity', 0)))

            if pid not in original_items:
                return Response(
                    {'error': f'Item {pid} not found in original transaction'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            orig_item = original_items[pid]
            if qty > orig_item.quantity:
                return Response(
                    {'error': f'Return quantity for {pid} exceeds original quantity'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item_total = orig_item.unit_price * qty
            refund_subtotal += item_total
            validated_items.append({
                'pid': pid,
                'name': orig_item.name,
                'unit_price': orig_item.unit_price,
                'weighed': orig_item.weighed,
                'quantity': qty,
                'member_eligible': orig_item.member_eligible,
            })

        refund_total = refund_subtotal  # Could apply surcharge reversal if needed

        with transaction.atomic():
            # ── Create RETURN transaction (negative totals) ──
            return_txn = PosTransaction.objects.create(
                shift=shift,
                customer=original_txn.customer,
                transaction_type='RETURN',
                related_transaction=original_txn,
                method=refund_method,
                subtotal=-refund_subtotal,
                member_discount=Decimal('0'),
                surcharge=Decimal('0'),
                total=-refund_total,
            )

            # ── Create return line items ──
            for item in validated_items:
                PosTransactionItem.objects.create(
                    transaction=return_txn,
                    pid=item['pid'],
                    name=item['name'],
                    unit_price=item['unit_price'],
                    weighed=item['weighed'],
                    quantity=item['quantity'],
                    member_eligible=item['member_eligible'],
                )

            # ── Create refund tender ──
            PosTender.objects.create(
                transaction=return_txn,
                method=refund_method,
                amount=-refund_total,
            )

            # ── Restock inventory ──
            for item in validated_items:
                try:
                    InventoryBatch.objects.filter(id=item['pid']).update(
                        stock_level=F('stock_level') + item['quantity']
                    )
                except Exception:
                    pass  # PID may not map directly to a batch ID

            # ── Deduct from shift totals ──
            shift.txn_count += 1
            shift.total_sales -= refund_total
            if refund_method == 'Cash':
                shift.cash_sales -= refund_total
            shift.save()

        result = PosTransactionSerializer(return_txn).data
        result['transaction_type'] = 'RETURN'
        result['original_transaction_id'] = str(original_id)
        result['authorized_by'] = manager.employee_id

        return Response(result, status=status.HTTP_201_CREATED)
