# NeuroSync VTuber System Redesign Proposal

## Problem Analysis

The current autonomous orchestrator has fundamental design flaws causing non-stop speech:

### 1. Broken Idle Time Management
- `last_input_time` is never updated when autonomous content is generated
- System thinks it's been idle for 200+ seconds while actively speaking
- Generates new content every 100ms because it always appears idle

### 2. Overly Aggressive Content Generation
- Idle thresholds too low: 3s, 5s, 15s, 30s
- Decision loop runs every 100ms (10 times per second!)
- No awareness of whether previous speech is still playing
- No minimum gap between speeches

### 3. No Queue Management
- System queues multiple speeches without checking if any are playing
- No ability to clear or prioritize the queue
- No feedback from audio/blendshape systems about completion

### 4. Poor Logging
- Duplicate logs make debugging difficult
- Critical state information not logged
- No clear indication of what's actually happening

## User Requirements

1. **Responsive to prompts**: VTuber should receive and respond to user input
2. **Autonomous when idle**: Produce small speeches when left alone
3. **Easily interruptible**: New prompts should interrupt current speech quickly
4. **Short, connected speeches**: Not long monologues
5. **Clear system state**: Logs should clearly show what's happening

## Proposed Architecture

### 1. State-Aware Content Generation

```python
class ImprovedAutonomousOrchestrator:
    def __init__(self):
        # Reasonable idle thresholds
        self.MIN_IDLE_FOR_CONTENT = 10.0  # 10 seconds minimum
        self.IDLE_THRESHOLDS = {
            "ambient": 15.0,      # 15s for subtle comments
            "continuation": 30.0,  # 30s for conversation continuation
            "engaging": 60.0      # 60s for re-engagement
        }
        
        # Speech timing controls
        self.MIN_SPEECH_GAP = 3.0  # Minimum 3s between speeches
        self.last_speech_end_time = 0
        
        # Content length limits
        self.MAX_SPEECH_LENGTH = 100  # ~10-15 seconds of speech
        
    async def _should_generate_content(self, current_state):
        """Determine if we should generate autonomous content"""
        
        # Never generate if currently speaking
        if current_state.is_speaking or current_state.blendshape_active:
            return False
            
        # Check minimum gap since last speech
        time_since_last_speech = time.time() - self.last_speech_end_time
        if time_since_last_speech < self.MIN_SPEECH_GAP:
            return False
            
        # Check idle time
        if not current_state.last_input_time:
            return False
            
        idle_time = time.time() - current_state.last_input_time
        
        # Only generate if truly idle
        return idle_time >= self.MIN_IDLE_FOR_CONTENT
```

### 2. Proper State Updates

```python
async def _execute_speech_action(self, action: ActionRequest) -> bool:
    """Execute speech with proper state tracking"""
    
    # Mark speech start
    self.state_monitor.update_audio_state(
        is_speaking=True,
        speech_start_time=time.time()
    )
    
    try:
        # Send speech
        response = await self._send_speech_request(action.content, action.metadata)
        
        if response.success:
            # Critical: Update last input time for autonomous content
            if action.metadata.get("auto_generated"):
                self.state_monitor.update_last_input_time()
                
            # Track speech end time
            self.last_speech_end_time = time.time() + self._estimate_speech_duration(action.content)
            
            return True
            
    finally:
        # Always mark speech as done
        self.state_monitor.update_audio_state(is_speaking=False)
```

### 3. Blendshape-Based Completion Detection

```python
class BlendshapeAwareOrchestrator:
    def __init__(self):
        self.blendshape_monitor = BlendshapeMonitor()
        self.blendshape_monitor.on_complete = self._on_blendshape_complete
        
    def _on_blendshape_complete(self):
        """Called when blendshape streaming completes"""
        self.last_speech_end_time = time.time()
        self.state_monitor.update_audio_state(
            is_speaking=False,
            blendshape_active=False
        )
        
        # Now safe to consider new content
        self._check_pending_actions()
```

### 4. Interruptible Speech System

