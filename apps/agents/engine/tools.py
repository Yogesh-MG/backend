"""
Tool Registry — Central registry of all tools agents can call.

Each tool is a plain Python function that queries Django models
and returns a dict/list result. The registry maps tool names to
their functions + metadata (description, parameters).

This is the production version of what you built in Lesson 2's
TOOL_REGISTRY.
"""

import json
import re
import logging
from dataclasses import dataclass, field
from typing import Callable, Any

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """A single tool that an agent can call."""
    name: str
    description: str
    parameters: dict[str, str]  # param_name -> description
    function: Callable[..., Any]
    requires_user: bool = False  # If True, the user object is auto-injected


class ToolRegistry:
    """
    Central registry of tools available to agents.
    
    Usage:
        registry = ToolRegistry()
        
        @registry.register(
            name="get_order_status",
            description="Look up order status by tracking ID",
            parameters={"tracking_id": "The order tracking ID (e.g., FRSH-A1B2C3)"},
        )
        def get_order_status(tracking_id: str) -> dict:
            order = Order.objects.get(tracking_id=tracking_id)
            return {"status": order.status, ...}
    """
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
    
    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, str] | None = None,
        requires_user: bool = False,
    ):
        """Decorator to register a function as an agent tool."""
        def decorator(func: Callable):
            self._tools[name] = Tool(
                name=name,
                description=description,
                parameters=parameters or {},
                function=func,
                requires_user=requires_user,
            )
            return func
        return decorator
    
    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def get_names(self) -> list[str]:
        """Get all tool names."""
        return list(self._tools.keys())
    
    def format_for_prompt(self, tool_names: list[str] | None = None) -> str:
        """
        Format tools into a string the LLM can understand.
        
        If tool_names is provided, only include those tools.
        Otherwise include all registered tools.
        """
        tools = self._tools.values()
        if tool_names:
            tools = [t for t in tools if t.name in tool_names]
        
        lines = ["You have the following tools available:\n"]
        for tool in tools:
            params = ", ".join(f'{k}: {v}' for k, v in tool.parameters.items())
            lines.append(f"  - {tool.name}({params}): {tool.description}")
        
        lines.append(
            '\nTo use a tool, respond with ONLY this on a single line:'
            '\nTOOL_CALL: {"tool": "tool_name", "args": {"param": "value"}}'
            '\n\nIf you do NOT need a tool, respond normally with text.'
            '\nAfter receiving a tool result, give a natural, friendly answer using that data.'
            '\nNEVER make up data. ALWAYS use a tool when you need factual information.'
        )
        return "\n".join(lines)
    
    def execute(self, tool_name: str, args: dict, user=None) -> dict | list:
        """
        Execute a tool by name with the given arguments.
        
        Returns the tool's result or an error dict.
        """
        tool = self._tools.get(tool_name)
        if not tool:
            logger.warning(f"[TOOL] Unknown tool called: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            # Inject user if the tool requires it
            if tool.requires_user and user:
                args["user"] = user
            
            logger.info(f"[TOOL] Executing {tool_name}({args})")
            result = tool.function(**args)
            logger.info(f"[TOOL] {tool_name} returned successfully")
            return result
            
        except Exception as e:
            logger.error(f"[TOOL] {tool_name} failed: {e}")
            return {"error": f"Tool execution failed: {str(e)}"}


def parse_tool_call(ai_response: str, registry: ToolRegistry) -> dict | None:
    """
    Extract a tool call from the AI's response.
    
    Handles multiple formats:
      1. TOOL_CALL: {"tool": "name", "args": {...}}
      2. {"tool": "name", "args": {...}}
      3. {"tool_name": "value"}  (shorthand)
      4. JSON in markdown code blocks
    
    Returns {"tool": "name", "args": {...}} or None.
    """
    
    # Method 1: TOOL_CALL: prefix
    for line in ai_response.split('\n'):
        line = line.strip()
        if line.startswith('TOOL_CALL:'):
            json_str = line[len('TOOL_CALL:'):].strip()
            try:
                parsed = json.loads(json_str)
                if "tool" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass
    
    # Method 2: {"tool": ...} on any line
    for line in ai_response.split('\n'):
        line = line.strip().strip('`')
        if line.startswith('{') and '"tool"' in line:
            try:
                parsed = json.loads(line)
                if "tool" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue
    
    # Method 3: Regex search for {"tool": ...}
    json_pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+"[^{}]*\}'
    matches = re.findall(json_pattern, ai_response)
    for match in matches:
        try:
            parsed = json.loads(match)
            if "tool" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue
    
    # Method 4: Shorthand {"tool_name": "value"}
    known_tools = registry.get_names()
    for line in ai_response.split('\n'):
        line = line.strip().strip('`')
        if line.startswith('{'):
            try:
                parsed = json.loads(line)
                for key in parsed:
                    if key in known_tools:
                        args = parsed[key]
                        tool = registry.get(key)
                        if isinstance(args, str) and tool.parameters:
                            first_param = list(tool.parameters.keys())[0]
                            return {"tool": key, "args": {first_param: args}}
                        elif isinstance(args, dict):
                            return {"tool": key, "args": args}
            except json.JSONDecodeError:
                continue
    
    return None
