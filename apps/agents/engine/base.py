"""
Base Agent — The multi-turn ReAct engine.

This is the production version of lesson_2's agent_chat().
It runs the Reason → Act → Observe → Answer loop with:
  - Configurable system prompts per agent type
  - Tool registry integration
  - Session persistence (Django models)
  - Multi-turn conversation memory
  - Error handling and fallbacks
"""

import json
import logging
from apps.agents.models import AgentSession, AgentMessage, AgentToolCall
from apps.agents.engine.router import get_router
from apps.agents.engine.tools import ToolRegistry, parse_tool_call
from apps.agents.engine.prompts import get_system_prompt

logger = logging.getLogger(__name__)

# Maximum ReAct iterations to prevent infinite loops
MAX_REACT_STEPS = 3


class FreshOnAgent:
    """
    The core agent that handles a conversation session.
    
    Usage:
        agent = FreshOnAgent(
            agent_type="CUSTOMER_ASSISTANT",
            tool_registry=customer_tools,
            user=request.user,
        )
        reply = agent.chat(session_id, "Where is my order?")
    """
    
    def __init__(
        self,
        agent_type: str,
        tool_registry: ToolRegistry,
        user=None,
    ):
        self.agent_type = agent_type
        self.tools = tool_registry
        self.user = user
        self.router = get_router()
    
    def chat(self, session: AgentSession, user_message: str) -> str:
        """
        Process a user message and return the agent's response.
        
        This is the ReAct loop:
          1. Build conversation context from session history
          2. Send to LLM with tool descriptions
          3. If LLM wants a tool → execute → feed result back → repeat
          4. Return the final text response
          
        All messages and tool calls are persisted to the database.
        """
        # Save the user's message
        AgentMessage.objects.create(
            session=session,
            sender="USER",
            content=user_message,
        )
        
        # Build message history from the session
        messages = self._build_messages(session)
        
        # ReAct loop (max MAX_REACT_STEPS iterations)
        for step in range(MAX_REACT_STEPS):
            logger.info(f"[AGENT] ReAct step {step + 1}/{MAX_REACT_STEPS}")
            
            try:
                ai_reply = self.router.chat(messages)
            except (ConnectionError, TimeoutError) as e:
                error_msg = f"I'm having trouble connecting right now. Please try again in a moment. 🔄"
                self._save_agent_message(session, error_msg, is_error=True)
                return error_msg
            except Exception as e:
                error_msg = "Something went wrong on my end. Please try again."
                logger.error(f"[AGENT] LLM error: {e}")
                self._save_agent_message(session, error_msg, is_error=True)
                return error_msg
            
            # Check if the AI wants to call a tool
            tool_call = parse_tool_call(ai_reply, self.tools)
            
            if tool_call:
                tool_name = tool_call["tool"]
                tool_args = tool_call.get("args", {})
                
                logger.info(f"[AGENT] Tool call: {tool_name}({tool_args})")
                
                # Save the thought (tool call request)
                thought_msg = AgentMessage.objects.create(
                    session=session,
                    sender="AGENT_THOUGHT",
                    content=ai_reply,
                )
                
                # Execute the tool
                result = self.tools.execute(tool_name, tool_args, user=self.user)
                result_str = json.dumps(result, indent=2, default=str, ensure_ascii=False)
                
                # Save the tool call audit
                AgentToolCall.objects.create(
                    message=thought_msg,
                    tool_name=tool_name,
                    arguments=tool_args,
                    result=result,
                    is_success="error" not in result if isinstance(result, dict) else True,
                )
                
                # Feed result back into conversation
                messages.append({"role": "assistant", "content": ai_reply})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Tool result for {tool_name}:\n{result_str}\n\n"
                        "Now answer the customer's question using this data. "
                        "Be natural and friendly."
                    ),
                })
                
                # Continue the loop — AI will now process the result
                continue
            
            else:
                # No tool call — this is the final answer
                self._save_agent_message(session, ai_reply)
                return ai_reply
        
        # If we exhausted all steps, return the last response
        fallback = "I need a moment to process this. Could you rephrase your question?"
        self._save_agent_message(session, fallback)
        return fallback
    
    def _build_messages(self, session: AgentSession) -> list[dict]:
        """
        Build the full message list from session history.
        
        Returns: [system_msg, ...history..., latest_user_msg]
        """
        # System prompt with tools
        tools_text = self.tools.format_for_prompt()
        system_prompt = get_system_prompt(self.agent_type, tools_text)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Load conversation history from DB
        history = AgentMessage.objects.filter(
            session=session
        ).order_by("created_at")
        
        for msg in history:
            if msg.sender == "USER":
                messages.append({"role": "user", "content": msg.content})
            elif msg.sender == "AGENT_OUTPUT":
                messages.append({"role": "assistant", "content": msg.content})
            # Skip AGENT_THOUGHT and SYSTEM messages (internal only)
        
        return messages
    
    def _save_agent_message(self, session: AgentSession, content: str, is_error: bool = False):
        """Save the agent's final response to the database."""
        AgentMessage.objects.create(
            session=session,
            sender="SYSTEM" if is_error else "AGENT_OUTPUT",
            content=content,
        )
