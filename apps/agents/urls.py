"""
Agent URL Configuration
"""

from django.urls import path
from apps.agents import views

urlpatterns = [
    # Session management
    path("sessions/", views.create_session, name="agent-create-session"),
    path("sessions/list/", views.list_sessions, name="agent-list-sessions"),
    path("sessions/<uuid:session_id>/", views.get_session, name="agent-get-session"),
    
    # Chat
    path("sessions/<uuid:session_id>/chat/", views.chat, name="agent-chat"),
]
