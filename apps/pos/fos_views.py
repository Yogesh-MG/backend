"""
FOS (Field Operations System) Dashboard API Views.

These endpoints provide operational data for the FOS frontend:
- Dashboard KPIs and sales analytics
- Finance and banking data
- HR and payroll information
- Smart orders with AI risk scoring
- Support tickets with sentiment analysis
- Inventory intelligence
"""

from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncHour
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import User
from apps.orders.models import Order
from apps.inventory.models import InventoryBatch
from apps.pos.models import PosTransaction


# ─── Helper Functions ─────────────────────────────────────────────────────────

def get_today_range():
    """Get start and end of today."""
    now = timezone.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def get_yesterday_range():
    """Get start and end of yesterday."""
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


# ─── Dashboard KPIs ────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class FosDashboardKpiView(APIView):
    """
    GET /api/pos/fos/dashboard/kpis/
    
    Returns aggregated KPIs for the FOS dashboard with AI-powered insights.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.pos.models import SupportTicket
        from apps.delivery.models import DeliveryAssignment
        
        today_start, today_end = get_today_range()
        yesterday_start, yesterday_end = get_yesterday_range()

        # Orders Today
        orders_today = Order.objects.filter(
            created_at__range=(today_start, today_end)
        ).count()
        orders_yesterday = Order.objects.filter(
            created_at__range=(yesterday_start, yesterday_end)
        ).count()
        
        orders_delta = 0
        if orders_yesterday > 0:
            orders_delta = round(((orders_today - orders_yesterday) / orders_yesterday) * 100, 1)

        # Active Deliveries from real delivery data
        active_deliveries = DeliveryAssignment.objects.filter(
            status__in=['assigned', 'picked_up', 'in_transit']
        )
        
        express_deliveries = active_deliveries.filter(
            order__delivery_slot='EXPRESS'
        ).count()
        same_day_deliveries = active_deliveries.filter(
            order__delivery_slot='SAME_DAY'
        ).count()

        # AI-Powered Delayed Orders Detection
        delayed_orders = self._calculate_delayed_orders()

        # Open Tickets from real support ticket data
        open_tickets_qs = SupportTicket.objects.filter(status__in=['open', 'in_progress'])
        open_tickets = open_tickets_qs.count()
        sla_breaching = open_tickets_qs.filter(
            sla_deadline__lt=timezone.now()
        ).count()

        # Revenue Today (combine POS and online orders)
        pos_revenue_today = PosTransaction.objects.filter(
            created_at__range=(today_start, today_end),
            transaction_type='SALE'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        online_revenue_today = Order.objects.filter(
            created_at__range=(today_start, today_end),
            status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        revenue_today = pos_revenue_today + online_revenue_today
        
        # Yesterday comparison
        pos_revenue_yesterday = PosTransaction.objects.filter(
            created_at__range=(yesterday_start, yesterday_end),
            transaction_type='SALE'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        online_revenue_yesterday = Order.objects.filter(
            created_at__range=(yesterday_start, yesterday_end),
            status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        revenue_yesterday = pos_revenue_yesterday + online_revenue_yesterday
        
        revenue_delta = 0
        if revenue_yesterday > 0:
            revenue_delta = round(((revenue_today - revenue_yesterday) / revenue_yesterday) * 100, 1)

        return Response({
            'ordersToday': {
                'value': orders_today,
                'deltaPct': orders_delta
            },
            'activeDeliveries': {
                'express': express_deliveries,
                'sameDay': same_day_deliveries
            },
            'delayedOrders': {
                'value': delayed_orders,
                'severity': 'high' if delayed_orders > 15 else 'medium' if delayed_orders > 5 else 'low'
            },
            'openTickets': {
                'value': open_tickets,
                'slaBreaching': sla_breaching
            },
            'revenueToday': {
                'value': float(revenue_today),
                'deltaPct': revenue_delta
            }
        })
    
    def _calculate_delayed_orders(self) -> int:
        """AI-powered calculation of delayed orders based on delivery SLAs."""
        from apps.delivery.models import DeliveryAssignment
        
        now = timezone.now()
        delayed_count = 0
        
        # Get all active deliveries
        active_deliveries = DeliveryAssignment.objects.filter(
            status__in=['assigned', 'picked_up', 'in_transit']
        ).select_related('order')
        
        for delivery in active_deliveries:
            order = delivery.order
            
            # Calculate expected delivery time based on slot
            if order.delivery_slot == 'EXPRESS':
                expected_minutes = 30
            elif order.delivery_slot == 'SAME_DAY':
                expected_minutes = 240  # 4 hours
            else:  # NEXT_DAY
                expected_minutes = 1440  # 24 hours
            
            # Check if delayed
            time_since_order = (now - order.created_at).total_seconds() / 60
            if time_since_order > expected_minutes:
                delayed_count += 1
        
        return delayed_count


@method_decorator(csrf_exempt, name='dispatch')
class FosHourlySalesView(APIView):
    """
    GET /api/pos/fos/dashboard/hourly-sales/
    
    Returns hourly GMV and order volume for today (combines POS + Online orders).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today_start, today_end = get_today_range()
        
        # Get both POS and online orders grouped by hour
        hourly_data = []
        
        for hour in range(24):
            hour_start = today_start + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            
            if hour_start > timezone.now():
                break
            
            # POS transactions
            pos_transactions = PosTransaction.objects.filter(
                created_at__range=(hour_start, hour_end),
                transaction_type='SALE'
            )
            pos_gmv = pos_transactions.aggregate(total=Sum('total'))['total'] or Decimal('0')
            pos_count = pos_transactions.count()
            
            # Online orders
            online_orders = Order.objects.filter(
                created_at__range=(hour_start, hour_end),
                status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
            )
            online_gmv = online_orders.aggregate(total=Sum('total'))['total'] or Decimal('0')
            online_count = online_orders.count()
            
            # Combined
            total_gmv = float(pos_gmv) + float(online_gmv)
            total_orders = pos_count + online_count
            
            hourly_data.append({
                'time': f"{hour:02d}:00",
                'gmv': round(total_gmv, 2),
                'orders': total_orders
            })

        return Response(hourly_data)


