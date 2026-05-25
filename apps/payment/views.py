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
        is_additional_payment = request.data.get('is_additional_payment', False)
        
        if is_additional_payment:
            amount = request.data.get('amount')
            order_id = request.data.get('order_id')
            if not amount:
                return Response(
                    {'error': 'amount is required for additional payments'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                total_amount = int(float(amount) * 100) # in paise
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
                    subtotal += batch.variant.price * quantity
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
        freshon_order_id = request.data.get('freshon_order_id')  # Our internal order tracking_id
        
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
                # Create or update PaymentTransaction record
                from apps.orders.models import Order
                from decimal import Decimal
                
                try:
                    # Try to find the order by tracking_id if provided
                    if freshon_order_id:
                        order = Order.objects.get(tracking_id=freshon_order_id)
                    else:
                        # Fallback: try to find by razorpay_order_id in existing transactions
                        pt = PaymentTransaction.objects.filter(razorpay_order_id=razorpay_order_id).first()
                        if pt:
                            order = pt.order
                        else:
                            order = None
                    
                    if order:
                        # Create or update PaymentTransaction
                        pt, created = PaymentTransaction.objects.update_or_create(
                            order=order,
                            defaults={
                                'razorpay_order_id': razorpay_order_id,
                                'razorpay_payment_id': razorpay_payment_id,
                                'razorpay_signature': razorpay_signature,
                                'amount': Decimal(str(payment['amount'])) / Decimal('100'),  # Convert paise to rupees
                                'currency': payment.get('currency', 'INR'),
                                'status': 'COMPLETED',
                            }
                        )
                        
                        # Update order payment status
                        if not order.is_paid:
                            order.is_paid = True
                            order.payment_status = 'COMPLETED'
                            order.save(update_fields=['is_paid', 'payment_status'])
                except Order.DoesNotExist:
                    pass  # Order not found, but payment is still verified
                except Exception as e:
                    # Log error but don't fail the verification
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create PaymentTransaction: {e}")
                
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
