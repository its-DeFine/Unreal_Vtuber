"""
Wrapper to integrate Autonomous Orchestrator V2 with existing NeuroSync system
This replaces the old orchestrator seamlessly
"""

import asyncio
import logging
import time
import threading
from typing import Optional, TYPE_CHECKING
from enum import Enum
from flask import Flask, request, jsonify

# Import for type checking only to avoid circular imports
if TYPE_CHECKING:
    from autonomous_orchestrator_v2 import AutonomousOrchestratorV2


# Export the enums for compatibility
class ActionType(Enum):
    """Types of actions the orchestrator can take"""
    SPEECH = "speech"
    ENVIRONMENT = "environment"
    INTERRUPT = "interrupt"
    IDLE = "idle"


class Priority(Enum):
    """Priority levels for decision making"""
    URGENT = 5      # Immediate interruption required
    HIGH = 4        # Important, interrupt if not critical
    MEDIUM = 3      # Normal conversation flow
    LOW = 2         # Background/ambient
    MINIMAL = 1     # Only when idle

# Global orchestrator instance and thread management
orchestrator_v2: Optional['AutonomousOrchestratorV2'] = None
orchestrator_thread: Optional[object] = None  
orchestrator_loop: Optional[asyncio.AbstractEventLoop] = None


def initialize_orchestrator_v2(app: Flask = None):
    """Initialize the V2 orchestrator"""
    global orchestrator_v2, orchestrator_thread, orchestrator_loop
    
    logger = logging.getLogger(__name__)
    logger.info("🔄 Initializing Autonomous Orchestrator V2...")
    
    # Create the V2 orchestrator  
    from autonomous_orchestrator_v2 import AutonomousOrchestratorV2
    orchestrator_v2 = AutonomousOrchestratorV2()
    orchestrator_loop = None
    
    # Start it in a background thread with its own event loop
    
    def run_orchestrator():
        """Run orchestrator in background thread with proper cleanup"""
        global orchestrator_loop
        try:
            orchestrator_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(orchestrator_loop)
            orchestrator_loop.run_until_complete(orchestrator_v2.start())
        except Exception as e:
            logger.error(f"❌ Error running orchestrator: {e}")
        finally:
            # Proper cleanup of event loop and tasks
            try:
                if orchestrator_loop and not orchestrator_loop.is_closed():
                    # Cancel all pending tasks
                    pending = asyncio.all_tasks(orchestrator_loop)
                    if pending:
                        for task in pending:
                            task.cancel()
                        # Wait for cancelled tasks to finish
                        orchestrator_loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    orchestrator_loop.close()
                    logger.info("🧹 Orchestrator event loop cleaned up")
            except Exception as cleanup_error:
                logger.error(f"❌ Error during orchestrator cleanup: {cleanup_error}")
    
    # Start orchestrator in background thread
    orchestrator_thread = threading.Thread(target=run_orchestrator, daemon=True)
    orchestrator_thread.start()
    
    # Give the thread a moment to start
    time.sleep(0.1)
    
    logger.info("✅ Autonomous Orchestrator V2 initialized and started in background")
    
    # Add Flask routes if app provided
    if app:
        add_orchestrator_routes(app)
        
    return orchestrator_v2


def shutdown_orchestrator_v2():
    """Properly shutdown the orchestrator and clean up background thread"""
    global orchestrator_v2, orchestrator_thread, orchestrator_loop
    
    logger = logging.getLogger(__name__)
    logger.info("🛑 Shutting down Autonomous Orchestrator V2...")
    
    try:
        if orchestrator_v2:
            orchestrator_v2.enabled = False
            
        # Give the orchestrator a moment to stop
        time.sleep(0.5)
        
        # If we have access to the event loop, signal it to stop
        if orchestrator_loop and not orchestrator_loop.is_closed():
            try:
                # Create a future to signal the shutdown
                orchestrator_loop.call_soon_threadsafe(lambda: orchestrator_loop.stop())
            except Exception as e:
                logger.error(f"❌ Error signaling loop shutdown: {e}")
        
        logger.info("✅ Orchestrator shutdown initiated")
        
    except Exception as e:
        logger.error(f"❌ Error during orchestrator shutdown: {e}")


