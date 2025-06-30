"""
Autonomous Orchestrator for System 1
====================================

This orchestrator sits above the NeuroSync Player and provides autonomous decision-making
capabilities for real-time conversational AI. It can:

1. Autonomously decide between speech generation and environment changes
2. Monitor audio/TTS/blendshape transmission states
3. Interrupt current processes like humans do in conversation
4. Integrate with System 2 through the Shared Cognitive Blackboard

Architecture:
- Decision Engine: Evaluates context and priorities
- State Monitor: Tracks all system states in real-time
- Action Executor: Manages speech and environment actions
- Context Manager: Maintains conversation and environmental context
"""

import asyncio
import threading
import time
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import queue
import json
import os

# SCB Integration (if available)
try:
    from utils.scb.orchestrator_scb_client import OrchestratorSCBClient
    SCB_AVAILABLE = True
except ImportError:
    SCB_AVAILABLE = False
    print("⚠️ SCB not available - System 2 integration disabled")


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


@dataclass
class SystemState:
    """Current state of all system components"""
    # Audio/TTS State
    is_speaking: bool = False
    tts_queue_size: int = 0
    audio_playback_active: bool = False
    current_speech_priority: Priority = Priority.MINIMAL
    speech_start_time: Optional[float] = None
    estimated_speech_end_time: Optional[float] = None
    
    # Blendshape/Animation State
    blendshape_active: bool = False
    animation_queue_size: int = 0
    
    # Game Environment State
    current_environment: str = "default"
    environment_changing: bool = False
    
    # Conversation Context
    last_input_time: Optional[float] = None
    conversation_active: bool = False
    context_keywords: List[str] = field(default_factory=list)
    
    # System 2 Integration
    scb_last_update: Optional[float] = None
    scb_priority_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionRequest:
    """Request for an action to be executed"""
    action_type: ActionType
    priority: Priority
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    interrupt_current: bool = False


class StateMonitor:
    """Monitors all system states in real-time"""
    
    def __init__(self):
        self.state = SystemState()
        self._lock = threading.Lock()
        self._callbacks = []
        self.logger = logging.getLogger("StateMonitor")
        
    def register_callback(self, callback):
        """Register callback for state changes"""
        self._callbacks.append(callback)
        
    def update_audio_state(self, is_speaking: bool, queue_size: int = 0, 
                          estimated_end_time: Optional[float] = None):
        """Update audio/TTS state"""
        with self._lock:
            prev_speaking = self.state.is_speaking
            self.state.is_speaking = is_speaking
            self.state.tts_queue_size = queue_size
            self.state.estimated_speech_end_time = estimated_end_time
            
            if is_speaking and not prev_speaking:
                self.state.speech_start_time = time.time()
            elif not is_speaking and prev_speaking:
                self.state.speech_start_time = None
                
        self._notify_callbacks("audio_state_changed")
        
    def update_blendshape_state(self, active: bool, queue_size: int = 0):
        """Update blendshape/animation state"""
        with self._lock:
            self.state.blendshape_active = active
            self.state.animation_queue_size = queue_size
        self._notify_callbacks("blendshape_state_changed")
        
    def update_environment_state(self, environment: str, changing: bool = False):
        """Update game environment state"""
        with self._lock:
            self.state.current_environment = environment
            self.state.environment_changing = changing
        self._notify_callbacks("environment_state_changed")
        
    def update_conversation_context(self, keywords: List[str], active: bool = True):
        """Update conversation context"""
        with self._lock:
            self.state.context_keywords = keywords
            self.state.conversation_active = active
            self.state.last_input_time = time.time()
        self._notify_callbacks("conversation_context_changed")
        
    def update_scb_context(self, scb_data: Dict[str, Any]):
        """Update System 2 context from SCB"""
        with self._lock:
            self.state.scb_priority_context = scb_data
            self.state.scb_last_update = time.time()
        self._notify_callbacks("scb_context_changed")
        
    def get_state_snapshot(self) -> SystemState:
        """Get thread-safe snapshot of current state"""
        with self._lock:
            # Create deep copy of state
            import copy
            return copy.deepcopy(self.state)
            
    def _notify_callbacks(self, event_type: str):
        """Notify all registered callbacks of state change"""
        for callback in self._callbacks:
            try:
                callback(event_type, self.get_state_snapshot())
            except Exception as e:
                self.logger.error(f"Error in state callback: {e}")


