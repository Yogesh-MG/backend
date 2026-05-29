from decimal import Decimal
from rest_framework import serializers
from django.db import transaction
from apps.inventory.models import InventoryBatch
from .models import Order, OrderItem
import re

def parse_weight_in_kg(unit_str: str) -> float:
    """Robust weight parser converting units like 500 g, 1.5 kg, 1 dozen into kg weights."""
    if not unit_str:
        return 1.0
        
    unit_str = unit_str.lower().strip()
    
    # Match standard packaging formats
    match = re.search(r'([\d\.]+)\s*(kg|g|gm|gram|grams|dozen|pcs|pc|unit|units)', unit_str)
    if match:
        val = float(match.group(1))
        unit = match.group(2)
        
        if unit in ['kg']:
            return val
        elif unit in ['g', 'gm', 'gram', 'grams']:
            return val / 1000.0
        elif unit in ['dozen']:
            return val * 1.2  # assume 1 dozen of fruits/eggs weights ~1.2 kg
        elif unit in ['pcs', 'pc', 'unit', 'units']:
            return val * 0.5  # assume 1 item weights ~0.5 kg
            
    match_digits = re.search(r'([\d\.]+)', unit_str)
    if match_digits:
        val = float(match_digits.group(1))
        if 'g' in unit_str or 'gm' in unit_str:
            return val / 1000.0
        return val
        
    return 1.0


def get_organic_impact_data(order, user):
    """Get organic impact data, using prefetched cache when available to avoid N+1 queries."""
    from apps.wallet.models import CustomerImpact
    
    # Use the correct related_name 'impact' (OneToOneField)
    impact = None
    try:
        impact = user.impact
    except CustomerImpact.DoesNotExist:
        impact = None
    
    lifetime = {
        "water": float(impact.total_water) if impact else 0.0,
        "soil": float(impact.total_soil) if impact else 0.0,
        "chemical": float(impact.total_chemical) if impact else 0.0,
        "farmers": float(impact.total_farmer) if impact else 0.0,
        "healthy_orders": impact.total_orders if impact else 0
    }

    return {
        "current_order": {
            "water": float(order.order_water),
            "soil": float(order.order_soil),
            "chemical": float(order.order_chemical),
            "farmers": float(order.order_farmer)
        },
        "lifetime": lifetime,
        "message": "Your healthy choices continue supporting organic farming."
    }

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['batch', 'quantity']

