"""
ASGI configuration for freshon_os project.

Exposes the ASGI callable as a module-level variable named `application`.
For more information on this file, see:
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freshon_os.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import routing after Django setup
from apps.notifications.routing import websocket_urlpatterns as notifications_patterns
from apps.agents.routing import websocket_urlpatterns as agents_patterns

# Combine all WebSocket patterns
all_websocket_patterns = notifications_patterns + agents_patterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            all_websocket_patterns
        )
    ),
})