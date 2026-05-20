"""
=================================================================
LESSON 1: The LLM Connection
=================================================================

GOAL: Understand that an LLM is just an HTTP API.
      Send a message, get a response. That's it.

CONCEPT:
  - An LLM is NOT magic. It's a server that accepts JSON and returns JSON.
  - The universal format is a list of "messages", each with a "role" and "content".
  - Ollama runs locally at http://localhost:11434 and speaks the same language
    as OpenAI, DeepSeek, etc. So what you learn here works everywhere.

HOW TO RUN:
  cd c:\\dev\\Freshon.in\\backend
  python -m apps.agents.lessons.lesson_1_llm_connection
=================================================================
"""

import requests  # The same library you use for Razorpay, Google Maps, etc.
import json


# --- STEP 1: Define where the LLM lives ---
# Ollama runs locally and exposes a chat API at this URL.
# This is identical in concept to "https://api.openai.com/v1/chat/completions"
# or "https://api.deepseek.com/v1/chat/completions" -- just a different address.

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"


# --- STEP 2: Build the message payload ---
# Every LLM conversation is a list of messages with roles.
# Think of it as a script for a play:
#   - "system" = the director's instructions (the AI never shows this to the user)
#   - "user"   = what the human said
#   - "assistant" = what the AI previously replied (for multi-turn memory)

def chat_with_llm(user_message: str) -> str:
    """
    Send a single message to the local LLM and get a response.
    
    This is the simplest possible LLM interaction.
    Everything else we build (agents, tools, ReAct loops) is built ON TOP of this.
    """
    
    # The payload -- this is the UNIVERSAL format used by all LLM APIs
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant for FreshOn, "
                    "an organic farm-to-table marketplace in India. "
                    "Keep your answers concise and practical."
                )
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "stream": False  # Get the full response at once (not word-by-word)
    }
    
    # --- STEP 3: Make the HTTP request ---
    # This is EXACTLY like calling any other API from Django.
    # requests.post(url, json=data) -- you've done this a hundred times.
    
    print(f"\n[SEND] Sending to LLM: \"{user_message}\"")
    print(f"   -> URL: {OLLAMA_URL}")
    print(f"   -> Model: {MODEL_NAME}")
    print(f"   -> Payload size: {len(json.dumps(payload))} bytes")
    print("   ... Waiting for response...\n")
    
    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=120  # Give it up to 120 seconds (CPU inference is slower)
    )
    
    # --- STEP 4: Parse the response ---
    # The response is JSON. The AI's reply is inside response["message"]["content"]
    
    data = response.json()
    ai_reply = data["message"]["content"]
    
    # Let's also peek at the metadata Ollama gives us
    # (tokens used, time taken -- useful for cost estimation later)
    total_duration_ms = data.get("total_duration", 0) / 1_000_000  # nanoseconds -> ms
    eval_count = data.get("eval_count", 0)  # tokens generated
    
    print("-" * 60)
    print(f"[REPLY] LLM Response:")
    print("-" * 60)
    print(ai_reply)
    print("-" * 60)
    print(f"[STATS] {eval_count} tokens generated in {total_duration_ms:.0f}ms")
    print("-" * 60)
    
    return ai_reply


# --- STEP 5: Run it! ---
if __name__ == "__main__":
    print("=" * 60)
    print("  LESSON 1: The LLM Connection")
    print("  Talking to a local AI model via HTTP API")
    print("=" * 60)
    
    # Test 1: A simple question
    chat_with_llm("What vegetables are in season during monsoon in India?")
    
    # Test 2: A FreshOn-specific question
    chat_with_llm(
        "A farmer just harvested 50kg of organic tomatoes at Rs 40/kg. "
        "How should I price it for retail with a 30% margin?"
    )
    
    print("\n[DONE] Lesson 1 Complete!")
    print("   KEY TAKEAWAY: An LLM is just an HTTP API.")
    print("   requests.post() -> JSON in, JSON out. No magic.")
    print("   Next lesson: We'll teach the AI to CALL OUR FUNCTIONS.")
