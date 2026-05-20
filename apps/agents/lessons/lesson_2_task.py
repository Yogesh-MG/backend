"""
=================================================================
LESSON 2 - PRACTICE TASK
=================================================================

You have 3 challenges below. Each one has scaffolding and
parts marked with "YOUR CODE HERE" for you to complete.

WHAT YOU LEARNED:
  - The AI doesn't run code. It ASKS you to run a function.
  - You parse the AI's response for a tool call JSON.
  - You execute the function and feed the result back.
  - This is the ReAct pattern: Reason → Act → Observe → Answer.

HOW TO RUN:
  cd c:\\dev\\Freshon.in\\backend
  python -m apps.agents.lessons.lesson_2_task

When all 3 challenges pass, you've mastered Lesson 2!
=================================================================
"""

import requests
import requests
import json
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"


# =================================================================
# FAKE DATABASE (same as lesson — don't change these)
# =================================================================

FAKE_ORDERS = {
    "FO-2001": {
        "customer": "Ananya Rao",
        "items": ["Mangoes (2kg)", "Curry Leaves (100g)"],
        "total": 480,
        "status": "Delivered",
        "delivered_at": "2:30 PM today",
    },
    "FO-2002": {
        "customer": "Vikram Patel",
        "items": ["Organic Rice (5kg)", "Coconut (3 pcs)"],
        "total": 650,
        "status": "Preparing",
        "delivery_eta": "60 minutes",
    },
}

FAKE_FARMERS = {
    "ramesh": {"name": "Ramesh Gowda", "location": "Mandya", "crops": ["Tomatoes", "Onions", "Chillies"], "organic": True, "rating": 4.8},
    "lakshmi": {"name": "Lakshmi Devi", "location": "Mysuru", "crops": ["Spinach", "Methi", "Coriander"], "organic": True, "rating": 4.9},
    "suresh": {"name": "Suresh Kumar", "location": "Kolar", "crops": ["Bananas", "Papayas"], "organic": False, "rating": 4.5},
}


# =================================================================
# CHALLENGE 1: Write your own tool function
# =================================================================
# In Lesson 2, I wrote get_order_status() and search_products() for you.
#
# YOUR TASK: Write TWO tool functions:
#
#   1. get_order(order_id: str) -> dict
#      - Look up the order in FAKE_ORDERS by order_id
#      - If found, return the order dict with "found": True added
#      - If not found, return {"found": False, "error": "Order not found"}
#
#   2. get_farmer_info(farmer_name: str) -> dict
#      - Look up the farmer in FAKE_FARMERS by farmer_name (lowercase)
#      - If found, return the farmer dict with "found": True added
#      - If not found, return {"found": False, "error": "Farmer not found"}
#
# HINT: Look at get_order_status() in lesson_2_tool_calling.py
# =================================================================

def get_order(order_id: str) -> dict:
    """YOUR CODE HERE: Look up order by ID in FAKE_ORDERS."""
    order = FAKE_ORDERS.get(order_id)
    if order:
        return {"found":True, **order}
    return {"found":False, "error":f"No order found with the give ID {order_id}"}


def get_farmer_info(farmer_name: str) -> dict:
    """YOUR CODE HERE: Look up farmer by name in FAKE_FARMERS."""
    farmer_name = farmer_name.lower()
    farmer = FAKE_FARMERS.get(farmer_name)
    if farmer:
        return {"found":True, **farmer}
    return {"found":False, "error": f"Farmer not found with given name {farmer_name}"}


def challenge_1():
    print("\n" + "=" * 60)
    print("  CHALLENGE 1: Write your own tool functions")
    print("=" * 60)

    # Test get_order
    result1 = get_order("FO-2001")
    result2 = get_order("FO-9999")

    print(f"\n  get_order('FO-2001') => {json.dumps(result1, default=str)}")
    print(f"  get_order('FO-9999') => {json.dumps(result2, default=str)}")

    ok1 = result1 and result1.get("found") == True and result1.get("status") == "Delivered"
    ok2 = result2 and result2.get("found") == False

    # Test get_farmer_info
    result3 = get_farmer_info("ramesh")
    result4 = get_farmer_info("nobody")

    print(f"  get_farmer_info('ramesh') => {json.dumps(result3, default=str)}")
    print(f"  get_farmer_info('nobody') => {json.dumps(result4, default=str)}")

    ok3 = result3 and result3.get("found") == True and result3.get("location") == "Mandya"
    ok4 = result4 and result4.get("found") == False

    if ok1 and ok2 and ok3 and ok4:
        print("\n  ✅ Challenge 1 PASSED! Your tool functions work correctly.")
    else:
        print("\n  ❌ Challenge 1 FAILED. Check your functions.")
        if not ok1: print("     - get_order('FO-2001') should return found=True with status='Delivered'")
        if not ok2: print("     - get_order('FO-9999') should return found=False")
        if not ok3: print("     - get_farmer_info('ramesh') should return found=True with location='Mandya'")
        if not ok4: print("     - get_farmer_info('nobody') should return found=False")

    return ok1 and ok2 and ok3 and ok4