class DecisionEngine:
    """Intelligent decision making for autonomous behavior"""
    
    def __init__(self, state_monitor: StateMonitor):
        self.state_monitor = state_monitor
        self.logger = logging.getLogger("DecisionEngine")
        
        # Decision parameters (configurable)
        self.interruption_threshold = Priority.HIGH
        self.idle_timeout = 2.0  # seconds before considering system idle
        self.conversation_timeout = 30.0  # seconds before conversation considered over
        
    def should_interrupt_current_speech(self, new_request: ActionRequest, 
                                      current_state: SystemState) -> bool:
        """Determine if current speech should be interrupted for new request"""
        
        if not current_state.is_speaking:
            return False
            
        # Always interrupt for urgent requests
        if new_request.priority == Priority.URGENT:
            self.logger.info("🚨 Interrupting for URGENT priority")
            return True
            
        # Interrupt high priority if current speech is medium or lower
        if (new_request.priority == Priority.HIGH and 
            current_state.current_speech_priority.value <= Priority.MEDIUM.value):
            self.logger.info("⚡ Interrupting for HIGH priority")
            return True
            
        # Don't interrupt if new request is explicitly marked as non-interrupting
        if not new_request.interrupt_current:
            return False
            
        # Consider speech timing - easier to interrupt early in speech
        if current_state.speech_start_time:
            speech_duration = time.time() - current_state.speech_start_time
            if speech_duration < 1.0:  # First second is interruptible for high priority
                return new_request.priority.value >= Priority.HIGH.value
                
        return False
        
    def evaluate_action_priority(self, request: ActionRequest, 
                               current_state: SystemState) -> Priority:
        """Evaluate and potentially adjust action priority based on context"""
        
        base_priority = request.priority
        
        # Boost priority based on SCB context from System 2
        if current_state.scb_priority_context:
            scb_boost = self._evaluate_scb_priority_boost(
                request, current_state.scb_priority_context
            )
            if scb_boost > 0:
                new_priority_value = min(5, base_priority.value + scb_boost)
                adjusted_priority = Priority(new_priority_value)
                self.logger.info(f"🧠 SCB boosted priority: {base_priority} → {adjusted_priority}")
                return adjusted_priority
                
        # Boost priority if conversation has been idle
        if current_state.last_input_time:
            idle_time = time.time() - current_state.last_input_time
            if idle_time > self.idle_timeout:
                self.logger.info(f"⏰ Boosting priority due to {idle_time:.1f}s idle time")
                return Priority(min(5, base_priority.value + 1))
                
        return base_priority
        
    def _evaluate_scb_priority_boost(self, request: ActionRequest, 
                                   scb_context: Dict[str, Any]) -> int:
        """Evaluate priority boost based on System 2 context"""
        boost = 0
        
        # Check for urgent flags from System 2
        if scb_context.get("urgent_response_needed"):
            boost += 2
            self.logger.info("🚨 SCB: Urgent response needed - boosting priority by 2")
            
        # Check for emotional context
        emotion = scb_context.get("emotional_state")
        if emotion in ["excited", "urgent", "concerned"]:
            boost += 1
            self.logger.info(f"😊 SCB: Emotional state '{emotion}' - boosting priority by 1")
            
        # Check for environmental change requests
        if scb_context.get("environment_change_requested"):
            if request.action_type == ActionType.ENVIRONMENT:
                boost += 1
                self.logger.info("🎮 SCB: Environment change requested - boosting environment action")
                
        # Check recent directives relevance
        directives = scb_context.get("recent_directives", [])
        for directive in directives[:3]:  # Check top 3 directives
            directive_text = directive.get("text", "").lower()
            request_text = request.content.lower()
            
            # Simple keyword matching for relevance
            matching_keywords = 0
            for word in directive_text.split():
                if len(word) > 3 and word in request_text:
                    matching_keywords += 1
                    
            if matching_keywords >= 2:  # At least 2 matching keywords
                boost += 1
                self.logger.info(f"🎯 SCB: Request matches directive - boosting priority")
                break
                
        return boost
        
    def select_next_action(self, pending_requests: List[ActionRequest], 
                          current_state: SystemState) -> Optional[ActionRequest]:
        """Select the next action to execute based on current state and priorities"""
        
        if not pending_requests:
            return None
            
        # Filter and sort by adjusted priority
        viable_requests = []
        for request in pending_requests:
            adjusted_priority = self.evaluate_action_priority(request, current_state)
            viable_requests.append((request, adjusted_priority))
            
        # Sort by priority (highest first), then by timestamp (oldest first)
        viable_requests.sort(key=lambda x: (-x[1].value, x[0].timestamp))
        
        # Check if top request should interrupt current activity
        top_request, top_priority = viable_requests[0]
        
        if self.should_interrupt_current_speech(top_request, current_state):
            self.logger.info(f"🎯 Selected action with interruption: {top_request.action_type}")
            return top_request
            
        # If system is idle, execute top priority request
        if not current_state.is_speaking and not current_state.environment_changing:
            self.logger.info(f"🎯 Selected action for idle system: {top_request.action_type}")
            return top_request
            
        # Check if we should wait for current activity to finish
        if current_state.estimated_speech_end_time:
            time_remaining = current_state.estimated_speech_end_time - time.time()
            if time_remaining < 0.5 and top_priority.value >= Priority.MEDIUM.value:
                self.logger.info(f"⏱️ Waiting {time_remaining:.1f}s for speech to finish")
                return None
                
        return None


