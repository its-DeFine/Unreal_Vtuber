"""
Main Reactive Orchestrator

Contains the core orchestrator class and event handling logic.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .events import ExternalEvent, ReactiveState
from .conversation import ConversationHistory
from character_config import get_character_manager, CharacterProfile

logger = logging.getLogger(__name__)


class ReactiveOrchestrator:
    """Simplified orchestrator focused on reactive character-driven responses"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.character_manager = get_character_manager()
        self.state = ReactiveState()
        self.conversation_history = ConversationHistory()
        
        # SCB client (if available)
        self.scb_client = config.get('scb_client')
        
        # LLM configuration
        self.llm_config = config.get('llm_config', {})
        
        # Timing configuration
        self.min_speech_gap = config.get('timing', {}).get('min_speech_gap', 2.5)
        self.response_timeout = config.get('timing', {}).get('response_timeout', 30.0)
        
        # Anti-repetition configuration
        self.enable_anti_repetition = config.get('anti_repetition', {}).get('enabled', True)
        self.similarity_threshold = config.get('anti_repetition', {}).get('threshold', 0.85)
        
        # Autonomous mode configuration
        self.autonomous_task = None
        self.autonomous_content_history = []
        
        # Event handlers registry
        self.event_handlers = {
            'email': self._handle_email_event,
            'calendar': self._handle_calendar_event,
            'task': self._handle_task_event,
            'chat': self._handle_chat_event,
            'system': self._handle_system_event,
            'autonomous': self._handle_autonomous_event
        }
        
        # Initialize with default character
        self._initialize_default_character()
        
        logger.info("Reactive Orchestrator initialized")
    
    def _initialize_default_character(self):
        """Initialize with a default character if none selected"""
        if not self.character_manager.current_character_id:
            characters = self.character_manager.list_characters()
            if characters:
                self.character_manager.switch_character(characters[0]['id'])
                logger.info(f"Initialized with character: {characters[0]['name']}")
            else:
                logger.warning("No characters available, creating default")
                # Create a basic reactive character
                default_char = {
                    "id": "reactive_default",
                    "name": "Reactive Assistant",
                    "role": "General Purpose Assistant",
                    "personality_traits": ["helpful", "responsive", "adaptive"],
                    "communication_style": "clear and friendly",
                    "emotional_range": "balanced and positive",
                    "autonomous_enabled": True,
                    "autonomous_behaviors": {
                        "description": "Proactively share helpful tips, interesting facts, and useful information without waiting for user requests",
                        "rules": [
                            "Share practical tips and life hacks",
                            "Provide interesting facts and trivia",
                            "Offer helpful suggestions for common problems",
                            "Share motivational or inspiring content",
                            "Present useful information on various topics"
                        ],
                        "content_style": "Friendly and helpful, with a focus on practical value"
                    },
                    "autonomous_topics": [
                        "productivity tips",
                        "interesting facts",
                        "helpful suggestions",
                        "technology insights",
                        "general knowledge"
                    ],
                    "autonomous_interval": 35.0
                }
                self.character_manager.create_character(default_char)
                self.character_manager.switch_character("reactive_default")
    
    async def add_external_event(self, event_data: Dict[str, Any]) -> str:
        """Add an external event to the queue"""
        event = ExternalEvent(
            id=f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.state.event_queue)}",
            event_type=event_data.get('type', 'system'),
            source=event_data.get('source', 'unknown'),
            priority=event_data.get('priority', 'medium'),
            data=event_data.get('data', {}),
            timestamp=datetime.now()
        )
        
        self.state.event_queue.append(event)
        logger.info(f"Added external event: {event.id} ({event.event_type})")
        
        # Process high priority events immediately
        if event.priority == 'high':
            await self.process_event(event)
        
        return event.id
    
    async def process_event(self, event: ExternalEvent) -> Optional[str]:
        """Process a specific event and generate response"""
        if event.processed:
            return None
        
        character = self.character_manager.get_current_character()
        if not character:
            logger.error("No active character")
            return None
        
        try:
            # Get handler for event type
            handler = self.event_handlers.get(event.event_type, self._handle_generic_event)
            
            # Generate context-aware response
            response = await handler(event, character)
            logger.info(f"Handler response for event {event.id}: {repr(response)}")
            
            if response:
                # Check for repetition
                if self.enable_anti_repetition and self._is_repetitive(response):
                    logger.info("Response detected as repetitive, regenerating...")
                    response = await self._regenerate_non_repetitive(event, character, response)
                    logger.info(f"Regenerated response: {repr(response)}")
                
                # Update state
                event.processed = True
                self.state.add_response(response)
                
                # Add to conversation history
                self.conversation_history.add_turn(
                    speaker="character",
                    text=response,
                    metadata={
                        "event_id": event.id,
                        "event_type": event.event_type,
                        "character_id": character.id
                    }
                )
                
                # CRITICAL: Send ALL responses to TTS pipeline (not just chat API responses)
                self._send_response_to_tts(response, character.id)
                
                logger.info(f"Returning final response for event {event.id}: {repr(response)}")
                return response
            else:
                logger.warning(f"Handler returned empty response for event {event.id}")
                
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}")
            return None
    
    async def _handle_email_event(self, event: ExternalEvent, character: CharacterProfile) -> str:
        """Handle email notification events"""
        email_data = event.data
        
        # Use character's email response pattern if available
        pattern = character.get_response_pattern("email_notification")
        if pattern:
            response = pattern.format(
                priority=event.priority,
                sender=email_data.get('sender', 'someone'),
                subject=email_data.get('subject', 'no subject')
            )
        else:
            # Generate using LLM with character context
            response = await self._generate_llm_response(
                event=event,
                character=character,
                prompt_template="You received an email from {sender} about {subject}. Respond according to your character."
            )
        
        return response
    
    async def _handle_calendar_event(self, event: ExternalEvent, character: CharacterProfile) -> str:
        """Handle calendar events"""
        calendar_data = event.data
        
        pattern = character.get_response_pattern("meeting_reminder")
        if pattern:
            response = pattern.format(
                meeting_type=calendar_data.get('type', 'meeting'),
                attendees=calendar_data.get('attendees', 'colleagues'),
                time=calendar_data.get('time', 'soon')
            )
        else:
            response = await self._generate_llm_response(
                event=event,
                character=character,
                prompt_template="You have a calendar event: {title} at {time}. Respond appropriately."
            )
        
        return response
    
    async def _handle_task_event(self, event: ExternalEvent, character: CharacterProfile) -> str:
        """Handle task update events"""
        task_data = event.data
        
        pattern = character.get_response_pattern("task_update")
        if pattern:
            response = pattern.format(
                task_name=task_data.get('name', 'task'),
                status=task_data.get('status', 'updated')
            )
        else:
            response = await self._generate_llm_response(
                event=event,
                character=character,
                prompt_template="A task has been updated: {name} is now {status}. Respond helpfully."
            )
        
        return response
    
    async def _handle_chat_event(self, event: ExternalEvent, character: CharacterProfile) -> str:
        """Handle direct chat messages"""
        message = event.data.get('message', '')
        
        # Add to conversation history
        self.conversation_history.add_turn(
            speaker="user",
            text=message,
            metadata={"source": event.source}
        )
        
        # Generate conversational response
        response = await self._generate_llm_response(
            event=event,
            character=character,
            prompt_template="User said: {message}. Respond naturally in character.",
            include_conversation_history=True
        )
        
        return response
    
    async def _handle_system_event(self, event: ExternalEvent, character: CharacterProfile) -> str:
        """Handle system events"""
        return await self._handle_generic_event(event, character)
    
    async def _handle_autonomous_event(self, event: ExternalEvent, character: CharacterProfile) -> str:
        """Handle autonomous content generation events"""
        topic = event.data.get('topic', 'general')
        
        # Generate autonomous content based on character configuration
        response = await self._generate_autonomous_content(character, topic)
        return response
    
    async def _handle_generic_event(self, event: ExternalEvent, character: CharacterProfile) -> str:
        """Generic handler for unknown event types"""
        response = await self._generate_llm_response(
            event=event,
            character=character,
            prompt_template="An event occurred: {event_type} from {source}. Respond appropriately."
        )
        return response
    
    async def _generate_llm_response(
        self,
        event: ExternalEvent,
        character: CharacterProfile,
        prompt_template: str,
        include_conversation_history: bool = False
    ) -> str:
        """Generate response using LLM with character context"""
        
        # Build prompt
        character_context = character.to_prompt_context()
        
        # Get SCB context if available
        scb_context = ""
        if self.scb_client and character.scb_context_lines > 0:
            try:
                scb_data = self.scb_client.get_context_for_decision()
                if scb_data:
                    scb_context = self.scb_client.format_context_for_prompt(scb_data)
                    # Limit to configured lines
                    scb_lines = scb_context.split('\n')[:character.scb_context_lines]
                    scb_context = '\n'.join(scb_lines)
            except Exception as e:
                logger.warning(f"Failed to get SCB context: {e}")
        
        # Get conversation history if needed
        conversation_context = ""
        if include_conversation_history:
            recent_turns = self.conversation_history.get_recent_turns(
                limit=character.conversation_history_size // 2  # Half the limit for context
            )
            conversation_context = self.conversation_history.format_for_prompt(recent_turns)
        
        # Format the prompt
        prompt_data = {
            **event.data,
            "event_type": event.event_type,
            "source": event.source,
            "priority": event.priority
        }
        
        specific_prompt = prompt_template.format(**prompt_data)
        
        # Build full prompt
        full_prompt = f"""{character_context}

{f"Memory Context:{chr(10)}{scb_context}{chr(10)}" if scb_context else ""}
{f"Conversation History:{chr(10)}{conversation_context}{chr(10)}" if conversation_context else ""}
Current Situation: {specific_prompt}

Generate a response that:
1. Stays true to your character
2. Addresses the current situation appropriately
3. Avoids repeating these recent responses: {', '.join([r['text'][:50] + '...' for r in list(self.state.recent_responses)[-3:]])}

Response:"""
        
        # Call LLM (this would integrate with your existing LLM system)
        response = await self._call_llm(full_prompt)
        
        return response
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM service using existing infrastructure - SIMPLE SYNCHRONOUS APPROACH"""
        try:
            # Use the existing LLM configuration - EXACTLY like reactive mode
            from utils.llm.llm_utils import stream_llm_chunks
            from queue import Queue
            from config import get_config
            
            # Get base configuration from the system
            base_config = get_config()
            
            # Create a config for the LLM call
            llm_config = {
                **base_config,  # Use system's LLM configuration
                **self.llm_config,   # Override with orchestrator specifics
                'USE_STREAMING': False,  # Disable streaming for orchestrator
                'max_tokens': 150,  # Shorter responses for orchestrator
            }
            
            # Create a queue to collect chunks
            chunk_queue = Queue()
            chat_history = []
            
            # SIMPLE: Just call synchronously like the original system does
            # No executor, no async wrapper - just direct call
            response = stream_llm_chunks(prompt, chat_history, chunk_queue, llm_config)
            
            logger.info(f"Raw LLM response: {repr(response)}")
            final_response = response.strip() if response else "I understand and will help with that."
            logger.info(f"Final processed response: {repr(final_response)}")
            return final_response
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            # Fallback to pattern-based response
            return "I understand your request and will help you with that."
    
    def _is_repetitive(self, response: str) -> bool:
        """Check if response is too similar to recent responses"""
        if not self.state.recent_responses:
            return False
        
        # Simple similarity check (would be replaced with proper semantic similarity)
        response_lower = response.lower().strip()
        
        for recent in list(self.state.recent_responses)[-5:]:
            recent_lower = recent['text'].lower().strip()
            
            # Check exact match
            if response_lower == recent_lower:
                return True
            
            # Check substring match
            if len(response_lower) > 20 and response_lower in recent_lower:
                return True
            
            if len(recent_lower) > 20 and recent_lower in response_lower:
                return True
        
        return False
    
    async def _regenerate_non_repetitive(
        self,
        event: ExternalEvent,
        character: CharacterProfile,
        original_response: str
    ) -> str:
        """Regenerate response to avoid repetition"""
        logger.info("Regenerating response to avoid repetition")
        
        # Add variation instruction to prompt
        varied_prompt = f"Generate a different way to say: {original_response}\nUse different words and structure."
        
        return await self._call_llm(varied_prompt)
    
    async def _generate_autonomous_content(self, character: CharacterProfile, topic: str = None) -> str:
        """Generate autonomous content for the character"""
        
        # Use character's autonomous prompt context
        character_context = character.to_autonomous_prompt_context()
        
        # Get recent autonomous content to avoid repetition
        recent_content = self.autonomous_content_history[-5:] if self.autonomous_content_history else []
        
        # Determine topic
        if not topic:
            # Select from character's autonomous topics or use expertise
            topics = character.autonomous_topics if character.autonomous_topics else character.domain_expertise
            if topics:
                import random
                topic = random.choice(topics)
            else:
                topic = "general knowledge"
        
        # Build autonomous prompt
        full_prompt = f"""{character_context}

