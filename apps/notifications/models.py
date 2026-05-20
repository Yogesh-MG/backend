"""
Models for the notifications app.

Handles Web Push subscriptions and notification history.
"""
import uuid
from django.db import models
from django.conf import settings


class WebPushSubscription(models.Model):
    """
    Stores a user's Web Push subscription for sending notifications
    even when the user is offline.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='webpush_subscriptions',
    )
    endpoint = models.URLField()
    p256dh_key = models.CharField(max_length=255)  # Public key
    auth_key = models.CharField(max_length=255)    # Auth secret
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['endpoint']),
        ]

    def __str__(self):
        return f"Push subscription for {self.user.username} ({self.endpoint[:50]}...)"


class NotificationHistory(models.Model):
    """
    History of notifications sent to users.
    Useful for debugging and analytics.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]

    CHANNEL_CHOICES = [
        ('websocket', 'WebSocket'),
        ('webpush', 'Web Push'),
        ('fcm', 'Firebase Cloud Messaging'),
        ('email', 'Email'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_history',
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name_plural = 'Notification histories'

    def __str__(self):
        return f"{self.channel} to {self.user.username}: {self.title[:50]}"