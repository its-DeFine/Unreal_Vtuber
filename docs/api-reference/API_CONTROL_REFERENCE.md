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

## 🎛️ **Admin Command Processing System**

### 6. **Stimuli-Based Admin Commands**

The system includes a sophisticated admin command processing architecture that differentiates between admin operations and speech content.

**Endpoint:** `POST http://localhost:8200/api/stimuli/receive`

#### **Silent Admin Commands (Default)**
```bash
# List characters silently (S2 logging only)
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "admin_list_001",
    "content": "admin: list characters",
    "source": "admin_console",
    "priority": "high"
  }'

# Create character silently
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "admin_create_001",
    "content": "admin: create character Dr. Smith teacher",
    "source": "admin_console",
    "priority": "high"
  }'

# Switch character silently  
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "admin_switch_001",
    "content": "admin: switch character dr._smith_teacher_template",
    "source": "admin_console",
    "priority": "medium"
  }'
```

#### **Announced Admin Commands (S1 + S2)**
```bash
# List characters with speech announcement
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "admin_announce_001",
    "content": "announce: admin: list characters",
    "source": "admin_console",
    "priority": "high"
  }'

# Create character with speech announcement
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "admin_announce_002",
    "content": "announce: admin: create character Dr. House doctor",
    "source": "admin_console",
    "priority": "high"
  }'
```

#### **Available Admin Commands**

**Character Management:**
- `admin: list characters` - List all available characters
- `admin: create character <name> <type>` - Create new character
- `admin: switch character <name>` - Switch active character
- `admin: info character <name>` - Get character information

**Character Types:**
- `teacher` - Educational instructor (patient, encouraging)
- `doctor` - Medical professional (caring, precise)
- `chef` - Culinary expert (creative, passionate)
- `coach` - Fitness and wellness (motivating, energetic)
- `librarian` - Information specialist (organized, helpful)

### 7. **Admin Control Panel**

Monitor and manage admin operations through the centralized control panel.

**Endpoint:** `GET http://localhost:8200/api/admin/control-panel`

#### **Check Admin Operations History**
```bash
# Get full control panel data
curl -s http://localhost:8200/api/admin/control-panel | jq .

# Get recent admin operations only
curl -s http://localhost:8200/api/admin/control-panel | jq '.admin_operations.recent_history'

# Get current character status
curl -s http://localhost:8200/api/admin/control-panel | jq '.s1_characters'
```

#### **System Status Monitoring**
```bash
# Check stimuli processing status
curl -s http://localhost:8200/api/stimuli/status | jq .

# Monitor consolidation statistics
curl -s http://localhost:8200/api/admin/control-panel | jq '.consolidation_stats'

# Check available tools
curl -s http://localhost:8200/api/stimuli/tools | jq .
```

### 8. **Processing Mode Control**

The admin system supports different processing modes:

#### **Silent Processing (Default)**
- **Behavior**: Processed in S2 (AutoGen) only
- **S1 Speech**: None
- **S2 Logging**: Full operation history
- **Format**: `admin: <command>`

#### **Announced Processing**
- **Behavior**: Processed in both S1 and S2
- **S1 Speech**: Full TTS synthesis with blendshape generation
- **S2 Logging**: Full operation history
- **Format**: `announce: admin: <command>`

#### **S1 + S2 Dual Processing**
- **Behavior**: Character operations executed in S1, announced via speech, logged in S2
- **Use Case**: Administrative changes that need user notification
- **Format**: `announce: admin: create character <name> <type>`

### 9. **Admin System Monitoring**

#### **Container Log Analysis**
```bash
# Check S1 container for speech synthesis activity
docker logs neurosync_s1 --tail 20 | grep -E "(🗣️|🎯|🎵)"

# Check S2 container for admin processing
docker logs autogen_agent --tail 20 | grep -E "(🔧|✅|🔇).*CONSOLIDATOR"

# Monitor both containers simultaneously
docker logs neurosync_s1 -f | grep -E "(🗣️|🎯)" &
docker logs autogen_agent -f | grep -E "CONSOLIDATOR.*admin"
```

#### **System Health Checks**
```bash
# Test admin endpoint availability
curl -f http://localhost:8200/health

# Check stimuli processing capability
curl -s http://localhost:8200/api/stimuli/status | jq '.ready_for_stimuli'

# Verify S1 character management
curl -s http://neurosync:5001/character/list | jq '.characters | length'
```

## 🎯 **Admin Command Examples**

### **Example 1: Silent Character Management**
```bash
# Create a doctor character silently
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "silent_doctor_001",
    "content": "admin: create character Dr. Wilson doctor",
    "source": "admin_panel",
    "priority": "high"
  }'

# Switch to the new character silently
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "silent_switch_001", 
    "content": "admin: switch character dr._wilson_doctor_template",
    "source": "admin_panel",
    "priority": "medium"
  }'
```

### **Example 2: Announced Character Operations**
```bash
# Create and announce a chef character
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "announce_chef_001",
    "content": "announce: admin: create character Chef Mario chef",
    "source": "admin_panel",
    "priority": "high"
  }'

# List characters with speech announcement
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "announce_list_001",
    "content": "announce: admin: list characters", 
    "source": "admin_panel",
    "priority": "high"
  }'
```

### **Example 3: Control Panel Monitoring**
```bash
# Monitor admin operations in real-time
watch -n 5 'curl -s http://localhost:8200/api/admin/control-panel | jq ".admin_operations.recent_history[-3:]"'

# Check system performance
curl -s http://localhost:8200/api/admin/control-panel | jq '{
  total_operations: .admin_operations.total_processed,
  recent_count: .admin_operations.history_count,
  system_capacity: .system_capacity.overall_status,
  pending_operations: .pending_operations
}'
```

## 🔧 **Admin System Troubleshooting**

### **Admin Commands Not Processing**
1. Check stimuli endpoint: `curl -f http://localhost:8200/api/stimuli/status`
2. Verify command format: Ensure `admin:` prefix is present
3. Check autogen container logs: `docker logs autogen_agent --tail 20`

### **Character Operations Failing**
1. Verify character ID format: Use underscores and `_template` suffix
2. Check S1 endpoint: `curl -f http://neurosync:5001/character/list`
3. Review admin control panel for error details

### **Speech Announcement Not Working**
1. Confirm `announce:` prefix is used
2. Check S1 container logs for TTS activity
3. Verify S1 endpoint configuration: `S1_AVATAR_ENDPOINT=http://neurosync:5001`

This comprehensive API reference provides complete control over both the VTuber system and the admin command processing architecture, enabling flexible management of characters, speech, and system operations. 