Current Topic Focus: {topic}

Recent Content (AVOID REPEATING):
{chr(10).join([f"- {content[:100]}..." for content in recent_content])}

Generate autonomous content that:
1. Focuses on the current topic: {topic}
2. Provides value without user prompts
3. Is completely different from recent content
4. Matches your character's autonomous behavior style
5. Encourages engagement or learning

Autonomous Content:"""
        
        # Generate content
        response = await self._call_llm(full_prompt)
        
        # Check for repetition against autonomous content history
        if self._is_content_repetitive(response, self.autonomous_content_history):
            logger.info("Autonomous content is repetitive, regenerating...")
            # Try with different approach
            varied_prompt = f"Generate completely different content about {topic}. Avoid: {response[:100]}... Use a different angle or approach."
            response = await self._call_llm(varied_prompt)
        
        # Add to autonomous content history
        self.autonomous_content_history.append(response)
        
        # Keep only recent autonomous content (last 10)
        if len(self.autonomous_content_history) > 10:
            self.autonomous_content_history = self.autonomous_content_history[-10:]
        
        return response
    
    def _is_content_repetitive(self, content: str, history: list, threshold: float = 0.7) -> bool:
        """Check if content is too similar to recent autonomous content"""
        if not history:
            return False
        
        content_lower = content.lower().strip()
        
        for past_content in history[-3:]:  # Check last 3 pieces of content
            past_lower = past_content.lower().strip()
            
            # Simple similarity check
            if len(content_lower) > 50 and len(past_lower) > 50:
                # Check for significant overlap
                content_words = set(content_lower.split())
                past_words = set(past_lower.split())
                
                if content_words and past_words:
                    intersection = content_words.intersection(past_words)
                    union = content_words.union(past_words)
                    similarity = len(intersection) / len(union) if union else 0
                    
                    if similarity > threshold:
                        return True
        
        return False
    
    async def start_autonomous_mode(self, topic: str = None) -> bool:
        """Start autonomous content generation"""
        try:
            if not self.character_manager.is_autonomous_mode():
                logger.warning("Character manager not in autonomous mode")
                return False
            
            character = self.character_manager.get_current_character()
            if not character or not character.autonomous_enabled:
                logger.warning(f"Character not suitable for autonomous mode: {character}")
                return False
            
            # Stop any existing autonomous task properly
            await self.stop_autonomous_mode()
            
            # Create continuous autonomous task
            logger.info(f"Starting autonomous mode for {character.name}")
            self.autonomous_task = asyncio.create_task(self._autonomous_content_loop(topic))
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting autonomous mode: {e}")
            return False
    
    async def stop_autonomous_mode(self) -> bool:
        """Stop autonomous content generation"""
        if self.autonomous_task:
            self.autonomous_task.cancel()
            try:
                # Wait for the task to be properly cancelled
                await asyncio.wait_for(self.autonomous_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                # Task was cancelled or timed out, which is expected
                pass
            except Exception as e:
                logger.warning(f"Error waiting for autonomous task to cancel: {e}")
            finally:
                self.autonomous_task = None
        
        logger.info("Stopped autonomous mode")
        return True
    
    async def _autonomous_content_loop(self, topic: str = None):
        """Continuous loop for autonomous content generation - SIMPLE APPROACH"""
        logger.info(f"🤖 Starting continuous autonomous content loop (simple approach)")
        
        try:
            while self.character_manager.is_autonomous_mode():
                character = self.character_manager.get_current_character()
                if not character or not character.autonomous_enabled:
                    logger.info("Character no longer supports autonomous mode, stopping loop")
                    break
                
                logger.info(f"🔄 Generating autonomous content for {character.name} (interval: {character.autonomous_interval}s)")
                
                # SIMPLE: Just call the same LLM function that reactive mode uses
                try:
                    # Create a simple autonomous prompt
                    autonomous_prompt = f"""You are {character.name}.
{character.role}