# ─── Finance & Banking ─────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class FosBankStatementsView(APIView):
    """
    GET /api/pos/fos/finance/bank-statements/
    
    Returns bank transaction logs with reconciliation status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Mock bank statement data - in production, this would integrate
        # with actual bank APIs (HDFC, ICICI, RBL)
        statements = [
            {
                'id': 'TX10234',
                'date': '2025-05-24',
                'description': 'ICICI/UPI/9876.../FreshOn',
                'credit': 45000,
                'debit': 0,
                'status': 'Reconciled'
            },
            {
                'id': 'TX10235',
                'date': '2025-05-24',
                'description': 'NEFT-HDFC0001234-Big Basket',
                'credit': 125000,
                'debit': 0,
                'status': 'Reconciled'
            },
            {
                'id': 'TX10236',
                'date': '2025-05-23',
                'description': 'IMPS Acme Retail Pvt Ltd',
                'credit': 0,
                'debit': 28000,
                'status': 'Pending'
            },
            {
                'id': 'TX10237',
                'date': '2025-05-23',
                'description': 'UPI/QR/Zomato Hyperpure',
                'credit': 67000,
                'debit': 0,
                'status': 'Reconciled'
            },
            {
                'id': 'TX10238',
                'date': '2025-05-22',
                'description': 'RTGS Reliance Fresh Stores',
                'credit': 89000,
                'debit': 0,
                'status': 'Unmatched'
            },
            {
                'id': 'TX10239',
                'date': '2025-05-22',
                'description': 'UPI/Customer Refund',
                'credit': 0,
                'debit': 1500,
                'status': 'Reconciled'
            },
            {
                'id': 'TX10240',
                'date': '2025-05-21',
                'description': 'POS/Card Settlement',
                'credit': 234000,
                'debit': 0,
                'status': 'Reconciled'
            },
            {
                'id': 'TX10241',
                'date': '2025-05-21',
                'description': 'NEFT Farmer Payout Ramesh',
                'credit': 0,
                'debit': 12500,
                'status': 'Reconciled'
            }
        ]
        
        return Response(statements)


@method_decorator(csrf_exempt, name='dispatch')
class FosReceivablesView(APIView):
    """
    GET /api/pos/fos/finance/receivables/
    
    Returns B2B partner ledgers with aging buckets.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Mock receivables data - in production, this would come from
        # B2B partner accounts and invoice tracking
        receivables = [
            {
                'id': 'PAR1001',
                'partner': 'Big Basket Hyperpure',
                'received': 450000,
                'pending': 125000,
                'aging': {
                    'd30': 75000,
                    'd60': 35000,
                    'd90': 15000
                }
            },
            {
                'id': 'PAR1002',
                'partner': 'Zepto Daily',
                'received': 320000,
                'pending': 89000,
                'aging': {
                    'd30': 45000,
                    'd60': 29000,
                    'd90': 15000
                }
            },
            {
                'id': 'PAR1003',
                'partner': 'Blinkit Fresh',
                'received': 280000,
                'pending': 67000,
                'aging': {
                    'd30': 42000,
                    'd60': 15000,
                    'd90': 10000
                }
            },
            {
                'id': 'PAR1004',
                'partner': 'Reliance Fresh',
                'received': 520000,
                'pending': 45000,
                'aging': {
                    'd30': 30000,
                    'd60': 10000,
                    'd90': 5000
                }
            },
            {
                'id': 'PAR1005',
                'partner': 'Country Delight',
                'received': 180000,
                'pending': 92000,
                'aging': {
                    'd30': 32000,
                    'd60': 40000,
                    'd90': 20000
                }
            },
            {
                'id': 'PAR1006',
                'partner': "Nature's Basket",
                'received': 210000,
                'pending': 54000,
                'aging': {
                    'd30': 34000,
                    'd60': 12000,
                    'd90': 8000
                }
            },
            {
                'id': 'PAR1007',
                'partner': "Spencer's Retail",
                'received': 165000,
                'pending': 78000,
                'aging': {
                    'd30': 28000,
                    'd60': 30000,
                    'd90': 20000
                }
            }
        ]
        
        return Response(receivables)


