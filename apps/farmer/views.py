"""
Farmer app views.

Endpoints:
  POST  /api/farmer/register/       — OTP-based farmer registration
  GET   /api/farmer/profile/        — Get farmer profile
  PATCH /api/farmer/profile/        — Update farmer profile
  POST  /api/farmer/media/          — Upload farm/product video
  GET   /api/farmer/dashboard/      — Aggregated dashboard metrics
  GET   /api/farmer/batches/        — Farmer's own inventory batches
  POST  /api/farmer/batches/        — Add new harvest batch
  PATCH /api/farmer/batches/{id}/   — Update batch
  GET   /api/farmer/payouts/        — Payment history
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Avg, Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, FarmerProfile
from apps.inventory.models import InventoryBatch, Product, ProductVariant
from apps.orders.models import Order, OrderItem
from .models import FarmerMedia, FarmerPayout, FarmerOTP, FarmerNotification, BankDetails
from .serializers import (
    FarmerProfileSerializer, FarmerBatchSerializer,
    FarmerAddBatchSerializer, FarmerPayoutSerializer, FarmerMediaSerializer,
    BankDetailsSerializer, FarmerNotificationSerializer,
)
from .permissions import IsFarmerUser


def _set_auth_cookies(response, access_token, refresh_token):
    """Reuse the cookie-setting pattern from accounts."""
    from django.conf import settings
    cookie_kwargs = dict(
        secure=settings.JWT_AUTH_COOKIE_SECURE,
        httponly=settings.JWT_AUTH_COOKIE_HTTP_ONLY,
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
        path=settings.JWT_AUTH_COOKIE_PATH,
    )
    response.set_cookie(key=settings.JWT_AUTH_COOKIE, value=access_token, max_age=3600, **cookie_kwargs)
    response.set_cookie(key=settings.JWT_AUTH_REFRESH_COOKIE, value=refresh_token, max_age=86400, **cookie_kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class FarmerRegisterView(APIView):
    """
    POST /api/farmer/register/
    Two-step OTP flow:
      Step 1: { phone } → generates OTP
      Step 2: { phone, otp, name } → verifies, creates user, returns tokens
    """
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone')
        otp = request.data.get('otp')
        name = request.data.get('name', '')

        if not phone:
            return Response({'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not otp:
            # Step 1: Generate OTP
            generated_otp = str(random.randint(100000, 999999))
            FarmerOTP.objects.create(
                phone=phone,
                otp=generated_otp,
                expires_at=timezone.now() + timedelta(minutes=5),
            )
            # In production, send SMS via Twilio/MSG91
            return Response({
                'message': 'OTP sent successfully',
                'debug_otp': generated_otp,  # Remove in production
            })

        # Step 2: Verify OTP
        otp_record = FarmerOTP.objects.filter(
            phone=phone, otp=otp, is_verified=False,
            expires_at__gte=timezone.now(),
        ).order_by('-created_at').first()

        if not otp_record:
            return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)

        otp_record.is_verified = True
        otp_record.save()

        # Create or get user
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={
                'username': f'farmer_{phone}',
                'role': 'FARMER',
                'is_verified': True,
            },
        )

        if created and name:
            parts = name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
            user.set_password(phone)  # Default password is phone
            user.save()

        # Ensure farmer profile exists
        profile, _ = FarmerProfile.objects.get_or_create(
            user=user,
            defaults={'location': '', 'speciality': ''},
        )

        # Determine if profile onboarding is complete
        profile_complete = bool(
            user.get_full_name().strip()
            and getattr(profile, 'total_acreage', None)
            and getattr(profile, 'organic_pledge_accepted', False)
        )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response({
            'message': 'Farmer registered successfully' if created else 'Welcome back!',
            'is_new_user': created,
            'profile_complete': profile_complete,
            'user': {
                'id': user.id, 'username': user.username,
                'name': user.get_full_name() or user.username,
                'email': user.email, 'role': user.role,
                'is_verified': user.is_verified,
            },
            'access': access_token,
            'refresh': refresh_token,
        })
        _set_auth_cookies(response, access_token, refresh_token)
        return response


@method_decorator(csrf_exempt, name='dispatch')
class FarmerProfileView(APIView):
    """GET/PATCH /api/farmer/profile/"""
    permission_classes = [IsFarmerUser]

    def get(self, request):
        try:
            profile = request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            profile = FarmerProfile.objects.create(user=request.user, location='', speciality='')
        serializer = FarmerProfileSerializer(profile)
        return Response(serializer.data)

    def patch(self, request):
        try:
            profile = request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            profile = FarmerProfile.objects.create(user=request.user, location='', speciality='')
        serializer = FarmerProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Update user name if provided
        name = request.data.get('name')
        if name:
            parts = name.split(' ', 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ''
            request.user.save()

        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class FarmerMediaUploadView(APIView):
    """POST /api/farmer/media/"""
    permission_classes = [IsFarmerUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        media_type = request.data.get('type')
        file = request.FILES.get('file')
        if not media_type or not file:
            return Response({'error': 'type and file are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            profile = request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            return Response({'error': 'Farmer profile not found'}, status=status.HTTP_404_NOT_FOUND)
        media = FarmerMedia.objects.create(farmer=profile, type=media_type, file=file)
        if media_type == 'profile_photo':
            profile.image = file
            profile.save(update_fields=['image'])
        url = request.build_absolute_uri(media.file.url) if media.file else ''
        return Response({'url': url, 'type': media_type})


@method_decorator(csrf_exempt, name='dispatch')
class FarmerDashboardView(APIView):
    """GET /api/farmer/dashboard/"""
    permission_classes = [IsFarmerUser]

    def get(self, request):
        try:
            profile = request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            return Response({'error': 'Farmer profile not found'}, status=status.HTTP_404_NOT_FOUND)

        batches = InventoryBatch.objects.filter(farmer=profile)
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Count sold items from order_items linked to this farmer's batches
        sold_items = OrderItem.objects.filter(batch__farmer=profile)
        total_revenue = sold_items.aggregate(
            total=Sum('price')
        )['total'] or 0
        monthly_items = sold_items.filter(order__created_at__gte=month_ago)
        weekly_items = sold_items.filter(order__created_at__gte=week_ago)

        monthly_total = float(monthly_items.aggregate(t=Sum('price'))['t'] or 0)
        recent_payouts = [
            {
                'id': str(p.id)[:8],
                'amount': float(p.amount),
                'status': p.status,
                'date': p.created_at.strftime('%d %b'),
                'type': 'credit',
                'description': f'Payout {p.status}',
            }
            for p in profile.payouts.all()[:5]
        ]

        return Response({
            'total_earnings': float(total_revenue),
            'total_sales': float(total_revenue),
            'lifetime_earnings': float(total_revenue),
            'current_month_earnings': monthly_total,
            'monthly_earnings': monthly_total,
            'total_products': batches.count(),
            'live_products': batches.filter(stock_level__gt=0).count(),
            'avg_rating': float(profile.rating),
            'total_orders': sold_items.values('order').distinct().count(),
            'weekly_sales': float(weekly_items.aggregate(t=Sum('price'))['t'] or 0),
            'monthly_sales': float(monthly_items.aggregate(t=Sum('price'))['t'] or 0),
            'pending_payouts': float(profile.payouts.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0),
            'unread_notifications_count': profile.notifications.filter(is_read=False).count(),
            'recent_transactions': recent_payouts,
        })


@method_decorator(csrf_exempt, name='dispatch')
class FarmerBatchListView(APIView):
    """GET/POST /api/farmer/batches/"""
    permission_classes = [IsFarmerUser]

    def get(self, request):
        try:
            profile = request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)
        batches = InventoryBatch.objects.filter(farmer=profile).select_related(
            'variant', 'variant__product',
        )
        serializer = FarmerBatchSerializer(batches, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = FarmerAddBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            profile = request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            return Response({'error': 'Farmer profile not found'}, status=status.HTTP_404_NOT_FOUND)

        custom_name = request.data.get('custom_product_name', '').strip()
        product_id = data.get('product_id', 0)

        if custom_name and (not product_id or product_id == 0):
            # Farmer-suggested custom product — find or create
            from apps.inventory.models import Category
            default_category = Category.objects.first()
            if not default_category:
                return Response({'error': 'No product categories configured'}, status=status.HTTP_400_BAD_REQUEST)
            product, _ = Product.objects.get_or_create(
                name__iexact=custom_name,
                defaults={
                    'name': custom_name.title(),
                    'category': default_category,
                    'description': f'Custom product added by farmer {profile.user.get_full_name()}',
                    'storage_instructions': 'Store in a cool, dry place.',
                },
            )
        else:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get or create a default variant
        variant = product.variants.first()
        if not variant:
            variant = ProductVariant.objects.create(product=product, unit='1 kg')
        batch = InventoryBatch.objects.create(
            farmer=profile,
            variant=variant,
            price=data['price'],
            mrp=data.get('mrp'),
            stock_level=data['stock_level'],
            harvest_date=data['harvest_date'],
            is_organic=data.get('is_organic', False),
        )
        return Response(FarmerBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class FarmerBatchDetailView(APIView):
    """PATCH /api/farmer/batches/{id}/"""
    permission_classes = [IsFarmerUser]

    def patch(self, request, batch_id):
        try:
            profile = request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            batch = InventoryBatch.objects.get(id=batch_id, farmer=profile)
        except InventoryBatch.DoesNotExist:
            return Response({'error': 'Batch not found'}, status=status.HTTP_404_NOT_FOUND)
        for field in ['price', 'mrp', 'stock_level', 'is_organic']:
            if field in request.data:
                setattr(batch, field, request.data[field])
        batch.save()
        return Response(FarmerBatchSerializer(batch).data)


@method_decorator(csrf_exempt, name='dispatch')
class FarmerPayoutView(APIView):
    """GET /api/farmer/payouts/"""
    permission_classes = [IsFarmerUser]

    def get(self, request):
        try:
            profile = request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)
        payouts = FarmerPayout.objects.filter(farmer=profile)
        serializer = FarmerPayoutSerializer(payouts, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class FarmerOrderListView(APIView):
    """GET /api/farmer/orders/ - Orders containing this farmer's batches."""
    permission_classes = [IsFarmerUser]

    def get(self, request):
        try:
            profile = request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        orders = (
            Order.objects.filter(items__batch__farmer=profile)
            .prefetch_related('items')
            .select_related('user')
            .distinct()
            .order_by('-created_at')[:50]
        )

        data = []
        for order in orders:
            farmer_items = [item for item in order.items.all() if item.batch and item.batch.farmer_id == profile.id]
            data.append({
                'id': order.id,
                'tracking_id': order.tracking_id,
                'customer_name': order.user.get_full_name() or order.user.username,
                'status': order.status,
                'total': float(sum(item.price * item.quantity for item in farmer_items)),
                'created_at': order.created_at,
                'items': [
                    {
                        'product_name': item.product_name,
                        'quantity': item.quantity,
                        'unit': item.unit,
                        'price': float(item.price),
                        'total': float(item.price * item.quantity),
                    }
                    for item in farmer_items
                ],
            })

        return Response(data)


