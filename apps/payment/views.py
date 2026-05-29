import os
import hashlib
import hmac
import json
import razorpay
import uuid
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.orders.serializers import OrderItemSerializer
from apps.inventory.models import InventoryBatch
from .models import PaymentTransaction
from .serializers import PaymentTransactionSerializer
from .icici_client import get_icici_client, configure_from_settings

logger = logging.getLogger(__name__)

# Initialize Razorpay client (kept for backward compatibility)
client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# Initialize ICICI client on module load
try:
    configure_from_settings()
except Exception as e:
    logger.warning(f"Could not configure ICICI client: {e}")


# ============================================================================
# RAZORPAY VIEWS (Legacy - kept for backward compatibility)
# ============================================================================

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
                                'provider': 'RAZORPAY',
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


# ============================================================================
# ICICI EAZYPAY VIEWS (New - for POS integration)
# ============================================================================

class ICICIGenerateQRView(APIView):
    """
    Generate a dynamic QR code for ICICI UPI payment.
    
    POST /api/payment/icici/qr/generate/
    
    Request Body:
        - amount: float (required) - Payment amount
        - order_id: string (optional) - Internal order tracking ID
        - validity_minutes: int (optional) - QR validity in minutes (default: 5)
    
    Response:
        - success: bool
        - qr_string: string - UPI QR code payload
        - transaction_id: string - ICICI merchant transaction ID
        - ref_id: string - ICICI reference ID
        - expires_at: timestamp - QR expiry time
        - message: string
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        amount = request.data.get('amount')
        order_id = request.data.get('order_id')
        validity_minutes = request.data.get('validity_minutes', 5)
        
        if not amount:
            return Response(
                {'error': 'amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount_decimal = Decimal(str(amount))
            if amount_decimal <= 0:
                return Response(
                    {'error': 'amount must be greater than 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'invalid amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate unique transaction ID (max 20 chars for ICICI)
        # Format: FON + timestamp (36-base) + random
        timestamp_part = str(int(timezone.now().timestamp()))[-10:]
        random_part = uuid.uuid4().hex[:4].upper()
        merchant_tran_id = f"FON{timestamp_part}{random_part}"[:20]
        
        try:
            icici_client = get_icici_client()
            
            # Check if client is configured
            if not icici_client._configured:
                # Try to configure from settings
                configure_from_settings()
            
            if not icici_client._configured:
                return Response(
                    {
                        'error': 'ICICI payment not configured',
                        'message': 'Please configure ICICI credentials in settings'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Generate QR code
            result = icici_client.generate_qr(
                amount=amount_decimal,
                merchant_tran_id=merchant_tran_id,
                bill_number=order_id,
                validity_minutes=validity_minutes
            )
            
            if result['success']:
                # Calculate expiry time
                expires_at = timezone.now() + timezone.timedelta(minutes=validity_minutes)
                
                return Response({
                    'success': True,
                    'qr_string': result['qr_string'],
                    'transaction_id': result['transaction_id'],
                    'ref_id': result['ref_id'],
                    'expires_at': expires_at.isoformat(),
                    'message': result['message'],
                })
            else:
                return Response({
                    'success': False,
                    'error': result['error'] or 'Failed to generate QR code',
                    'message': result['message'],
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error generating ICICI QR: {e}")
            return Response(
                {'error': f'Failed to generate QR: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ICICICheckStatusView(APIView):
    """
    Check the status of an ICICI payment transaction.
    
    GET /api/payment/icici/status/<merchant_tran_id>/
    
    Response:
        - success: bool (API call succeeded)
        - status: string - Payment status (SUCCESS, FAILURE, PENDING, EXPIRED, ERROR)
        - transaction_id: string - Merchant transaction ID
        - amount: string - Transaction amount
        - bank_rrn: string - Bank reference number
        - message: string
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, merchant_tran_id):
        if not merchant_tran_id:
            return Response(
                {'error': 'transaction_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            icici_client = get_icici_client()
            
            # Check if client is configured
            if not icici_client._configured:
                configure_from_settings()
            
            if not icici_client._configured:
                return Response(
                    {
                        'error': 'ICICI payment not configured',
                        'message': 'Please configure ICICI credentials in settings'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Check status
            result = icici_client.check_status(merchant_tran_id)
            
            return Response({
                'success': result['success'],
                'status': result['status'],
                'transaction_id': result['transaction_id'],
                'amount': result['amount'],
                'bank_rrn': result['bank_rrn'],
                'message': result['message'],
                'error': result['error'],
            })
            
        except Exception as e:
            logger.error(f"Error checking ICICI status: {e}")
            return Response(
                {'error': f'Failed to check status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ICICIRecordPaymentView(APIView):
    """
    Record a completed ICICI payment and link it to an order.
    
    POST /api/payment/icici/record/
    
    Request Body:
        - order_id: string (required) - Internal order tracking ID
        - merchant_tran_id: string (required) - ICICI transaction ID
        - ref_id: string (optional) - ICICI reference ID
        - bank_rrn: string (optional) - Bank reference number
        - amount: float (required) - Payment amount
    
    Response:
        - success: bool
        - message: string
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        order_id = request.data.get('order_id')
        merchant_tran_id = request.data.get('merchant_tran_id')
        ref_id = request.data.get('ref_id')
        bank_rrn = request.data.get('bank_rrn')
        amount = request.data.get('amount')
        
        if not all([order_id, merchant_tran_id, amount]):
            return Response(
                {'error': 'order_id, merchant_tran_id, and amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.orders.models import Order
            
            order = Order.objects.get(tracking_id=order_id)
            amount_decimal = Decimal(str(amount))
            
            # Create or update PaymentTransaction
            PaymentTransaction.objects.update_or_create(
                order=order,
                defaults={
                    'provider': 'ICICI',
                    'icici_merchant_tran_id': merchant_tran_id,
                    'icici_ref_id': ref_id,
                    'icici_bank_rrn': bank_rrn,
                    'amount': amount_decimal,
                    'currency': 'INR',
                    'status': 'COMPLETED',
                    'metadata': {
                        'recorded_by': request.user.id,
                        'recorded_at': timezone.now().isoformat(),
                    }
                }
            )
            
            # Update order payment status
            if not order.is_paid:
                order.is_paid = True
                order.payment_status = 'COMPLETED'
                order.save(update_fields=['is_paid', 'payment_status'])
            
            return Response({
                'success': True,
                'message': 'Payment recorded successfully',
                'order_id': order_id,
                'transaction_id': merchant_tran_id,
            })
            
        except Order.DoesNotExist:
            return Response(
                {'error': f'Order {order_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error recording ICICI payment: {e}")
            return Response(
                {'error': f'Failed to record payment: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ICICIWebhookView(APIView):
    """
    Webhook endpoint for ICICI payment callbacks.
    
    POST /api/payment/icici/webhook/
    
    This endpoint receives encrypted callbacks from ICICI when payment status changes.
    The SDK automatically decrypts the payload.
    """
    permission_classes = []  # Webhooks don't use standard auth
    
    def post(self, request):
        try:
            # The SDK handles decryption automatically
            # This endpoint is for receiving async notifications
            
            # TODO: Implement webhook handling based on ICICI callback format
            # The httpcore.utils.CallbackUtils.decrypt_callback can be used here
            
            logger.info(f"Received ICICI webhook: {request.data}")
            
            return Response({'status': 'received'})
            
        except Exception as e:
            logger.error(f"Error processing ICICI webhook: {e}")
            return Response(
                {'error': 'Webhook processing failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