def add_orchestrator_routes(app: Flask):
    """Add orchestrator control routes to Flask app"""
    
    @app.route('/orchestrator/status', methods=['GET'])
    def orchestrator_status():
        """Get orchestrator status"""
        if not orchestrator_v2:
            return jsonify({"error": "Orchestrator not initialized"}), 500
            
        try:
            state = orchestrator_v2.state
        except Exception as e:
            return jsonify({"error": f"Failed to get orchestrator state: {e}"}), 500
        
        status = {
            "enabled": orchestrator_v2.enabled,
            "running": orchestrator_v2.running,
            "current_action": {
                "is_speaking": state.is_speaking,
                "blendshape_active": state.blendshape_active,
                "current_speech_id": state.current_speech_id,
                "speech_queue_size": state.speech_queue_size
            },
            "idle_state": {
                "last_user_input": state.last_user_input_time,
                "true_idle_duration": state.true_idle_duration,
                "last_speech_completed": state.last_speech_completed
            },
            "configuration": {
                "min_idle_time": orchestrator_v2.MIN_IDLE_FOR_CONTENT,
                "min_speech_gap": orchestrator_v2.MIN_SPEECH_GAP,
                "decision_interval": orchestrator_v2.DECISION_INTERVAL
            }
        }
        
        return jsonify(status)
        
    @app.route('/orchestrator/control', methods=['POST'])
    def orchestrator_control():
        """Control orchestrator actions"""
        if not orchestrator_v2:
            return jsonify({"error": "Orchestrator not initialized"}), 500
            
        data = request.json
        action = data.get('action')
        
        if action == 'interrupt':
            # Trigger interrupt
            asyncio.create_task(orchestrator_v2._interrupt_current_speech())
            return jsonify({"status": "interrupt_requested"})
            
        elif action == 'pause':
            # Pause autonomous generation
            orchestrator_v2.enabled = False
            return jsonify({"status": "paused"})
            
        elif action == 'resume':
            # Resume autonomous generation
            orchestrator_v2.enabled = True
            return jsonify({"status": "resumed"})
            
        elif action == 'queue_speech':
            # Queue manual speech
            text = data.get('text', '')
            priority = data.get('priority', 'medium')
            
            orchestrator_v2.process_user_input(text, {
                "source": "manual_control",
                "priority_override": priority
            })
            
            return jsonify({"status": "speech_queued"})
            
        else:
            return jsonify({"error": "Unknown action"}), 400


