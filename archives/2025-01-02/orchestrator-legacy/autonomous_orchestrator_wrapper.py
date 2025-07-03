"""
Wrapper to integrate Autonomous Orchestrator V2 with existing NeuroSync system
This replaces the old orchestrator seamlessly
"""

import asyncio
import logging
import time
import threading
from typing import Optional, TYPE_CHECKING, Any, Dict
from enum import Enum
from flask import Flask, request, jsonify

# Import for type checking only to avoid circular imports
if TYPE_CHECKING:
    from .autonomous_orchestrator_v2 import AutonomousOrchestratorV2

# Import simple speech system (using absolute import)
from simple_autonomous_speech import start_simple_autonomous_speech, get_simple_speech_instance

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
orchestrator_thread: Optional[threading.Thread] = None
orchestrator_loop: Optional[asyncio.AbstractEventLoop] = None
simple_speech_task: Optional[asyncio.Task] = None


def initialize_orchestrator_v2(app: Flask = None):
    """Initialize and start the Autonomous Orchestrator V2 with Simple Speech System"""
    global orchestrator_v2, orchestrator_thread, orchestrator_loop, simple_speech_task
    
    logger = logging.getLogger(__name__)
    logger.info("🔄 Initializing Hybrid Autonomous Orchestrator System...")
    
    try:
        # Import here to avoid circular imports
        from autonomous_orchestrator_v2 import create_autonomous_orchestrator_v2
        
        # Create orchestrator instance
        orchestrator_v2 = create_autonomous_orchestrator_v2()
        
        def run_orchestrator():
            """Run both orchestrators in a hybrid approach"""
            global orchestrator_loop, simple_speech_task
            
            try:
                # Create new event loop for this thread
                orchestrator_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(orchestrator_loop)
                
                logger.info("🧠 Starting Hybrid Orchestrator System...")
                
                async def start_hybrid_system():
                    """Start both the enhanced orchestrator and simple speech system"""
                    
                    # Start the enhanced orchestrator (for complex decision making)
                    if orchestrator_v2:
                        await orchestrator_v2.start()
                        logger.info("✅ Enhanced Orchestrator V2 started")
                    
                    # Start the simple speech system (for reliable autonomous speech)
                    simple_speech_task = asyncio.create_task(start_simple_autonomous_speech())
                    logger.info("✅ Simple Autonomous Speech started")
                    
                    # Keep both systems running
                    while orchestrator_v2 and orchestrator_v2.running:
                        await asyncio.sleep(1.0)
                        
                # Run the hybrid system
                orchestrator_loop.run_until_complete(start_hybrid_system())
                
            except Exception as e:
                logger.error(f"❌ Error in orchestrator thread: {e}")
            finally:
                logger.info("🧹 Orchestrator event loop cleaned up")
                
        # Start in background thread
        orchestrator_thread = threading.Thread(target=run_orchestrator, daemon=True)
        orchestrator_thread.start()
        
        # Brief pause to ensure initialization
        time.sleep(0.5)
        
        # Add routes if Flask app provided
        if app:
            add_orchestrator_routes(app)
            add_simple_speech_routes(app)
            
        logger.info("✅ Hybrid Autonomous Orchestrator System initialized and started")
        return orchestrator_v2
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize orchestrator: {e}")
        return None


def shutdown_orchestrator_v2():
    """Properly shutdown both orchestrators and clean up background thread"""
    global orchestrator_v2, orchestrator_thread, orchestrator_loop, simple_speech_task
    
    logger = logging.getLogger(__name__)
    logger.info("🛑 Shutting down Hybrid Autonomous Orchestrator System...")
    
    try:
        # Stop the enhanced orchestrator
        if orchestrator_v2:
            orchestrator_v2.enabled = False
            
        # Stop the simple speech system
        simple_speech_instance = get_simple_speech_instance()
        if simple_speech_instance.running:
            asyncio.create_task(simple_speech_instance.stop())
            
        # Give both systems a moment to stop
        time.sleep(0.5)
        
        # If we have access to the event loop, signal it to stop
        if orchestrator_loop and not orchestrator_loop.is_closed():
            try:
                # Create a future to signal the shutdown
                orchestrator_loop.call_soon_threadsafe(lambda: orchestrator_loop.stop())
            except Exception as e:
                logger.error(f"❌ Error signaling loop shutdown: {e}")
        
        logger.info("✅ Hybrid orchestrator shutdown initiated")
        
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

    @app.route('/orchestrator/event', methods=['POST'])
    def orchestrator_event():
        """Endpoint to send external environment events to orchestrator"""
        if not orchestrator_v2:
            return jsonify({"error": "Orchestrator not initialized"}), 500
        try:
            data = request.json or {}
            event_type = data.get('event_type', 'unknown')
            payload = data.get('payload', {})
            priority = data.get('priority', 'medium')  # Currently unused but reserved
            # Process event in orchestrator loop thread-safe
            if orchestrator_loop and not orchestrator_loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    orchestrator_v2.process_external_event(event_type, payload),
                    orchestrator_loop
                )
            else:
                # Fallback to current loop
                asyncio.create_task(orchestrator_v2.process_external_event(event_type, payload))
            return jsonify({"status": "event_processed", "event_type": event_type})
        except Exception as e:
            return jsonify({"error": f"Failed to process event: {e}"}), 500

    @app.route('/orchestrator/config', methods=['POST'])
    def orchestrator_config():
        """Update orchestrator runtime config (e.g., scb_max_inputs)"""
        if not orchestrator_v2:
            return jsonify({"error": "Orchestrator not initialized"}), 500
        data = request.json or {}
        orchestrator_loop.call_soon_threadsafe(lambda: orchestrator_v2.update_config(**data))
        return jsonify({"status": "config_updated", **data})


def add_simple_speech_routes(app: Flask):
    """Add simple speech control routes to Flask app"""
    
    @app.route('/simple_speech/status', methods=['GET'])
    def simple_speech_status():
        """Get simple speech system status"""
        try:
            speech_system = get_simple_speech_instance()
            status = speech_system.get_status()
            return jsonify(status)
        except Exception as e:
            return jsonify({"error": f"Failed to get speech system status: {e}"}), 500
            
    @app.route('/simple_speech/control', methods=['POST'])
    def simple_speech_control():
        """Control simple speech system"""
        try:
            speech_system = get_simple_speech_instance()
            data = request.json
            action = data.get('action')
            
            if action == 'pause':
                speech_system.config.enabled = False
                return jsonify({"status": "paused"})
                
            elif action == 'resume':
                speech_system.config.enabled = True
                return jsonify({"status": "resumed"})
                
            elif action == 'set_interval':
                interval = float(data.get('interval', 15.0))
                speech_system.config.speech_interval = interval
                return jsonify({"status": "interval_updated", "new_interval": interval})
                
            elif action == 'trigger_now':
                # Trigger immediate speech generation
                speech_system.last_speech_time = 0.0  # Force next cycle
                return jsonify({"status": "triggered"})
                
            else:
                return jsonify({"error": "Unknown action"}), 400
                
        except Exception as e:
            return jsonify({"error": f"Failed to control speech system: {e}"}), 500


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