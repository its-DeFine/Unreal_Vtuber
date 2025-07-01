"""
Autonomous Orchestrator V2 - Complete Redesign
Addresses all issues with non-stop talking and provides natural, interruptible speech
"""

import asyncio
import time
import logging
import os
import hashlib
import random
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

# Import Pipeline integration
try:
    from .core.pipeline import PipelineContext, Priority as PipelinePriority
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False
    logging.warning("Pipeline integration not available")

# Try to import SCB if available
try:
    from utils.scb.scb_client import OrchestratorSCBClient
    SCB_AVAILABLE = True
except ImportError:
    SCB_AVAILABLE = False


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
class SpeechRequest:
    """Represents a speech request with tracking"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    priority: Priority = Priority.MEDIUM
    timestamp: float = field(default_factory=time.time)
    duration_estimate: float = 0.0
    is_autonomous: bool = False
    interruptible: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemStateV2:
    """Improved system state tracking"""
    # Speech State
    is_speaking: bool = False
    current_speech_id: Optional[str] = None
    speech_start_time: Optional[float] = None
    speech_end_time: Optional[float] = None
    last_speech_completed: float = 0.0
    
    # Blendshape State (ground truth)
    blendshape_active: bool = False
    blendshape_start_time: Optional[float] = None
    blendshape_frame_count: int = 0
    blendshape_total_frames: int = 0
    
    # Idle Tracking
    last_user_input_time: float = field(default_factory=time.time)
    last_autonomous_speech_time: float = 0.0
    true_idle_duration: float = 0.0
    
    # Queue State
    speech_queue_size: int = 0
    pending_interrupts: int = 0
    
    # Content Tracking
    recent_content_hashes: List[str] = field(default_factory=list)
    content_history: List[Dict[str, Any]] = field(default_factory=list)


class StateLogger:
    """Clear, single-line logging for system state"""
    
    def __init__(self, logger):
        self.logger = logger
        
    def log_decision(self, action: str, reason: str, state: SystemStateV2):
        """Log decisions in a clear, parseable format"""
        idle_time = time.time() - state.last_user_input_time
        speech_gap = time.time() - state.last_speech_completed
        
        self.logger.info(
            f"[DECISION] {action} | {reason} | "
            f"Speaking: {state.is_speaking} | "
            f"Blendshapes: {state.blendshape_active} | "
            f"Idle: {idle_time:.1f}s | "
            f"Gap: {speech_gap:.1f}s"
        )
        
    def log_speech(self, speech_id: str, content: str, is_autonomous: bool):
        """Log speech events clearly"""
        content_preview = content[:50] + "..." if len(content) > 50 else content
        speech_type = "AUTO" if is_autonomous else "USER"
        self.logger.info(f"[SPEECH-{speech_type}] {speech_id[:8]} | {content_preview}")
        
    def log_state_change(self, field: str, old_value: Any, new_value: Any):
        """Log important state changes"""
        self.logger.info(f"[STATE] {field}: {old_value} → {new_value}")


class ContentGenerator:
    """Enhanced content generator with contextual awareness and conversation flow"""
    
    def __init__(self):
        self.recent_topics = []
        self.conversation_context = {
            'user_interests': [],
            'conversation_style': 'friendly',
            'engagement_level': 'moderate',
            'last_user_sentiment': 'neutral'
        }
        self.content_templates = {
            'ambient': [
                "Hmm...",
                "This is nice.",
                "*thinking quietly*",
                "Interesting...",
                "*glances around thoughtfully*"
            ],
            'continuation': [
                "What's on your mind?",
                "Feel free to ask me anything!",
                "I'm here if you want to chat.",
                "Is there something you'd like to explore?",
                "Any interesting thoughts today?",
                "I'm curious what you're thinking about."
            ],
            'engaging': [
                "Hey, are you still there?",
                "I'm here whenever you're ready!",
                "Take your time - I'll be here.",
                "Let me know if you'd like to continue.",
                "Hope you're having a good day!",
                "Feel free to jump back in anytime!"
            ],
            'contextual': {
                'greeting_time': [
                    "Good morning! Ready for a new day?",
                    "Good afternoon! How's your day going?",
                    "Good evening! Winding down from the day?"
                ],
                'work_context': [
                    "How's the project coming along?",
                    "Need help brainstorming anything?",
                    "Want to talk through any ideas?"
                ],
                'creative_context': [
                    "Any creative sparks today?",
                    "What's inspiring you lately?",
                    "Want to explore some new ideas?"
                ],
                'learning_context': [
                    "Discovered anything interesting recently?",
                    "Want to dive deeper into something?",
                    "Any questions on your mind?"
                ]
            },
            'follow_up': [
                "Building on what we discussed earlier...",
                "Speaking of {topic}, I was thinking...",
                "That reminds me of something...",
                "Following up on our conversation about {topic}..."
            ]
        }
        
    def generate_idle_content(self, idle_duration: float, state: SystemStateV2) -> Optional[str]:
        """Generate sophisticated contextual content based on idle time and conversation history"""
        
        # Determine content category
        content_category = self._determine_content_category(idle_duration)
        
        # Generate contextual content if we have conversation history
        if self.recent_topics and idle_duration > 30:
            contextual_content = self._generate_contextual_content(content_category)
            if contextual_content:
                return contextual_content
                
        # Generate time-aware content
        time_content = self._generate_time_aware_content(content_category)
        if time_content:
            return time_content
            
        # Fall back to basic content
        return self._generate_basic_content(content_category, state.recent_content_hashes)
        
    def _determine_content_category(self, idle_duration: float) -> str:
        """Determine the appropriate content category based on idle duration"""
        if idle_duration < 20:
            return 'ambient'
        elif idle_duration < 45:
            return 'continuation' 
        else:
            return 'engaging'
            
    def _generate_contextual_content(self, category: str) -> Optional[str]:
        """Generate content based on conversation context and user interests"""
        
        # Check if we can reference a recent topic
        if self.recent_topics and category in ['continuation', 'engaging']:
            recent_topic = self.recent_topics[-1] if self.recent_topics else None
            
            if recent_topic:
                follow_up_options = [
                    f"Still thinking about {recent_topic}?",
                    f"Want to continue our discussion about {recent_topic}?",
                    f"Any new thoughts on {recent_topic}?",
                    f"That {recent_topic} topic was interesting..."
                ]
                return random.choice(follow_up_options)
                
        # Generate content based on user interests
        if self.conversation_context['user_interests']:
            interest = random.choice(self.conversation_context['user_interests'])
            context_type = self._classify_interest_context(interest)
            
            if context_type in self.content_templates['contextual']:
                return random.choice(self.content_templates['contextual'][context_type])
                
        return None
        
    def _generate_time_aware_content(self, category: str) -> Optional[str]:
        """Generate content aware of time of day and context"""
        from datetime import datetime
        
        hour = datetime.now().hour
        
        # Time-of-day greetings for engaging content
        if category == 'engaging':
            if 5 <= hour < 12:
                return random.choice(self.content_templates['contextual']['greeting_time'][:1])
            elif 12 <= hour < 17:
                return random.choice(self.content_templates['contextual']['greeting_time'][1:2])
            elif 17 <= hour < 22:
                return random.choice(self.content_templates['contextual']['greeting_time'][2:])
                
        return None
        
    def _generate_basic_content(self, category: str, recent_hashes: List[str]) -> Optional[str]:
        """Generate basic content from templates"""
        if category not in self.content_templates:
            category = 'ambient'
            
        options = self.content_templates[category].copy()
        
        # Pick non-duplicate content
        content = self._pick_non_duplicate(options, recent_hashes)
        
        # Ensure it's short (max ~10 seconds of speech)
        if content and len(content) > 100:
            content = content[:100]
            
        return content
        
    def _classify_interest_context(self, interest: str) -> str:
        """Classify user interest into context categories"""
        work_keywords = ['project', 'work', 'coding', 'development', 'business', 'meeting']
        creative_keywords = ['art', 'music', 'writing', 'design', 'creative', 'story']
        learning_keywords = ['learn', 'study', 'research', 'explore', 'understand']
        
        interest_lower = interest.lower()
        
        if any(keyword in interest_lower for keyword in work_keywords):
            return 'work_context'
        elif any(keyword in interest_lower for keyword in creative_keywords):
            return 'creative_context'
        elif any(keyword in interest_lower for keyword in learning_keywords):
            return 'learning_context'
        else:
            return 'greeting_time'  # Default fallback
            
    def update_conversation_context(self, user_input: str, sentiment: str = 'neutral'):
        """Update conversation context based on user interaction"""
        
        # Extract potential topics/interests
        topics = self._extract_topics(user_input)
        
        # Update recent topics
        for topic in topics:
            if topic not in self.recent_topics:
                self.recent_topics.append(topic)
                
        # Keep only recent topics
        if len(self.recent_topics) > 5:
            self.recent_topics = self.recent_topics[-5:]
            
        # Update conversation context
        self.conversation_context['last_user_sentiment'] = sentiment
        
        # Update user interests
        for topic in topics:
            if topic not in self.conversation_context['user_interests']:
                self.conversation_context['user_interests'].append(topic)
                
        # Keep interests manageable
        if len(self.conversation_context['user_interests']) > 10:
            self.conversation_context['user_interests'] = self.conversation_context['user_interests'][-10:]
            
    def _extract_topics(self, text: str) -> List[str]:
        """Extract potential topics from user input"""
        # Simple keyword extraction (could be enhanced with NLP)
        topic_keywords = [
            'project', 'work', 'coding', 'programming', 'development',
            'art', 'music', 'writing', 'design', 'creative',
            'learning', 'studying', 'research', 'exploring',
            'game', 'movie', 'book', 'story', 'idea'
        ]
        
        text_lower = text.lower()
        found_topics = []
        
        for keyword in topic_keywords:
            if keyword in text_lower:
                found_topics.append(keyword)
                
        return found_topics

    def _pick_non_duplicate(self, options: List[str], recent_hashes: List[str]) -> Optional[str]:
        """Pick content that hasn't been used recently"""
        
        # Try each option
        for _ in range(len(options)):
            content = random.choice(options)
            content_hash = hashlib.md5(content.lower().encode()).hexdigest()[:8]
            
            if content_hash not in recent_hashes:
                return content
                
        # If all are duplicates, return None to skip this cycle
        return None


