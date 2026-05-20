"""
=================================================================
LESSON 2: Tool Calling — Teach the AI to Use Your Functions
=================================================================

GOAL: Understand that an LLM can "call" your Python functions.
      The LLM doesn't execute code — it ASKS you to run a function,
      and you feed the result back into the conversation.

CONCEPT:
  In Lesson 1 we sent text → got text back.
  Now we teach the AI: "Hey, you have these tools available.
  If you need data, ask me to call one, and I'll give you the result."

  This is how agents work:
    1. User asks a question
    2. AI thinks: "I need to look up the order first"
    3. AI outputs: {"tool": "get_order", "args": {"order_id": "123"}}
    4. YOUR CODE runs get_order("123") and gets the result
    5. You feed the result back to the AI
    6. AI gives the final answer to the user

  This is called the ReAct pattern (Reason + Act).

HOW TO RUN:
  cd c:\\dev\\Freshon.in\\backend
  python -m apps.agents.lessons.lesson_2_tool_calling
=================================================================
"""

import requests
import json
import sys
import io

# Fix Windows console encoding for ₹ symbol etc.
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"


# =================================================================
# STEP 1: Define some "tools" (plain Python functions)
# =================================================================
# These simulate the real Django ORM queries we'll use in production.
# In the real system, these will query Order, Product, Delivery models.

# Fake database for this lesson
FAKE_ORDERS = {
    "FO-1001": {
        "customer": "Priya Sharma",
        "items": ["Organic Tomatoes (2kg)", "Fresh Spinach (500g)"],
        "total": 340,
        "status": "Out for Delivery",
        "delivery_eta": "15 minutes",
    },
    "FO-1002": {
        "customer": "Rahul Menon",
        "items": ["Bananas (1 dozen)", "Coconut Oil (500ml)"],
        "total": 220,
        "status": "Preparing",
        "delivery_eta": "45 minutes",
    },
}

FAKE_PRODUCTS = [
    {"name": "Organic Tomatoes", "price_per_kg": 80, "farmer": "Ramesh (Mandya)", "stock_kg": 120},
    {"name": "Fresh Spinach", "price_per_kg": 60, "farmer": "Lakshmi (Mysuru)", "stock_kg": 45},
    {"name": "Red Onions", "price_per_kg": 40, "farmer": "Ramesh (Mandya)", "stock_kg": 200},
    {"name": "Green Chillies", "price_per_kg": 120, "farmer": "Suresh (Kolar)", "stock_kg": 30},
    {"name": "Bananas", "price_per_dozen": 50, "farmer": "Gowda (Hassan)", "stock_kg": 80},
]


def get_order_status(order_id: str) -> dict:
    """Look up an order by its ID. Returns order details or an error."""
    order = FAKE_ORDERS.get(order_id)
    if order:
        return {"found": True, **order}
    return {"found": False, "error": f"No order found with ID '{order_id}'"}


def search_products(query: str) -> list:
    """Search products by name. Returns matching products."""
    query_lower = query.lower()
    results = [p for p in FAKE_PRODUCTS if query_lower in p["name"].lower()]
    return results if results else [{"message": f"No products matching '{query}'"}]


def get_available_products() -> list:
    """List all currently available products with stock info."""
    return [
        {"name": p["name"], "price": p.get("price_per_kg", p.get("price_per_dozen")), "stock": p["stock_kg"], "farmer": p["farmer"]}
        for p in FAKE_PRODUCTS
    ]


# =================================================================
# STEP 2: Build the TOOL REGISTRY
# =================================================================
# This maps tool names → functions + descriptions.
# We send these descriptions to the LLM so it knows what's available.

TOOL_REGISTRY = {
    "get_order_status": {
        "function": get_order_status,
        "description": "Look up the status of an order by its order ID (e.g., FO-1001)",
        "parameters": {
            "order_id": "The order ID to look up (string, e.g., 'FO-1001')"
        }
    },
    "search_products": {
        "function": search_products,
        "description": "Search for products by name or keyword",
        "parameters": {
            "query": "The search term (string, e.g., 'tomato')"
        }
    },
    "get_available_products": {
        "function": get_available_products,
        "description": "List all currently available products with prices and stock levels",
        "parameters": {}
    },
}


def format_tools_for_prompt() -> str:
    """Format the tool registry into a string the LLM can understand."""
    lines = ["You have the following tools available:\n"]
    for name, info in TOOL_REGISTRY.items():
        params = ", ".join(f'{k}: {v}' for k, v in info["parameters"].items())
        lines.append(f"  - {name}({params}): {info['description']}")
    lines.append(
        '\nTo use a tool, you MUST respond with ONLY this JSON on a single line, nothing else:'
        '\nTOOL_CALL: {"tool": "tool_name", "args": {"param": "value"}}'
        '\n\nExamples:'
        '\nTOOL_CALL: {"tool": "get_order_status", "args": {"order_id": "FO-1001"}}'
        '\nTOOL_CALL: {"tool": "search_products", "args": {"query": "tomato"}}'
        '\nTOOL_CALL: {"tool": "get_available_products", "args": {}}'
        '\n\nIf no tool is needed, respond normally with text (no TOOL_CALL prefix).'
        '\nAfter receiving a tool result, answer the user naturally using that data.'
        '\nNEVER make up data. ALWAYS use a tool if you need factual information.'
    )
    return "\n".join(lines)


# =================================================================
# STEP 3: The SINGLE-STEP ReAct Loop
# =================================================================
# This is a simplified version. The real agent will loop multiple times.
# Here we do: User question → AI decides tool → We execute → AI answers.