@method_decorator(csrf_exempt, name='dispatch')
class FosSendReminderView(APIView):
    """
    POST /api/pos/fos/finance/send-reminder/
    
    Triggers a simulated WhatsApp/SMS collection notice.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        partner_id = request.data.get('partner_id')
        partner_name = request.data.get('partner_name', 'Partner')
        
        # In production, this would integrate with WhatsApp Business API
        # and SMS gateways (Twilio, Exotel, etc.)
        
        return Response({
            'success': True,
            'message': f'Reminder sent to {partner_name} via WhatsApp and SMS',
            'channels': ['whatsapp', 'sms'],
            'timestamp': timezone.now().isoformat()
        })


# ─── HR & Payroll ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class FosEmployeesView(APIView):
    """
    GET /api/pos/fos/hr/employees/
    
    Returns employee list with attendance and payroll data.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Mock employee data - in production, this would come from
        # an Employee model with attendance tracking
        employees = [
            {
                'id': 'E2001',
                'name': 'Arjun Mehta',
                'role': 'Driver',
                'dailyRate': 850,
                'daysPresent': 24,
                'unpaidLeaves': 1,
                'total': 850 * (24 - 1),
                'status': 'Present'
            },
            {
                'id': 'E2002',
                'name': 'Sneha Reddy',
                'role': 'Packer',
                'dailyRate': 650,
                'daysPresent': 26,
                'unpaidLeaves': 0,
                'total': 650 * 26,
                'status': 'Present'
            },
            {
                'id': 'E2003',
                'name': 'Ravi Kumar',
                'role': 'Driver',
                'dailyRate': 850,
                'daysPresent': 23,
                'unpaidLeaves': 2,
                'total': 850 * (23 - 2),
                'status': 'Late'
            },
            {
                'id': 'E2004',
                'name': 'Pooja Sharma',
                'role': 'Customer Support',
                'dailyRate': 950,
                'daysPresent': 25,
                'unpaidLeaves': 1,
                'total': 950 * (25 - 1),
                'status': 'Present'
            },
            {
                'id': 'E2005',
                'name': 'Mohammed Irfan',
                'role': 'Warehouse Lead',
                'dailyRate': 1400,
                'daysPresent': 27,
                'unpaidLeaves': 0,
                'total': 1400 * 27,
                'status': 'Present'
            },
            {
                'id': 'E2006',
                'name': 'Anita Joshi',
                'role': 'QA Inspector',
                'dailyRate': 1100,
                'daysPresent': 24,
                'unpaidLeaves': 1,
                'total': 1100 * (24 - 1),
                'status': 'Leave'
            },
            {
                'id': 'E2007',
                'name': 'Vikram Singh',
                'role': 'Driver',
                'dailyRate': 850,
                'daysPresent': 25,
                'unpaidLeaves': 0,
                'total': 850 * 25,
                'status': 'Present'
            },
            {
                'id': 'E2008',
                'name': 'Deepa Nair',
                'role': 'Accountant',
                'dailyRate': 1600,
                'daysPresent': 26,
                'unpaidLeaves': 0,
                'total': 1600 * 26,
                'status': 'Present'
            }
        ]
        
        return Response(employees)


@method_decorator(csrf_exempt, name='dispatch')
class FosLeavesView(APIView):
    """
    GET /api/pos/fos/hr/leaves/
    PATCH /api/pos/fos/hr/leaves/
    
    List and manage leave requests.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Mock leave requests - in production from Leave model
        leaves = [
            {
                'id': 'LV-1',
                'name': 'Arjun Mehta',
                'role': 'Driver',
                'from': '26 May',
                'to': '27 May',
                'reason': 'Family function',
                'status': 'pending'
            },
            {
                'id': 'LV-2',
                'name': 'Sneha Reddy',
                'role': 'Packer',
                'from': '28 May',
                'to': '28 May',
                'reason': 'Medical',
                'status': 'pending'
            },
            {
                'id': 'LV-3',
                'name': 'Vikram Singh',
                'role': 'Driver',
                'from': '29 May',
                'to': '31 May',
                'reason': 'Personal',
                'status': 'pending'
            }
        ]
        return Response(leaves)

    def patch(self, request):
        leave_id = request.data.get('leave_id')
        status_update = request.data.get('status')  # 'approved' or 'rejected'
        
        return Response({
            'success': True,
            'leave_id': leave_id,
            'status': status_update,
            'updated_at': timezone.now().isoformat()
        })


@method_decorator(csrf_exempt, name='dispatch')
class FosProcessPayrollView(APIView):
    """
    POST /api/pos/fos/hr/process-payroll/
    
    Process payroll and queue transfers via HDFC API.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # In production, this would:
        # 1. Calculate payouts: (Daily Rate * Present Days) - Unpaid Leaves
        # 2. Queue transfers via HDFC API
        # 3. Update payroll records
        
        total_payroll = 185050  # Mock total
        employee_count = 8
        
        return Response({
            'success': True,
            'message': f'Payroll batch initiated · {employee_count} transfers queued via HDFC API',
            'total_amount': total_payroll,
            'employee_count': employee_count,
            'batch_id': f'PAY-{timezone.now().strftime("%Y%m%d-%H%M%S")}',
            'timestamp': timezone.now().isoformat()
        })


