"""
Push notification utilities for farmers.

This module provides functions to send Firebase Cloud Messaging (FCM)
notifications to farmers' devices.
"""
import logging
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


def send_farmer_push_notification(farmer_profile, title: str, body: str, data: Optional[dict] = None) -> bool:
    """
    Send a push notification to a farmer's device via FCM.
    
    Args:
        farmer_profile: The FarmerProfile instance
        title: Notification title
        body: Notification body
        data: Optional dict of additional data to send
        
    Returns:
        True if notification was sent successfully, False otherwise
    """
    if not farmer_profile.fcm_token:
        logger.debug(f"No FCM token for farmer {farmer_profile.id}")
        return False
    
    # Check if firebase-admin is configured
    try:
        import firebase_admin
        from firebase_admin import messaging
        
        # Initialize Firebase if not already done
        if not firebase_admin._apps:
            cred = firebase_admin.credentials.Certificate(
                getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None) or 
                getattr(settings, 'FIREBASE_CREDENTIALS', None)
            )
            firebase_admin.initialize_app(cred)
        
        # Build the message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=farmer_profile.fcm_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id='farmer_notifications',
                    priority='high',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(title=title, body=body),
                        badge=1,
                        sound='default',
                    ),
                ),
            ),
        )
        
        # Send the message
        response = messaging.send(message)
        logger.info(f"Successfully sent FCM notification to farmer {farmer_profile.id}: {response}")
        return True
        
    except ImportError:
        logger.warning("firebase-admin not installed. Skipping FCM notification.")
        return False
    except Exception as e:
        logger.error(f"Failed to send FCM notification to farmer {farmer_profile.id}: {e}")
        # If the token is invalid, we might want to clear it
        if "registration-token-not-registered" in str(e).lower():
            farmer_profile.fcm_token = ""
            farmer_profile.save(update_fields=['fcm_token'])
        return False


def notify_new_order(farmer_profile, order_id: str, product_name: str, quantity: str) -> bool:
    """Send notification when a new order is placed for farmer's product."""
    return send_farmer_push_notification(
        farmer_profile,
        title="🛒 New Order Received!",
        body=f"Order for {quantity} of {product_name}",
        data={
            'type': 'new_order',
            'order_id': order_id,
            'product_name': product_name,
            'quantity': quantity,
        }
    )


def notify_payment_credited(farmer_profile, amount: str, payout_id: str) -> bool:
    """Send notification when a payout is credited to farmer's account."""
    return send_farmer_push_notification(
        farmer_profile,
        title="💰 Payment Credited!",
        body=f"₹{amount} has been credited to your account",
        data={
            'type': 'payment_credited',
            'amount': amount,
            'payout_id': payout_id,
        }
    )


def notify_pickup_scheduled(farmer_profile, order_id: str, pickup_time: str) -> bool:
    """Send notification when a pickup is scheduled for farmer's order."""
    return send_farmer_push_notification(
        farmer_profile,
        title="🚚 Pickup Scheduled",
        body=f"Pickup scheduled for order {order_id} at {pickup_time}",
        data={
            'type': 'pickup_scheduled',
            'order_id': order_id,
            'pickup_time': pickup_time,
        }
    )


def notify_quality_alert(farmer_profile, message: str) -> bool:
    """Send notification for quality-related alerts."""
    return send_farmer_push_notification(
        farmer_profile,
        title="⚠️ Quality Alert",
        body=message,
        data={
            'type': 'quality_alert',
            'message': message,
        }
    )
