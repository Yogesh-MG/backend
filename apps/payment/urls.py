from django.urls import path
from . import views

urlpatterns = [
    # Legacy Razorpay endpoints (kept for backward compatibility)
    path('razorpay-init/', views.RazorpayInitializeView.as_view(), name='razorpay-init'),
    path('razorpay-verify/', views.RazorpayVerifyView.as_view(), name='razorpay-verify'),
    
    # ICICI Eazypay endpoints (new)
    path('icici/qr/generate/', views.ICICIGenerateQRView.as_view(), name='icici-qr-generate'),
    path('icici/status/<str:merchant_tran_id>/', views.ICICICheckStatusView.as_view(), name='icici-status'),
    path('icici/record/', views.ICICIRecordPaymentView.as_view(), name='icici-record'),
    path('icici/webhook/', views.ICICIWebhookView.as_view(), name='icici-webhook'),
]
