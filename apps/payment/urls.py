from django.urls import path
from . import views

urlpatterns = [
    path('razorpay-init/', views.RazorpayInitializeView.as_view(), name='razorpay-init'),
    path('razorpay-verify/', views.RazorpayVerifyView.as_view(), name='razorpay-verify'),
]
