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

urlpatterns = [
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
]
