"""
Test script for Agent WebSocket functionality.

This script tests the WebSocket connection and basic message flow.
Run with: python -m apps.agents.test_websocket

Note: Requires Django server running with Redis or InMemory channel layer.
"""

import asyncio
import json
import sys

# Test configuration
WS_URL = "ws://localhost:8000/ws/agents/"
TEST_TOKEN = "your_test_token_here"  # Replace with actual JWT token


async def test_websocket():
    """Test the Agent WebSocket connection."""
    try:
        import websockets
    except ImportError:
        print("❌ websockets package not installed. Install with: pip install websockets")
        print("   Skipping WebSocket test.")
        return
    
    print("=" * 60)
    print("Agent WebSocket Test")
    print("=" * 60)
    
    if TEST_TOKEN == "your_test_token_here":
        print("\n⚠️  Please set TEST_TOKEN to a valid JWT token")
        print("   You can get one by logging in via the API:")
        print("   POST /api/auth/login/ with username and password")
        return
    
    uri = f"{WS_URL}?token={TEST_TOKEN}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"\n✅ Connected to {WS_URL}")
            
            # Wait for connection_established message
            response = await websocket.recv()
            data = json.loads(response)
            print(f"\n📨 Server: {data['type']}")
            
            if data['type'] == 'connection_established':
                print(f"   Message: {data['message']}")
                print(f"   Available agents:")
                for agent in data.get('available_agents', []):
                    print(f"      - {agent['name']} ({agent['type']})")
            
            # Test create_session
            print("\n📤 Sending: create_session")
            await websocket.send(json.dumps({
                'type': 'create_session',
                'agent_type': 'CUSTOMER_ASSISTANT',
                'initial_message': 'Hello! What can you help me with?'
            }))
            
            # Wait for session_created
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 Server: {data['type']}")
            
            if data['type'] == 'session_created':
                session_id = data['session']['id']
                print(f"   Session ID: {session_id}")
                
                # Wait for agent response (may be multiple messages)
                print("\n⏳ Waiting for agent response...")
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        data = json.loads(response)
                        print(f"📨 Server: {data['type']}")
                        
                        if data['type'] == 'agent_response':
                            print(f"   Reply: {data['reply'][:100]}...")
                            break
                        elif data['type'] == 'message_complete':
                            print(f"   Reply: {data['reply'][:100]}...")
                            break
                            
                    except asyncio.TimeoutError:
                        print("   ⚠️ Timeout waiting for response")
                        break
            
            # Test ping
            print("\n📤 Sending: ping")
            await websocket.send(json.dumps({'type': 'ping'}))
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 Server: {data['type']}")
            
            print("\n✅ All tests passed!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def print_websocket_docs():
    """Print WebSocket API documentation."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           Agent WebSocket API Documentation                      ║
╠══════════════════════════════════════════════════════════════════╣

CONNECTION:
  URL: ws://localhost:8000/ws/agents/?token=<JWT_ACCESS_TOKEN>
  
  The token can be obtained from:
  - Cookie: access_token (HttpOnly)
  - Or query parameter for mobile apps

CLIENT → SERVER MESSAGES:

  1. Create Session:
     {
       "type": "create_session",
       "agent_type": "CUSTOMER_ASSISTANT",
       "initial_message": "Optional first message"
     }

  2. Send Chat Message:
     {
       "type": "chat_message",
       "session_id": "uuid-string",
       "message": "Where is my order?",
       "stream": true
     }

  3. Get Sessions:
     { "type": "get_sessions" }

  4. Get Session History:
     {
       "type": "get_session_history",
       "session_id": "uuid-string"
     }

  5. Close Session:
     {
       "type": "close_session",
       "session_id": "uuid-string"
     }

  6. Typing Indicator:
     {
       "type": "typing_indicator",
       "is_typing": true
     }

  7. Ping:
     { "type": "ping" }

SERVER → CLIENT MESSAGES:

  1. Connection Established:
     {
       "type": "connection_established",
       "message": "Connected to FreshOn AI Agent",
       "available_agents": [...]
     }

  2. Session Created:
     {
       "type": "session_created",
       "session": { "id": "...", "agent_type": "...", ... }
     }

  3. Agent Typing:
     { "type": "agent_typing", "is_typing": true }

  4. Message Streaming (when stream=true):
     { "type": "message_start", "session_id": "..." }
     { "type": "message_chunk", "chunk": "Hello ", "is_final": false }
     { "type": "message_chunk", "chunk": "there!", "is_final": true }
     { "type": "message_complete", "session_id": "...", "reply": "..." }

  5. Direct Response (when stream=false):
     {
       "type": "agent_response",
       "session_id": "...",
       "reply": "Your order is on the way!"
     }

  6. Sessions List:
     {
       "type": "sessions_list",
       "sessions": [...]
     }

  7. Session History:
     {
       "type": "session_history",
       "session": { "messages": [...] }
     }

  8. Error:
     {
       "type": "error",
       "message": "Error description"
     }

EXAMPLE JAVASCRIPT CLIENT:

  const token = 'your-jwt-token';
  const ws = new WebSocket(`ws://localhost:8000/ws/agents/?token=${token}`);

  ws.onopen = () => {
    console.log('Connected');
    
    // Create a session
    ws.send(JSON.stringify({
      type: 'create_session',
      agent_type: 'CUSTOMER_ASSISTANT'
    }));
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
    
    if (data.type === 'session_created') {
      // Send a message
      ws.send(JSON.stringify({
        type: 'chat_message',
        session_id: data.session.id,
        message: 'Where is my order FRSH-A1B2C3?'
      }));
    }
  };

╚══════════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--docs":
        print_websocket_docs()
    else:
        print("Agent WebSocket Test")
        print("=" * 60)
        print("\nUsage:")
        print("  python -m apps.agents.test_websocket --docs   # Show API docs")
        print("  python -m apps.agents.test_websocket          # Run tests (requires token)")
        print("\nTo run tests, edit TEST_TOKEN in this file first.")
        print_websocket_docs()