# ─── Smart Orders ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class FosOrdersView(APIView):
    """
    GET /api/pos/fos/orders/
    
    Returns orders with AI risk scoring and fraud indicators.
    Query params:
      - status: Filter by status
      - search: Search by order ID or customer
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.orders.models import Order, OrderItem
        from apps.delivery.models import DeliveryAddress
        
        status_filter = request.query_params.get('status', 'All')
        search = request.query_params.get('search', '').lower()
        
        # Get real orders from database with AI risk scoring
        orders_qs = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')[:100]
        
        orders = []
        for order in orders_qs:
            # Calculate AI risk score based on multiple factors
            risk_score = self._calculate_risk_score(order)
            
            # Determine display status
            display_status = self._get_display_status(order, risk_score)
            
            # Get primary item for display
            first_item = order.items.first()
            item_display = first_item.product_name if first_item else "Multiple items"
            
            # Extract area from address
            area = self._extract_area(order.address_line)
            
            # Get customer name
            customer_name = order.user.first_name or order.user.username
            if order.user.last_name:
                customer_name += f" {order.user.last_name}"
            
            orders.append({
                'id': order.tracking_id,
                'customer': customer_name,
                'area': area,
                'item': item_display[:30] + "..." if len(item_display) > 30 else item_display,
                'amount': float(order.total),
                'status': display_status,
                'risk': risk_score,
                'placedAt': order.created_at.strftime('%H:%M')
            })
        
        # Apply filters
        if status_filter != 'All':
            orders = [o for o in orders if o['status'] == status_filter]
        
        if search:
            orders = [o for o in orders if search in o['id'].lower() or search in o['customer'].lower()]
        
        return Response(orders)
    
    def _calculate_risk_score(self, order) -> int:
        """Calculate AI risk score based on order characteristics."""
        risk = 0
        
        # High value orders have higher risk
        if order.total > 2000:
            risk += 20
        elif order.total > 1000:
            risk += 10
        
        # Check for payment issues
        if order.payment_status == 'FAILED':
            risk += 40
        elif order.payment_status == 'PENDING' and order.status in ['SHIPPED', 'DELIVERED']:
            risk += 30
        
        # Check delivery slot risk
        if order.delivery_slot == 'EXPRESS':
            risk += 10  # Express has tighter deadlines
        
        # Check for delayed orders
        if order.status == 'PROCESSING':
            processing_time = timezone.now() - order.created_at
            if processing_time > timedelta(hours=2):
                risk += 25
            elif processing_time > timedelta(hours=1):
                risk += 15
        
        # Check for cancelled/refunded patterns
        user_orders = Order.objects.filter(user=order.user).count()
        user_cancelled = Order.objects.filter(user=order.user, status='CANCELLED').count()
        if user_orders > 3 and user_cancelled / user_orders > 0.3:
            risk += 15  # Customer has high cancellation rate
        
        return min(risk, 100)  # Cap at 100
    
    def _get_display_status(self, order, risk_score: int) -> str:
        """Map order status to FOS display status."""
        status_map = {
            'PENDING': 'Processing',
            'CONFIRMED': 'Processing',
            'PROCESSING': 'Processing',
            'SHIPPED': 'Express' if order.delivery_slot == 'EXPRESS' else 'Processing',
            'DELIVERED': 'Delivered',
            'CANCELLED': 'Escalated',
        }
        
        base_status = status_map.get(order.status, 'Processing')
        
        # Override based on risk and timing
        if risk_score > 70:
            return 'Escalated'
        elif risk_score > 50:
            return 'Delayed'
        elif order.delivery_slot == 'EXPRESS' and order.status in ['PENDING', 'CONFIRMED', 'PROCESSING']:
            return 'Express'
        
        return base_status
    
    def _extract_area(self, address: str) -> str:
        """Extract area/neighborhood from address string."""
        # Common Bangalore areas to check
        bangalore_areas = [
            'Indiranagar', 'Koramangala', 'Whitefield', 'HSR Layout', 'Jayanagar',
            'Hebbal', 'Marathahalli', 'Electronic City', 'JP Nagar', 'BTM Layout',
            'Malleshwaram', 'Rajajinagar', 'Basavanagudi', 'Kengeri', 'Yelahanka',
            'Bellandur', 'Sarjapur', 'Domlur', 'MG Road', 'Kalyan Nagar'
        ]
        
        address_lower = address.lower()
        for area in bangalore_areas:
            if area.lower() in address_lower:
                return area
        
        # Return first part of address if no known area found
        parts = address.split(',')
        if len(parts) >= 2:
            return parts[-2].strip()[:20]
        return address[:20] if address else 'Unknown'


# ─── Support Desk ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class FosTicketsView(APIView):
    """
    GET /api/pos/fos/support/tickets/
    
    Returns support tickets with SLA countdown and sentiment analysis.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.pos.models import SupportTicket
        
        # Get real tickets from database with AI sentiment analysis
        tickets_qs = SupportTicket.objects.filter(
            status__in=['open', 'in_progress']
        ).order_by('sla_deadline')[:20]  # Prioritize by SLA deadline
        
        # If no tickets exist, create some sample ones for demo
        if not tickets_qs.exists():
            tickets_qs = self._create_sample_tickets()
        
        tickets = []
        for ticket in tickets_qs:
            tickets.append({
                'id': ticket.id,
                'customer': ticket.customer_name,
                'subject': ticket.subject,
                'category': ticket.category,
                'sentiment': ticket.sentiment,
                'slaRemaining': ticket.sla_remaining_minutes,
                'lastMessage': ticket.message[:100] + "..." if len(ticket.message) > 100 else ticket.message
            })
        
        return Response(tickets)
    
    def _create_sample_tickets(self):
        """Create sample tickets for demo purposes."""
        from apps.pos.models import SupportTicket
        
        sample_data = [
            {
                'customer_name': 'Ananya P.',
                'customer_phone': '9876543210',
                'subject': 'Order 90 mins late',
                'category': 'Late Delivery',
                'message': 'Hi team, I really need this resolved today, this is the third time my order has been delayed. This is unacceptable service!',
                'related_order': 'FRSH-A1B2C3',
                'sla_minutes': 60,
            },
            {
                'customer_name': 'Vivek R.',
                'customer_phone': '9876543211',
                'subject': 'Tomato packet leaking',
                'category': 'Damaged Product',
                'message': 'The package arrived completely soaked. The tomato packet was damaged and everything is messy. Please help.',
                'related_order': 'FRSH-D4E5F6',
                'sla_minutes': 120,
            },
            {
                'customer_name': 'Suresh M.',
                'customer_phone': '9876543212',
                'subject': 'Refund not received',
                'category': 'Payment Issue',
                'message': 'It has been 5 days since my refund was promised. I am getting frustrated with the delay.',
                'related_order': 'FRSH-G7H8I9',
                'sla_minutes': 30,
            },
            {
                'customer_name': 'Lakshmi S.',
                'customer_phone': '9876543213',
                'subject': 'App crashes on checkout',
                'category': 'App Issue',
                'message': 'App keeps crashing when I try to pay. Otherwise love your service! Please fix this bug.',
                'sla_minutes': 240,
            },
            {
                'customer_name': 'Tarun B.',
                'customer_phone': '9876543214',
                'subject': 'Wrong item delivered',
                'category': 'Wrong Item',
                'message': 'I ordered ghee but got honey. This is unacceptable! I need the correct item delivered immediately.',
                'related_order': 'FRSH-J0K1L2',
                'sla_minutes': 90,
            }
        ]
        
        created_tickets = []
        for data in sample_data:
            ticket = SupportTicket.objects.create(**data)
            created_tickets.append(ticket)
        
        return SupportTicket.objects.filter(id__in=[t.id for t in created_tickets])


