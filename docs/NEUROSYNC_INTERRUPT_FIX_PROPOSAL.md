# NeuroSync Interrupt & State Tracking Fix Proposal

## Problem Analysis

### Current Issues

1. **State Tracking Disconnect**
   - Orchestrator shows `is_speaking: false` while audio is actually playing
   - State monitor updates don't reflect actual audio/TTS pipeline state
   - No feedback from audio/TTS workers to orchestrator

2. **Interrupt Not Working**
   - `_execute_interrupt_action` tries to access queues through `system_objects`
   - These references may not be properly initialized or connected
   - Pygame audio stopping doesn't actually affect the running TTS/audio workers

3. **Queue Processing Issues**
   - Old queued actions processed before new ones
   - No proper queue flushing mechanism
   - Direct speech takes time to override existing queue

4. **Continuous Speech Loop**
   - Autonomous content generation continues even when unwanted
   - No way to truly "stop" the system
   - State mismatches cause inappropriate autonomous actions

## Root Causes

### 1. Architecture Issue
```
Current Flow:
Orchestrator → Flask App → TTS Worker → Audio Worker → Pygame
     ↓                                                      ↓
State Monitor ←───────────────X─────────────────────── No Feedback
```

The orchestrator updates its state optimistically but never receives confirmation that:
- Audio actually started/stopped
- TTS processing completed
- Queues were actually flushed

### 2. Missing System Object References
```python
# In orchestrator_integration.py
self.orchestrator.system_objects = system_objects

# But in llm_to_face.py, system_objects contains:
system_objects = {
    'chunk_queue': chunk_queue,
    'audio_queue': audio_queue,
    'tts_worker': tts_worker,  # These workers not accessible
    'audio_worker': audio_worker
}
```

### 3. Worker Thread Isolation
- TTS and audio workers run in separate threads
- No mechanism to interrupt running TTS generation
- Audio playback in pygame doesn't notify orchestrator

## Proposed Solution

### Phase 1: Immediate Fixes

#### 1.1 Proper Queue Access in Interrupt
```python
# In autonomous_orchestrator.py
async def _execute_interrupt_action(self, action: ActionRequest) -> bool:
    """Execute interruption with proper queue access"""
    self.logger.info("⚡ Executing interruption action")
    
    success = False
    
    # 1. Send interrupt command to Flask app
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Call a new interrupt endpoint that has direct access
            async with session.post("http://localhost:5001/internal/interrupt", 
                                  json={"force": True}) as response:
                if response.status == 200:
                    success = True
                    self.logger.info("✅ Interrupt command sent to system")
    except Exception as e:
        self.logger.error(f"❌ Failed to send interrupt: {e}")
    
    # 2. Clear internal action queue
    self.action_queue.clear()
    self.logger.info("🗑️ Cleared internal action queue")
    
    # 3. Update state
    self.state_monitor.update_audio_state(is_speaking=False, queue_size=0)
    
    return success
```

#### 1.2 Add Internal Interrupt Endpoint
```python
# In llm_to_face.py
@app.route("/internal/interrupt", methods=['POST'])
def handle_internal_interrupt():
    """Internal endpoint for forceful interruption"""
    global system_objects
    
    try:
        # 1. Stop pygame audio
        if pygame.mixer.get_init():
            pygame.mixer.stop()
            app.logger.info("🔇 Stopped pygame audio")
        
        # 2. Flush queues properly
        chunk_queue = system_objects.get('chunk_queue')
        audio_queue = system_objects.get('audio_queue')
        
        if chunk_queue:
            # Clear the queue
            while not chunk_queue.empty():
                try:
                    chunk_queue.get_nowait()
                except:
                    break
            # Put end marker to stop TTS worker
            chunk_queue.put(None)
            app.logger.info("🗑️ Flushed chunk queue")
        
        if audio_queue:
            while not audio_queue.empty():
                try:
                    audio_queue.get_nowait()
                except:
                    break
            app.logger.info("🗑️ Flushed audio queue")
        
        # 3. Reset any ongoing processes
        stop_default_animation()
        
        return jsonify({"status": "interrupted"}), 200
        
    except Exception as e:
        app.logger.error(f"Interrupt error: {e}")
        return jsonify({"error": str(e)}), 500
```

### Phase 2: State Feedback System

#### 2.1 Audio State Callbacks
```python
# In audio worker (utils/audio/play_audio.py or similar)
def audio_playback_started(text, queue_size):
    """Notify orchestrator when audio starts"""
    try:
        requests.post("http://localhost:5001/internal/audio_state", 
                     json={
                         "state": "started",
                         "text": text[:100],
                         "queue_size": queue_size
                     })
    except:
        pass

def audio_playback_ended():
    """Notify orchestrator when audio ends"""
    try:
        requests.post("http://localhost:5001/internal/audio_state",
                     json={"state": "ended"})
    except:
        pass
```

