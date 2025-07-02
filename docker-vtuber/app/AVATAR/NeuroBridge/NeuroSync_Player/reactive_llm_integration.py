"""
Integration module to connect Reactive Orchestrator with existing llm_to_face.py
This provides a compatibility layer for the existing infrastructure
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from queue import Queue
import os

from orchestrator import ReactiveOrchestrator
from character_config import get_character_manager

logger = logging.getLogger(__name__)


class ReactiveOrchestratorWrapper:
    """Wrapper to make ReactiveOrchestrator compatible with existing llm_to_face.py interface"""
    
    def __init__(self, app, system_objects: Dict[str, Any]):
        self.app = app
        self.system_objects = system_objects
        
        # Initialize reactive orchestrator with config
        config = {
            'scb_client': system_objects.get('scb_client'),
            'llm_config': system_objects.get('llm_config', {}),
            'timing': {
                'min_speech_gap': float(os.getenv('MIN_SPEECH_GAP', '2.5')),
                'response_timeout': float(os.getenv('RESPONSE_TIMEOUT', '30.0'))
            },
            'anti_repetition': {
                'enabled': os.getenv('ANTI_REPETITION_ENABLED', 'true').lower() == 'true',
                'threshold': float(os.getenv('SIMILARITY_THRESHOLD', '0.85'))
            }
        }
        
        self.orchestrator = ReactiveOrchestrator(config)
        self.processing_task = None
        
        # Register API routes
        self._register_routes()
        
        logger.info("Reactive Orchestrator Wrapper initialized")
    
    def _register_routes(self):
        """Register reactive API routes with the Flask app"""
        from orchestrator.api import reactive_api
        self.app.register_blueprint(reactive_api)
        logger.info("Reactive API routes registered")
    
    def should_orchestrate_request(self, user_input: str, autonomous_context: Any) -> bool:
        """Check if request should be orchestrated"""
        # Don't orchestrate if it's already from orchestrator
        if autonomous_context and isinstance(autonomous_context, dict):
            source = autonomous_context.get('source', '')
            if source in ['reactive_orchestrator', 'autonomous_content']:
                return False
        
        # Always orchestrate regular user input
        return True
    
    def process_orchestrated_input(self, user_input: str, autonomous_context: Any):
        """Process input through reactive orchestrator"""
        try:
            # Run async processing synchronously for Flask compatibility
            asyncio.run(self._process_input_async(user_input, autonomous_context))
        except Exception as e:
            logger.error(f"Error in process_orchestrated_input: {e}")
            # Fallback: send direct response
            self._send_to_llm_face("I understand your message and will respond accordingly.")
    
    async def _process_input_async(self, user_input: str, autonomous_context: Any):
        """Async processing of input"""
        try:
            # Create chat event
            event_data = {
                'type': 'chat',
                'source': 'user',
                'priority': 'high',
                'data': {
                    'message': user_input,
                    'context': autonomous_context
                }
            }
            
            # Add to queue and process
            event_id = await self.orchestrator.add_external_event(event_data)
            
            # Get the event and process it
            event = next((e for e in self.orchestrator.state.event_queue if e.id == event_id), None)
            if event:
                response = await self.orchestrator.process_event(event)
                logger.info(f"Orchestrator generated response: {repr(response)}")
                
                if response:
                    # Send response through the existing system
                    logger.info(f"Sending response to TTS pipeline: {response[:100]}...")
                    self._send_to_llm_face(response)
                    logger.info(f"Response sent to TTS pipeline successfully")
                else:
                    logger.warning(f"No response generated for event {event_id}")
            
        except Exception as e:
            logger.error(f"Error processing orchestrated input: {e}")
    
    def _send_to_llm_face(self, text: str):
        """Send text through the existing llm_to_face process_text endpoint"""
        import requests
        
        logger.info(f"_send_to_llm_face called with text: {text[:100]}...")
        
        try:
            payload = {
                'text': text,
                'autonomous_context': {
                    'source': 'reactive_orchestrator',
                    'character_id': self.orchestrator.character_manager.current_character_id
                },
                'direct_speech': True  # Use direct speech for orchestrator output
            }
            
            logger.info(f"Sending HTTP POST to /process_text with payload: {payload}")
            
            # Call the process_text endpoint with our response
            response = requests.post(
                'http://localhost:5001/process_text',
                json=payload,
                timeout=10
            )
            
            logger.info(f"HTTP response status: {response.status_code}")
            logger.info(f"HTTP response body: {response.text}")
            
            if response.status_code != 200:
                logger.error(f"Failed to send to llm_to_face: {response.text}")
            else:
                logger.info(f"Successfully sent response to TTS pipeline")
                
        except Exception as e:
            logger.error(f"Error sending to llm_to_face: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def start_orchestrator(self):
        """Start the orchestrator background processing"""
        logger.info("Starting Reactive Orchestrator background processing")
        
        # Start event processing loop
        self.processing_task = asyncio.create_task(self._background_processing())
    
    async def _background_processing(self):
        """Background task to process events"""
        while True:
            try:
                # Process event queue periodically
                await self.orchestrator.process_event_queue()
                
                # Wait before next check
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background processing: {e}")
                await asyncio.sleep(5.0)  # Wait longer on error
    
    async def stop_orchestrator(self):
        """Stop the orchestrator"""
        logger.info("Stopping Reactive Orchestrator")
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup
        self.orchestrator.cleanup()
    
    def register_speech_completion_callback(self, system_objects: Dict[str, Any]):
        """Register callback for speech completion events"""
        # This maintains compatibility with existing system
        pass
    
    @property
    def state_hooks(self):
        """Provide state hooks interface for compatibility"""
        return ReactiveStateHooks(self.orchestrator)


class ReactiveStateHooks:
    """State hooks for compatibility with existing orchestrator interface"""
    
    def __init__(self, orchestrator: ReactiveOrchestrator):
        self.orchestrator = orchestrator
    
    def hook_conversation_input(self, user_input: str, autonomous_context: Any):
        """Hook for conversation input"""
        # Add to conversation history
        self.orchestrator.conversation_history.add_turn(
            speaker="user",
            text=user_input,
            metadata={"context": autonomous_context}
        )
    
    def hook_environment_change_start(self, prompt: str):
        """Hook for environment change start"""
        self.orchestrator.state.active_topic = f"environment_change: {prompt}"
    
    def hook_environment_change_end(self, prompt: str, success: bool):
        """Hook for environment change end"""
        if success:
            logger.info(f"Environment change completed: {prompt}")
        else:
            logger.error(f"Environment change failed: {prompt}")
        
        self.orchestrator.state.active_topic = None
    
    def hook_audio_start(self):
        """Hook for audio start"""
        self.orchestrator.state.is_speaking = True
    
    def hook_audio_end(self):
        """Hook for audio end"""
        self.orchestrator.state.is_speaking = False


def initialize_reactive_orchestrator(app, system_objects: Dict[str, Any]) -> Optional[ReactiveOrchestratorWrapper]:
    """Initialize the reactive orchestrator wrapper"""
    try:
        wrapper = ReactiveOrchestratorWrapper(app, system_objects)
        
        # Store in app config for access by routes
        app.config['REACTIVE_ORCHESTRATOR'] = wrapper.orchestrator
        
        return wrapper
        
    except Exception as e:
        logger.error(f"Failed to initialize reactive orchestrator: {e}")
        return None 