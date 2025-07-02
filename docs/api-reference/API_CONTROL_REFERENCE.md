# VTuber & Orchestrator API Control Reference

This document provides complete reference for controlling the autonomous VTuber system, including direct speech control, environment changes, and orchestrator management.

## 🎯 **Direct VTuber Control**

### 1. **Orchestrator Speech Control** (Recommended)

Control what the VTuber says through the intelligent orchestrator system.

**Endpoint:** `POST http://localhost:5001/orchestrator/control`

#### **Make VTuber Say Specific Text**
```bash
curl -X POST http://localhost:5001/orchestrator/control \
  -H "Content-Type: application/json" \
  -d '{
    "action": "queue_speech",
    "text": "Hello! I can speak exactly what you tell me to say.",
    "priority": "high"
  }'
```

**Priority Levels:**
- `"urgent"` - Interrupts current speech immediately
- `"high"` - Important, interrupts medium/low priority
- `"medium"` - Normal conversation flow
- `"low"` - Background/ambient

#### **Interrupt Current Speech**
```bash
curl -X POST http://localhost:5001/orchestrator/control \
  -H "Content-Type: application/json" \
  -d '{"action": "interrupt"}'
```

#### **Check Orchestrator Status**
```bash
curl -s http://localhost:5001/orchestrator/status | jq .
```

### 2. **Direct Text Processing** (Bypasses Orchestrator)

Send text directly to the LLM for processing and speech generation.

**Endpoint:** `POST http://localhost:5001/process_text`

#### **Process Text with LLM Response**
```bash
curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Tell me about artificial intelligence",
    "autonomous_context": "user_input"
  }'
```

#### **Direct Speech (No LLM Processing)**
```bash
curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I will speak this exact text without LLM modification",
    "direct_speech": true
  }'
```

## 🎮 **Environment Control**

### 3. **Game Environment Changes**

**Endpoint:** `POST http://localhost:5001/game_control`

#### **Change Environment with Natural Language**
```bash
curl -X POST http://localhost:5001/game_control \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Change to medieval castle with red hair and cozy lighting"
  }'
```

#### **Available Environment Commands**

**Levels/Scenes:**
- `LVL.Home` - Cloud environment
- `LVL.Medieval` - Castle/fantasy scene  
- `LVL.DJ` - Music/party environment
- `LVL.Lofi` - Cozy ambient setting

**Character Appearance:**
- `PRS.Fem` - Feminine build
- `PRS.Masc` - Masculine build
- `OF.Maid Dress`, `OF.Pop Star`, `OF.Kimono` - Outfits
- `HCR.0.9`, `HCG.0.1`, `HCB.0.1` - Hair color (RGB values 0.0-1.0)

**Environment Settings:**
- `SNH.0.1` - Night time (sun height)
- `STRB.0.9` - Bright stars
- `CLDS.0.3` - Cloud speed/opacity

#### **Direct TCP Commands**
```bash
curl -X POST http://localhost:5001/game_control \
  -H "Content-Type: application/json" \
  -d '{
    "commands": ["HCR.0.9", "HCG.0.1", "HCB.0.1", "LVL.Medieval"]
  }'
```

## 🤖 **Orchestrator Management**

### 4. **Orchestrator Configuration**

**Check Current Settings:**
```bash
curl -s http://localhost:5001/orchestrator/status | jq '.config'
```

**Environment Variables for Control:**
```bash
# Enable/disable orchestrator
AUTONOMOUS_ORCHESTRATION_ENABLED=true

# Enable interruptions
AUTO_INTERRUPT_ENABLED=true

# Decision loop timing
DECISION_LOOP_INTERVAL=0.1

# Idle timeout before autonomous speech
ORCHESTRATOR_IDLE_TIMEOUT=2.0

# Priority threshold for interruptions  
INTERRUPT_THRESHOLD=4

# Disable environment changes (recommended)
AUTONOMOUS_ENVIRONMENT_ENABLED=false
```

### 5. **System Status & Monitoring**

#### **Container Health Check**
```bash
docker logs neurosync_s1 --tail 50
```

#### **Service Status**
```bash
curl -s http://localhost:5001/health | jq .
```

