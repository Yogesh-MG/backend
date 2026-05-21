"""
WebSocket consumer for real-time AI Agent chat.

This consumer handles authenticated WebSocket connections for live
conversations with FreshOn AI Agents (Customer Assistance, Farmer Inventory, etc.)

Connection URL: /ws/agents/
Authentication: JWT token via query parameter ?token=<jwt>
"""
import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class AgentChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time AI agent conversations.
    
    Features:
    - Real-time chat with AI agents
    - Typing indicators
    - Message streaming (word-by-word)
    - Session management
    - Multi-agent support (Customer, Farmer, Delivery)
    """

    async def connect(self):
        """Handle connection and authenticate user."""
        self.user = await self.get_user_from_token()
        
        if self.user.is_anonymous:
            logger.warning("[AgentChat] Connection rejected: anonymous user")
            await self.close(code=4001)
            return

        self.user_group_name = f"agent_user_{self.user.id}"
        self.current_session_id = None
        self.is_processing = False
        
        # Join user-specific group for cross-device sync
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"[AgentChat] User {self.user.username} connected")
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Connected to FreshOn AI Agent',
            'user_id': str(self.user.id),
            'available_agents': [
                {'type': 'CUSTOMER_ASSISTANT', 'name': 'Customer Assistant', 'description': 'Help with orders, products, and support'},
                {'type': 'FARMER_INVENTORY', 'name': 'Farmer Assistant', 'description': 'List harvests and manage inventory'},
                {'type': 'DELIVERY_OPTIMIZER', 'name': 'Delivery Support', 'description': 'Track deliveries and routing'},
            ]
        }))

    async def disconnect(self, close_code):
        """Handle disconnection."""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            logger.info(f"[AgentChat] User {self.user.username} disconnected (code: {close_code})")

    async def receive(self, text_data):
        """Handle incoming messages from client."""
        if self.is_processing:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Please wait for the current response to complete.',
            }))
            return

        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'unknown')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            
            elif message_type == 'create_session':
                await self.handle_create_session(data)
            
            elif message_type == 'chat_message':
                await self.handle_chat_message(data)
            
            elif message_type == 'get_sessions':
                await self.handle_get_sessions()
            
            elif message_type == 'get_session_history':
                await self.handle_get_session_history(data)
            
            elif message_type == 'close_session':
                await self.handle_close_session(data)
            
            elif message_type == 'typing_indicator':
                # Echo typing indicator back (for UI feedback)
                await self.send(text_data=json.dumps({
                    'type': 'typing_indicator',
                    'is_typing': data.get('is_typing', False)
                }))
            
            else:
                logger.warning(f"[AgentChat] Unknown message type: {message_type}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}',
                }))
                
        except json.JSONDecodeError:
            logger.error("[AgentChat] Invalid JSON received")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format',
            }))
        except Exception as e:
            logger.error(f"[AgentChat] Error processing message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal error processing your request',
            }))

    async def handle_create_session(self, data):
        """Create a new agent session."""
        agent_type = data.get('agent_type', 'CUSTOMER_ASSISTANT')
        initial_message = data.get('initial_message', '')
        
        try:
            session = await self.create_session_db(agent_type, initial_message)
            self.current_session_id = str(session['id'])
            
            await self.send(text_data=json.dumps({
                'type': 'session_created',
                'session': session,
            }))
            
            # If initial message provided, process it
            if initial_message:
                await self.process_agent_message(session['id'], initial_message, stream=data.get('stream', True))
                
        except Exception as e:
            logger.error(f"[AgentChat] Failed to create session: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to create session',
            }))

    async def handle_chat_message(self, data):
        """Process a chat message and get AI response."""
        session_id = data.get('session_id') or self.current_session_id
        message = data.get('message', '').strip()
        stream = data.get('stream', True)
        
        if not session_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'No active session. Create a session first.',
            }))
            return
        
        if not message:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message cannot be empty',
            }))
            return
        
        self.current_session_id = session_id
        await self.process_agent_message(session_id, message, stream=stream)

    async def process_agent_message(self, session_id, message, stream=True):
        """Process message through the agent and send response."""
        self.is_processing = True
        
        try:
            # Send typing indicator
            await self.send(text_data=json.dumps({
                'type': 'agent_typing',
                'is_typing': True,
            }))
            
            # Get session details
            session = await self.get_session_db(session_id)
            if not session:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Session not found',
                }))
                return
            
            # Check if session is active
            if session['status'] != 'ACTIVE':
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'This session is no longer active',
                }))
                return
            
            # Import and run the agent
            from apps.agents.engine.base import FreshOnAgent
            from apps.agents.tools.customer import customer_tools
            
            agent = FreshOnAgent(
                agent_type=session['agent_type'],
                tool_registry=customer_tools,
                user=self.user,
            )
            
            # Get the actual session object
            session_obj = await self.get_session_object(session_id)
            
            if stream:
                # For streaming, we'd need to modify the router to support it
                # For now, send the full response
                reply = await asyncio.to_thread(agent.chat, session_obj, message)
                
                # Simulate streaming by sending word by word
                await self.send(text_data=json.dumps({
                    'type': 'agent_typing',
                    'is_typing': False,
                }))
                
                # Send message start
                await self.send(text_data=json.dumps({
                    'type': 'message_start',
                    'session_id': session_id,
                }))
                
                # Stream words
                words = reply.split(' ')
                for i, word in enumerate(words):
                    await self.send(text_data=json.dumps({
                        'type': 'message_chunk',
                        'chunk': word + (' ' if i < len(words) - 1 else ''),
                        'is_final': i == len(words) - 1,
                    }))
                    await asyncio.sleep(0.03)  # Small delay for natural feel
                
                # Send message complete
                await self.send(text_data=json.dumps({
                    'type': 'message_complete',
                    'session_id': session_id,
                    'reply': reply,
                }))
            else:
                # Non-streaming: get full response
                reply = await asyncio.to_thread(agent.chat, session_obj, message)
                
                await self.send(text_data=json.dumps({
                    'type': 'agent_typing',
                    'is_typing': False,
                }))
                
                await self.send(text_data=json.dumps({
                    'type': 'agent_response',
                    'session_id': session_id,
                    'reply': reply,
                }))
            
            # Broadcast to user's other devices
            await self.channel_layer.group_send(
                self.user_group_name,
                {
                    'type': 'session_update',
                    'session_id': session_id,
                    'message': message,
                    'reply': reply if not stream else None,
                }
            )
            
        except Exception as e:
            logger.error(f"[AgentChat] Agent processing error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Agent encountered an error. Please try again.',
            }))
        finally:
            self.is_processing = False

    async def handle_get_sessions(self):
        """Get list of user's recent sessions."""
        try:
            sessions = await self.get_user_sessions_db()
            await self.send(text_data=json.dumps({
                'type': 'sessions_list',
                'sessions': sessions,
            }))
        except Exception as e:
            logger.error(f"[AgentChat] Failed to get sessions: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to retrieve sessions',
            }))

    async def handle_get_session_history(self, data):
        """Get full message history for a session."""
        session_id = data.get('session_id')
        if not session_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Session ID required',
            }))
            return
        
        try:
            session = await self.get_session_with_messages_db(session_id)
            if not session:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Session not found',
                }))
                return
            
            await self.send(text_data=json.dumps({
                'type': 'session_history',
                'session': session,
            }))
        except Exception as e:
            logger.error(f"[AgentChat] Failed to get session history: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to retrieve session history',
            }))

    async def handle_close_session(self, data):
        """Close an active session."""
        session_id = data.get('session_id') or self.current_session_id
        if not session_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'No session to close',
            }))
            return
        
        try:
            await self.close_session_db(session_id)
            if self.current_session_id == session_id:
                self.current_session_id = None
            
            await self.send(text_data=json.dumps({
                'type': 'session_closed',
                'session_id': session_id,
            }))
        except Exception as e:
            logger.error(f"[AgentChat] Failed to close session: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to close session',
            }))

    async def session_update(self, event):
        """Handle session updates from other devices."""
        # Only process if from another connection (not this one)
        if event.get('sender_channel') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'session_update',
                'session_id': event.get('session_id'),
                'message': event.get('message'),
            }))

    # Database operations
    @database_sync_to_async
    def get_user_from_token(self):
        """Extract and validate JWT token from query parameters."""
        try:
            query_string = self.scope.get('query_string', b'').decode('utf-8')
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            token = params.get('token', '')
            
            if not token:
                return AnonymousUser()
            
            access_token = AccessToken(token)
            user_id = access_token.get('user_id')
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                return AnonymousUser()
                
        except Exception as e:
            logger.error(f"[AgentChat] Token validation error: {e}")
            return AnonymousUser()

    @database_sync_to_async
    def create_session_db(self, agent_type, initial_message):
        """Create a new agent session in the database."""
        from apps.agents.models import AgentSession
        
        session = AgentSession.objects.create(
            user=self.user,
            agent_type=agent_type,
            status='ACTIVE'
        )
        
        return {
            'id': str(session.id),
            'agent_type': session.agent_type,
            'agent_type_display': session.get_agent_type_display(),
            'status': session.status,
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat(),
        }

    @database_sync_to_async
    def get_session_db(self, session_id):
        """Get session details from database."""
        from apps.agents.models import AgentSession
        
        try:
            session = AgentSession.objects.get(id=session_id, user=self.user)
            return {
                'id': str(session.id),
                'agent_type': session.agent_type,
                'status': session.status,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
            }
        except AgentSession.DoesNotExist:
            return None

    @database_sync_to_async
    def get_session_object(self, session_id):
        """Get the actual session model instance."""
        from apps.agents.models import AgentSession
        return AgentSession.objects.get(id=session_id, user=self.user)

    @database_sync_to_async
    def get_user_sessions_db(self):
        """Get user's recent sessions."""
        from apps.agents.models import AgentSession
        from django.db.models import Count
        
        sessions = AgentSession.objects.filter(
            user=self.user
        ).annotate(
            message_count=Count('messages')
        ).order_by('-updated_at')[:20]
        
        return [
            {
                'id': str(s.id),
                'agent_type': s.agent_type,
                'agent_type_display': s.get_agent_type_display(),
                'status': s.status,
                'message_count': s.message_count,
                'created_at': s.created_at.isoformat(),
                'updated_at': s.updated_at.isoformat(),
            }
            for s in sessions
        ]

    @database_sync_to_async
    def get_session_with_messages_db(self, session_id):
        """Get session with full message history."""
        from apps.agents.models import AgentSession, AgentMessage, AgentToolCall
        
        try:
            session = AgentSession.objects.prefetch_related('messages', 'messages__tool_calls').get(
                id=session_id, user=self.user
            )
            
            messages = []
            for msg in session.messages.all():
                msg_data = {
                    'id': str(msg.id),
                    'sender': msg.sender,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat(),
                }
                
                # Include tool calls if any
                tool_calls = msg.tool_calls.all()
                if tool_calls:
                    msg_data['tool_calls'] = [
                        {
                            'tool_name': tc.tool_name,
                            'arguments': tc.arguments,
                            'result': tc.result,
                            'is_success': tc.is_success,
                            'executed_at': tc.executed_at.isoformat(),
                        }
                        for tc in tool_calls
                    ]
                
                messages.append(msg_data)
            
            return {
                'id': str(session.id),
                'agent_type': session.agent_type,
                'agent_type_display': session.get_agent_type_display(),
                'status': session.status,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'messages': messages,
            }
        except AgentSession.DoesNotExist:
            return None

    @database_sync_to_async
    def close_session_db(self, session_id):
        """Close a session in the database."""
        from apps.agents.models import AgentSession
        
        session = AgentSession.objects.get(id=session_id, user=self.user)
        session.status = 'COMPLETED'
        session.save(update_fields=['status'])
