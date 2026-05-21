"""
WebSocket routing configuration for the agents app.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/agents/$', consumers.AgentChatConsumer.as_asgi()),
]
