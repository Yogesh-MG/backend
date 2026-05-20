"""
Notification service for broadcasting messages to users.

This module provides high-level functions for sending notifications
via WebSocket, Web Push, FCM, or all channels.
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def send_user_notification(
    user_id: int,
    title: str,
    body: str,
    notification_type: str = 'info',
    payload: Optional[Dict[str, Any]] = None,
    channels: Optional[list] = None
) -> Dict[str, Any]:
    """
    Send a notification to a specific user across all available channels.
    
    Args:
        user_id: The target user's ID
        title: Notification title
        body: Notification body
        notification_type: Type of notification (info, success, warning, error)
        payload: Additional data to include
        channels: List of channels to use ('websocket', 'webpush', 'fcm'). 
                  Defaults to all available.
    
    Returns:
        Dict with status of each channel
    """
    if channels is None:
        channels = ['websocket', 'webpush', 'fcm']
    
    results = {
        'websocket': False,
        'webpush': False,
        'fcm': False,
    }
    
    notification_data = {
        'id': str(datetime.now().timestamp()),
        'title': title,
        'body': body,
        'notification_type': notification_type,
        'data': payload or {},
        'timestamp': datetime.now().isoformat(),
    }
    
    # Try WebSocket first (real-time)
    if 'websocket' in channels:
        try:
            results['websocket'] = _send_websocket_notification(user_id, notification_data)
        except Exception as e:
            logger.error(f"[Notifications] WebSocket send failed: {e}")
    
    # If WebSocket failed or not requested, try Web Push
    if not results['websocket'] and 'webpush' in channels:
        try:
            results['webpush'] = _send_webpush_notification(user_id, notification_data)
        except Exception as e:
            logger.error(f"[Notifications] Web Push send failed: {e}")
    
    # Try FCM as last resort
    if not results['websocket'] and not results['webpush'] and 'fcm' in channels:
        try:
            results['fcm'] = _send_fcm_notification(user_id, notification_data)
        except Exception as e:
            logger.error(f"[Notifications] FCM send failed: {e}")
    
    # Log the notification attempt
    _log_notification(user_id, title, body, results)
    
    return results


def _send_websocket_notification(user_id: int, data: Dict[str, Any]) -> bool:
    """
    Send notification via WebSocket (Django Channels).
    Returns True if message was sent (user is online), False otherwise.
    """
    channel_layer = get_channel_layer()
    group_name = f"user_{user_id}"
    
    # Send to user's group
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'notification_message',
            **data
        }
    )
    
    # Note: We can't know if the user actually received it,
    # but the message was sent to the channel layer
    logger.info(f"[Notifications] WebSocket notification sent to user {user_id}")
    return True


def _send_webpush_notification(user_id: int, data: Dict[str, Any]) -> bool:
    """
    Send notification via Web Push (for browsers/PWAs).
    Returns True if at least one subscription received the notification.
    """
    from .models import WebPushSubscription
    
    subscriptions = WebPushSubscription.objects.filter(
        user_id=user_id,
        is_active=True
    )
    
    if not subscriptions.exists():
        logger.debug(f"[Notifications] No Web Push subscriptions for user {user_id}")
        return False
    
    if not settings.WEBPUSH_VAPID_PRIVATE_KEY:
        logger.warning("[Notifications] WEBPUSH_VAPID_PRIVATE_KEY not set")
        return False
    
    try:
        from pywebpush import webpush, WebPushException
        
        sent_count = 0
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub.endpoint,
                        'keys': {
                            'p256dh': sub.p256dh_key,
                            'auth': sub.auth_key,
                        }
                    },
                    data=json.dumps({
                        'title': data['title'],
                        'body': data['body'],
                        'type': data['notification_type'],
                        'data': data['data'],
                    }),
                    vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
                    vapid_claims={
                        'sub': f'mailto:{settings.WEBPUSH_VAPID_ADMIN_EMAIL}'
                    }
                )
                sent_count += 1
                
                # Update last used timestamp
                sub.last_used_at = datetime.now()
                sub.save(update_fields=['last_used_at'])
                
            except WebPushException as e:
                logger.error(f"[Notifications] WebPush failed for subscription {sub.id}: {e}")
                # Deactivate invalid subscriptions
                if 'expired' in str(e).lower() or 'invalid' in str(e).lower():
                    sub.is_active = False
                    sub.save(update_fields=['is_active'])
        
        logger.info(f"[Notifications] Web Push sent to {sent_count}/{subscriptions.count()} subscriptions for user {user_id}")
        return sent_count > 0
        
    except ImportError:
        logger.error("[Notifications] pywebpush not installed")
        return False


def _send_fcm_notification(user_id: int, data: Dict[str, Any]) -> bool:
    """
    Send notification via Firebase Cloud Messaging (for mobile apps).
    Returns True if notification was sent successfully.
    """
    try:
        from apps.accounts.models import FarmerProfile
        from apps.farmer.notifications import send_farmer_push_notification
        
        # Try to get FCM token from FarmerProfile
        try:
            profile = FarmerProfile.objects.get(user_id=user_id)
            if profile.fcm_token:
                success = send_farmer_push_notification(
                    profile,
                    title=data['title'],
                    body=data['body'],
                    data=data['data']
                )
                if success:
                    logger.info(f"[Notifications] FCM notification sent to user {user_id}")
                return success
        except FarmerProfile.DoesNotExist:
            pass
        
        # TODO: Check other profile types (Customer, DeliveryPartner, etc.)
        
        logger.debug(f"[Notifications] No FCM token found for user {user_id}")
        return False
        
    except Exception as e:
        logger.error(f"[Notifications] FCM send error: {e}")
        return False


def _log_notification(user_id: int, title: str, body: str, results: Dict[str, bool]):
    """Log notification to database for analytics."""
    try:
        from .models import NotificationHistory
        
        # Determine which channel succeeded
        channel = 'failed'
        for ch, success in results.items():
            if success:
                channel = ch
                break
        
        NotificationHistory.objects.create(
            user_id=user_id,
            title=title,
            body=body,
            channel=channel,
            status='sent' if any(results.values()) else 'failed',
        )
    except Exception as e:
        logger.error(f"[Notifications] Failed to log notification: {e}")


def broadcast_notification(
    title: str,
    body: str,
    notification_type: str = 'info',
    payload: Optional[Dict[str, Any]] = None,
    exclude_users: Optional[list] = None
) -> int:
    """
    Broadcast a notification to all connected users.
    
    Returns:
        Number of users the notification was sent to
    """
    channel_layer = get_channel_layer()
    
    data = {
        'type': 'broadcast_message',
        'title': title,
        'body': body,
        'notification_type': notification_type,
        'data': payload or {},
        'timestamp': datetime.now().isoformat(),
    }
    
    async_to_sync(channel_layer.group_send)("broadcast", data)
    
    logger.info(f"[Notifications] Broadcast sent: {title}")
    return -1  # We don't know exact count with channel layer


def get_user_notification_stats(user_id: int) -> Dict[str, Any]:
    """
    Get notification statistics for a user.
    """
    from .models import NotificationHistory, WebPushSubscription
    
    history = NotificationHistory.objects.filter(user_id=user_id)
    subscriptions = WebPushSubscription.objects.filter(user_id=user_id, is_active=True)
    
    return {
        'total_sent': history.count(),
        'delivered': history.filter(status='delivered').count(),
        'failed': history.filter(status='failed').count(),
        'webpush_subscriptions': subscriptions.count(),
        'channels_used': list(history.values_list('channel', flat=True).distinct()),
    }