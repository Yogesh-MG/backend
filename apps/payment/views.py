import os
import hashlib
import hmac
import json
import razorpay
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import PaymentTransaction
from .serializers import PaymentTransactionSerializer


# Initialize Razorpay client
client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


class RazorpayInitializeView(APIView):
    """Initialize a Razorpay payment order."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        amount = request.data.get('amount')  # in paise
        currency = request.data.get('currency', 'INR')
        
        if not amount:
            return Response(
                {'error': 'Amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create Razorpay order
            razorpay_order = client.order.create({
                'amount': int(amount),
                'currency': currency,
                'payment_capture': 1,  # Auto-capture payment
            })
            
            return Response({
                'orderId': razorpay_order['id'],
                'key': settings.RAZORPAY_KEY_ID,
                'amount': amount,
                'currency': currency,
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to initialize payment: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RazorpayVerifyView(APIView):
    """Verify Razorpay payment and create PaymentTransaction."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_signature = request.data.get('razorpay_signature')
        
        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            return Response(
                {'error': 'Missing payment details'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify signature
            message = f'{razorpay_order_id}|{razorpay_payment_id}'
            expected_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if expected_signature != razorpay_signature:
                return Response(
                    {'error': 'Invalid signature', 'success': False},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Fetch payment details from Razorpay
            payment = client.payment.fetch(razorpay_payment_id)
            
            if payment['status'] == 'captured':
                return Response({
                    'success': True,
                    'message': 'Payment verified successfully',
                    'payment_id': razorpay_payment_id,
                    'order_id': razorpay_order_id,
                })
            else:
                return Response(
                    {'error': f'Payment status: {payment["status"]}', 'success': False},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'error': f'Payment verification failed: {str(e)}', 'success': False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