#### **Real-time Orchestrator Logs**
```bash
docker logs neurosync_s1 -f | grep "autonomous_orchestrator"
```

## 🎭 **Common Usage Scenarios**

### **Scenario 1: Make VTuber Say Something Specific**
```bash
# High priority - will interrupt current speech
curl -X POST http://localhost:5001/orchestrator/control \
  -H "Content-Type: application/json" \
  -d '{
    "action": "queue_speech",
    "text": "Welcome to our AI demonstration! I can respond to your commands and change my environment in real-time.",
    "priority": "high"
  }'
```

### **Scenario 2: Quick Speech Interruption + New Content**
```bash
# First interrupt
curl -X POST http://localhost:5001/orchestrator/control \
  -H "Content-Type: application/json" \
  -d '{"action": "interrupt"}'

# Then queue new speech
sleep 0.5
curl -X POST http://localhost:5001/orchestrator/control \
  -H "Content-Type: application/json" \
  -d '{
    "action": "queue_speech", 
    "text": "Sorry for the interruption! Here is the new information you requested.",
    "priority": "urgent"
  }'
```

### **Scenario 3: Change Appearance + Announce Change**
```bash
# Change to medieval scene with red hair
curl -X POST http://localhost:5001/game_control \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "medieval castle scene with red hair and feminine character"
  }'

# Announce the change
sleep 1
curl -X POST http://localhost:5001/orchestrator/control \
  -H "Content-Type: application/json" \
  -d '{
    "action": "queue_speech",
    "text": "Welcome to my medieval castle! I have changed my appearance to match the royal atmosphere.",
    "priority": "medium"
  }'
```

### **Scenario 4: Interactive Q&A Session**
```bash
# Process user question through LLM
curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What are the latest developments in artificial intelligence?",
    "autonomous_context": "interactive_qa"
  }'
```

### **Scenario 5: Direct Control (No AI Processing)**
```bash
# Speak exact text without LLM modification
curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Thank you for joining our demonstration. I am now speaking exactly what was programmed, without any AI interpretation.",
    "direct_speech": true
  }'
```

## 🔧 **Troubleshooting**

### **VTuber Not Speaking**
1. Check orchestrator status: `curl -s http://localhost:5001/orchestrator/status`
2. Verify container logs: `docker logs neurosync_s1 --tail 20`
3. Test direct speech: Use `/process_text` with `"direct_speech": true`

### **Content Repetition**
- The system includes anti-repetition mechanisms
- If still repeating, restart container: `docker-compose restart neurosync_s1`

### **Environment Changes Breaking**
- Environment changes are disabled by default (they can crash the game)
- Use only speech control unless environment is stable

### **Speed Interruption Not Working**
- Ensure `AUTO_INTERRUPT_ENABLED=true` in environment
- Check that priority is high enough (`"high"` or `"urgent"`)
- Verify system objects are properly initialized

## 📝 **Response Formats**

All endpoints return JSON responses:

**Success Response:**
```json
{
  "status": "queued|processing|interrupted",
  "action": "speech|environment|interrupt", 
  "message": "Description of action taken"
}
```

**Error Response:**
```json
{
  "error": "Error description",
  "status": "failed"
}
```

---

## 🚀 **Quick Start Commands**

```bash
# 1. Make her speak immediately
curl -X POST http://localhost:5001/orchestrator/control -H "Content-Type: application/json" -d '{"action": "queue_speech", "text": "Hello! I am your AI assistant ready to help.", "priority": "high"}'

# 2. Check system status  
curl -s http://localhost:5001/orchestrator/status | jq .

# 3. Interrupt and speak new content
curl -X POST http://localhost:5001/orchestrator/control -H "Content-Type: application/json" -d '{"action": "interrupt"}' && sleep 0.5 && curl -X POST http://localhost:5001/orchestrator/control -H "Content-Type: application/json" -d '{"action": "queue_speech", "text": "I have been interrupted and am now speaking new content!", "priority": "urgent"}'

# 4. Process interactive question
curl -X POST http://localhost:5001/process_text -H "Content-Type: application/json" -d '{"text": "What is artificial intelligence and how does it work?"}'
```

This system provides complete control over the VTuber's speech, behavior, and environment while maintaining intelligent autonomous operation when not directly controlled. 