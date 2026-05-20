"""
Agent API Serializers — Data validation and formatting for the API.
"""

from rest_framework import serializers
from apps.agents.models import AgentSession, AgentMessage, AgentToolCall


class AgentToolCallSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentToolCall
        fields = ["tool_name", "arguments", "result", "is_success", "executed_at"]


class AgentMessageSerializer(serializers.ModelSerializer):
    tool_calls = AgentToolCallSerializer(many=True, read_only=True)
    
    class Meta:
        model = AgentMessage
        fields = ["id", "sender", "content", "created_at", "tool_calls"]


class AgentSessionSerializer(serializers.ModelSerializer):
    messages = AgentMessageSerializer(many=True, read_only=True)
    agent_type_display = serializers.CharField(source="get_agent_type_display", read_only=True)
    
    class Meta:
        model = AgentSession
        fields = [
            "id", "agent_type", "agent_type_display", "status",
            "created_at", "updated_at", "messages",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class AgentSessionListSerializer(serializers.ModelSerializer):
    """Lighter serializer for listing sessions (no messages)."""
    agent_type_display = serializers.CharField(source="get_agent_type_display", read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = AgentSession
        fields = [
            "id", "agent_type", "agent_type_display", "status",
            "created_at", "updated_at", "message_count", "last_message",
        ]
    
    def get_last_message(self, obj):
        last = obj.messages.filter(
            sender__in=["USER", "AGENT_OUTPUT"]
        ).order_by("-created_at").first()
        if last:
            return {
                "sender": last.sender,
                "content": last.content[:100],
                "created_at": last.created_at,
            }
        return None


class ChatInputSerializer(serializers.Serializer):
    """Validates incoming chat messages."""
    message = serializers.CharField(max_length=2000, min_length=1)


class CreateSessionSerializer(serializers.Serializer):
    """Validates session creation requests."""
    agent_type = serializers.ChoiceField(
        choices=["CUSTOMER_ASSISTANT", "FARMER_INVENTORY", "DELIVERY_OPTIMIZER"],
        default="CUSTOMER_ASSISTANT",
    )
    initial_message = serializers.CharField(max_length=2000, required=False)
