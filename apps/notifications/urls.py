"""
URL configuration for the notifications app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('vapid-key/', views.VapidPublicKeyView.as_view(), name='vapid_public_key'),
    path('subscribe/', views.SubscribeView.as_view(), name='subscribe'),
    path('unsubscribe/', views.UnsubscribeView.as_view(), name='unsubscribe'),
    path('test/', views.TestNotificationView.as_view(), name='test_notification'),
]