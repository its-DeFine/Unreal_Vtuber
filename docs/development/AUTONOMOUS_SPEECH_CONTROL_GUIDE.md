# Autonomous Speech Control Guide

## Method 1: Manual API Control

### Queue Speech via HTTP
```bash
# Send speech to the VTuber
curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello! This is a test message.",
    "autonomous_context": "manual_trigger"
  }'
```

### Control Orchestrator via API
```bash
# Pause autonomous generation
curl -X POST http://localhost:5001/orchestrator/control \
  -H "Content-Type: application/json" \
  -d '{"action": "pause"}'

# Resume autonomous generation  
curl -X POST http://localhost:5001/orchestrator/control \
  -H "Content-Type: application/json" \
  -d '{"action": "resume"}'

# Interrupt current speech
curl -X POST http://localhost:5001/orchestrator/control \
  -H "Content-Type: application/json" \
  -d '{"action": "interrupt"}'

# Queue priority speech
curl -X POST http://localhost:5001/orchestrator/control \
  -H "Content-Type: application/json" \
  -d '{
    "action": "queue_speech",
    "text": "This is important!",
    "priority": "high"
  }'
```

### Check Status
```bash
# Get orchestrator status
curl http://localhost:5001/orchestrator/status
```

## Method 2: Continuous Autonomous Mode

### Environment Configuration
```yaml
# In docker-compose.neurobridge.yml
environment:
  - AUTONOMOUS_ORCHESTRATION_ENABLED=true
  - AUTONOMOUS_MIN_IDLE_TIME=5.0        # Start speaking after 5s idle
  - AUTONOMOUS_SPEECH_GAP=2.0           # 2s gap between speeches
  - IDLE_AMBIENT_THRESHOLD=5.0          # Ambient content at 5s
  - IDLE_CONTINUATION_THRESHOLD=10.0    # Prompts at 10s
  - IDLE_ENGAGING_THRESHOLD=20.0        # Re-engagement at 20s
```

### Content Types Generated
- **Ambient (5s idle)**: "Hmm...", "This is nice.", "Interesting..."
- **Continuation (10s idle)**: "What's on your mind?", "Feel free to ask!"
- **Engaging (20s idle)**: "Are you still there?", "I'm here when ready!"

## Method 3: Python Script for Continuous Prompting

```python
import requests
import time
import random

def continuous_speech_loop():
    """Send continuous speech to VTuber"""
    
    prompts = [
        "Let me tell you something interesting...",
        "I've been thinking about this topic...",
        "Here's what I find fascinating...",
        "You know what's really cool?",
        "I just realized something...",
        "This reminds me of...",
        "Have you ever wondered about...",
        "Let me share my thoughts on..."
    ]
    
    base_url = "http://localhost:5001"
    
    while True:
        try:
            # Pick random prompt
            prompt = random.choice(prompts)
            
            # Send to VTuber
            response = requests.post(f"{base_url}/process_text", json={
                "text": prompt,
                "autonomous_context": "continuous_loop"
            })
            
            if response.status_code == 200:
                print(f"✅ Sent: {prompt}")
            else:
                print(f"❌ Error: {response.status_code}")
                
            # Wait before next prompt (adjust timing)
            time.sleep(random.uniform(8, 15))  # 8-15 seconds between prompts
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    continuous_speech_loop()
```

## Recommendations

### For Natural Conversation:
Use **Method 2 (Autonomous Mode)** - it handles timing naturally and avoids repetition.

### For Scripted Content:
Use **Method 1 (Manual API)** - full control over what gets said and when.

### For Testing:
Use **Method 3 (Python Script)** - easy to customize and experiment with different prompts.

## Troubleshooting

### If No Speech is Generated:
1. Check orchestrator status: `curl http://localhost:5001/orchestrator/status`
2. Verify environment variables are set correctly
3. Check container logs: `docker logs neurosync_s1`
4. Ensure TTS/LLM providers are configured properly

### If Speech is Too Frequent:
Increase the threshold values:
- `AUTONOMOUS_MIN_IDLE_TIME=10.0`
- `AUTONOMOUS_SPEECH_GAP=5.0`
- `IDLE_AMBIENT_THRESHOLD=15.0`

### If Speech is Too Infrequent:
Decrease the threshold values (as shown in current config):
- `AUTONOMOUS_MIN_IDLE_TIME=3.0`
- `AUTONOMOUS_SPEECH_GAP=1.0`
- `IDLE_AMBIENT_THRESHOLD=3.0` 