# Compatibility layer for old orchestrator interface
class AutonomousOrchestratorCompat:
    """Compatibility wrapper to make V2 work with existing code"""
    
    def __init__(self, neurosync_player=None):
        self.neurosync_player = neurosync_player
        self.orchestrator_v2 = initialize_orchestrator_v2()
        self.logger = logging.getLogger(__name__)
        
        # Add compatibility attributes for the old interface
        self.decision_engine = self._create_decision_engine_proxy()
        self.action_queue = []  # Proxy for queue operations
        self._running_state = True  # Internal running state
        self.last_action_time = time.time()
        self.decision_loop_interval = 1.0
        self.state_monitor = self._create_state_monitor_proxy()
        
    def _create_decision_engine_proxy(self):
        """Create proxy object for decision_engine compatibility"""
        class DecisionEngineProxy:
            def __init__(self, wrapper):
                self.wrapper = wrapper
                self.interruption_threshold = Priority.HIGH
                self.idle_timeout = 10.0
                
        return DecisionEngineProxy(self)
        
    def _create_state_monitor_proxy(self):
        """Create proxy object for state_monitor compatibility"""
        class StateMonitorProxy:
            def __init__(self, wrapper):
                self.wrapper = wrapper
                
            def get_state_snapshot(self):
                """Get state snapshot from V2 orchestrator"""
                try:
                    if self.wrapper.orchestrator_v2:
                        state = self.wrapper.orchestrator_v2.state
                        # Create a simple object with the expected attributes
                        class StateSnapshot:
                            def __init__(self, v2_state):
                                self.is_speaking = v2_state.is_speaking
                                self.tts_queue_size = v2_state.speech_queue_size
                                self.blendshape_active = v2_state.blendshape_active
                                self.current_environment = "default"
                                self.environment_changing = False
                                self.conversation_active = True
                                self.last_input_time = v2_state.last_user_input_time
                        return StateSnapshot(state)
                except Exception as e:
                    self.wrapper.logger.error(f"Error getting state snapshot: {e}")
                    
                # Return default state if error
                class DefaultState:
                    is_speaking = False
                    tts_queue_size = 0
                    blendshape_active = False
                    current_environment = "default"
                    environment_changing = False
                    conversation_active = False
                    last_input_time = None
                return DefaultState()
                
            def update_audio_state(self, is_speaking=None, queue_size=None, estimated_end_time=None):
                """Update audio state (compatibility)"""
                if self.wrapper.orchestrator_v2 and is_speaking is not None:
                    self.wrapper.orchestrator_v2.state.is_speaking = is_speaking
                    
            def update_blendshape_state(self, active=None, queue_size=None):
                """Update blendshape state (called by the system)"""
                if self.wrapper.orchestrator_v2 and active is not None:
                    if active and not self.wrapper.orchestrator_v2.state.blendshape_active:
                        self.wrapper.orchestrator_v2.blendshape_monitor.on_blendshape_start()
                    elif not active and self.wrapper.orchestrator_v2.state.blendshape_active:
                        self.wrapper.orchestrator_v2.blendshape_monitor.on_blendshape_complete()
                        
            def update_conversation_context(self, keywords, active=True):
                """Update conversation context (compatibility)"""
                # This updates last input time in V2
                if self.wrapper.orchestrator_v2 and active:
                    self.wrapper.orchestrator_v2.state.last_user_input_time = time.time()
                
        return StateMonitorProxy(self)
        
    async def start(self):
        """Start the orchestrator (already started in init)"""
        self.logger.info("Compatibility layer: start() called - orchestrator already running")
        
    async def stop(self):
        """Stop the orchestrator"""
        try:
            self.logger.info("🛑 Compatibility layer: stop() called - shutting down orchestrator")
            shutdown_orchestrator_v2()
        except Exception as e:
            self.logger.error(f"❌ Error stopping orchestrator: {e}")
        
    def process_external_input(self, text: str, autonomous_context: str = None):
        """Process external input"""
        try:
            if self.orchestrator_v2:
                self.orchestrator_v2.process_user_input(text, {
                    "autonomous_context": autonomous_context
                })
        except Exception as e:
            self.logger.error(f"Error processing external input: {e}")
        
    def queue_action(self, action_type, content, priority=None, metadata=None, interrupt_current=False):
        """Queue an action (compatibility method)"""
        # Convert old action to new format
        if hasattr(action_type, 'value'):
            action_value = action_type.value
        else:
            action_value = str(action_type)
            
        if action_value == "speech":
            self.orchestrator_v2.process_user_input(content, metadata or {})
            
    @property
    def enabled(self):
        return self.orchestrator_v2.enabled if self.orchestrator_v2 else False
        
    @enabled.setter
    def enabled(self, value):
        if self.orchestrator_v2:
            self.orchestrator_v2.enabled = value
            
    @property 
    def running(self):
        return self.orchestrator_v2.running if self.orchestrator_v2 else self._running_state
        
    @running.setter
    def running(self, value):
        self._running_state = value
        if self.orchestrator_v2:
            self.orchestrator_v2.enabled = value



# Drop-in replacement for old orchestrator
def create_autonomous_orchestrator(neurosync_player=None):
    """Create orchestrator with compatibility layer"""
    return AutonomousOrchestratorCompat(neurosync_player)


# Alias for compatibility with existing imports
AutonomousOrchestrator = AutonomousOrchestratorCompat 