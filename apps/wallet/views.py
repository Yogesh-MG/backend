from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from decimal import Decimal
import razorpay
import os

from .models import Wallet, WalletTransaction, WalletTopup, Partnership, Referral
from .serializers import (
    WalletSerializer, WalletDetailSerializer, WalletTransactionSerializer,
    WalletTopupSerializer, WalletTopupInitiateSerializer,
    PartnershipSerializer, ReferralSerializer
)


class WalletViewSet(viewsets.ViewSet):
    """Wallet balance and top-up operations."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Get current wallet balance."""
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def detail(self, request):
        """Get detailed wallet info with recent transactions and partnership."""
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletDetailSerializer(wallet)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get paginated wallet transaction history."""
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        # Filters
        reason = request.query_params.get('reason')
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        transactions = wallet.transactions.all()
        
        if reason:
            transactions = transactions.filter(reason=reason)
        
        total_count = transactions.count()
        transactions = transactions[offset:offset + limit]
        
        serializer = WalletTransactionSerializer(transactions, many=True)
        return Response({
            'count': total_count,
            'limit': limit,
            'offset': offset,
            'results': serializer.data
        })

    @action(detail=False, methods=['post'])
    def initiate_topup(self, request):
        """Initiate a wallet top-up via Razorpay."""
        serializer = WalletTopupInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        # Initialize Razorpay client using settings
        from django.conf import settings
        razorpay_client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        
        try:
            # Create Razorpay order
            razorpay_order = razorpay_client.order.create({
                'amount': int(amount * 100),  # Razorpay expects amount in paise
                'currency': 'INR',
                'notes': {
                    'user_id': request.user.id,
                    'username': request.user.username,
                    'purpose': 'wallet_topup'
                }
            })
            
            # Create WalletTopup record
            topup = WalletTopup.objects.create(
                wallet=wallet,
                amount=amount,
                razorpay_order_id=razorpay_order['id'],
                status='INITIATED'
            )
            
            return Response({
                'topup_id': topup.id,
                'razorpay_order_id': razorpay_order['id'],
                'amount': float(amount),
                'key_id': settings.RAZORPAY_KEY_ID
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def verify_topup(self, request):
        """Verify Razorpay payment and credit wallet."""
        topup_id = request.data.get('topup_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        
        if not all([topup_id, razorpay_payment_id, razorpay_signature]):
            return Response(
                {'error': 'Missing payment verification details'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.db import transaction
            import logging
            logger = logging.getLogger(__name__)

            with transaction.atomic():
                # Fetch topup and lock it for processing
                try:
                    topup = WalletTopup.objects.select_for_update().get(id=topup_id, wallet__user=request.user)
                except WalletTopup.DoesNotExist:
                    return Response({'error': 'Top-up record not found'}, status=status.HTTP_404_NOT_FOUND)

                # 1. Idempotency Check: Don't process if already successful
                if topup.status == 'SUCCESS':
                    return Response({
                        'status': 'success',
                        'message': 'This top-up was already processed.',
                        'new_balance': float(topup.wallet.balance)
                    })

                # 2. Verify Signature with Razorpay
                from django.conf import settings
                razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                
                try:
                    razorpay_client.utility.verify_payment_signature({
                        'razorpay_order_id': topup.razorpay_order_id,
                        'razorpay_payment_id': razorpay_payment_id,
                        'razorpay_signature': razorpay_signature
                    })
                except razorpay.BadRequestError:
                    topup.status = 'FAILED'
                    topup.save(update_fields=['status', 'updated_at'])
                    logger.error(f"Signature verification failed for topup {topup_id}")
                    return Response({'error': 'Payment signature verification failed'}, status=status.HTTP_400_BAD_REQUEST)
                
                # 3. Update top-up record
                topup.razorpay_payment_id = razorpay_payment_id
                topup.razorpay_signature = razorpay_signature
                topup.status = 'SUCCESS'
                topup.save()
                
                # 4. Credit wallet with atomicity
                wallet = topup.wallet
                balance_before = wallet.balance
                wallet.balance += topup.amount
                wallet.save(update_fields=['balance'])
                
                # 5. Create transaction record for audit trail
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=topup.amount,
                    reason='TOPUP',
                    balance_before=balance_before,
                    balance_after=wallet.balance,
                    related_topup=topup,
                    notes=f'Razorpay Payment ID: {razorpay_payment_id}'
                )
                
                logger.info(f"Wallet credited: User {request.user.id}, Amount {topup.amount}, New Balance {wallet.balance}")

                return Response({
                    'status': 'success',
                    'message': f'Wallet credited with ₹{topup.amount}',
                    'new_balance': float(wallet.balance)
                })
        
        except Exception as e:
            import traceback
            logger.error(f"Unexpected error in verify_topup: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {'error': 'An internal error occurred while verifying the payment.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def topup_history(self, request):
        """Get wallet top-up history."""
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        topups = wallet.topups.all()
        
        serializer = WalletTopupSerializer(topups, many=True)
        return Response({
            'count': topups.count(),
            'results': serializer.data
        })


class PartnershipViewSet(viewsets.ViewSet):
    """PRIDE Partnership management."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def my_partnership(self, request):
        """Get user's partnership details."""
        try:
            partnership = Partnership.objects.get(user=request.user)
            serializer = PartnershipSerializer(partnership)
            return Response(serializer.data)
        except Partnership.DoesNotExist:
            return Response(
                {'message': 'No active partnership'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def request_refund(self, request):
        """Request withdrawal from partnership."""
        try:
            partnership = Partnership.objects.get(user=request.user)
        except Partnership.DoesNotExist:
            return Response(
                {'error': 'No active partnership'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if partnership.refund_requested:
            return Response(
                {'error': 'Refund already requested'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        partnership.refund_requested = True
        partnership.save()
        
        return Response({
            'status': 'success',
            'message': 'Refund request submitted. You will receive 100% principal return within 30 days.'
        })


class ReferralViewSet(viewsets.ViewSet):
    """Referral program management."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def my_referrals(self, request):
        """Get user's referral information."""
        referrals = Referral.objects.filter(referrer=request.user)
        serializer = ReferralSerializer(referrals, many=True)
        
        total_bonus = sum(r.bonus_amount for r in referrals if r.status == 'CREDITED')
        
        return Response({
            'total_referrals': referrals.count(),
            'total_bonus_earned': float(total_bonus),
            'referrals': serializer.data
        })

    @action(detail=False, methods=['get'])
    def referral_code(self, request):
        """Get or create user's referral code."""
        referral, _ = Referral.objects.get_or_create(
            referrer=request.user,
            defaults={'referee': None, 'referral_code': f"REF{request.user.id}"}
        )
        return Response({
            'referral_code': referral.referral_code,
            'share_link': f"https://freshon.in/join?ref={referral.referral_code}"
        })