# =================================================================
# CHALLENGE 2: Build a tool registry
# =================================================================
# In Lesson 2, I defined TOOL_REGISTRY as a dict mapping
# tool names → {"function": ..., "description": ..., "parameters": ...}
#
# YOUR TASK: Build TOOL_REGISTRY for the two functions you just wrote.
#   - "get_order" should map to your get_order function
#   - "get_farmer_info" should map to your get_farmer_info function
#   - Each needs a "description" and "parameters" dict
#
# Then write format_tools_for_prompt() that turns your registry
# into a string the LLM can read.
#
# HINT: Copy the pattern from lesson_2_tool_calling.py's TOOL_REGISTRY
# =================================================================

# YOUR CODE HERE: Define TOOL_REGISTRY with both tools
TOOL_REGISTRY = {
    "get_order": { 
        "function": get_order,
        "description": "Look up the order details with the order_id (eg..FO-2002)",
        "parameters": {
            "order_id": "The order ID to look up (string, e.g., 'FO-1001')"
        }
     },
    "get_farmer_info": { 
        "function": get_farmer_info,
        "description": "Look up the farmer information with the name (eg..ramesh)",
        "parameters": {
            "farmer_name":"The name of farmer to look up (string, e.g., 'ramesh')"
        }
     },
}


def format_tools_for_prompt() -> str:
    """
    YOUR CODE HERE: Convert TOOL_REGISTRY into a readable string.

    The output should look something like:
      You have the following tools available:
        - get_order(order_id: ...): description here
        - get_farmer_info(farmer_name: ...): description here

      To use a tool, respond with:
      TOOL_CALL: {"tool": "tool_name", "args": {"param": "value"}}
    """
    lines = ["You have the following tools available:\n"]
    for name, info in TOOL_REGISTRY.items():
        params = ", ".join(f'{k}: {v}' for k, v in info['parameters'].items())
        lines.append(f"  - {name}({params}): {info['description']}")
    lines.append(
        '\nTo use a tool, you MUST respond with ONLY this JSON on a single line, nothing else:'
        '\nTOOL_CALL: {"tool": "tool_name", "args": {"param": "value"}}'
        '\n\nExamples:'
        '\nTOOL_CALL: {"tool": "get_order", "args": {"order_id": "FO-1001"}}'
        '\nTOOL_CALL: {"tool": "get_farmer_info", "args": {"farmer_name": "ramesh"}}'
        '\n\nIf no tool is needed, respond normally with text (no TOOL_CALL prefix).'
        '\nAfter receiving a tool result, answer the user naturally using that data.'
        '\nNEVER make up data. ALWAYS use a tool if you need factual information.'
    )
    return "\n".join(lines)

def challenge_2():
    print("\n" + "=" * 60)
    print("  CHALLENGE 2: Build a tool registry")
    print("=" * 60)

    # Check registry has both tools
    has_order = "get_order" in TOOL_REGISTRY and callable(TOOL_REGISTRY["get_order"].get("function"))
    has_farmer = "get_farmer_info" in TOOL_REGISTRY and callable(TOOL_REGISTRY["get_farmer_info"].get("function"))

    print(f"\n  TOOL_REGISTRY has 'get_order': {has_order}")
    print(f"  TOOL_REGISTRY has 'get_farmer_info': {has_farmer}")

    # Check format_tools_for_prompt returns something useful
    prompt_text = format_tools_for_prompt()
    has_prompt = prompt_text is not None and len(prompt_text) > 50 and "get_order" in prompt_text

    print(f"  format_tools_for_prompt() returns valid text: {has_prompt}")
    if has_prompt:
        print(f"\n  --- Your tool prompt ---")
        print(f"  {prompt_text[:300]}...")

    if has_order and has_farmer and has_prompt:
        print("\n  ✅ Challenge 2 PASSED! Registry and prompt builder work.")
    else:
        print("\n  ❌ Challenge 2 FAILED.")
        if not has_order: print("     - Add 'get_order' to TOOL_REGISTRY with 'function', 'description', 'parameters'")
        if not has_farmer: print("     - Add 'get_farmer_info' to TOOL_REGISTRY")
        if not has_prompt: print("     - format_tools_for_prompt() should return a string describing the tools")

    return has_order and has_farmer and has_prompt


# =================================================================
# CHALLENGE 3: Build the single-step agent loop
# =================================================================
# This is the big one. Write agent_ask() that:
#   1. Sends the user message to the LLM (with tool descriptions)
#   2. Checks if the AI wants to call a tool
#   3. If yes → execute the tool → feed result back → get final answer
#   4. If no → return the direct answer
#
# I've given you the extract_tool_call() helper (it's the same as
# lesson 2). You just need to write the agent loop.
#
# HINT: The flow is in lesson_2_tool_calling.py's agent_chat().
#       Try to write it from memory, then check if you're stuck.
# =================================================================