#### 2.2 State Update Endpoint
```python
# In llm_to_face.py
@app.route("/internal/audio_state", methods=['POST'])
def handle_audio_state_update():
    """Receive audio state updates from workers"""
    if not orchestrator_wrapper:
        return jsonify({"status": "ignored"}), 200
    
    state = request.json.get('state')
    
    if state == 'started':
        orchestrator_wrapper.state_hooks.hook_audio_start(
            request.json.get('text', ''),
            estimated_duration=None
        )
    elif state == 'ended':
        orchestrator_wrapper.state_hooks.hook_audio_end()
    
    return jsonify({"status": "updated"}), 200
```

### Phase 3: Autonomous Control

#### 3.1 Pause/Resume Autonomous Generation
```python
# Add to AutonomousOrchestrator
class AutonomousOrchestrator:
    def __init__(self):
        # ... existing init ...
        self.autonomous_enabled = True  # New flag
        
    def pause_autonomous(self):
        """Pause autonomous content generation"""
        self.autonomous_enabled = False
        self.logger.info("⏸️ Autonomous generation paused")
        
    def resume_autonomous(self):
        """Resume autonomous content generation"""
        self.autonomous_enabled = True
        self.logger.info("▶️ Autonomous generation resumed")
        
    async def _generate_autonomous_actions(self, current_state: SystemState):
        """Generate autonomous actions when idle"""
        if not self.autonomous_enabled:
            return  # Skip if paused
        # ... rest of existing code ...
```

#### 3.2 Control Endpoint
```python
# In orchestrator routes
elif action == "pause_autonomous":
    orchestrator_wrapper.orchestrator.pause_autonomous()
    return jsonify({"status": "paused"}), 200
    
elif action == "resume_autonomous":
    orchestrator_wrapper.orchestrator.resume_autonomous()
    return jsonify({"status": "resumed"}), 200
```

## Implementation Priority

1. **Immediate** (Stop the looping):
   - Add internal interrupt endpoint
   - Fix queue flushing
   - Add pause autonomous feature

2. **Short-term** (Better control):
   - Implement audio state feedback
   - Fix state tracking accuracy
   - Add queue inspection tools

3. **Long-term** (Robust system):
   - Redesign worker communication
   - Add proper event system
   - Implement queue priorities

## Testing the Fix

```python
# Test script
def test_interrupt():
    # 1. Check if speaking
    status = requests.get(f"{BASE_URL}/orchestrator/status").json()
    print(f"Before: Speaking={status['current_action']['is_speaking']}")
    
    # 2. Send interrupt
    requests.post(f"{BASE_URL}/internal/interrupt", json={"force": True})
    
    # 3. Wait and check
    time.sleep(1)
    status = requests.get(f"{BASE_URL}/orchestrator/status").json()
    print(f"After: Speaking={status['current_action']['is_speaking']}")
    
    # 4. Send test message
    requests.post(f"{BASE_URL}/process_text", 
                  json={"text": "Interrupt test complete", "direct_speech": True})
```

## Benefits

1. **Immediate Control**: Actually stops audio/TTS instead of just updating state
2. **Accurate State**: State reflects reality through feedback system
3. **User Control**: Can pause autonomous generation when needed
4. **Queue Management**: Proper flushing prevents old content playback
5. **Debugging**: Clear understanding of system state at all times 

### 1. Blendshape-Based State Tracking
```python
# In send_to_unreal.py, add callbacks
def send_pre_encoded_data_to_unreal(encoded_facial_data, start_event, fps, socket_connection=None, callbacks=None):
    """
    callbacks = {
        'on_start': callable,
        'on_frame': callable(frame_index, total_frames),
        'on_complete': callable
    }
    """
    try:
        if callbacks and 'on_start' in callbacks:
            callbacks['on_start']()
            
        # ... existing streaming code ...
        
        for frame_index, frame_data in enumerate(encoded_facial_data):
            # ... existing frame sending ...
            
            if callbacks and 'on_frame' in callbacks:
                callbacks['on_frame'](frame_index, len(encoded_facial_data))
                
        if callbacks and 'on_complete' in callbacks:
            callbacks['on_complete']()
            
    except Exception as e:
        if callbacks and 'on_error' in callbacks:
            callbacks['on_error'](e)
```

