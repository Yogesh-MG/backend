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
from apps.orders.serializers import OrderItemSerializer
from apps.inventory.models import InventoryBatch
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
        items_data = request.data.get('items', [])
        
        if not items_data:
            return Response(
                {'error': 'No items in order'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 1. Calculate Total on Backend
            subtotal = 0
            for item in items_data:
                batch_id = item.get('batch')
                quantity = item.get('quantity', 0)
                
                try:
                    batch = InventoryBatch.objects.get(id=batch_id)
                    subtotal += batch.price * quantity
                except InventoryBatch.DoesNotExist:
                    continue # Or raise error
            
            delivery_fee = 25 if subtotal < 199 else 0
            total_amount = int((subtotal + delivery_fee) * 100) # in paise
            
            if total_amount <= 0:
                return Response({'error': 'Invalid order amount'}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Create Razorpay order
            razorpay_order = client.order.create({
                'amount': total_amount,
                'currency': 'INR',
                'payment_capture': 1,
            })
            
            return Response({
                'orderId': razorpay_order['id'],
                'key': settings.RAZORPAY_KEY_ID,
                'amount': total_amount,
                'currency': 'INR',
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
            # Verify signature using Razorpay SDK utility
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            
            # Fetch payment details from Razorpay
            payment = client.payment.fetch(razorpay_payment_id)
            
            if payment['status'] in ['captured', 'authorized']:
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
        except razorpay.errors.SignatureVerificationError:
            return Response(
                {'error': 'Invalid payment signature', 'success': False},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Payment verification failed: {str(e)}', 'success': False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