def extract_tool_call(ai_response: str) -> dict | None:
    """
    I'm giving you this one for free — it's the same parser from Lesson 2.
    It finds tool calls in the AI's response.
    """
    import re

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

    for line in ai_response.split('\n'):
        line = line.strip().strip('`')
        if line.startswith('{') and '"tool"' in line:
            try:
                parsed = json.loads(line)
                if "tool" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

    json_pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+"[^{}]*\}'
    matches = re.findall(json_pattern, ai_response)
    for match in matches:
        try:
            parsed = json.loads(match)
            if "tool" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue

    # Handle shorthand like {"get_order": "FO-2001"}
    for line in ai_response.split('\n'):
        line = line.strip().strip('`')
        if line.startswith('{'):
            try:
                parsed = json.loads(line)
                for key in parsed:
                    if key in TOOL_REGISTRY:
                        args = parsed[key]
                        if isinstance(args, str):
                            param_names = list(TOOL_REGISTRY[key]["parameters"].keys())
                            if param_names:
                                return {"tool": key, "args": {param_names[0]: args}}
                        elif isinstance(args, dict):
                            return {"tool": key, "args": args}
            except json.JSONDecodeError:
                continue

    return None


SYSTEM_PROMPT = """You are a helpful customer assistant for FreshOn, an organic farm-to-table marketplace in India.
Keep your answers concise and friendly.

{tools}

To use a tool, respond with ONLY this on a single line:
TOOL_CALL: {{"tool": "tool_name", "args": {{"param": "value"}}}}

NEVER make up data. ALWAYS use a tool if you need factual order or farmer information."""


def agent_ask(user_message: str) -> str:
    """
    YOUR CODE HERE: The single-step agent loop.

    Steps:
      1. Build the system prompt using SYSTEM_PROMPT.format(tools=format_tools_for_prompt())
      2. Create messages list: [system_msg, user_msg]
      3. Send to Ollama (requests.post, json=payload, stream=False)
      4. Get the AI's reply from response.json()["message"]["content"]
      5. Use extract_tool_call(ai_reply) to check for a tool call
      6. If tool call found:
         a. Get the function from TOOL_REGISTRY[tool_name]["function"]
         b. Execute it: result = function(**tool_args)
         c. Add the AI's reply as an "assistant" message
         d. Add the tool result as a "user" message
         e. Send to Ollama again for the final answer
         f. Return the final answer
      7. If no tool call: return the AI's reply directly

    Return the final answer string.
    """
    system = SYSTEM_PROMPT.format(tools=format_tools_for_prompt())
    messages = [
        {"role":"system","content":system},
        {"role":"user","content":user_message}
    ]
    payload = {"model": MODEL_NAME, "messages": messages, "stream": False}
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    data = response.json()
    ai_reply = data['message']['content']

    print(f"[ AI Raw response ] --- {ai_reply} /n")

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

def challenge_3():
    print("\n" + "=" * 60)
    print("  CHALLENGE 3: Build the agent loop")
    print("=" * 60)

    # Test 1: Should use get_order tool
    print("\n  [Test 1] Asking about order FO-2001...")
    reply1 = agent_ask("What's the status of my order FO-2001?")
    print(f"  [Reply]: {reply1}")

    ok1 = reply1 is not None and len(reply1) > 10

    # Test 2: Should use get_farmer_info tool
    print("\n  [Test 2] Asking about farmer Ramesh...")
    reply2 = agent_ask("Tell me about farmer Ramesh")
    print(f"  [Reply]: {reply2}")

    ok2 = reply2 is not None and len(reply2) > 10

    # Test 3: Should answer directly (no tool needed)
    print("\n  [Test 3] General question...")
    reply3 = agent_ask("What does organic certification mean?")
    print(f"  [Reply]: {reply3}")

    ok3 = reply3 is not None and len(reply3) > 10

    if ok1 and ok2 and ok3:
        print("\n  ✅ Challenge 3 PASSED! Your agent loop works!")
        print("     🎉 You've built a working AI agent from scratch!")
    else:
        print("\n  ❌ Challenge 3 FAILED.")
        if not ok1: print("     - agent_ask() returned None for order query")
        if not ok2: print("     - agent_ask() returned None for farmer query")
        if not ok3: print("     - agent_ask() returned None for general question")

    return ok1 and ok2 and ok3


# =================================================================
# RUN ALL CHALLENGES
# =================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  LESSON 2 - PRACTICE TASKS")
    print("  Complete all 3 challenges to master tool calling")
    print("=" * 60)

    c1 = challenge_1()
    if not c1:
        print("\n  ⛔ Fix Challenge 1 before moving on.")
    else:
        c2 = challenge_2()
        if not c2:
            print("\n  ⛔ Fix Challenge 2 before moving on.")
        else:
            c3 = challenge_3()

    print("\n" + "=" * 60)
    if c1 and c2 and c3:
        print("  🏆 ALL CHALLENGES PASSED!")
        print("  You now understand the ReAct agent pattern.")
        print("  Next: We build the REAL FreshOn agent engine.")
    else:
        print("  Keep going! Fix the failing challenges and re-run.")
    print("=" * 60)