class BlendshapeMonitor:
    """Monitors blendshape streaming for accurate speech detection"""
    
    def __init__(self, state: SystemStateV2, logger: logging.Logger):
        self.state = state
        self.logger = logger
        self.callbacks = {
            'on_start': [],
            'on_frame': [],
            'on_complete': []
        }
        
    def register_callback(self, event: str, callback):
        """Register callbacks for blendshape events"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
            
    def on_blendshape_start(self):
        """Called when blendshape streaming starts"""
        old_state = self.state.blendshape_active
        self.state.blendshape_active = True
        self.state.blendshape_start_time = time.time()
        self.state.blendshape_frame_count = 0
        
        self.logger.info("[BLENDSHAPE] Streaming started")
        
        # Trigger callbacks
        for callback in self.callbacks['on_start']:
            callback()
            
    def on_blendshape_frame(self, frame_index: int, total_frames: int):
        """Track streaming progress"""
        self.state.blendshape_frame_count = frame_index
        self.state.blendshape_total_frames = total_frames
        
        # Log progress every 25%
        progress = (frame_index / total_frames) * 100 if total_frames > 0 else 0
        if progress > 0 and progress % 25 < 1:
            self.logger.debug(f"[BLENDSHAPE] Progress: {progress:.0f}%")
            
        # Trigger callbacks
        for callback in self.callbacks['on_frame']:
            callback(frame_index, total_frames)
            
    def on_blendshape_complete(self):
        """Called when blendshape streaming completes"""
        self.state.blendshape_active = False
        self.state.is_speaking = False
        self.state.last_speech_completed = time.time()
        
        duration = time.time() - (self.state.blendshape_start_time or time.time())
        self.logger.info(f"[BLENDSHAPE] Streaming completed ({duration:.1f}s)")
        
        # Reset frame tracking
        self.state.blendshape_frame_count = 0
        self.state.blendshape_total_frames = 0
        
        # Trigger callbacks
        for callback in self.callbacks['on_complete']:
            callback()


@dataclass  
class ActionRequest:
    """Enhanced action request for different types of autonomous actions"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: ActionType = ActionType.SPEECH
    priority: Priority = Priority.MEDIUM
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_estimate: float = 0.0
    interruptible: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Speech specific
    speech_content: Optional[str] = None
    
    # Environment specific  
    environment_action: Optional[str] = None
    environment_params: Dict[str, Any] = field(default_factory=dict)