```python
class InterruptibleSpeechManager:
    def __init__(self):
        self.current_speech_id = None
        self.speech_can_be_interrupted = False
        
    async def send_speech(self, text: str, priority: Priority, interruptible: bool = True):
        """Send speech with interrupt capability"""
        
        speech_id = str(uuid.uuid4())
        self.current_speech_id = speech_id
        self.speech_can_be_interrupted = interruptible
        
        # Send with metadata for tracking
        await self._send_to_tts(text, {
            "speech_id": speech_id,
            "priority": priority.value,
            "can_interrupt": interruptible
        })
        
    async def interrupt_current_speech(self):
        """Interrupt current speech if possible"""
        
        if not self.speech_can_be_interrupted:
            return False
            
        # Send interrupt signal
        await self._send_interrupt_signal(self.current_speech_id)
        
        # Clear queues
        await self._clear_speech_queues()
        
        return True
```

### 5. Improved Content Generation

```python
def generate_idle_content(self, idle_duration: float, context: Dict) -> Optional[str]:
    """Generate appropriate content based on idle time"""
    
    # Short, contextual responses
    if idle_duration < 30:
        # Ambient thoughts - very short
        options = [
            "Hmm...",
            "This is nice.",
            "I wonder...",
            "*looks around thoughtfully*"
        ]
        
    elif idle_duration < 60:
        # Gentle prompts - still short
        options = [
            "What's on your mind?",
            "Feel free to ask me anything!",
            "Should we try something different?"
        ]
        
    else:
        # Re-engagement - slightly longer but still concise
        options = [
            "Hey, are you still there? Let me know if you want to chat!",
            "I'm here whenever you're ready to continue.",
            "Take your time - I'll be here when you want to talk."
        ]
        
    # Pick content that hasn't been used recently
    content = self._pick_non_duplicate(options)
    
    # Ensure it's short
    if len(content) > self.MAX_SPEECH_LENGTH:
        content = content[:self.MAX_SPEECH_LENGTH]
        
    return content
```

### 6. Clear Logging System

```python
class ClearLogger:
    def log_decision(self, action: str, reason: str, state: Dict):
        """Single, clear log entry for decisions"""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "reason": reason,
            "state": {
                "is_speaking": state.is_speaking,
                "blendshape_active": state.blendshape_active,
                "idle_time": state.idle_time,
                "queue_size": state.queue_size
            }
        }
        
        # Single line, easy to parse
        self.logger.info(f"[DECISION] {action} | {reason} | Speaking: {state.is_speaking} | Idle: {state.idle_time:.1f}s")
```

## Implementation Steps

### Phase 1: Fix Critical Bugs
1. Update `last_input_time` when autonomous content is generated
2. Increase idle thresholds to reasonable values
3. Check if system is actually speaking before generating content
4. Add minimum gap between speeches

### Phase 2: Add Blendshape Monitoring
1. Integrate blendshape completion callbacks
2. Use blendshape state as truth for speaking status
3. Only generate content when blendshapes are inactive

### Phase 3: Implement Interruption
1. Add speech ID tracking
2. Implement queue clearing mechanism
3. Add interrupt priority handling

### Phase 4: Improve Content & Logging
1. Shorten autonomous content
2. Add non-duplication checks
3. Implement clear, single-line logging
4. Remove duplicate log handlers

## Expected Behavior

With these changes:

1. **Normal Idle**: VTuber stays quiet for at least 10-15 seconds before speaking
2. **Short Speeches**: Autonomous content is brief (5-10 seconds max)
3. **Natural Gaps**: 3-5 second pauses between speeches
4. **Quick Interrupts**: User input immediately stops current speech
5. **Clear State**: Logs clearly show "Speaking", "Idle", "Interrupted", etc.

## Configuration

```env
# Autonomous Content Timing
AUTONOMOUS_MIN_IDLE_TIME=10.0
AUTONOMOUS_SPEECH_GAP=3.0
AUTONOMOUS_MAX_SPEECH_LENGTH=100

# Idle Thresholds
IDLE_AMBIENT_THRESHOLD=15.0
IDLE_CONTINUATION_THRESHOLD=30.0
IDLE_ENGAGING_THRESHOLD=60.0

# Decision Loop
DECISION_LOOP_INTERVAL=1.0  # Check every 1s, not 0.1s

# Interruption
AUTO_INTERRUPT_ENABLED=true
INTERRUPT_AUTONOMOUS_CONTENT=true
```

This design creates a much more natural, interruptible VTuber that responds to users while providing gentle autonomous content during true idle periods. 