### 2. Update StateMonitor to Track Real State
```python
class StateMonitor:
    def __init__(self):
        # ... existing init ...
        self.blendshape_stream_active = False
        self.blendshape_start_time = None
        self.blendshape_progress = 0
        
    def on_blendshape_start(self):
        """Called when blendshape streaming starts"""
        self.blendshape_stream_active = True
        self.blendshape_start_time = time.time()
        self.state.blendshape_active = True
        self._notify_callbacks("blendshape_stream_started")
        
    def on_blendshape_frame(self, frame_index, total_frames):
        """Track streaming progress"""
        self.blendshape_progress = frame_index / total_frames
        
    def on_blendshape_complete(self):
        """Called when blendshape streaming completes"""
        self.blendshape_stream_active = False
        self.state.blendshape_active = False
        self.state.is_speaking = False  # Speech is actually done
        self._notify_callbacks("blendshape_stream_completed")
```

### 3. Proper Interrupt Implementation
```python
# ... existing code ...

### 2. Internal Interrupt Endpoint
```python
@app.route('/internal/force_interrupt', methods=['POST'])
def force_interrupt():
    """Internal endpoint with full system access"""
    try:
        # 1. Stop autonomous generation
        orchestrator.pause_autonomous_generation()
        
        # 2. Clear all queues
        if hasattr(orchestrator, 'audio_queue'):
            while not orchestrator.audio_queue.empty():
                orchestrator.audio_queue.get_nowait()
                
        if hasattr(orchestrator, 'tts_queue'):
            while not orchestrator.tts_queue.empty():
                orchestrator.tts_queue.get_nowait()
        
        # 3. Interrupt any active blendshape streaming
        if orchestrator.state_monitor.blendshape_stream_active:
            # Signal to stop streaming
            orchestrator.interrupt_blendshape_stream = True
            
        # 4. Reset state
        orchestrator.state_monitor.state.is_speaking = False
        orchestrator.state_monitor.state.blendshape_active = False
        orchestrator.state_monitor.state.tts_queue_size = 0
        
        return jsonify({
            "status": "interrupted",
            "queues_cleared": True,
            "blendshape_interrupted": orchestrator.interrupt_blendshape_stream
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### 3. Audio State Feedback System
```python
class AudioWorker:
    def __init__(self, state_monitor):
        self.state_monitor = state_monitor
        
    def play_audio_with_feedback(self, audio_path, facial_data):
        """Play audio and update state based on actual playback"""
        try:
            # Create callbacks for blendshape tracking
            callbacks = {
                'on_start': lambda: self.state_monitor.on_blendshape_start(),
                'on_frame': lambda i, t: self.state_monitor.on_blendshape_frame(i, t),
                'on_complete': lambda: self.state_monitor.on_blendshape_complete(),
                'on_error': lambda e: self.state_monitor.on_blendshape_error(e)
            }
            
            # Run animation with callbacks
            run_audio_animation(
                audio_path, 
                facial_data, 
                py_face, 
                socket_connection, 
                default_animation_thread,
                callbacks=callbacks
            )
            
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            self.state_monitor.update_audio_state(is_playing=False)
```

### 4. Blendshape-Aware Interrupt
```python
def interrupt_with_blendshape_check():
    """Interrupt that waits for blendshape completion"""
    # 1. Set interrupt flag
    orchestrator.interrupt_requested = True
    
    # 2. If blendshapes are active, wait for completion or timeout
    if orchestrator.state_monitor.blendshape_stream_active:
        timeout = 5  # seconds
        start_time = time.time()
        
        while (orchestrator.state_monitor.blendshape_stream_active and 
               time.time() - start_time < timeout):
            time.sleep(0.1)
            
    # 3. Force clear if still active
    if orchestrator.state_monitor.blendshape_stream_active:
        orchestrator.force_interrupt_blendshapes = True
        
    # 4. Clear queues and reset
    clear_all_queues()
    reset_state()
```

## Implementation Priority

1. **Phase 1**: Add blendshape callbacks to track real streaming state
2. **Phase 2**: Implement proper interrupt with queue access
3. **Phase 3**: Add pause/resume for autonomous generation
4. **Phase 4**: Create monitoring dashboard for debugging

## Benefits

- **Accurate State**: Blendshape streaming provides ground truth for speaking state
- **Reliable Interrupts**: Can interrupt based on actual streaming progress
- **Better Synchronization**: Components stay in sync through feedback
- **Easier Debugging**: Clear visibility into what's actually happening

## Testing Strategy

1. Test blendshape callback integration
2. Verify interrupt during active streaming
3. Test state synchronization accuracy
4. Validate queue clearing effectiveness
5. Stress test with rapid interrupts 