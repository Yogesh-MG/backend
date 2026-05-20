"""
Agent API Views — REST endpoints for chat sessions.

Endpoints:
  POST   /api/agents/sessions/           → Create a new chat session
  GET    /api/agents/sessions/           → List user's sessions
  GET    /api/agents/sessions/<id>/      → Get session with messages
  POST   /api/agents/sessions/<id>/chat/ → Send a message, get reply
"""

import logging
from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.agents.models import AgentSession
from apps.agents.serializers import (
    AgentSessionSerializer,
    AgentSessionListSerializer,
    ChatInputSerializer,
    CreateSessionSerializer,
)
from apps.agents.engine.base import FreshOnAgent
from apps.agents.tools.customer import customer_tools

logger = logging.getLogger(__name__)


def _get_agent_for_type(agent_type: str, user):
    """Create the appropriate agent for the given type."""
    # For now, all agent types use customer_tools
    # Later we'll add farmer_tools, delivery_tools
    tool_registries = {
        "CUSTOMER_ASSISTANT": customer_tools,
        # "FARMER_INVENTORY": farmer_tools,
        # "DELIVERY_OPTIMIZER": delivery_tools,
    }
    
    registry = tool_registries.get(agent_type, customer_tools)
    return FreshOnAgent(
        agent_type=agent_type,
        tool_registry=registry,
        user=user,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_session(request):
    """
    Create a new agent chat session.
    
    POST /api/agents/sessions/
    Body: {"agent_type": "CUSTOMER_ASSISTANT", "initial_message": "optional"}
    """
    serializer = CreateSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    agent_type = serializer.validated_data["agent_type"]
    initial_message = serializer.validated_data.get("initial_message")
    
    session = AgentSession.objects.create(
        user=request.user,
        agent_type=agent_type,
    )
    
    # If an initial message was provided, process it immediately
    reply = None
    if initial_message:
        agent = _get_agent_for_type(agent_type, request.user)
        reply = agent.chat(session, initial_message)
    
    session_data = AgentSessionSerializer(session).data
    response_data = {"session": session_data}
    if reply:
        response_data["reply"] = reply
    
    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_sessions(request):
    """
    List the user's recent chat sessions.
    
    GET /api/agents/sessions/
    """
    sessions = AgentSession.objects.filter(
        user=request.user
    ).annotate(
        message_count=Count("messages")
    ).order_by("-updated_at")[:20]
    
    serializer = AgentSessionListSerializer(sessions, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_session(request, session_id):
    """
    Get a session with its full message history.
    
    GET /api/agents/sessions/<session_id>/
    """
    try:
        session = AgentSession.objects.prefetch_related(
            "messages", "messages__tool_calls"
        ).get(id=session_id, user=request.user)
    except AgentSession.DoesNotExist:
        return Response(
            {"error": "Session not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    serializer = AgentSessionSerializer(session)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat(request, session_id):
    """
    Send a message to the agent and get a reply.
    
    POST /api/agents/sessions/<session_id>/chat/
    Body: {"message": "Where is my order FRSH-A1B2C3?"}
    """
    # Validate input
    input_serializer = ChatInputSerializer(data=request.data)
    input_serializer.is_valid(raise_exception=True)
    user_message = input_serializer.validated_data["message"]
    
    # Get the session
    try:
        session = AgentSession.objects.get(id=session_id, user=request.user)
    except AgentSession.DoesNotExist:
        return Response(
            {"error": "Session not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    if session.status != "ACTIVE":
        return Response(
            {"error": "This session is no longer active"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Run the agent
    agent = _get_agent_for_type(session.agent_type, request.user)
    
    try:
        reply = agent.chat(session, user_message)
    except Exception as e:
        logger.error(f"[API] Agent error: {e}")
        return Response(
            {"error": "Agent encountered an error. Please try again."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    
    return Response({
        "reply": reply,
        "session_id": str(session.id),
    })