SYSTEM_PROMPT = """You are a helpful customer assistant for FreshOn, an organic farm-to-table marketplace in India.
You help customers check orders, find products, and answer questions.
Keep your answers concise, friendly, and in a natural tone.

{tools}

IMPORTANT RULES:
- If the user asks about an order, ALWAYS use get_order_status first.
- If the user asks about products/prices, use search_products or get_available_products.
- Only use a tool if you genuinely need data you don't have.
- After getting tool results, give a natural, friendly answer."""


def agent_chat(user_message: str) -> str:
    """
    A single-turn agent interaction with tool calling.
    
    Flow:
      1. Send user message to LLM with tool descriptions
      2. If LLM wants to call a tool → execute it
      3. Feed result back → get final answer
    """
    
    system = SYSTEM_PROMPT.format(tools=format_tools_for_prompt())
    
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]
    
    print(f"\n{'='*60}")
    print(f"  USER: {user_message}")
    print(f"{'='*60}")
    
    # --- TURN 1: Ask the LLM what to do ---
    print("\n[STEP 1] Asking LLM to decide action...")
    
    payload = {"model": MODEL_NAME, "messages": messages, "stream": False}
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    ai_reply = response.json()["message"]["content"]
    
    print(f"[AI RAW RESPONSE]:\n{ai_reply}\n")
    
    # --- STEP 2: Check if the AI wants to call a tool ---
    tool_call = extract_tool_call(ai_reply)
    
    if tool_call:
        tool_name = tool_call["tool"]
        tool_args = tool_call.get("args", {})
        
        print(f"[TOOL CALL DETECTED] {tool_name}({tool_args})")
        
        # --- STEP 3: Execute the tool ---
        if tool_name in TOOL_REGISTRY:
            tool_fn = TOOL_REGISTRY[tool_name]["function"]
            result = tool_fn(**tool_args)
            result_str = json.dumps(result, indent=2, ensure_ascii=False)
            
            print(f"[TOOL RESULT]:\n{result_str}\n")
            
            # --- STEP 4: Feed result back to LLM for final answer ---
            messages.append({"role": "assistant", "content": ai_reply})
            messages.append({
                "role": "user",
                "content": f"Tool result for {tool_name}:\n{result_str}\n\nNow answer the customer's original question using this data."
            })
            
            print("[STEP 4] Sending tool result back to LLM for final answer...")
            
            payload2 = {"model": MODEL_NAME, "messages": messages, "stream": False}
            response2 = requests.post(OLLAMA_URL, json=payload2, timeout=120)
            final_reply = response2.json()["message"]["content"]
            
            print(f"\n[FINAL ANSWER]: {final_reply}")
            return final_reply
        else:
            error_msg = f"Unknown tool: {tool_name}"
            print(f"[ERROR] {error_msg}")
            return error_msg
    else:
        # No tool needed — AI answered directly
        print(f"[DIRECT ANSWER] (no tool needed): {ai_reply}")
        return ai_reply


def extract_tool_call(ai_response: str) -> dict | None:
    """
    Parse the AI's response to find a tool call.
    
    Expected format:
      TOOL_CALL: {"tool": "get_order_status", "args": {"order_id": "FO-1001"}}
    
    But LLMs are messy, so we also handle:
      - {"tool": "...", "args": {...}}  (without prefix)
      - {"get_order_status": "FO-1001"}  (shorthand)
      - JSON wrapped in markdown code blocks
    """
    import re
    
    # Method 1: Look for TOOL_CALL: prefix
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
    
    # Method 2: Look for {"tool": ...} JSON on any line
    for line in ai_response.split('\n'):
        line = line.strip().strip('`')  # remove markdown backticks
        if line.startswith('{') and '"tool"' in line:
            try:
                parsed = json.loads(line)
                if "tool" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue
    
    # Method 3: Regex for {"tool": ...} anywhere in text
    json_pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+"[^{}]*\}'
    matches = re.findall(json_pattern, ai_response)
    for match in matches:
        try:
            parsed = json.loads(match)
            if "tool" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue
    
    # Method 4: Handle shorthand like {"get_order_status": "FO-1001"}
    # Convert to our standard format
    for line in ai_response.split('\n'):
        line = line.strip().strip('`')
        if line.startswith('{'):
            try:
                parsed = json.loads(line)
                for key in parsed:
                    if key in TOOL_REGISTRY:
                        # Convert shorthand to standard format
                        args = parsed[key]
                        if isinstance(args, str):
                            # Figure out the first param name
                            param_names = list(TOOL_REGISTRY[key]["parameters"].keys())
                            if param_names:
                                return {"tool": key, "args": {param_names[0]: args}}
                            else:
                                return {"tool": key, "args": {}}
                        elif isinstance(args, dict):
                            return {"tool": key, "args": args}
            except json.JSONDecodeError:
                continue
    
    return None


# =================================================================
# STEP 5: Run it!
# =================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  LESSON 2: Tool Calling")
    print("  Teaching the AI to call your Python functions")
    print("=" * 60)
    
    # Test 1: Order status query (should trigger get_order_status tool)
    agent_chat("Where is my order FO-1001?")
    
    print("\n" + "=" * 60 + "\n")
    
    # Test 2: Product search (should trigger search_products tool)
    agent_chat("How much do tomatoes cost?")
    
    print("\n" + "=" * 60 + "\n")
    
    # Test 3: General question (should NOT need a tool)
    agent_chat("What payment methods do you accept?")
    
    print("\n" + "=" * 60)
    print("  LESSON 2 Complete!")
    print("  KEY TAKEAWAY: The AI doesn't run your code.")
    print("  It ASKS you to run it, and you feed the result back.")
    print("  This is the ReAct pattern: Reason → Act → Observe → Answer.")
    print("=" * 60)
