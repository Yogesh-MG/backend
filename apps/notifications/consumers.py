"""
WebSocket consumer for real-time notifications.

Uses Django Channels to handle authenticated WebSocket connections
and deliver notifications in real-time.
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for sending real-time notifications to users.
    
    Connection URL: /ws/notifications/
    Authentication: JWT token passed as query parameter ?token=<jwt>
    """

    async def connect(self):
        """Handle connection and authenticate user."""
        self.user = await self.get_user_from_token()
        
        if self.user.is_anonymous:
            logger.warning("[Notifications] Connection rejected: anonymous user")
            await self.close(code=4001)  # Authentication required
            return

        self.user_group_name = f"user_{self.user.id}"
        
        # Join user-specific group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"[Notifications] User {self.user.username} connected to WebSocket")
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Connected as {self.user.username}',
            'user_id': str(self.user.id),
        }))

    async def disconnect(self, close_code):
        """Handle disconnection."""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            logger.info(f"[Notifications] User {self.user.username} disconnected (code: {close_code})")

    async def receive(self, text_data):
        """Handle incoming messages from client."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'unknown')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            elif message_type == 'mark_read':
                # Handle marking notifications as read
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)
                await self.send(text_data=json.dumps({
                    'type': 'marked_read',
                    'notification_id': notification_id,
                }))
            else:
                logger.warning(f"[Notifications] Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("[Notifications] Invalid JSON received")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON',
            }))

    async def notification_message(self, event):
        """
        Handle notification messages sent to the user's group.
        This is called when a notification is broadcast to the group.
        """
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'id': event.get('id'),
            'title': event.get('title'),
            'body': event.get('body'),
            'notification_type': event.get('notification_type', 'info'),
            'data': event.get('data', {}),
            'timestamp': event.get('timestamp'),
        }))

    @database_sync_to_async
    def get_user_from_token(self):
        """Extract and validate JWT token from query parameters."""
        try:
            query_string = self.scope.get('query_string', b'').decode('utf-8')
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            token = params.get('token', '')
            
            if not token:
                return AnonymousUser()
            
            # Validate JWT token
            access_token = AccessToken(token)
            user_id = access_token.get('user_id')
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                return AnonymousUser()
                
        except Exception as e:
            logger.error(f"[Notifications] Token validation error: {e}")
            return AnonymousUser()

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read in the database."""
        try:
            from apps.farmer.models import FarmerNotification
            notification = FarmerNotification.objects.get(
                id=notification_id,
                farmer__user=self.user
            )
            notification.is_read = True
            notification.save(update_fields=['is_read'])
        except Exception as e:
            logger.error(f"[Notifications] Failed to mark notification as read: {e}")


class BroadcastConsumer(AsyncWebsocketConsumer):
    """
    Admin-only consumer for broadcasting messages to all users.
    Used for system-wide announcements.
    """
    
    async def connect(self):
        """Only allow admin users."""
        self.user = await self.get_user_from_token()
        
        if not self.user.is_staff:
            await self.close(code=4003)  # Forbidden
            return
            
        await self.channel_layer.group_add("broadcast", self.channel_name)
        await self.accept()
        logger.info(f"[Notifications] Admin {self.user.username} connected to broadcast")

    async def disconnect(self, close_code):
        """Leave broadcast group."""
        await self.channel_layer.group_discard("broadcast", self.channel_name)

    async def receive(self, text_data):
        """Handle broadcast requests from admin."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'broadcast':
                await self.channel_layer.group_send(
                    "broadcast",
                    {
                        'type': 'broadcast_message',
                        'title': data.get('title'),
                        'body': data.get('body'),
                        'data': data.get('data', {}),
                    }
                )
        except json.JSONDecodeError:
            pass

    async def broadcast_message(self, event):
        """Send broadcast to admin."""
        await self.send(text_data=json.dumps({
            'type': 'broadcast',
            'title': event.get('title'),
            'body': event.get('body'),
            'data': event.get('data'),
        }))

    @database_sync_to_async
    def get_user_from_token(self):
        """Same as NotificationConsumer."""
        try:
            query_string = self.scope.get('query_string', b'').decode('utf-8')
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            token = params.get('token', '')
            
            if not token:
                return AnonymousUser()
            
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(token)
            user_id = access_token.get('user_id')
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                return AnonymousUser()
                
        except Exception:
            return AnonymousUser()