class AutonomousOrchestrator:
    """
    Main orchestrator class that provides autonomous decision-making for System 1
    
    This orchestrator:
    1. Monitors all system states in real-time
    2. Makes autonomous decisions about speech vs environment actions
    3. Can interrupt current processes like humans do
    4. Integrates with System 2 through SCB
    """
    
    def __init__(self, neurosync_player=None):
        """Initialize the Autonomous Orchestrator
        
        Args:
            neurosync_player: Optional reference to the NeuroSync Player instance
        """
        self.neurosync_player = neurosync_player
        self.system_objects = None  # Will be set later
        self.logger = logging.getLogger(__name__)
        
        # Load configuration from environment
        self.enabled = os.getenv("AUTONOMOUS_ORCHESTRATION_ENABLED", "false").lower() == "true"
        self.auto_interrupt_enabled = os.getenv("AUTO_INTERRUPT_ENABLED", "true").lower() == "true"
        self.decision_interval = float(os.getenv("DECISION_LOOP_INTERVAL", "0.1"))
        self.interrupt_threshold = int(os.getenv("INTERRUPT_THRESHOLD", "4"))  # HIGH priority
        self.idle_timeout = float(os.getenv("ORCHESTRATOR_IDLE_TIMEOUT", "2.0"))
        self.autonomous_environment_enabled = os.getenv("AUTONOMOUS_ENVIRONMENT_ENABLED", "true").lower() == "true"
        self.scb_poll_interval = float(os.getenv("SCB_POLL_INTERVAL", "2.0"))
        
        # Core components
        self.state_monitor = StateMonitor()
        self.decision_engine = DecisionEngine(self.state_monitor)
        self.action_queue: List[ActionRequest] = []
        self.running = False
        
        # Execution tracking
        self.current_action: Optional[ActionRequest] = None
        self.last_action_time = time.time()
        
        # Background tasks
        self.decision_task = None
        self.scb_monitor_task = None
        
        # Streaming context for more aware autonomous content
        self.streaming_context = {
            "stream_purpose": "AI Avatar Streaming and Interaction Demo",
            "interaction_count": 0,
            "recent_activities": [],
            "previous_topics": [],
            "last_environment_theme": "default"
        }
        
        # System 2 Integration
        self.scb_client = None
        self._initialize_scb_client()
        
        # Register state change callback
        self.state_monitor.register_callback(self._on_state_change)
        
        self.logger.info(f"🤖 Autonomous Orchestrator initialized (enabled: {self.enabled})")
        
    def _initialize_scb_client(self):
        """Initialize SCB client if available"""
        if SCB_AVAILABLE:
            try:
                self.scb_client = OrchestratorSCBClient()
                self.logger.info("✅ SCB integration enabled")
            except Exception as e:
                self.logger.warning(f"⚠️ SCB integration failed: {e}")
        
    async def start(self):
        """Start the autonomous orchestrator"""
        if self.running:
            self.logger.warning("Orchestrator already running")
            return
            
        self.running = True
        self.logger.info("🚀 Starting Autonomous Orchestrator")
        
        # Start decision loop
        self.decision_loop_task = asyncio.create_task(self._decision_loop())
        
        # Start SCB monitoring if available
        if self.scb_client:
            asyncio.create_task(self._scb_monitoring_loop())
            
        self.logger.info("✅ Autonomous Orchestrator started")
        
    async def stop(self):
        """Stop the autonomous orchestrator"""
        if not self.running:
            return
            
        self.running = False
        self.logger.info("🛑 Stopping Autonomous Orchestrator")
        
        # Cancel decision loop
        if self.decision_loop_task:
            self.decision_loop_task.cancel()
            try:
                await self.decision_loop_task
            except asyncio.CancelledError:
                pass
                
        self.logger.info("✅ Autonomous Orchestrator stopped")
        
    def queue_action(self, action_type: ActionType, content: str, 
                    priority: Priority = Priority.MEDIUM, 
                    metadata: Dict[str, Any] = None,
                    interrupt_current: bool = False) -> None:
        """Queue an action request for execution
        
        Args:
            action_type: Type of action (SPEECH, ENVIRONMENT, etc.)
            content: The content/payload for the action
            priority: Priority level for the action
            metadata: Additional metadata for the action
            interrupt_current: Whether to interrupt current action
        """
        
        request = ActionRequest(
            action_type=action_type,
            priority=priority,
            content=content,
            metadata=metadata or {},
            interrupt_current=interrupt_current
        )
        
        self.action_queue.append(request)
        self.logger.debug(f"📥 Queued {action_type.value} action with priority {priority.value}")
        
    def process_external_input(self, text: str, autonomous_context: str = None) -> None:
        """Process external input and decide on appropriate action"""
        
        # Update conversation context
        keywords = self._extract_keywords(text)
        self.state_monitor.update_conversation_context(keywords, active=True)
        
        # Track interaction
        self.streaming_context["interaction_count"] += 1
        
        # Determine if this is speech or environment request
        action_type = self._classify_input(text)
        
        # Determine priority based on salience (how important/relevant is this input?)
        priority = self._evaluate_input_salience(text, autonomous_context)
        
        # Decide if we should interrupt based on what we're currently doing
        current_state = self.state_monitor.get_state_snapshot()
        should_interrupt = self._should_interrupt_for_input(text, priority, current_state)
        
        # Queue the action
        metadata = {
            "autonomous_context": autonomous_context,
            "keywords": keywords,
            "interaction_number": self.streaming_context["interaction_count"]
        }
        
        self.queue_action(
            action_type=action_type,
            content=text,
            priority=priority,
            metadata=metadata,
            interrupt_current=should_interrupt
        )
        
        self.logger.info(f"📥 External input processed: {action_type.value}, priority={priority.name}, interrupt={should_interrupt}")
        
    def _evaluate_input_salience(self, text: str, autonomous_context: Any) -> Priority:
        """Evaluate how salient/important the input is in the current context"""
        
        # Start with base priority determination
        base_priority = self._determine_priority(text, autonomous_context)
        
        # Check for direct questions - these are highly salient
        if any(q in text.lower() for q in ["?", "what", "how", "why", "when", "where", "who"]):
            if base_priority.value < Priority.HIGH.value:
                base_priority = Priority.HIGH
                
        # Check for commands or requests
        command_words = ["show", "change", "set", "make", "do", "can you", "please", "try"]
        if any(cmd in text.lower() for cmd in command_words):
            if base_priority.value < Priority.HIGH.value:
                base_priority = Priority.HIGH
                
        # Check for topic changes - moderately salient
        current_keywords = self.state_monitor.get_state_snapshot().context_keywords
        new_keywords = self._extract_keywords(text)
        
        # If keywords are very different, it's a topic change
        if current_keywords and new_keywords:
            overlap = set(current_keywords) & set(new_keywords)
            if len(overlap) < len(new_keywords) * 0.3:  # Less than 30% overlap
                if base_priority.value < Priority.MEDIUM.value:
                    base_priority = Priority.MEDIUM
                    
        return base_priority
        
    def _should_interrupt_for_input(self, text: str, priority: Priority, current_state: SystemState) -> bool:
        """Decide if we should interrupt current activity for this input"""
        
        # Always interrupt for urgent priority
        if priority == Priority.URGENT:
            return True
            
        # If we're idle, no need to interrupt
        if not current_state.is_speaking and not current_state.environment_changing:
            return False
            
        # For high priority, consider what we're doing
        if priority == Priority.HIGH:
            # If we're doing auto-generated content, interrupt
            if current_state.is_speaking and hasattr(current_state, 'current_speech_metadata'):
                if current_state.current_speech_metadata.get('auto_generated'):
                    return True
                    
            # If we've been speaking for a while, consider interrupting
            if current_state.speech_start_time:
                speaking_duration = time.time() - current_state.speech_start_time
                if speaking_duration > 3.0:  # Been speaking for more than 3 seconds
                    return True
                    
        # For direct questions or commands, usually interrupt
        if "?" in text or any(cmd in text.lower() for cmd in ["stop", "wait", "hold on"]):
            return True
            
        return False
        
    async def _decision_loop(self):
        """Main decision-making loop"""
        self.logger.info("🧠 Decision loop started")
        
        while self.running:
            try:
                await self._make_decision()
                await asyncio.sleep(self.decision_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in decision loop: {e}")
                await asyncio.sleep(1.0)  # Back off on error
                
        self.logger.info("🧠 Decision loop stopped")
        
    async def _make_decision(self):
        """Make a decision about what action to take next"""
        
        self.decision_count += 1
        if self.decision_count % 50 == 0:  # Log every 5 seconds (50 * 0.1s)
            self.logger.info(f"🔄 Decision loop running - count: {self.decision_count}")
        
        # Get current system state
        current_state = self.state_monitor.get_state_snapshot()
        
        # Get pending actions
        pending_actions = self.action_queue.copy()
        
        if not pending_actions:
            # No pending actions - check if we should generate autonomous content
            await self._generate_autonomous_actions(current_state)
            return
            
        # Let decision engine select the best action
        selected_action = self.decision_engine.select_next_action(
            pending_actions, current_state
        )
        
        if selected_action:
            # Execute the selected action
            self.logger.info(f"🎯 Executing {selected_action.action_type.value} action")
            self.current_action = selected_action
            
            # Remove from queue
            if selected_action in self.action_queue:
                self.action_queue.remove(selected_action)
                
            # Execute the action
            success = await self._execute_action(selected_action)
            
            if success:
                self.logger.info(f"✅ Successfully executed {selected_action.action_type.value}")
            else:
                self.logger.error(f"❌ Failed to execute {selected_action.action_type.value}")
            
            self.current_action = None
            
    async def _execute_action(self, action: ActionRequest) -> bool:
        """Execute an action request"""
        
        try:
            if action.action_type == ActionType.SPEECH:
                return await self._execute_speech_action(action)
            elif action.action_type == ActionType.ENVIRONMENT:
                return await self._execute_environment_action(action)
            elif action.action_type == ActionType.INTERRUPT:
                return await self._execute_interrupt_action(action)
            else:
                self.logger.warning(f"Unknown action type: {action.action_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing action {action.action_type}: {e}")
            return False
            
    async def _execute_speech_action(self, action: ActionRequest) -> bool:
        """Execute speech generation with monitoring"""
        
        self.logger.info(f"🗣️ Executing speech action: {action.content[:50]}...")
        
        # Update state to indicate speech starting
        self.state_monitor.update_audio_state(
            is_speaking=True, 
            queue_size=1,
            estimated_end_time=time.time() + self._estimate_speech_duration(action.content)
        )
        
        try:
            # Call the real NeuroSync Player process_text endpoint
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Check if this is direct speech content from orchestrator
                is_direct_speech = action.metadata.get("auto_generated", False)
                
                payload = {
                    "text": action.content,
                    "autonomous_context": {
                        "source": action.metadata.get("autonomous_context", "orchestrator_speech"),
                        "is_directive": is_direct_speech,  # Mark as directive for direct speech
                        "auto_generated": action.metadata.get("auto_generated", False),
                        "direct_speech": is_direct_speech  # Explicit flag for direct speech
                    }
                }
                
                # If it's direct speech from orchestrator, add a flag
                if is_direct_speech:
                    payload["direct_speech"] = True
                
                # Call localhost since we're in the same container
                async with session.post("http://localhost:5001/process_text", json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"✅ Speech action completed successfully")
                        # Update state to indicate speech finished
                        self.state_monitor.update_audio_state(is_speaking=False, queue_size=0)
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"❌ Speech action failed: HTTP {response.status} - {error_text}")
                        self.state_monitor.update_audio_state(is_speaking=False, queue_size=0)
                        return False
            
        except Exception as e:
            self.logger.error(f"❌ Speech action failed: {e}")
            self.state_monitor.update_audio_state(is_speaking=False, queue_size=0)
            return False
            
    async def _execute_environment_action(self, action: ActionRequest) -> bool:
        """Execute environment change with monitoring"""
        
        self.logger.info(f"🎮 Executing environment action: {action.content}")
        
        # Update state to indicate environment changing
        self.state_monitor.update_environment_state(
            environment=action.content, 
            changing=True
        )
        
        try:
            # Call the real NeuroSync Player game_control endpoint
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "prompt": action.content,
                    "autonomous_context": {
                        "source": action.metadata.get("autonomous_context", "orchestrator_environment"),
                        "is_directive": False,
                        "auto_generated": action.metadata.get("auto_generated", False)
                    }
                }
                
                # Call localhost since we're in the same container
                async with session.post("http://localhost:5001/game_control", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        success = result.get("commands_successful", 0) > 0
                        
                        # Update state to indicate environment change complete
                        self.state_monitor.update_environment_state(
                            environment=action.content if success else "error", 
                            changing=False
                        )
                        
                        if success:
                            self.logger.info(f"✅ Environment action completed successfully ({result.get('commands_successful')} commands)")
                        else:
                            self.logger.warning(f"⚠️ Environment action completed but no commands succeeded")
                        
                        return success
                    else:
                        error_text = await response.text()
                        self.logger.error(f"❌ Environment action failed: HTTP {response.status} - {error_text}")
                        self.state_monitor.update_environment_state(
                            environment="error", 
                            changing=False
                        )
                        return False
            
        except Exception as e:
            self.logger.error(f"❌ Environment action failed: {e}")
            self.state_monitor.update_environment_state(
                environment="unknown", 
                changing=False
            )
            return False
            
    async def _execute_interrupt_action(self, action: ActionRequest) -> bool:
        """Execute interruption of current processes"""
        
        self.logger.info(f"⚡ Executing interruption action")
        
        # Get access to system objects if available
        if hasattr(self, 'system_objects') and self.system_objects:
            try:
                # 1. Stop pygame audio playback
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.stop()
                    self.logger.info("🔇 Stopped pygame audio playback")
                
                # 2. Flush the audio queue
                audio_queue = self.system_objects.get('audio_queue')
                if audio_queue:
                    while not audio_queue.empty():
                        try:
                            audio_queue.get_nowait()
                        except:
                            break
                    self.logger.info("🗑️ Flushed audio queue")
                
                # 3. Flush the chunk queue (TTS chunks)
                chunk_queue = self.system_objects.get('chunk_queue')
                if chunk_queue:
                    while not chunk_queue.empty():
                        try:
                            chunk_queue.get_nowait()
                        except:
                            break
                    self.logger.info("🗑️ Flushed TTS chunk queue")
                    
            except Exception as e:
                self.logger.error(f"❌ Error during interruption: {e}")
        
        # Update states to reflect interruption
        self.state_monitor.update_audio_state(is_speaking=False, queue_size=0)
        self.state_monitor.update_blendshape_state(active=False, queue_size=0)
        self.state_monitor.update_environment_state(
            environment="interrupted", 
            changing=False
        )
        
        return True
        
    async def _scb_monitoring_loop(self):
        """Monitor System 2 updates through SCB"""
        self.logger.info("🔗 SCB monitoring loop started")
        
        while self.running:
            try:
                if self.scb_client:
                    # Read latest updates from SCB
                    scb_data = await self._read_scb_updates()
                    if scb_data:
                        self.state_monitor.update_scb_context(scb_data)
                        
                await asyncio.sleep(self.scb_poll_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in SCB monitoring: {e}")
                await asyncio.sleep(5.0)  # Back off on error
                
        self.logger.info("🔗 SCB monitoring loop stopped")
        
    async def _read_scb_updates(self) -> Optional[Dict[str, Any]]:
        """Read updates from System 2 through SCB"""
        try:
            if not self.scb_client or not self.scb_client.should_check_scb():
                return None
                
            # Get context from SCB
            scb_context = self.scb_client.get_context_for_decision()
            
            # Convert to dictionary format for state monitor
            return {
                "urgent_response_needed": len(scb_context.urgent_flags) > 0,
                "emotional_state": scb_context.emotional_state,
                "environment_change_requested": len(scb_context.environmental_suggestions) > 0,
                "recent_directives": scb_context.recent_directives,
                "high_salience_events": scb_context.high_salience_events,
                "formatted_prompt": self.scb_client.format_context_for_prompt(scb_context)
            }
            
        except Exception as e:
            self.logger.error(f"Error reading SCB updates: {e}")
            return None
            
    def _on_state_change(self, event_type: str, state: SystemState):
        """Handle state change notifications"""
        self.logger.debug(f"🔄 State change: {event_type}")
        
        # React to specific state changes if needed
        if event_type == "audio_state_changed" and not state.is_speaking:
            self.logger.debug("🔇 Speech ended - system ready for next action")
            
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from input text for context"""
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3]
        return keywords[:10]
        
    def _classify_input(self, text: str) -> ActionType:
        """Classify input as speech or environment action"""
        
        env_keywords = [
            "scene", "environment", "background", "setting", "level",
            "hair", "color", "appearance", "look", "style",
            "lighting", "atmosphere", "mood", "theme"
        ]
        
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in env_keywords):
            return ActionType.ENVIRONMENT
        else:
            return ActionType.SPEECH
            
    def _determine_priority(self, text: str, autonomous_context: str = None) -> Priority:
        """Determine priority based on text content and context"""
        
        # Check for urgent indicators
        urgent_keywords = ["urgent", "emergency", "stop", "interrupt", "immediately"]
        if any(keyword in text.lower() for keyword in urgent_keywords):
            return Priority.URGENT
            
        # Check for high priority indicators
        high_keywords = ["important", "priority", "now", "quick", "fast"]
        if any(keyword in text.lower() for keyword in high_keywords):
            return Priority.HIGH
            
        # Check autonomous context
        if autonomous_context:
            # Handle both string and dict formats
            if isinstance(autonomous_context, dict):
                # Check source field or other indicators
                source = autonomous_context.get('source', '')
                if "high_priority" in source.lower():
                    return Priority.HIGH
            elif isinstance(autonomous_context, str):
                if "high_priority" in autonomous_context.lower():
                    return Priority.HIGH
            
        return Priority.MEDIUM
        
    def _estimate_speech_duration(self, text: str) -> float:
        """Estimate speech duration based on text length"""
        words = len(text) / 5
        duration = (words / 150) * 60
        return max(1.0, duration)
        
    async def _generate_autonomous_actions(self, current_state: SystemState):
        """Generate autonomous actions when system is idle"""
        
        # Check if system is truly idle (not speaking, not changing environment)
        if current_state.is_speaking or current_state.environment_changing:
            self.logger.debug(f"🔄 System busy: speaking={current_state.is_speaking}, env_changing={current_state.environment_changing}")
            return
            
        # Check idle time
        if not current_state.last_input_time:
            self.logger.warning("⚠️ No last_input_time set - cannot calculate idle time")
            # Set initial time if not set
            self.state_monitor.update_conversation_context([], active=True)
            return
            
        idle_time = time.time() - current_state.last_input_time
        self.logger.debug(f"⏰ Idle time: {idle_time:.1f}s since last input")
        
        # Only generate content if idle for more than 3 seconds
        if idle_time < 3.0:
            self.logger.debug(f"⏳ Too soon for autonomous content (idle: {idle_time:.1f}s < 3.0s)")
            return
        
        # Generate different types of content based on idle time
        if idle_time > 30.0:  # Very idle - generate engaging content
            self.logger.info("🎭 Generating engaging content after 30s idle")
            await self._generate_engaging_content(current_state)
            
        elif idle_time > 15.0:  # Moderately idle - continue conversation
            self.logger.info("💭 Continuing conversation after 15s idle")
            await self._generate_conversation_continuation(current_state)
            
        elif idle_time > 5.0:  # Slightly idle - ambient actions
            self.logger.info("🌟 Generating ambient action after 5s idle")
            await self._generate_ambient_action(current_state)
                
    async def _generate_engaging_content(self, current_state: SystemState):
        """Generate engaging content to re-capture attention"""
        
        # Think about what we've done and what makes sense next
        recent_topics = self.streaming_context.get("previous_topics", [])[-3:]  # Last 3 topics
        stream_purpose = self.streaming_context.get("stream_purpose", "")
        
        # Get SCB context if available
        scb_prompt_addition = ""
        if current_state.scb_priority_context and current_state.scb_priority_context.get("formatted_prompt"):
            scb_prompt_addition = current_state.scb_priority_context["formatted_prompt"]
            self.logger.info(f"🧠 Using SCB context: {scb_prompt_addition[:100]}...")
        
        # Choose content based on streaming context
        content_options = []
        
        # If SCB has urgent directives, prioritize those
        if current_state.scb_priority_context and current_state.scb_priority_context.get("urgent_response_needed"):
            directives = current_state.scb_priority_context.get("recent_directives", [])
            if directives:
                directive_text = directives[0].get("text", "")
                content_options.extend([
                    f"I just received an important update: {directive_text}",
                    f"System 2 has flagged something urgent: {directive_text}",
                    f"Let me address this priority: {directive_text}"
                ])
        
        # If we haven't talked much, introduce the stream
        if self.streaming_context["interaction_count"] < 2:
            content_options.extend([
                f"You know, I'm really excited about {stream_purpose}. There's so much we can explore together!",
                "I love being able to chat and show you different virtual environments. What would you like to see?",
                "Welcome to our interactive AI stream! I can chat, change scenes, and even adjust my appearance. What interests you most?"
            ])
        
        # Reference previous topics if we have them
        elif recent_topics:
            topic = random.choice(recent_topics) if recent_topics else "our conversation"
            content_options.extend([
                f"I've been thinking more about {topic}. There's actually another interesting aspect...",
                f"You know what's fascinating about {topic}? Let me show you something cool...",
                f"Going back to {topic} for a moment, I realized something interesting..."
            ])
        
        # Stream-aware content
        content_options.extend([
            "As an AI streamer, I love how we can instantly change environments. Should we try a different scene?",
            "I'm curious about your thoughts on AI and virtual avatars. What brings you to this stream?",
            "One thing I enjoy about streaming is the real-time interaction. What would you like to explore together?"
        ])
        
        # Pick and queue the content
        content = random.choice(content_options)
        
        # Add SCB context to metadata but NOT to the speech content itself
        metadata = {
            "auto_generated": True, 
            "type": "engaging", 
            "context": "stream_aware",
            "scb_context": scb_prompt_addition  # Store for decision-making, not speech
        }
        
        self.queue_action(
            ActionType.SPEECH,
            content,
            Priority.MEDIUM,
            metadata=metadata
        )
        
        # Sometimes follow up with an environment change
        if random.random() < 0.3:  # 30% chance
            await asyncio.sleep(0.5)  # Small delay
            self._suggest_environment_change()
            
    async def _generate_conversation_continuation(self, current_state: SystemState):
        """Generate natural conversation continuation based on context"""
        
        # Think about the flow of conversation
        keywords = current_state.context_keywords
        recent_activities = self.streaming_context.get("recent_activities", [])[-5:]
        
        # Build contextual responses
        if keywords:
            # Update our topic tracking
            self.streaming_context["previous_topics"].extend(keywords[:2])
            self.streaming_context["previous_topics"] = self.streaming_context["previous_topics"][-10:]  # Keep last 10
            
            # Generate continuation based on keywords and streaming context
            keyword = random.choice(keywords)
            continuations = [
                f"Speaking of {keyword}, have you ever wondered how AI perceives these concepts?",
                f"That reminds me, {keyword} is actually really relevant to what we're doing here in the stream...",
                f"I find {keyword} fascinating, especially in the context of virtual interactions like this."
            ]
            content = random.choice(continuations)
        else:
            # Stream-aware generic continuations
            continuations = [
                "So, what aspect of AI or virtual avatars interests you most?",
                "I'm here to demonstrate and chat. What would you like to explore?",
                "As an AI streamer, I'm always learning from our conversations. What's on your mind?"
            ]
            content = random.choice(continuations)
            
        self.queue_action(
            ActionType.SPEECH,
            content,
            Priority.MEDIUM,
            metadata={"auto_generated": True, "type": "continuation", "keywords": keywords}
        )
        
    async def _generate_ambient_action(self, current_state: SystemState):
        """Generate subtle ambient actions that feel natural for a streamer"""
        
        # Track what we've been doing
        recent_activities = self.streaming_context.get("recent_activities", [])
        
        # Mix of different ambient actions
        action_type = random.choice(["thoughtful", "interactive", "self_aware"])
        
        if action_type == "thoughtful":
            # Streaming-aware thoughtful comments
            thoughts = [
                "Hmm, I wonder what else we could explore today...",
                "This virtual space has so many possibilities, doesn't it?",
                "I love how technology lets us connect like this."
            ]
            content = random.choice(thoughts)
            
        elif action_type == "interactive":
            # Acknowledge the streaming context
            interactions = [
                "Feel free to ask me anything or suggest what to do next!",
                "I'm here to chat and demonstrate. What catches your interest?",
                "*glances at the virtual environment* This setup is pretty cool, right?"
            ]
            content = random.choice(interactions)
            
        elif action_type == "self_aware":
            # Self-aware AI streamer comments
            awareness = [
                "As an AI, I find these real-time interactions fascinating.",
                "It's interesting being a virtual streamer - I can be anything or anywhere!",
                "I appreciate you spending time here. Every conversation helps me learn."
            ]
            content = random.choice(awareness)
            
        self.queue_action(
            ActionType.SPEECH,
            content,
            Priority.LOW,
            metadata={"auto_generated": True, "type": f"ambient_{action_type}"}
        )
        
        # Update activity tracking
        self.streaming_context["recent_activities"].append(f"ambient_{action_type}")
        self.streaming_context["recent_activities"] = self.streaming_context["recent_activities"][-20:]
        
    def _suggest_environment_change(self):
        """Suggest an environment change that makes sense in the streaming context"""
        
        current_env = self.streaming_context.get("last_environment_theme", "default")
        
        # Check if SCB has environmental suggestions
        current_state = self.state_monitor.get_state_snapshot()
        scb_suggestions = []
        
        if current_state.scb_priority_context:
            scb_env_suggestions = current_state.scb_priority_context.get("environmental_suggestions", [])
            if scb_env_suggestions:
                self.logger.info(f"🧠 SCB environmental suggestions: {scb_env_suggestions}")
                # Convert SCB suggestions to our format
                for suggestion in scb_env_suggestions[:2]:  # Take top 2
                    scb_suggestions.append((
                        f"System 2 suggests: {suggestion}",
                        suggestion
                    ))
        
        # Default environment suggestions based on streaming flow
        default_suggestions = [
            ("How about we change the mood? Let me set up a cozy evening scene.", "Set scene to cozy fireplace with warm lighting"),
            ("Let's try something different. How about a futuristic setting?", "Change to cyberpunk tech lab with neon lights"),
            ("I think a change of scenery would be nice. Let me show you a peaceful garden.", "Switch to Japanese garden scene"),
            ("Want to see something cool? Let me change the atmosphere.", "Create mystical forest environment with particles")
        ]
        
        # Combine SCB suggestions with defaults, prioritizing SCB
        all_suggestions = scb_suggestions + default_suggestions
        
        speech, action = random.choice(all_suggestions[:4])  # Pick from top 4 options
        
        # Queue the speech announcement
        self.queue_action(
            ActionType.SPEECH,
            speech,
            Priority.MEDIUM,
            metadata={"auto_generated": True, "type": "environment_suggestion", "scb_influenced": len(scb_suggestions) > 0}
        )
        
        # Queue the actual environment change
        self.queue_action(
            ActionType.ENVIRONMENT,
            action,
            Priority.LOW,
            metadata={"auto_generated": True, "type": "environment_execution", "scb_influenced": len(scb_suggestions) > 0}
        )


def create_autonomous_orchestrator(neurosync_player=None) -> AutonomousOrchestrator:
    """Create and configure an AutonomousOrchestrator instance"""
    
    orchestrator = AutonomousOrchestrator(neurosync_player)
    
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    return orchestrator


if __name__ == "__main__":
    async def test_orchestrator():
        """Test the autonomous orchestrator"""
        
        print("🧪 Testing Autonomous Orchestrator")
        
        # Create orchestrator
        orchestrator = create_autonomous_orchestrator()
        
        # Start orchestrator
        await orchestrator.start()
        
        # Test speech action
        orchestrator.process_external_input(
            "Hello, this is a test speech action",
            autonomous_context="test_context"
        )
        
        # Test environment action
        orchestrator.process_external_input(
            "Change the scene to medieval with red hair",
            autonomous_context="environment_change"
        )
        
        # Test interruption
        await asyncio.sleep(1)
        orchestrator.queue_action(
            ActionType.SPEECH,
            "This is an urgent interruption!",
            Priority.URGENT,
            interrupt_current=True
        )
        
        # Let it run for a few seconds
        await asyncio.sleep(5)
        
        # Stop orchestrator
        await orchestrator.stop()
        
        print("✅ Test completed")
        
    # Run test
    asyncio.run(test_orchestrator()) 