Current topic focus: {topic or 'general content'}

You are in AUTONOMOUS MODE - generate engaging content without waiting for user prompts.
Provide educational, entertaining, or helpful content that matches your character.
Keep it conversational and engaging.

Generate autonomous content:"""
                    
                    # Call the SAME LLM function that reactive mode uses
                    response = await self._call_llm(autonomous_prompt)
                    
                    if response and response.strip():
                        logger.info(f"✅ Generated autonomous content: {response[:100]}...")
                        
                        # Send directly to TTS - SAME as reactive mode
                        self._send_response_to_tts(response, character.id)
                        
                        # Add to history (same as reactive mode)
                        self.autonomous_content_history.append(response)
                        if len(self.autonomous_content_history) > 10:
                            self.autonomous_content_history = self.autonomous_content_history[-10:]
                    else:
                        logger.warning("❌ No autonomous content generated")
                        
                except Exception as e:
                    logger.error(f"❌ Error generating autonomous content: {e}")
                
                # Wait for the character's autonomous interval
                logger.info(f"⏱️ Waiting {character.autonomous_interval}s until next autonomous content...")
                await asyncio.sleep(character.autonomous_interval)
                
        except asyncio.CancelledError:
            logger.info("🛑 Autonomous content loop cancelled")
            raise
        except Exception as e:
            logger.error(f"❌ Error in autonomous content loop: {e}")
            await asyncio.sleep(5)  # Brief pause before retrying
        
        logger.info("🏁 Autonomous content loop ended")
    
    def _send_response_to_tts(self, text: str, character_id: str):
        """Send response to TTS pipeline - CENTRALIZED for ALL response types"""
        import requests
        
        logger.info(f"🔊 CORE TTS: Sending response to TTS pipeline: {text[:100]}...")
        
        try:
            payload = {
                'text': text,
                'autonomous_context': {
                    'source': 'reactive_orchestrator',
                    'character_id': character_id
                },
                'direct_speech': True
            }
            
            # Call the process_text endpoint for TTS processing
            response = requests.post(
                'http://localhost:5001/process_text',
                json=payload,
                timeout=10
            )
            
            logger.info(f"🔊 CORE TTS: HTTP response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ CORE TTS: Failed to send to TTS pipeline: {response.text}")
            else:
                logger.info(f"✅ CORE TTS: Successfully sent response to TTS pipeline")
                
        except Exception as e:
            logger.error(f"❌ CORE TTS: Error sending to TTS pipeline: {e}")
    
    async def process_event_queue(self):
        """Process pending events in the queue"""
        import time
        
        pending_events = [e for e in self.state.event_queue if not e.processed]
        
        # Sort by priority and timestamp
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        pending_events.sort(
            key=lambda e: (priority_order.get(e.priority, 3), e.timestamp)
        )
        
        for event in pending_events:
            # Check speech gap
            time_since_last = time.time() - self.state.last_speech_time
            if time_since_last < self.min_speech_gap:
                await asyncio.sleep(self.min_speech_gap - time_since_last)
            
            await self.process_event(event)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current orchestrator state"""
        character = self.character_manager.get_current_character()
        
        return {
            "character": {
                "id": character.id if character else None,
                "name": character.name if character else None,
                "autonomous_enabled": character.autonomous_enabled if character else False
            },
            "mode": {
                "current_mode": self.character_manager.get_current_mode(),
                "autonomous_active": self.character_manager.autonomous_active,
                "autonomous_content_count": len(self.autonomous_content_history)
            },
            "event_queue": [e.to_dict() for e in self.state.event_queue],
            "recent_responses": list(self.state.recent_responses),
            "is_speaking": self.state.is_speaking,
            "last_speech_time": self.state.last_speech_time,
            "active_topic": self.state.active_topic
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.character_manager.cleanup() 