class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list/admin views - minimal nested data."""
    user_name = serializers.CharField(source='user.get_full_name')
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'tracking_id', 'user_name', 'status', 'total', 'delivery_slot', 'created_at', 'items_count']
    
    def get_items_count(self, obj):
        # Uses prefetched cache
        return obj.items.count()

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    organic_impact = serializers.SerializerMethodField(read_only=True)
    # Payment details (write-only, for creating PaymentTransaction)
    # Legacy Razorpay fields
    razorpay_payment_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    razorpay_order_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    razorpay_signature = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # ICICI Eazypay fields
    icici_merchant_tran_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    icici_ref_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    icici_bank_rrn = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Order
        fields = [
            'id', 'tracking_id', 'address_title', 'address_line', 'delivery_slot', 
            'payment_method', 'items', 'subtotal', 'delivery_fee', 'total', 'is_paid',
            'wallet_amount_used', 'remaining_amount', 'organic_impact',
            'razorpay_payment_id', 'razorpay_order_id', 'razorpay_signature',
            'icici_merchant_tran_id', 'icici_ref_id', 'icici_bank_rrn'
        ]
        read_only_fields = ['id', 'tracking_id', 'subtotal', 'delivery_fee', 'total']

    def get_organic_impact(self, obj):
        user = self.context['request'].user if 'request' in self.context else obj.user
        return get_organic_impact_data(obj, user)

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        # Remove fields that might be passed twice (from perform_create or frontend)
        validated_data.pop('subtotal', None)
        validated_data.pop('delivery_fee', None)
        validated_data.pop('total', None)
        is_paid_passed = validated_data.pop('is_paid', False)
        wallet_amount_used_passed = validated_data.pop('wallet_amount_used', Decimal('0.00'))
        remaining_amount_passed = validated_data.pop('remaining_amount', Decimal('0.00'))
        validated_data.pop('member_discount', None)
        validated_data.pop('pride_limit_used', None)
        # Extract payment details
        razorpay_payment_id = validated_data.pop('razorpay_payment_id', None)
        razorpay_order_id = validated_data.pop('razorpay_order_id', None)
        razorpay_signature = validated_data.pop('razorpay_signature', None)
        icici_merchant_tran_id = validated_data.pop('icici_merchant_tran_id', None)
        icici_ref_id = validated_data.pop('icici_ref_id', None)
        icici_bank_rrn = validated_data.pop('icici_bank_rrn', None)
        user = validated_data.pop('user', self.context['request'].user)
        delivery_slot_type = validated_data.get('delivery_slot', 'EXPRESS')

        with transaction.atomic():
            # 1. Calculate Prices on Backend
            subtotal = Decimal('0.00')
            order_items_to_create = []

            for item_data in items_data:
                batch = item_data['batch']
                qty = item_data['quantity']

                # Stock Check
                if batch.stock_level < qty:
                    raise serializers.ValidationError(f"Only {batch.stock_level} units of {batch.variant.product.name} are available.")

                item_price = batch.variant.price
                subtotal += item_price * qty

                # Prepare item for creation (snapshotting)
                order_items_to_create.append({
                    'batch': batch,
                    'product_name': batch.variant.product.name,
                    'price': item_price,
                    'purchase_price': batch.purchase_price,
                    'quantity': qty,
                    'unit': batch.variant.unit
                })

            # 2. Get Delivery Fee from actual slot config (or weight-based charge if out of radius)
            total_weight = 0.0
            for item in order_items_to_create:
                weight_per_unit = parse_weight_in_kg(item['unit'])
                total_weight += weight_per_unit * float(item['quantity'])

            from apps.delivery.models import DeliverySlot, ServiceArea
            
            # Retrieve request coordinates
            request = self.context.get('request')
            latitude = None
            longitude = None
            if request:
                latitude = request.data.get('latitude')
                longitude = request.data.get('longitude')
                
            out_of_radius = False
            
            # Check coordinates
            if latitude and longitude:
                try:
                    lat = float(latitude)
                    lng = float(longitude)
                    out_of_radius = not ServiceArea.is_in_any_active_service_area(lat, lng)
                except (ValueError, TypeError):
                    pass
            # Fallback to default user address
            if not latitude or not longitude:
                default_addr = user.delivery_addresses.filter(is_default=True).first()
                if default_addr and default_addr.latitude and default_addr.longitude:
                    try:
                        lat = float(default_addr.latitude)
                        lng = float(default_addr.longitude)
                        out_of_radius = not ServiceArea.is_in_any_active_service_area(lat, lng)
                    except (ValueError, TypeError):
                        pass

            # Get checkout config for free delivery threshold
            from apps.delivery.models import CheckoutConfig
            checkout_config = CheckoutConfig.get_config()
            free_delivery_threshold = checkout_config.free_delivery_threshold
            
            if out_of_radius:
                # Find standard out-of-radius slot to fetch its weight charge
                oor_slot = DeliverySlot.objects.filter(slot_type='OUT_OF_RADIUS').first()
                weight_charge = Decimal('10.00')  # fallback rate per kg
                if oor_slot and oor_slot.weight_charge > 0:
                    weight_charge = oor_slot.weight_charge
                
                delivery_fee = (Decimal(str(total_weight)) * weight_charge).quantize(Decimal('0.01'))
            else:
                # Standard slot delivery charges
                slot = DeliverySlot.objects.filter(id__iexact=delivery_slot_type).first()
                if not slot:
                    slot = DeliverySlot.objects.filter(slot_type=delivery_slot_type).first()
                
                if slot:
                    # Apply free delivery if subtotal meets threshold
                    delivery_fee = slot.delivery_fee if subtotal < free_delivery_threshold else Decimal('0.00')
                else:
                    delivery_fee = Decimal('25.00') if subtotal < free_delivery_threshold else Decimal('0.00')


            # 3. Apply PRIDE discount limit and credit 10% wallet (if user has PRIDE partnership)
            from apps.wallet.models import Wallet, WalletTransaction
            member_discount = Decimal('0.00')
            pride_limit_used = Decimal('0.00')
            monthly_wallet_credit = Decimal('0.00')
            wallet_credit_balance_before = Decimal('0.00')
            wallet_credit_balance_after = Decimal('0.00')
            wallet_for_credit = None
            
            try:
                wallet_for_credit = Wallet.objects.select_for_update().get(user=user)
                has_partnership = hasattr(user, 'partnership') and user.partnership and not user.partnership.refund_requested
                if has_partnership and wallet_for_credit.accumulated_pride_limit > 0:
                    # How much MRP can be discounted and get wallet credit?
                    discountable_mrp = min(subtotal, wallet_for_credit.accumulated_pride_limit)
                    member_discount = (discountable_mrp * Decimal('0.30')).quantize(Decimal('0.01'))
                    pride_limit_used = discountable_mrp
                    
                    # Credit 10% of the purchase amount (within tier limit) to wallet
                    monthly_wallet_credit = (discountable_mrp * Decimal('0.10')).quantize(Decimal('0.01'))
                    wallet_credit_balance_before = wallet_for_credit.balance
                    wallet_for_credit.balance += monthly_wallet_credit
                    wallet_credit_balance_after = wallet_for_credit.balance
                    
                    # Deduct the MRP value that got discounted from the limit
                    wallet_for_credit.accumulated_pride_limit -= discountable_mrp
                    wallet_for_credit.save(update_fields=['accumulated_pride_limit', 'balance'])
            except Wallet.DoesNotExist:
                pass

            total = subtotal + delivery_fee - member_discount

            # 4. Validate COD availability based on backend config
            payment_method = validated_data.get('payment_method', 'UPI')
            
            # Check if COD is enabled in backend config
            from apps.delivery.models import CheckoutConfig
            checkout_config = CheckoutConfig.get_config()
            
            if payment_method == 'COD' and not checkout_config.cod_enabled:
                raise serializers.ValidationError("Cash on Delivery is currently not available. Please choose another payment method.")
            
            is_paid = is_paid_passed or (payment_method == 'WALLET')

            wallet_to_deduct = Decimal('0.00')
            if payment_method == 'WALLET':
                wallet_to_deduct = total
            elif payment_method in ['WALLET_UPI', 'WALLET_CARD']:
                wallet_to_deduct = wallet_amount_used_passed

            deducted_balance_before = None
            deducted_balance_after = None
            wallet_obj = None

            if wallet_to_deduct > 0:
                try:
                    wallet_obj = Wallet.objects.select_for_update().get(user=user)
                    if wallet_obj.balance < wallet_to_deduct:
                        raise serializers.ValidationError(f"Insufficient wallet balance. Required: ₹{wallet_to_deduct}, Available: ₹{wallet_obj.balance}")
                    
                    # Deduct balance atomically
                    deducted_balance_before = wallet_obj.balance
                    wallet_obj.balance -= wallet_to_deduct
                    wallet_obj.save(update_fields=['balance'])
                    deducted_balance_after = wallet_obj.balance
                    wallet_amount_used = wallet_to_deduct
                except Wallet.DoesNotExist:
                    raise serializers.ValidationError("No wallet found for this user. Please top up first.")
            else:
                wallet_amount_used = Decimal('0.00')

            # 5. Create the Order with calculated values
            order = Order.objects.create(
                user=user,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                total=total,
                member_discount=member_discount,
                pride_limit_used=pride_limit_used,
                wallet_amount_used=wallet_amount_used,
                remaining_amount=total - wallet_amount_used,
                is_paid=is_paid,
                status='CONFIRMED',
                payment_status='COMPLETED' if is_paid else 'PENDING',
                **validated_data
            )

            # Link/Create the wallet transaction record directly with the order
            if wallet_to_deduct > 0 and wallet_obj:
                WalletTransaction.objects.create(
                    wallet=wallet_obj,
                    amount=-wallet_to_deduct,
                    reason='ORDER_PAYMENT',
                    balance_before=deducted_balance_before,
                    balance_after=deducted_balance_after,
                    related_order=order,
                    notes=f"Wallet split payment for order {order.tracking_id}"
                )
            
            # Create wallet transaction for monthly credit (10% of purchase within tier limit)
            if monthly_wallet_credit > 0 and wallet_for_credit:
                WalletTransaction.objects.create(
                    wallet=wallet_for_credit,
                    amount=monthly_wallet_credit,
                    reason='MONTHLY_CREDIT',
                    balance_before=wallet_credit_balance_before,
                    balance_after=wallet_credit_balance_after,
                    related_order=order,
                    notes=f"10% credit on ₹{pride_limit_used} purchase (within tier limit)"
                )

            # 6. Create items, deduct stock, and calculate organic impact
            order_water = Decimal('0.00')
            order_soil = Decimal('0.00')
            order_chemical = Decimal('0.00')
            order_farmer = Decimal('0.00')

            for item in order_items_to_create:
                batch = item.pop('batch')
                qty = item['quantity']
                
                batch.stock_level -= qty
                batch.save()
                
                # Dynamic organic impact calculation
                product = batch.variant.product
                order_water += product.water_score * qty
                order_soil += product.soil_score * qty
                order_chemical += product.chemical_score * qty
                order_farmer += product.farmer_score * qty
                
                OrderItem.objects.create(order=order, batch=batch, **item)

            # Update the order with calculated impact scores
            order.order_water = order_water
            order.order_soil = order_soil
            order.order_chemical = order_chemical
            order.order_farmer = order_farmer
            order.save(update_fields=['order_water', 'order_soil', 'order_chemical', 'order_farmer'])

            # Update or create customer lifetime impact record
            from apps.wallet.models import CustomerImpact
            impact, _ = CustomerImpact.objects.get_or_create(user=user)
            impact.total_water += order_water
            impact.total_soil += order_soil
            impact.total_chemical += order_chemical
            impact.total_farmer += order_farmer
            impact.total_orders += 1
            impact.save()

            # Create PaymentTransaction for Razorpay payments
            if is_paid and razorpay_payment_id and razorpay_order_id:
                from apps.payment.models import PaymentTransaction
                PaymentTransaction.objects.create(
                    order=order,
                    provider='RAZORPAY',
                    razorpay_payment_id=razorpay_payment_id,
                    razorpay_order_id=razorpay_order_id,
                    razorpay_signature=razorpay_signature or '',
                    amount=order.total - wallet_amount_used,  # Amount paid via Razorpay
                    currency='INR',
                    status='COMPLETED'
                )
            
            # Create PaymentTransaction for ICICI payments
            if is_paid and icici_merchant_tran_id:
                from apps.payment.models import PaymentTransaction
                PaymentTransaction.objects.create(
                    order=order,
                    provider='ICICI',
                    icici_merchant_tran_id=icici_merchant_tran_id,
                    icici_ref_id=icici_ref_id or '',
                    icici_bank_rrn=icici_bank_rrn or '',
                    amount=order.total - wallet_amount_used,  # Amount paid via ICICI
                    currency='INR',
                    status='COMPLETED'
                )

            return order

class OrderDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    organic_impact = serializers.SerializerMethodField(read_only=True)
    amount_due = serializers.SerializerMethodField()
    additional_payment_required = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'

    def get_amount_due(self, obj):
        """Compute the difference between order total and total paid amount."""
        total_paid = obj.wallet_amount_used or Decimal('0')
        # Include completed payment transaction amount if exists
        try:
            pt = obj.payment_transaction
            if pt and pt.status == 'COMPLETED':
                total_paid += pt.amount
        except Exception:
            pass
        due = obj.total - total_paid
        return float(max(Decimal('0'), due))

    def get_additional_payment_required(self, obj):
        """Returns True if the order has been modified and needs additional payment."""
        if obj.payment_status != 'COMPLETED':
            return False
        if obj.status in ('CANCELLED', 'DELIVERED'):
            return False
        amount_due = self.get_amount_due(obj)
        return amount_due > 0.05

    def get_organic_impact(self, obj):
        user = self.context['request'].user if 'request' in self.context else obj.user
        return get_organic_impact_data(obj, user)

    def get_items(self, obj):
        from apps.inventory.serializers import InventoryBatchSerializer
        # Use prefetched items if available (from OrderViewSet queryset), otherwise fetch with select_related
        if hasattr(obj, '_prefetched_objects_cache') and 'items' in obj._prefetched_objects_cache:
            items = obj._prefetched_objects_cache['items']
        else:
            items = obj.items.select_related(
                'batch', 
                'batch__variant', 
                'batch__variant__product',
                'batch__variant__product__category',
                'batch__farmer',
                'batch__farmer__user'
            ).all()
        return [
            {
                "id": i.id,
                "batch": InventoryBatchSerializer(i.batch).data if i.batch else None,
                "product_name": i.product_name,
                "price": float(i.price),
                "quantity": i.quantity,
                "unit": i.unit,
                "total": float(i.price * i.quantity)
            } for i in items
        ]