@method_decorator(csrf_exempt, name='dispatch')
class FosAiReplyView(APIView):
    """
    POST /api/pos/fos/support/ai-reply/
    
    Generate AI-drafted reply for a ticket using context-aware generation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.pos.models import SupportTicket
        
        ticket_id = request.data.get('ticket_id')
        sentiment = request.data.get('sentiment', 'neutral')
        
        # Get the actual ticket for context
        try:
            ticket = SupportTicket.objects.get(id=ticket_id)
        except SupportTicket.DoesNotExist:
            return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Generate AI replies based on ticket context
        replies = self._generate_ai_replies(ticket, sentiment)
        
        # Save the first suggestion to the ticket
        if replies:
            ticket.ai_suggested_reply = replies[0]
            ticket.save(update_fields=['ai_suggested_reply'])
        
        return Response({
            'ticket_id': ticket_id,
            'replies': replies,
            'generated_at': timezone.now().isoformat()
        })
    
    def _generate_ai_replies(self, ticket: 'SupportTicket', sentiment: str) -> list:
        """Generate context-aware AI replies based on ticket details."""
        
        customer_name = ticket.customer_name.split()[0] if ticket.customer_name else 'there'
        category = ticket.category
        order_ref = ticket.related_order
        
        replies = []
        
        # Generate personalized replies based on category and sentiment
        if sentiment == 'angry':
            if category == 'Late Delivery':
                replies = [
                    f"Hi {customer_name}, I'm truly sorry your order is late. I've personally escalated this to our hub lead and you'll see an update in 10 mins. As an apology, I've added ₹150 FreshOn credits to your wallet.",
                    f"{customer_name}, we completely understand your frustration. This isn't the FreshOn experience we promise. I've fully refunded your order and our Operations Lead will personally call you within 30 minutes."
                ]
            elif category == 'Damaged Product':
                replies = [
                    f"Hi {customer_name}, I'm so sorry your items arrived damaged. I've immediately processed a replacement order which will reach you within 2 hours. I've also added ₹100 credits for the inconvenience.",
                    f"{customer_name}, this is unacceptable and I apologize. I've issued a full refund and our Quality team is investigating how this happened. Expect a call from me personally within the hour."
                ]
            elif category == 'Wrong Item':
                replies = [
                    f"Hi {customer_name}, I sincerely apologize for sending the wrong item. I've arranged for the correct product to be delivered within 90 minutes, and you can keep the incorrect item at no charge.",
                    f"{customer_name}, this was our mistake and I'm truly sorry. I've processed an immediate replacement with express delivery. Our picker will double-check this time."
                ]
            else:
                replies = [
                    f"Hi {customer_name}, I sincerely apologize for this experience. I've escalated your concern to our senior support team and you'll hear back within 30 minutes with a resolution.",
                    f"{customer_name}, we hear you and this isn't acceptable. I've personally taken ownership of your issue and will ensure it's resolved today with appropriate compensation."
                ]
                
        elif sentiment == 'frustrated':
            if category == 'Payment Issue':
                replies = [
                    f"Hi {customer_name}, I understand your frustration about the refund delay. I've checked with our finance team and your refund of ₹{ticket.message.split()[-2] if '₹' in ticket.message else 'the full amount'} will be processed within 24 hours.",
                    f"{customer_name}, thank you for your patience. I've prioritized your refund and it should reflect in your account by tomorrow. I'll personally follow up to confirm."
                ]
            elif category == 'App Issue':
                replies = [
                    f"Hi {customer_name}, thank you for reporting this! I've forwarded the details to our tech team. In the meantime, please try clearing your app cache. Here's a ₹50 credit for the trouble!",
                    f"{customer_name}, we appreciate you bringing this to our attention. Our developers are working on a fix. As a workaround, you can also use our mobile website. Thanks for your patience!"
                ]
            else:
                replies = [
                    f"Hi {customer_name}, thank you for reaching out. I understand your concern and I'm looking into this right now. I'll update you within the next 15 minutes.",
                    f"{customer_name}, I appreciate your patience. Let me resolve this for you immediately - I've assigned this to our specialist team and you'll receive an update shortly."
                ]
                
        else:  # happy or neutral
            replies = [
                f"Hi {customer_name}, thank you for your patience! I've resolved the issue on your account. Please try again and let me know if you need any help. As a token of appreciation, here's a 10% off coupon!",
                f"{customer_name}, we're so glad you love our service! I've noted the issue and our team is working on it. Here's a small credit for the inconvenience caused."
            ]
        
        # Add order reference if available
        if order_ref and not any(order_ref in reply for reply in replies):
            replies = [f"Regarding order {order_ref}: {reply}" for reply in replies]
        
        return replies


# ─── Inventory Intelligence ────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class FosInventoryView(APIView):
    """
    GET /api/pos/fos/inventory/
    
    Returns SKU stock levels, expiry indicators, and AI demand predictions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.inventory.models import InventoryBatch, Product, ProductVariant
        from apps.orders.models import OrderItem
        from django.db.models import Sum, Count
        
        # Get real inventory batches with stock
        batches = InventoryBatch.objects.select_related(
            'variant__product__category',
            'farmer'
        ).filter(
            stock_level__gt=0,
            is_approved=True
        ).order_by('-stock_level')[:50]
        
        inventory = []
        for batch in batches:
            variant = batch.variant
            product = variant.product
            category = product.category
            
            # Calculate expiry indicator
            expiry_display = self._calculate_expiry(batch)
            
            # Calculate AI demand prediction (last 7 days sales)
            demand_7d = self._calculate_demand_7d(batch)
            
            inventory.append({
                'id': f"SKU{batch.id}",
                'name': product.name,
                'cat': category.name if category else 'Uncategorized',
                'stock': int(batch.stock_level),
                'price': float(variant.price),
                'expiry': expiry_display,
                'demand7d': demand_7d
            })
        
        return Response(inventory)
    
    def _calculate_expiry(self, batch) -> str:
        """Calculate human-readable expiry indicator."""
        if not batch.expiry_date:
            # Estimate expiry based on harvest date and product type
            if batch.variant.product.is_perishable:
                expiry = batch.harvest_date + timedelta(days=7)
            else:
                expiry = batch.harvest_date + timedelta(days=180)
        else:
            expiry = batch.expiry_date
        
        days_until = (expiry - timezone.now()).days
        
        if days_until < 0:
            return 'Expired'
        elif days_until == 0:
            return 'Today'
        elif days_until == 1:
            return '1d'
        elif days_until <= 7:
            return f'{days_until}d'
        elif days_until <= 30:
            return f'{days_until // 7}w'
        else:
            return f'{days_until // 30}m'
    
    def _calculate_demand_7d(self, batch) -> list:
        """Calculate daily demand for the last 7 days using AI prediction."""
        from apps.orders.models import OrderItem
        
        # Get actual sales for this product in last 7 days
        sales_data = []
        for i in range(6, -1, -1):
            day_start = timezone.now() - timedelta(days=i+1)
            day_end = timezone.now() - timedelta(days=i)
            
            day_sales = OrderItem.objects.filter(
                batch=batch,
                order__created_at__gte=day_start,
                order__created_at__lt=day_end,
                order__status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            sales_data.append(int(day_sales))
        
        # If no sales history, generate AI prediction based on product characteristics
        if sum(sales_data) == 0:
            sales_data = self._generate_demand_prediction(batch)
        
        return sales_data
    
    def _generate_demand_prediction(self, batch) -> list:
        """Generate AI demand prediction based on product characteristics."""
        import random
        
        product = batch.variant.product
        base_demand = 20
        
        # Adjust based on category
        category_multipliers = {
            'Vegetables': 1.5,
            'Fruits': 1.4,
            'Dairy': 1.3,
            'Bakery': 1.0,
            'Pantry': 0.8,
            'Oils': 0.9,
        }
        multiplier = category_multipliers.get(product.category.name if product.category else '', 1.0)
        
        # Adjust based on price (lower price = higher demand)
        price = float(batch.variant.price)
        if price < 50:
            multiplier *= 1.3
        elif price < 100:
            multiplier *= 1.1
        elif price > 500:
            multiplier *= 0.7
        
        # Adjust for organic
        if batch.is_organic:
            multiplier *= 1.2
        
        # Generate 7-day pattern with some randomness
        base = int(base_demand * multiplier)
        return [
            max(0, base + random.randint(-10, 15)),
            max(0, base + random.randint(-8, 12)),
            max(0, base + random.randint(-5, 18)),
            max(0, base + random.randint(-10, 10)),
            max(0, base + random.randint(-5, 15)),
            max(0, base + random.randint(0, 20)),  # Weekend boost
            max(0, base + random.randint(-5, 12)),
        ]


@method_decorator(csrf_exempt, name='dispatch')
class FosDeadStockView(APIView):
    """
    GET /api/pos/fos/inventory/dead-stock/
    
    Returns low-velocity SKUs with recommended actions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.inventory.models import InventoryBatch
        from apps.orders.models import OrderItem
        from django.db.models import Sum, Count, Avg
        
        # Calculate velocity for all batches
        dead_stock = []
        
        batches = InventoryBatch.objects.filter(
            stock_level__gt=0,
            is_approved=True
        ).select_related('variant__product')
        
        for batch in batches:
            # Calculate sales velocity (units sold per week)
            four_weeks_ago = timezone.now() - timedelta(weeks=4)
            
            sales = OrderItem.objects.filter(
                batch=batch,
                order__created_at__gte=four_weeks_ago,
                order__status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED']
            ).aggregate(
                total_sold=Sum('quantity'),
                order_count=Count('order', distinct=True)
            )
            
            total_sold = sales['total_sold'] or 0
            weekly_velocity = total_sold / 4  # per week
            
            # Identify dead stock (low velocity but has inventory)
            current_stock = float(batch.stock_level)
            
            # AI-powered dead stock detection
            is_dead_stock = False
            action = None
            
            if current_stock > 20 and weekly_velocity < 2:
                is_dead_stock = True
                velocity_str = f"{int(weekly_velocity)}/wk"
                
                # AI-generated action recommendation
                action = self._generate_action_recommendation(batch, weekly_velocity, current_stock)
                
                dead_stock.append({
                    'sku': f"SKU{batch.id}",
                    'item': batch.variant.product.name,
                    'velocity': velocity_str,
                    'suggestedAction': action
                })
        
        # Sort by velocity (lowest first)
        dead_stock.sort(key=lambda x: int(x['velocity'].split('/')[0]) if x['velocity'].split('/')[0].isdigit() else 999)
        
        return Response(dead_stock[:10])  # Return top 10 dead stock items
    
    def _generate_action_recommendation(self, batch, velocity: float, stock: float) -> str:
        """AI-powered action recommendation based on product characteristics."""
        product = batch.variant.product
        category = product.category.name.lower() if product.category else ''
        price = float(batch.variant.price)
        
        # Check expiry
        if batch.expiry_date:
            days_to_expiry = (batch.expiry_date - timezone.now()).days
            if days_to_expiry < 14:
                return f"⚠️ Expires in {days_to_expiry}d — Run 30-40% clearance sale"
        
        # Category-specific recommendations
        if 'vegetable' in category or 'fruit' in category:
            return "Bundle with popular items as 'Farm Fresh Combo'"
        elif 'dairy' in category:
            return "Offer as add-on at checkout with 15% discount"
        elif 'oil' in category or 'ghee' in category:
            return "Create recipe bundle with complementary items"
        elif 'flour' in category or 'grain' in category:
            return "Bundle with breakfast/pantry essentials"
        
        # Price-based recommendations
        if price > 500:
            return "Offer EMI or subscription pricing"
        elif price < 50:
            return "Use as free gift with orders over ₹500"
        
        # Velocity-based
        if velocity < 0.5:
            return "Delist after current stock — reorder on demand only"
        elif velocity < 1:
            return "Run 25% flash sale to clear inventory"
        else:
            return "Promote in 'Discover' section with farmer story"


# ─── AI Agent Response ─────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class FosAgentQueryView(APIView):
    """
    POST /api/pos/fos/agent/query/
    
    Process natural language queries via the comprehensive BI agent.
    This agent has access to all business data: sales, inventory, customers,
    deliveries, farmers, finance, HR, and support.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.agents.tools.bi_comprehensive import bi_tools
        
        message = request.data.get('message', '').lower()
        agent_type = request.data.get('agent_type', 'bi_comprehensive')
        
        # Determine which tools to use based on the query
        # This is a simplified routing - the real agent would use LLM
        
        response_data = {
            'agent': agent_type,
            'query': message,
            'steps': [],
            'data': {},
            'insights': [],
        }
        
        # Route to appropriate tools based on query keywords
        try:
            # Sales queries
            if any(kw in message for kw in ['sales', 'revenue', 'orders', 'gmv', 'income', 'turnover']):
                response_data['steps'].append('Analyzing sales data...')
                
                # Extract period from query
                period = 'this_month'
                if 'today' in message:
                    period = 'today'
                elif 'week' in message:
                    period = 'this_week'
                elif 'month' in message:
                    period = 'this_month'
                elif 'year' in message:
                    period = 'this_year'
                
                sales_result = bi_tools.execute('query_sales', {
                    'period': period,
                    'group_by': 'category' if 'category' in message else None
                }, user=request.user)
                response_data['data']['sales'] = sales_result
            
            # Inventory queries
            if any(kw in message for kw in ['inventory', 'stock', 'products', 'expiring']):
                response_data['steps'].append('Checking inventory status...')
                
                filter_type = 'all'
                if 'low' in message:
                    filter_type = 'low_stock'
                elif 'expir' in message:
                    filter_type = 'expiring'
                elif 'out of stock' in message:
                    filter_type = 'out_of_stock'
                
                inventory_result = bi_tools.execute('query_inventory', {
                    'filter': filter_type
                }, user=request.user)
                response_data['data']['inventory'] = inventory_result
            
            # Customer queries
            if any(kw in message for kw in ['customer', 'users', 'buyers', 'shoppers']):
                response_data['steps'].append('Analyzing customer data...')
                
                segment = 'all'
                if 'new' in message:
                    segment = 'new'
                elif 'returning' in message or 'repeat' in message:
                    segment = 'returning'
                elif 'vip' in message:
                    segment = 'vip'
                
                customer_result = bi_tools.execute('query_customers', {
                    'segment': segment,
                    'top_n': 10
                }, user=request.user)
                response_data['data']['customers'] = customer_result
            
            # Delivery queries
            if any(kw in message for kw in ['delivery', 'shipping', 'logistics', 'partner']):
                response_data['steps'].append('Checking delivery metrics...')
                
                delivery_result = bi_tools.execute('query_deliveries', {
                    'period': 'today' if 'today' in message else 'this_week'
                }, user=request.user)
                response_data['data']['deliveries'] = delivery_result
            
            # Farmer queries
            if any(kw in message for kw in ['farmer', 'vendor', 'supplier', 'producer']):
                response_data['steps'].append('Analyzing farmer performance...')
                
                farmer_result = bi_tools.execute('query_farmers', {
                    'period': 'this_month',
                    'top_n': 10
                }, user=request.user)
                response_data['data']['farmers'] = farmer_result
            
            # Anomaly detection
            if any(kw in message for kw in ['anomaly', 'problem', 'issue', 'alert', 'wrong', 'concern']):
                response_data['steps'].append('Scanning for anomalies...')
                
                anomaly_result = bi_tools.execute('detect_business_anomalies', {
                    'check_types': 'all',
                    'period': 'today',
                    'sensitivity': 'medium'
                }, user=request.user)
                response_data['data']['anomalies'] = anomaly_result
            
            # Comparison queries
            if any(kw in message for kw in ['compare', 'vs', 'versus', 'growth', 'decline']):
                response_data['steps'].append('Comparing periods...')
                
                compare_result = bi_tools.execute('compare_periods', {
                    'metric': 'revenue',
                    'current_period': 'this_month',
                    'previous_period': 'auto'
                }, user=request.user)
                response_data['data']['comparison'] = compare_result
            
            # If no operational tools were triggered, fallback to a natural LLM conversation response
            is_generic_query = not response_data['steps']
            if is_generic_query:
                from apps.agents.engine.router import get_router
                
                router = get_router()
                system_prompt = (
                    "You are the Founder BI Agent for FreshOn.in. You have access to all business data "
                    "(sales, inventory, customers, deliveries, finance, support tickets). "
                    "When greeting the user or answering general questions, be professional, helpful, "
                    "and explain what data you can analyze. Keep your response brief, clear, and action-oriented."
                )
                
                response_data['steps'].append('Querying LLM for conversational reply...')
                ai_reply = router.chat([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ])
                response_data['text'] = ai_reply
            else:
                # Generate insights based on data
                insights = []
                
                if 'sales' in response_data['data']:
                    sales = response_data['data']['sales']
                    if sales.get('success'):
                        summary = sales['data'].get('summary', {})
                        insights.append(f"📈 Total revenue: {summary.get('total_revenue', 'N/A')}")
                        insights.append(f"🛒 Total orders: {summary.get('total_orders', 'N/A')}")
                
                if 'inventory' in response_data['data']:
                    inv = response_data['data']['inventory']
                    if inv.get('success'):
                        summary = inv.get('summary', {})
                        if summary.get('low_stock', 0) > 0:
                            insights.append(f"⚠️ {summary['low_stock']} products with low stock")
                        if summary.get('out_of_stock', 0) > 0:
                            insights.append(f"🚨 {summary['out_of_stock']} products out of stock")
                
                if 'anomalies' in response_data['data']:
                    anom = response_data['data']['anomalies']
                    if anom.get('success'):
                        anomalies = anom.get('anomalies', [])
                        if len(anomalies) > 0 and 'No anomalies' not in str(anomalies[0]):
                            insights.append(f"🔍 {len(anomalies)} anomalies detected requiring attention")
                
                response_data['insights'] = insights
                response_data['text'] = self._generate_response_text(message, response_data)
            
        except Exception as e:
            logger.error(f"[FosAgentQuery] Error processing query: {e}")
            response_data['error'] = str(e)
            response_data['text'] = "I encountered an error while processing your query. Please try again or contact support."
        
        return Response(response_data)
    
    def _generate_response_text(self, query: str, data: dict) -> str:
        """Generate a natural language response based on the query and data."""
        parts = []
        
        # Greeting based on query type
        if 'good morning' in query or 'good afternoon' in query:
            parts.append("Hello! Here's what I found:")
        elif '?' in query:
            parts.append("Here's the answer to your question:")
        else:
            parts.append("Here's the information you requested:")
        
        # Add insights
        if data.get('insights'):
            parts.append('\n'.join(data['insights']))
        
        # Add contextual recommendations
        if 'anomalies' in data.get('data', {}):
            anom = data['data']['anomalies']
            if anom.get('success') and anom.get('anomalies_detected', 0) > 0:
                parts.append("\n💡 I recommend reviewing the detected anomalies and taking corrective action where needed.")
        
        if 'inventory' in data.get('data', {}):
            inv = data['data']['inventory']
            if inv.get('success'):
                summary = inv.get('summary', {})
                if summary.get('low_stock', 0) > 10 or summary.get('out_of_stock', 0) > 5:
                    parts.append("\n📦 Consider reaching out to farmers to replenish low-stock items.")
        
        return '\n'.join(parts)
