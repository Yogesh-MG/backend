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
    
    Returns aggregated KPIs for the FOS dashboard:
    - Orders Today with % change
    - Active Express/Same-Day Deliveries
    - Delayed Orders
    - Open Tickets
    - Revenue Today
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
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

        # Active Deliveries (mock data - would come from delivery tracking)
        express_deliveries = 86
        same_day_deliveries = 142

        # Delayed Orders (mock logic - orders not delivered within expected time)
        delayed_orders = 17  # Would be calculated from delivery tracking

        # Open Tickets (mock - would come from support ticket system)
        open_tickets = 23
        sla_breaching = 4

        # Revenue Today
        revenue_today = PosTransaction.objects.filter(
            created_at__range=(today_start, today_end),
            transaction_type='SALE'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        revenue_yesterday = PosTransaction.objects.filter(
            created_at__range=(yesterday_start, yesterday_end),
            transaction_type='SALE'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
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


@method_decorator(csrf_exempt, name='dispatch')
class FosHourlySalesView(APIView):
    """
    GET /api/pos/fos/dashboard/hourly-sales/
    
    Returns hourly GMV and order volume for today.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today_start, today_end = get_today_range()
        
        # Get transactions grouped by hour
        hourly_data = []
        
        for hour in range(24):
            hour_start = today_start + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            
            if hour_start > timezone.now():
                break
            
            transactions = PosTransaction.objects.filter(
                created_at__range=(hour_start, hour_end),
                transaction_type='SALE'
            )
            
            gmv = transactions.aggregate(total=Sum('total'))['total'] or Decimal('0')
            order_count = transactions.count()
            
            hourly_data.append({
                'time': f"{hour:02d}:00",
                'gmv': float(gmv),
                'orders': order_count
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
        status_filter = request.query_params.get('status', 'All')
        search = request.query_params.get('search', '').lower()
        
        # Mock orders data - in production from Order model with AI scoring
        orders = [
            {
                'id': 'FO-50231',
                'customer': 'Aisha Khan',
                'area': 'Indiranagar',
                'item': 'Organic Red Tomatoes 1kg',
                'amount': 289,
                'status': 'Processing',
                'risk': 25,
                'placedAt': '10:14'
            },
            {
                'id': 'FO-50232',
                'customer': 'Rohit Verma',
                'area': 'Koramangala',
                'item': 'A2 Desi Cow Ghee 500ml',
                'amount': 749,
                'status': 'Express',
                'risk': 15,
                'placedAt': '10:21'
            },
            {
                'id': 'FO-50233',
                'customer': 'Meera Iyer',
                'area': 'Whitefield',
                'item': 'Almond Flour Natural 250g',
                'amount': 449,
                'status': 'Delayed',
                'risk': 75,
                'placedAt': '09:45'
            },
            {
                'id': 'FO-50234',
                'customer': 'Karthik Rao',
                'area': 'HSR Layout',
                'item': 'Cold-Pressed Coconut Oil 1L',
                'amount': 399,
                'status': 'Delivered',
                'risk': 10,
                'placedAt': '09:30'
            },
            {
                'id': 'FO-50235',
                'customer': 'Sanjana Gupta',
                'area': 'Jayanagar',
                'item': 'Farm Fresh Eggs (Dozen)',
                'amount': 110,
                'status': 'Express',
                'risk': 20,
                'placedAt': '10:35'
            },
            {
                'id': 'FO-50236',
                'customer': 'Naveen Bhat',
                'area': 'Hebbal',
                'item': 'Himalayan Pink Salt 500g',
                'amount': 129,
                'status': 'Escalated',
                'risk': 85,
                'placedAt': '08:15'
            }
        ]
        
        # Apply filters
        if status_filter != 'All':
            orders = [o for o in orders if o['status'] == status_filter]
        
        if search:
            orders = [o for o in orders if search in o['id'].lower() or search in o['customer'].lower()]
        
        return Response(orders)


# ─── Support Desk ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class FosTicketsView(APIView):
    """
    GET /api/pos/fos/support/tickets/
    
    Returns support tickets with SLA countdown and sentiment analysis.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Mock tickets data - in production from SupportTicket model
        tickets = [
            {
                'id': 'TKT-8801',
                'customer': 'Ananya P.',
                'subject': 'Order 90 mins late',
                'category': 'Late Delivery',
                'sentiment': 'angry',
                'slaRemaining': 12,
                'lastMessage': 'Hi team, I really need this resolved today, this is the third time…'
            },
            {
                'id': 'TKT-8802',
                'customer': 'Vivek R.',
                'subject': 'Tomato packet leaking',
                'category': 'Damaged Product',
                'sentiment': 'frustrated',
                'slaRemaining': 45,
                'lastMessage': 'The package arrived completely soaked. Please help.'
            },
            {
                'id': 'TKT-8803',
                'customer': 'Suresh M.',
                'subject': 'Refund not received',
                'category': 'Payment Issue',
                'sentiment': 'frustrated',
                'slaRemaining': 8,
                'lastMessage': 'It has been 5 days since my refund was promised.'
            },
            {
                'id': 'TKT-8804',
                'customer': 'Lakshmi S.',
                'subject': 'App crashes on checkout',
                'category': 'App Issue',
                'sentiment': 'happy',
                'slaRemaining': 120,
                'lastMessage': 'App keeps crashing when I try to pay. Otherwise love your service!'
            },
            {
                'id': 'TKT-8805',
                'customer': 'Tarun B.',
                'subject': 'Wrong item delivered',
                'category': 'Late Delivery',
                'sentiment': 'angry',
                'slaRemaining': 25,
                'lastMessage': 'I ordered ghee but got honey. This is unacceptable!'
            }
        ]
        
        return Response(tickets)


@method_decorator(csrf_exempt, name='dispatch')
class FosAiReplyView(APIView):
    """
    POST /api/pos/fos/support/ai-reply/
    
    Generate AI-drafted reply for a ticket.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ticket_id = request.data.get('ticket_id')
        sentiment = request.data.get('sentiment', 'neutral')
        
        # AI-generated replies based on sentiment
        replies = {
            'angry': [
                "Hi, I'm so sorry your order is late — I've personally escalated this to our Indiranagar hub lead and you'll see an update in 10 mins. As an apology, I've added ₹150 FreshOn credits to your wallet.",
                "We hear you, and this isn't the experience FreshOn promises. I've fully refunded your order and our Quality Lead will personally call you within the hour."
            ],
            'frustrated': [
                "Thank you for flagging this. I can see the driver is 2 stops away. ETA is now 18 minutes. I'm also issuing a 20% refund on this order — no need to reply.",
                "I understand your frustration. Let me resolve this immediately - I've prioritized your issue and assigned a senior agent."
            ],
            'happy': [
                "Thank you for your patience! I've fixed the app issue on your account. Please try again and let me know if you need any help. As a token of appreciation, here's a 10% off coupon!",
                "We're so glad you love our service! I've noted the issue and our tech team is working on it. Here's a small credit for the inconvenience."
            ]
        }
        
        import random
        selected_replies = replies.get(sentiment, replies['frustrated'])
        
        return Response({
            'ticket_id': ticket_id,
            'replies': selected_replies,
            'generated_at': timezone.now().isoformat()
        })


# ─── Inventory Intelligence ────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class FosInventoryView(APIView):
    """
    GET /api/pos/fos/inventory/
    
    Returns SKU stock levels, expiry indicators, and AI demand predictions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Mock inventory data - in production from InventoryBatch model
        # with AI demand prediction service
        inventory = [
            {
                'id': 'SKU3001',
                'name': 'Organic Red Tomatoes',
                'cat': 'Vegetables',
                'stock': 42,
                'price': 89,
                'expiry': '2d',
                'demand7d': [45, 52, 38, 61, 55, 48, 42]
            },
            {
                'id': 'SKU3002',
                'name': 'A2 Desi Cow Ghee',
                'cat': 'Dairy',
                'stock': 128,
                'price': 749,
                'expiry': '60d',
                'demand7d': [12, 15, 18, 14, 16, 20, 17]
            },
            {
                'id': 'SKU3003',
                'name': 'Almond Flour Natural',
                'cat': 'Baking',
                'stock': 6,
                'price': 449,
                'expiry': '90d',
                'demand7d': [8, 6, 9, 7, 5, 8, 6]
            },
            {
                'id': 'SKU3004',
                'name': 'Cold-Pressed Coconut Oil',
                'cat': 'Oils',
                'stock': 78,
                'price': 399,
                'expiry': '180d',
                'demand7d': [15, 18, 22, 19, 16, 20, 18]
            },
            {
                'id': 'SKU3005',
                'name': 'Farm Fresh Eggs',
                'cat': 'Dairy',
                'stock': 240,
                'price': 110,
                'expiry': '10d',
                'demand7d': [35, 42, 38, 45, 40, 48, 44]
            },
            {
                'id': 'SKU3006',
                'name': 'Himalayan Pink Salt',
                'cat': 'Pantry',
                'stock': 312,
                'price': 129,
                'expiry': '365d',
                'demand7d': [22, 25, 20, 28, 24, 26, 23]
            },
            {
                'id': 'SKU3007',
                'name': 'Organic Spinach',
                'cat': 'Vegetables',
                'stock': 18,
                'price': 49,
                'expiry': '1d',
                'demand7d': [25, 28, 22, 30, 26, 32, 28]
            },
            {
                'id': 'SKU3008',
                'name': 'Raw Forest Honey',
                'cat': 'Pantry',
                'stock': 4,
                'price': 525,
                'expiry': '365d',
                'demand7d': [5, 4, 6, 5, 4, 5, 4]
            }
        ]
        
        return Response(inventory)


@method_decorator(csrf_exempt, name='dispatch')
class FosDeadStockView(APIView):
    """
    GET /api/pos/fos/inventory/dead-stock/
    
    Returns low-velocity SKUs with recommended actions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Mock dead stock data
        dead_stock = [
            {
                'sku': 'SKU3042',
                'item': 'Organic Quinoa 1kg',
                'velocity': '3/wk',
                'suggestedAction': 'Bundle with breakfast pack'
            },
            {
                'sku': 'SKU3061',
                'item': 'Sprouted Ragi Flour',
                'velocity': '2/wk',
                'suggestedAction': 'Run 25% flash sale'
            },
            {
                'sku': 'SKU3084',
                'item': 'Bamboo Salt',
                'velocity': '1/wk',
                'suggestedAction': 'Delist after current stock'
            }
        ]
        
        return Response(dead_stock)


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
