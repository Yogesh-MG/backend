"""
API views for the notifications app.

Handles Web Push subscription management and VAPID key distribution.
"""
import logging
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import WebPushSubscription
from .services import send_user_notification

logger = logging.getLogger(__name__)


class VapidPublicKeyView(APIView):
    """
    GET /api/notifications/vapid-key/
    
    Returns the VAPID public key for Web Push subscription.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        public_key = settings.WEBPUSH_VAPID_PUBLIC_KEY
        
        if not public_key:
            return Response(
                {'error': 'Web Push not configured'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        return Response({'publicKey': public_key})


@method_decorator(csrf_exempt, name='dispatch')
class SubscribeView(APIView):
    """
    POST /api/notifications/subscribe/
    
    Subscribe to Web Push notifications.
    Request body: { endpoint, keys: { p256dh, auth } }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        endpoint = request.data.get('endpoint')
        keys = request.data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')
        
        if not all([endpoint, p256dh, auth]):
            return Response(
                {'error': 'endpoint, keys.p256dh, and keys.auth are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Deactivate any existing subscriptions for this endpoint
        WebPushSubscription.objects.filter(
            endpoint=endpoint,
            is_active=True
        ).update(is_active=False)
        
        # Create new subscription
        subscription, created = WebPushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={
                'p256dh_key': p256dh,
                'auth_key': auth,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'is_active': True,
            }
        )
        
        action = 'created' if created else 'updated'
        logger.info(f"[Notifications] Web Push subscription {action} for user {request.user.username}")
        
        return Response({
            'status': 'subscribed',
            'subscription_id': str(subscription.id),
        })


@method_decorator(csrf_exempt, name='dispatch')
class UnsubscribeView(APIView):
    """
    POST /api/notifications/unsubscribe/
    
    Unsubscribe from Web Push notifications.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        endpoint = request.data.get('endpoint')
        
        if endpoint:
            # Deactivate specific subscription
            WebPushSubscription.objects.filter(
                user=request.user,
                endpoint=endpoint
            ).update(is_active=False)
        else:
            # Deactivate all subscriptions for this user
            WebPushSubscription.objects.filter(
                user=request.user
            ).update(is_active=False)
        
        logger.info(f"[Notifications] Web Push unsubscribed for user {request.user.username}")
        
        return Response({'status': 'unsubscribed'})


class TestNotificationView(APIView):
    """
    POST /api/notifications/test/
    
    Send a test notification to the current user.
    Only for development/testing.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        title = request.data.get('title', 'Test Notification')
        body = request.data.get('body', 'This is a test notification from FreshOn!')
        
        results = send_user_notification(
            user_id=request.user.id,
            title=title,
            body=body,
            notification_type='info',
            payload={'test': True}
        )
        
        return Response({
            'status': 'sent',
            'channels': results,
            'delivered_via': [ch for ch, success in results.items() if success] or None,
        })