class AutonomousOrchestratorV2:
    """
    Enhanced Autonomous Orchestrator with sophisticated decision-making and contextual awareness
    """
    
    def __init__(self):
        """Initialize the enhanced orchestrator"""
        
        # Core components
        self.logger = logging.getLogger(__name__)
        self.state = SystemStateV2()
        self.state_logger = StateLogger(self.logger)
        self.content_generator = ContentGenerator()
        self.blendshape_monitor = BlendshapeMonitor(self.state, self.logger)
        
        # Configuration
        self.enabled = os.getenv("AUTONOMOUS_ORCHESTRATION_ENABLED", "true").lower() == "true"
        
        # Enhanced timing configuration
        self.MIN_IDLE_FOR_CONTENT = float(os.getenv("AUTONOMOUS_MIN_IDLE_TIME", "8.0"))
        self.MIN_SPEECH_GAP = float(os.getenv("AUTONOMOUS_SPEECH_GAP", "2.5"))
        self.DECISION_INTERVAL = float(os.getenv("DECISION_LOOP_INTERVAL", "0.8"))
        
        # Content thresholds (more nuanced)
        self.IDLE_THRESHOLDS = {
            "ambient": float(os.getenv("IDLE_AMBIENT_THRESHOLD", "12.0")),
            "continuation": float(os.getenv("IDLE_CONTINUATION_THRESHOLD", "25.0")),
            "engaging": float(os.getenv("IDLE_ENGAGING_THRESHOLD", "45.0"))
        }
        
        # Speech configuration
        self.MAX_SPEECH_LENGTH = int(os.getenv("AUTONOMOUS_MAX_SPEECH_LENGTH", "100"))
        # Failsafe duration after which we assume speech has completed if no callback was received (in seconds)
        self.SPEECH_MAX_DURATION = float(os.getenv("SPEECH_MAX_DURATION", "20.0"))
        self.MAX_RECENT_HASHES = 20
        
        # Enhanced queue management
        self.action_queue: List[ActionRequest] = []
        self.speech_queue: List[SpeechRequest] = []  # Keep for compatibility
        self.current_action: Optional[ActionRequest] = None
        self.current_speech: Optional[SpeechRequest] = None
        
        # Running state
        self.running = False
        self.decision_task = None
        
        # SCB Integration
        self.scb_client = None
        if SCB_AVAILABLE:
            try:
                self.scb_client = OrchestratorSCBClient()
                self.logger.info("✅ SCB integration enabled")
            except Exception as e:
                self.logger.warning(f"⚠️ SCB integration failed: {e}")
                
        # Limit how many SCB memories/inputs to inject per prompt
        self.SCB_MAX_INPUTS = int(os.getenv("SCB_MAX_INPUTS", "3"))
        
        # External environment context store
        self.environment_context: Dict[str, Any] = {}
        
        # Register blendshape callbacks
        self.blendshape_monitor.register_callback('on_complete', self._on_speech_complete)
        
        self.logger.info(
            f"🤖 Enhanced Autonomous Orchestrator V2 initialized | "
            f"Min Idle: {self.MIN_IDLE_FOR_CONTENT}s | "
            f"Speech Gap: {self.MIN_SPEECH_GAP}s | "
            f"Decision Rate: {self.DECISION_INTERVAL}s"
        )
        
    async def start(self):
        """Start the orchestrator"""
        if self.running:
            return
            
        self.running = True
        self.logger.info("🚀 Starting Enhanced Autonomous Orchestrator V2")
        
        # Start decision loop
        self.decision_task = asyncio.create_task(self._decision_loop())
        
    async def stop(self):
        """Stop the orchestrator"""
        if not self.running:
            return
            
        self.running = False
        self.logger.info("🛑 Stopping Enhanced Autonomous Orchestrator V2")
        
        if self.decision_task:
            self.decision_task.cancel()
            try:
                await self.decision_task
            except asyncio.CancelledError:
                pass
                
    def process_user_input(self, text: str, metadata: Dict[str, Any] = None):
        """Enhanced user input processing with conversation context updates"""
        
        # Update conversation context for better autonomous responses
        self.content_generator.update_conversation_context(text)
        
        # Update last user input time
        self.state.last_user_input_time = time.time()
        self.state_logger.log_state_change("last_user_input_time", "old", "now")
        
        # Create speech request
        speech = SpeechRequest(
            content=text,
            priority=Priority.HIGH,
            is_autonomous=False,
            interruptible=False,  # User speech shouldn't be interrupted
            metadata=metadata or {}
        )
        
        # Log the request
        self.state_logger.log_speech(speech.id, text, is_autonomous=False)
        
        # Check if we should interrupt current speech
        if self._should_interrupt_current():
            asyncio.create_task(self._interrupt_current_speech())
            
        # Add to priority queue
        self._queue_speech(speech)
        
    async def _decision_loop(self):
        """Enhanced decision loop with sophisticated reasoning"""
        
        self.logger.info(f"🧠 Enhanced decision loop started (interval: {self.DECISION_INTERVAL}s)")
        
        decision_cycle = 0
        
        while self.running:
            try:
                decision_cycle += 1
                
                # Enhanced decision making with context awareness
                await self._make_enhanced_decision(decision_cycle)
                
                # Dynamic interval based on activity level
                sleep_duration = self._calculate_dynamic_interval()
                await asyncio.sleep(sleep_duration)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in decision loop: {e}")
                await asyncio.sleep(self.DECISION_INTERVAL)
                
    def _calculate_dynamic_interval(self) -> float:
        """Calculate dynamic decision interval based on activity"""
        base_interval = self.DECISION_INTERVAL
        
        # Speed up if user recently interacted
        recent_interaction = time.time() - self.state.last_user_input_time < 30
        if recent_interaction:
            return base_interval * 0.7  # 30% faster when user is active
            
        # Slow down if very idle
        if self.state.true_idle_duration > 120:
            return base_interval * 1.5  # 50% slower when very idle
            
        return base_interval
        
    async def _make_enhanced_decision(self, cycle: int):
        """Enhanced decision making with contextual awareness"""
        
        # Update state
        self._update_idle_state()
        self._update_speaking_state_from_activity()
        
        # Check if currently processing
        if self.state.blendshape_active or self.state.is_speaking:
            if cycle % 10 == 0:  # Log every 10 cycles to avoid spam
                self.state_logger.log_decision(
                    "WAIT", 
                    f"Currently processing (blendshape: {self.state.blendshape_active}, speaking: {self.state.is_speaking})", 
                    self.state
                )
            return
            
        # Process action queue first (higher priority)
        if await self._process_action_queue():
            return
            
        # Process speech queue (compatibility)
        if await self._process_speech_queue():
            return
            
        # Consider generating new autonomous content
        if self._should_generate_autonomous_content():
            await self._generate_contextual_autonomous_content()
            
    async def _process_action_queue(self) -> bool:
        """Process the enhanced action queue"""
        if not self.action_queue:
            return False
            
        # Sort by priority and timestamp
        self.action_queue.sort(key=lambda a: (-a.priority.value, a.timestamp))
        
        # Get next action
        action = self.action_queue.pop(0)
        self.current_action = action
        
        self.state_logger.log_decision(
            f"EXECUTE_{action.action_type.value.upper()}", 
            f"Processing {action.action_type.value} action: {action.content[:50]}...", 
            self.state
        )
        
        # Execute based on action type
        if action.action_type == ActionType.SPEECH:
            await self._execute_speech_action(action)
        elif action.action_type == ActionType.ENVIRONMENT:
            await self._execute_environment_action(action)
            
        return True
        
    async def _process_speech_queue(self) -> bool:
        """Process the legacy speech queue for compatibility"""
        if not self.speech_queue:
            return False
            
        # Get next speech
        speech = self.speech_queue.pop(0)
        self.current_speech = speech
        
        # Update state
        self.state.is_speaking = True
        self.state.current_speech_id = speech.id
        self.state.speech_start_time = time.time()
        
        self.state_logger.log_decision(
            "EXECUTE_SPEECH", 
            f"Processing speech: {speech.content[:50]}...", 
            self.state
        )
        
        # Send to TTS system
        await self._send_speech_to_tts(speech)
        return True
        
    async def _execute_speech_action(self, action: ActionRequest):
        """Execute a speech action"""
        speech_content = action.speech_content or action.content
        
        # Create speech request for compatibility
        speech = SpeechRequest(
            content=speech_content,
            priority=action.priority,
            is_autonomous=True,
            interruptible=action.interruptible,
            metadata=action.metadata
        )
        
        # Update state
        self.state.is_speaking = True
        self.state.current_speech_id = speech.id
        self.state.speech_start_time = time.time()
        
        # Send to TTS
        await self._send_speech_to_tts(speech)
        
    async def _execute_environment_action(self, action: ActionRequest):
        """Execute an environment action"""
        env_action = action.environment_action
        params = action.environment_params
        
        self.logger.info(f"🌍 Executing environment action: {env_action}")
        
        # Here you could add specific environment actions like:
        # - Changing avatar pose
        # - Adjusting lighting
        # - Playing ambient sounds
        # - Triggering game events
        
        # Mark action as completed
        self.current_action = None
        
    def _should_generate_autonomous_content(self) -> bool:
        """Enhanced autonomous content generation logic"""
        
        # Check minimum idle time
        if self.state.true_idle_duration < self.MIN_IDLE_FOR_CONTENT:
            return False
            
        # Check speech gap
        speech_gap = time.time() - self.state.last_speech_completed
        if speech_gap < self.MIN_SPEECH_GAP:
            return False
            
        # Check if we recently generated autonomous content
        auto_gap = time.time() - self.state.last_autonomous_speech_time
        min_auto_gap = self.MIN_SPEECH_GAP * 2  # Double gap for autonomous
        
        # Dynamic gap based on user engagement
        if len(self.content_generator.conversation_context['user_interests']) > 0:
            min_auto_gap *= 0.7  # Be more responsive if user has shown interests
            
        if auto_gap < min_auto_gap:
            return False
            
        # Check queue size - don't add more if queue is building up
        if len(self.action_queue) + len(self.speech_queue) > 2:
            return False
            
        return True
        
    async def _generate_contextual_autonomous_content(self):
        """Generate sophisticated autonomous content with enhanced context"""
        
        idle_duration = self.state.true_idle_duration
        
        # Determine content approach based on conversation history
        has_conversation_history = len(self.content_generator.recent_topics) > 0
        user_engagement_level = len(self.content_generator.conversation_context['user_interests'])
        
        # Choose content strategy
        if has_conversation_history and idle_duration > 20:
            content_strategy = "contextual_follow_up"
        elif user_engagement_level > 2 and idle_duration > 15:
            content_strategy = "interest_based"
        else:
            content_strategy = "time_based"
            
        # Generate content using enhanced generator
        content = self.content_generator.generate_idle_content(idle_duration, self.state)
        
        if not content:
            self.state_logger.log_decision(
                "SKIP", 
                f"No suitable content generated (strategy: {content_strategy})", 
                self.state
            )
            return
            
        # Determine priority based on idle duration and context
        if idle_duration >= self.IDLE_THRESHOLDS["engaging"]:
            priority = Priority.MEDIUM  # More engaging when very idle
        elif has_conversation_history and idle_duration >= 20:
            priority = Priority.LOW  # Contextual follow-ups
        else:
            priority = Priority.MINIMAL  # Ambient content
            
        # Create enhanced action request
        action = ActionRequest(
            action_type=ActionType.SPEECH,
            priority=priority,
            content=content,
            speech_content=content,
            interruptible=True,
            metadata={
                "content_strategy": content_strategy,
                "idle_duration": idle_duration,
                "is_autonomous": True,
                "user_engagement_level": user_engagement_level
            }
        )
        
        # Log decision
        self.state_logger.log_decision(
            "GENERATE_ENHANCED", 
            f"Autonomous content ({content_strategy}): {content[:30]}...", 
            self.state
        )
        
        # Update autonomous timing
        self.state.last_autonomous_speech_time = time.time()
        
        # Queue the action
        self._queue_action(action)
        
    def _queue_action(self, action: ActionRequest):
        """Add action to enhanced action queue with priority ordering"""
        
        # Add to queue
        self.action_queue.append(action)
        
        # Sort by priority (highest first) then by timestamp (oldest first)
        self.action_queue.sort(key=lambda a: (-a.priority.value, a.timestamp))
        
        # Track content hash for duplicates
        content_hash = hashlib.md5(action.content.lower().encode()).hexdigest()[:8]
        self.state.recent_content_hashes.append(content_hash)
        
        # Keep only recent hashes
        if len(self.state.recent_content_hashes) > self.MAX_RECENT_HASHES:
            self.state.recent_content_hashes = self.state.recent_content_hashes[-self.MAX_RECENT_HASHES:]
            
        self.logger.debug(f"🎯 Action queued: {action.action_type.value} - {action.content[:30]}...")
        
    def _queue_speech(self, speech: SpeechRequest):
        """Add speech to legacy queue with priority ordering (for compatibility)"""
        
        # Add to queue
        self.speech_queue.append(speech)
        
        # Sort by priority (highest first) then by timestamp (oldest first)
        self.speech_queue.sort(key=lambda s: (-s.priority.value, s.timestamp))
        
        # Update queue size
        self.state.speech_queue_size = len(self.speech_queue)
        
        # Track content hash
        content_hash = hashlib.md5(speech.content.lower().encode()).hexdigest()[:8]
        self.state.recent_content_hashes.append(content_hash)
        
        # Keep only recent hashes
        if len(self.state.recent_content_hashes) > self.MAX_RECENT_HASHES:
            self.state.recent_content_hashes = self.state.recent_content_hashes[-self.MAX_RECENT_HASHES:]
         
    def _update_idle_state(self):
        """Update the true idle duration"""
        current_time = time.time()
        self.state.true_idle_duration = current_time - self.state.last_user_input_time
        
    async def _send_speech_to_tts(self, speech: SpeechRequest):
        """Send speech to TTS system with enhanced context"""
        
        try:
            # Set speaking state when starting speech
            self.state.is_speaking = True
            self.state.speech_start_time = time.time()
            self.state.current_speech_id = speech.id
            self.current_speech = speech
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": speech.content,
                    "direct_speech": True,  # Always direct for V2
                    "autonomous_context": {
                        "source": "enhanced_orchestrator_v2",
                        "speech_id": speech.id,
                        "priority": speech.priority.value,
                        "is_autonomous": speech.is_autonomous,
                        "interruptible": speech.interruptible,
                        "user_idle_duration": self.state.true_idle_duration,
                        "conversation_topics": self.content_generator.recent_topics[-3:],  # Last 3 topics
                        **speech.metadata
                    }
                }
                
                async with session.post("http://localhost:5001/process_text", json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"[TTS] Enhanced speech sent successfully: {speech.id[:8]}")
                    else:
                        self.logger.error(f"[TTS] Failed to send speech: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"[TTS] Error sending speech: {e}")
            # Reset state on error
            self.state.is_speaking = False
            self.state.current_speech_id = None
            self.current_speech = None
         
    def _should_interrupt_current(self) -> bool:
        """Determine if current speech should be interrupted"""
        
        if not self.current_speech:
            return False
            
        # Don't interrupt user speech
        if not self.current_speech.is_autonomous:
            return False
            
        # Don't interrupt if not interruptible
        if not self.current_speech.interruptible:
            return False
            
        # Check if there's a higher priority item waiting
        if self.speech_queue:
            highest_waiting = max(self.speech_queue, key=lambda s: s.priority.value)
            if highest_waiting.priority.value > self.current_speech.priority.value:
                return True
                
        # Check action queue for higher priority items
        if self.action_queue:
            highest_action = max(self.action_queue, key=lambda a: a.priority.value)
            if highest_action.priority.value >= Priority.HIGH.value:
                return True
                
        return False
        
    async def _interrupt_current_speech(self):
        """Interrupt current speech and reset state"""
        
        if self.current_speech:
            self.logger.info(f"🛑 Interrupting speech: {self.current_speech.id[:8]}")
            
            # TODO: Send interruption signal to TTS/audio system
            # This would depend on your TTS system's interrupt capabilities
            
            # Reset state
            self.state.is_speaking = False
            self.state.blendshape_active = False
            self.current_speech = None
            self.current_action = None
            
            # Update timing
            self.state.last_speech_completed = time.time()
            
    def _on_speech_complete(self):
        """Called when speech/blendshape streaming completes"""
        self.logger.info(f"[SPEECH-COMPLETE] Speech completed, resetting state")
        self.state.is_speaking = False
        self.state.blendshape_active = False
        self.state.last_speech_completed = time.time()
        
        # Clear current speech
        if self.current_speech:
            self.logger.info(f"[SPEECH-COMPLETE] Cleared current speech: {self.current_speech.id}")
            self.current_speech = None
            
        # Trigger callbacks
        for callback in self.blendshape_monitor.callbacks.get('on_complete', []):
            callback()
            
    def notify_speech_complete(self, speech_id: str = None):
        """Public method to notify orchestrator that speech has completed"""
        if speech_id:
            self.logger.info(f"[NOTIFY] Speech completion notification for: {speech_id}")
        else:
            self.logger.info(f"[NOTIFY] Speech completion notification (no ID)")
        self._on_speech_complete()
        
    def _update_speaking_state_from_activity(self):
        """Update speaking state based on recent activity detection"""
        current_time = time.time()
        
        # Failsafe: if speaking for too long without completion callback -> reset
        if (self.state.is_speaking and 
            self.state.speech_start_time and 
            current_time - self.state.speech_start_time > self.SPEECH_MAX_DURATION):
            
            self.logger.warning(
                f"[AUTO-RESET] Speech exceeded max duration ({self.SPEECH_MAX_DURATION}s). Forcing completion reset.")
            self._on_speech_complete()
            return
        
        # If we haven't had any speech activity for a while (last_speech_completed in past) assume reset already happened
        if (self.state.is_speaking and 
            self.state.last_speech_completed > 0 and
            current_time - self.state.last_speech_completed > self.SPEECH_MAX_DURATION):
            self.logger.info(f"[AUTO-RESET] Resetting speaking state due to timeout")
            self.state.is_speaking = False
            self.state.blendshape_active = False
        
    # Public methods for external control
    def queue_speech_external(self, content: str, priority: Priority = Priority.MEDIUM, 
                            interruptible: bool = True, metadata: Dict[str, Any] = None):
        """Queue speech from external source (API, game control, etc.)"""
        
        speech = SpeechRequest(
            content=content,
            priority=priority,
            is_autonomous=False,  # External control
            interruptible=interruptible,
            metadata=metadata or {}
        )
        
        self._queue_speech(speech)
        self.logger.info(f"📥 External speech queued: {content[:30]}...")
        
    def queue_action_external(self, action_type: ActionType, content: str, 
                            priority: Priority = Priority.MEDIUM, **kwargs):
        """Queue action from external source"""
        
        action = ActionRequest(
            action_type=action_type,
            priority=priority,
            content=content,
            interruptible=kwargs.get('interruptible', True),
            metadata=kwargs.get('metadata', {}),
            speech_content=kwargs.get('speech_content'),
            environment_action=kwargs.get('environment_action'),
            environment_params=kwargs.get('environment_params', {})
        )
        
        self._queue_action(action)
        self.logger.info(f"📥 External {action_type.value} action queued: {content[:30]}...")
        
    def get_enhanced_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status"""
        
        return {
            "running": self.running,
            "state": {
                "is_speaking": self.state.is_speaking,
                "blendshape_active": self.state.blendshape_active,
                "true_idle_duration": self.state.true_idle_duration,
                "speech_queue_size": len(self.speech_queue),
                "action_queue_size": len(self.action_queue),
                "last_speech_completed": self.state.last_speech_completed,
                "last_autonomous_speech_time": self.state.last_autonomous_speech_time
            },
            "conversation_context": {
                "recent_topics": self.content_generator.recent_topics,
                "user_interests": self.content_generator.conversation_context['user_interests'],
                "engagement_level": self.content_generator.conversation_context['engagement_level']
            },
            "configuration": {
                "min_idle_for_content": self.MIN_IDLE_FOR_CONTENT,
                "min_speech_gap": self.MIN_SPEECH_GAP,
                "decision_interval": self.DECISION_INTERVAL,
                "idle_thresholds": self.IDLE_THRESHOLDS
            },
            "current_processing": {
                "current_speech_id": self.state.current_speech_id,
                "current_action": self.current_action.id if self.current_action else None
            }
        }

    async def process_external_event(self, event_type: str, payload: Dict[str, Any]):
        """Allow external systems to influence orchestrator context (e.g., new viewers)"""
        self.logger.info(f"[EXT-EVENT] Received event '{event_type}' payload={payload}")
        # Store in environment context
        self.environment_context[event_type] = payload
        
        # Simple handling for 'new_viewers'
        if event_type == 'new_viewers':
            names = payload.get('names', [])
            if names:
                # Construct a synthetic user input to update conversation context
                synthetic_input = f"We have new viewers joining: {', '.join(names)}."
                self.content_generator.update_conversation_context(synthetic_input)
                # Also log state change
                self.state_logger.log_state_change('new_viewers', None, names)
        
        # Push to SCB so it appears at the top (most recent)
        try:
            from utils.scb.scb_store import scb_store
            if event_type == 'change_subject':
                text = payload.get('topic', '')
                if text:
                    scb_store.append_directive(f"Change subject to: {text}", actor="external", ttl=120)
            else:
                # Generic event logged as high salience event
                txt = payload.get('text') or str(payload)
                scb_store.append_chat(txt, actor="external", salience=0.8)
        except Exception as e:
            self.logger.warning(f"Failed to push event to SCB: {e}")

        # --- Immediate reaction speech generation ---
        try:
            if event_type == 'change_subject':
                topic = payload.get('topic', '')
                if topic:
                    speech_text = (
                        f"Switching gears! Let's talk about {topic}. "
                        f"It's always exciting to explore new topics together."
                    )
                    # Queue with URGENT priority so it speaks next
                    self.queue_speech_external(
                        speech_text,
                        priority=Priority.URGENT,
                        interruptible=False,
                        metadata={"source": "external_event", "event_type": event_type}
                    )
            elif event_type == 'tweet_mention':
                txt = payload.get('text') or ''
                author = payload.get('author', '')
                speech_text = (
                    f"Hey everyone! We just got a mention on Twitter from {author}: {txt}. "
                    f"What do you all think about that?"
                )
                self.queue_speech_external(
                    speech_text,
                    priority=Priority.HIGH,
                    interruptible=True,
                    metadata={"source": "external_event", "event_type": event_type}
                )
        except Exception as e:
            self.logger.warning(f"Failed to queue speech for event {event_type}: {e}")

    def update_config(self, **kwargs):
        """Update orchestrator runtime configuration dynamically"""
        if 'scb_max_inputs' in kwargs:
            value = int(kwargs['scb_max_inputs'])
            self.logger.info(f"[CONFIG] Updating SCB_MAX_INPUTS: {self.SCB_MAX_INPUTS} -> {value}")
            self.SCB_MAX_INPUTS = value


# Factory function
def create_autonomous_orchestrator_v2() -> AutonomousOrchestratorV2:
    """
    Factory function to create an enhanced Autonomous Orchestrator V2 instance
    
    Returns:
        AutonomousOrchestratorV2: A fully configured enhanced orchestrator instance
    """
    return AutonomousOrchestratorV2() 