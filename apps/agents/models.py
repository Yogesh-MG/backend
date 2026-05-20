import uuid
from django.db import models
from django.conf import settings

class AgentSession(models.Model):
    """Represents an active task or chat thread managed by an agent."""
    AGENT_TYPES = [
        ('FARMER_INVENTORY', "Farmer's Inventory Agent"),
        ('DELIVERY_OPTIMIZER', "Delivery Optimization Agent"),
        ('CUSTOMER_ASSISTANT', "Customer Assistance Agent"),
        ('FOUNDER_BI', "Founder's BI Command Agent"),
    ]
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    agent_type = models.CharField(max_length=30, choices=AGENT_TYPES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_agent_type_display()} Session ({self.status}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class AgentMessage(models.Model):
    """Represents a single turn (thought, prompt, or output) inside an agent session."""
    SENDER_CHOICES = [
        ('USER', 'User'),
        ('AGENT_THOUGHT', 'Agent Internal Thought'),
        ('AGENT_OUTPUT', 'Agent Final Response'),
        ('SYSTEM', 'System/Error'),
    ]

    session = models.ForeignKey(AgentSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} Message - Session {str(self.session.id)[:8]}..."

class AgentToolCall(models.Model):
    """Audit log of database-manipulating actions executed by the agent."""
    message = models.ForeignKey(AgentMessage, on_delete=models.CASCADE, related_name='tool_calls')
    tool_name = models.CharField(max_length=100)
    arguments = models.JSONField()
    result = models.JSONField(null=True, blank=True)
    is_success = models.BooleanField(default=True)
    executed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tool Call: {self.tool_name} (Success: {self.is_success})"
