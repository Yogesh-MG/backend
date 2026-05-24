"""POS app URL configuration."""
from django.urls import path
from .views import (
    PosLoginView,
    PosShiftOpenView,
    PosShiftCloseView,
    PosShiftSummaryView,
    PosProductsView,
    PosCustomerLookupView,
    PosCustomerCreateView,
    PosOrderCreateView,
    PosOrderLookupView,
    PosRefundView,
    PosWastageView,
    PosSettingsView,
    PosCompanyListView,
    PosCompanyCreateView,
)
from .fos_views import (
    FosDashboardKpiView,
    FosHourlySalesView,
    FosBankStatementsView,
    FosReceivablesView,
    FosSendReminderView,
    FosEmployeesView,
    FosLeavesView,
    FosProcessPayrollView,
    FosOrdersView,
    FosTicketsView,
    FosAiReplyView,
    FosInventoryView,
    FosDeadStockView,
    FosAgentQueryView,
)

urlpatterns = [
    # Standard POS endpoints
    path('login/', PosLoginView.as_view(), name='pos_login'),
    path('shift/open/', PosShiftOpenView.as_view(), name='pos_shift_open'),
    path('shift/close/', PosShiftCloseView.as_view(), name='pos_shift_close'),
    path('shift/summary/', PosShiftSummaryView.as_view(), name='pos_shift_summary'),
    path('settings/', PosSettingsView.as_view(), name='pos_settings'),
    path('products/', PosProductsView.as_view(), name='pos_products'),
    path('customers/lookup/', PosCustomerLookupView.as_view(), name='pos_customer_lookup'),
    path('customers/', PosCustomerCreateView.as_view(), name='pos_customer_create'),
    path('companies/', PosCompanyListView.as_view(), name='pos_company_list'),
    path('companies/create/', PosCompanyCreateView.as_view(), name='pos_company_create'),
    path('orders/lookup/', PosOrderLookupView.as_view(), name='pos_order_lookup'),
    path('orders/refund/', PosRefundView.as_view(), name='pos_order_refund'),
    path('orders/', PosOrderCreateView.as_view(), name='pos_order_create'),
    path('wastage/', PosWastageView.as_view(), name='pos_wastage'),
    
    # FOS (Field Operations System) endpoints
    # Dashboard
    path('fos/dashboard/kpis/', FosDashboardKpiView.as_view(), name='fos_dashboard_kpis'),
    path('fos/dashboard/hourly-sales/', FosHourlySalesView.as_view(), name='fos_hourly_sales'),
    
    # Finance
    path('fos/finance/bank-statements/', FosBankStatementsView.as_view(), name='fos_bank_statements'),
    path('fos/finance/receivables/', FosReceivablesView.as_view(), name='fos_receivables'),
    path('fos/finance/send-reminder/', FosSendReminderView.as_view(), name='fos_send_reminder'),
    
    # HR
    path('fos/hr/employees/', FosEmployeesView.as_view(), name='fos_employees'),
    path('fos/hr/leaves/', FosLeavesView.as_view(), name='fos_leaves'),
    path('fos/hr/process-payroll/', FosProcessPayrollView.as_view(), name='fos_process_payroll'),
    
    # Orders
    path('fos/orders/', FosOrdersView.as_view(), name='fos_orders'),
    
    # Support
    path('fos/support/tickets/', FosTicketsView.as_view(), name='fos_tickets'),
    path('fos/support/ai-reply/', FosAiReplyView.as_view(), name='fos_ai_reply'),
    
    # Inventory
    path('fos/inventory/', FosInventoryView.as_view(), name='fos_inventory'),
    path('fos/inventory/dead-stock/', FosDeadStockView.as_view(), name='fos_dead_stock'),
    
    # AI Agent
    path('fos/agent/query/', FosAgentQueryView.as_view(), name='fos_agent_query'),
]
