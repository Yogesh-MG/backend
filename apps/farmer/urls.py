"""Farmer app URL configuration."""
from django.urls import path
from .views import (
    FarmerRegisterView,
    FarmerProfileView,
    FarmerMediaUploadView,
    FarmerDashboardView,
    FarmerBatchListView,
    FarmerBatchDetailView,
    FarmerPayoutView,
    FarmerOrderListView,
    BankDetailsView,
    NotificationListView,
)

urlpatterns = [
    path('register/', FarmerRegisterView.as_view(), name='farmer_register'),
    path('profile/', FarmerProfileView.as_view(), name='farmer_profile'),
    path('media/', FarmerMediaUploadView.as_view(), name='farmer_media'),
    path('dashboard/', FarmerDashboardView.as_view(), name='farmer_dashboard'),
    path('batches/', FarmerBatchListView.as_view(), name='farmer_batches'),
    path('batches/<int:batch_id>/', FarmerBatchDetailView.as_view(), name='farmer_batch_detail'),
    path('payouts/', FarmerPayoutView.as_view(), name='farmer_payouts'),
    path('orders/', FarmerOrderListView.as_view(), name='farmer_orders'),
    path('bank/', BankDetailsView.as_view(), name='farmer_bank'),
    path('notifications/', NotificationListView.as_view(), name='farmer_notifications'),
]
