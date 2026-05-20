"""
=================================================================
LESSON 1 - PRACTICE TASK
=================================================================

You have 3 challenges below. Each one has some code written
and some parts marked with "YOUR CODE HERE" for you to complete.

HOW TO RUN:
  cd c:\\dev\\Freshon.in\\backend
  python -m apps.agents.lessons.lesson_1_task

When all 3 challenges pass, you've mastered Lesson 1!
=================================================================
"""

from requests import request
from email import message
import requests
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"


# =================================================================
# CHALLENGE 1: Change the personality
# =================================================================
# Right now the system prompt says "You are a helpful assistant".
# YOUR TASK: Change the system prompt so the AI responds as if it
#            is a FARMER named "Ramesh" who speaks casually.
#
# HINT: Only the "system" message content needs to change.
#       The structure stays exactly the same.
# =================================================================

def challenge_1():
    print("\n" + "=" * 60)
    print("  CHALLENGE 1: Change the personality")
    print("=" * 60)
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                # YOUR CODE HERE: Change this system prompt so the AI
                # acts like a farmer named Ramesh who speaks casually
                "content": "You are a Farmer named Ramesh who speaks very casually."
            },
            {
                "role": "user",
                "content": "How are the tomatoes looking today?"
            }
        ],
        "stream": False
    }
    
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    data = response.json()
    print(f"\n[REPLY]: {data['message']['content']}")
    print("\n>> Does the AI respond AS Ramesh the farmer? If yes, Challenge 1 passed!")


# =================================================================
# CHALLENGE 2: Multi-turn conversation
# =================================================================
# In Lesson 1 we only sent ONE user message. But real conversations
# have HISTORY. The AI needs to "remember" what was said before.
#
# YOUR TASK: Add the missing messages to create this conversation:
#   1. User asks: "What did Farmer Ramesh deliver today?"
#   2. AI replied: "Ramesh delivered 30kg of spinach and 20kg of tomatoes."
#   3. User asks: "What was the total weight?"
#
# The AI should be able to answer "50kg" because it can see the
# history. If you DON'T include message #2, it won't know.
#
# HINT: You need 3 messages in the list (after system).
#       Use roles: "user", "assistant", "user"
# =================================================================

def challenge_2():
    print("\n" + "=" * 60)
    print("  CHALLENGE 2: Multi-turn conversation")
    print("=" * 60)
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are an inventory assistant for FreshOn. Be concise."
            },
            {
                "role": "user",
                "content": "What did Farmer Ramesh deliver today"
            },
            {
                "role": "assistant",
                "content": "Ramesh delivered 30kg of spinach and 20kg of tomatoes."
            },
            {
                "role": "user",
                "content": "What was the total weight"
            },
            # YOUR CODE HERE: Add 3 messages to create the conversation
            # described above. The first "user" message, then the
            # "assistant" reply, then the follow-up "user" question.
            #
            # Message 1: role "user", content "What did Farmer Ramesh deliver today?"
            # Message 2: role "assistant", content "Ramesh delivered 30kg of spinach and 20kg of tomatoes."
            # Message 3: role "user", content "What was the total weight?"
        ],
        "stream": False
    }
    
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    data = response.json()
    print(f"\n[REPLY]: {data['message']['content']}")
    print("\n>> Does the AI answer '50kg'? If yes, Challenge 2 passed!")
    print(">> KEY LEARNING: The 'assistant' role is how we give the AI MEMORY.")


# =================================================================
# CHALLENGE 3: Build your OWN reusable function
# =================================================================
# In Lesson 1, I wrote the chat_with_llm() function for you.
# YOUR TASK: Write your own function called "ask_freshon()" that:
#   1. Takes two arguments: system_prompt (str) and user_question (str)
#   2. Builds the payload with those two messages
#   3. Sends it to Ollama
#   4. Returns ONLY the AI's reply text (a string)
#
# Then call it twice with different prompts to prove it works.
#
# HINT: Look at lesson_1_llm_connection.py for reference, but
#       try to write it from memory first!
# =================================================================

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:3b"

def ask_freshon(system_prompt: str, user_question: str) -> str:
    
    payload = {
        "model": MODEL_NAME,
        "message": [
        system_prompt,
        user_question
        ],
        "stream": True

        response = request.post(
            OLLAMA_URL,
            json=payload,
            timeout=120
        )
    }


def ask_freshon(system_prompt: str, user_question: str) -> str:
    """
    YOUR CODE HERE: Build payload, send to Ollama, return the reply.
    """
    # Step 1: Build the payload dict with "model", "messages", "stream"
    # Step 2: requests.post(OLLAMA_URL, json=payload, timeout=120)
    # Step 3: Parse response.json() and return data["message"]["content"]
    pass  # Remove this line and write your code


def challenge_3():
    print("\n" + "=" * 60)
    print("  CHALLENGE 3: Build your own reusable function")
    print("=" * 60)
    
    # Test 1: Ask as a pricing expert
    reply1 = ask_freshon(
        "You are a pricing expert for organic vegetables in India. Be concise.",
        "What is a fair retail price for 1kg of organic spinach?"
    )
    print(f"\n[Test 1 Reply]: {reply1}")
    
    # Test 2: Ask as a delivery coordinator
    reply2 = ask_freshon(
        "You are a delivery coordinator. Be brief and direct.",
        "An order needs to go from Whitefield to Koramangala in Bangalore. Estimated time?"
    )
    print(f"\n[Test 2 Reply]: {reply2}")
    
    if reply1 and reply2:
        print("\n>> Both calls returned responses? Challenge 3 passed!")
    else:
        print("\n>> One or both calls returned None. Check your ask_freshon() function.")


# =================================================================
# RUN ALL CHALLENGES
# =================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  LESSON 1 - PRACTICE TASKS")
    print("  Complete all 3 challenges to master the LLM connection")
    print("=" * 60)
    
    challenge_1()
    challenge_2()
    challenge_3()
    
    print("\n" + "=" * 60)
    print("  ALL DONE! Show me your completed file and I'll review it.")
    print("=" * 60)