@method_decorator(csrf_exempt, name='dispatch')
class BankDetailsView(APIView):
    """GET/POST /api/farmer/bank/ - Manage farmer bank account."""
    permission_classes = [IsFarmerUser]

    def get(self, request):
        try:
            profile = request.user.farmer_profile
            bank_details = profile.bank_details
            serializer = BankDetailsSerializer(bank_details)
            return Response(serializer.data)
        except (FarmerProfile.DoesNotExist, BankDetails.DoesNotExist):
            return Response({}, status=status.HTTP_200_OK)

    def post(self, request):
        profile = request.user.farmer_profile
        bank_details, _ = BankDetails.objects.get_or_create(farmer=profile)
        serializer = BankDetailsSerializer(bank_details, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class NotificationListView(APIView):
    """GET /api/farmer/notifications/ - List all notifications."""
    permission_classes = [IsFarmerUser]

    def get(self, request):
        profile = request.user.farmer_profile
        notifications = profile.notifications.all()[:50]
        serializer = FarmerNotificationSerializer(notifications, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Mark as read."""
        notification_id = request.data.get('id')
        if not notification_id:
            # Mark all as read
            request.user.farmer_profile.notifications.update(is_read=True)
            return Response({'status': 'all marked as read'})
        
        try:
            notif = request.user.farmer_profile.notifications.get(id=notification_id)
            notif.is_read = True
            notif.save()
            return Response({'status': 'marked as read'})
        except FarmerNotification.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
