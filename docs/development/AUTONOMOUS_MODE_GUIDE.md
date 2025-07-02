# 🤖 Autonomous Mode Guide

The NeuroSync Player now supports **Autonomous Mode** where characters can proactively generate content without waiting for user input, in addition to the traditional **Reactive Mode** that responds to user prompts.

## 🔄 **Mode Overview**

### **Reactive Mode** (Default)
- Characters wait for user input and respond accordingly
- Traditional chat-based interaction
- Example: "You ask about photosynthesis" → "Teacher explains photosynthesis"

### **Autonomous Mode**
- Characters proactively generate content without user prompts
- Continuous content generation based on character expertise
- Anti-repetition system ensures varied content
- Example: Teacher continuously explains math concepts in sequence

## 📋 **Character Autonomous Behaviors**

Each character has specialized autonomous behaviors:

### **Professor Smith** (`demo_teacher`)
- **Autonomous Focus:** Mathematics fundamentals, science concepts, critical thinking
- **Behavior:** Continuously teaches subjects in depth, building complexity gradually
- **Content Style:** Educational and progressive, step-by-step knowledge building
- **Interval:** 45 seconds between autonomous content

### **Alice** (`demo_secretary`) 
- **Autonomous Focus:** Productivity strategies, workplace organization, time management
- **Behavior:** Proactively shares business tips and professional insights
- **Content Style:** Professional and actionable with practical business focus
- **Interval:** 40 seconds between autonomous content

### **Reactive Assistant** (`reactive_default`)
- **Autonomous Focus:** Productivity tips, interesting facts, technology insights
- **Behavior:** Shares helpful information and practical suggestions
- **Content Style:** Friendly and helpful with practical value focus
- **Interval:** 35 seconds between autonomous content

## 🔌 **API Endpoints**

All mode management endpoints are at: `http://localhost:5001/api/v1/reactive/mode/`

### **Check Mode Status**
```bash
GET /api/v1/reactive/mode/status
```
**Response:**
```json
{
  "current_mode": "reactive",
  "autonomous_active": false,
  "character_supports_autonomous": true,
  "character_id": "demo_teacher",
  "mode_history": [
    {
      "from": "reactive",
      "to": "autonomous", 
      "character_id": "demo_teacher",
      "timestamp": "2025-07-02T11:58:22.793923"
    }
  ]
}
```

### **Switch Mode**
```bash
POST /api/v1/reactive/mode/switch
Content-Type: application/json

{
  "mode": "autonomous"
}
```
**Response:**
```json
{
  "success": true,
  "mode": "autonomous",
  "autonomous_active": true
}
```

### **Start Autonomous Content Generation**
```bash
POST /api/v1/reactive/mode/autonomous/start
Content-Type: application/json

{
  "topic": "mathematics fundamentals"
}
```
**Response:**
```json
{
  "success": true,
  "message": "Autonomous mode started",
  "topic": "mathematics fundamentals",
  "character": "Professor Smith"
}
```

### **Stop Autonomous Content Generation**
```bash
POST /api/v1/reactive/mode/autonomous/stop
Content-Type: application/json
```
**Response:**
```json
{
  "success": true,
  "message": "Autonomous mode stopped"
}
```

## 💡 **Usage Examples**

### **1. Basic Mode Switching**
```bash
# Check current mode
curl -X GET http://localhost:5001/api/v1/reactive/mode/status

# Switch to autonomous mode
curl -X POST http://localhost:5001/api/v1/reactive/mode/switch \
  -H "Content-Type: application/json" \
  -d '{"mode": "autonomous"}'

# Start autonomous content generation
curl -X POST http://localhost:5001/api/v1/reactive/mode/autonomous/start \
  -H "Content-Type: application/json" \
  -d '{"topic": "science concepts"}'
```

### **2. Teacher Autonomous Session**
```bash
# Switch to teacher character
curl -X POST http://localhost:5001/api/v1/reactive/character/load \
  -H "Content-Type: application/json" \
  -d '{"character_id": "demo_teacher"}'

# Enable autonomous mode with math topic
curl -X POST http://localhost:5001/api/v1/reactive/mode/switch \
  -H "Content-Type: application/json" \
  -d '{"mode": "autonomous"}'

curl -X POST http://localhost:5001/api/v1/reactive/mode/autonomous/start \
  -H "Content-Type: application/json" \
  -d '{"topic": "mathematics fundamentals"}'

# Teacher will now continuously explain math concepts
# You can still ask questions in reactive chat while autonomous mode is active
```

### **3. Business Assistant Autonomous Session**
```bash
# Switch to secretary character
curl -X POST http://localhost:5001/api/v1/reactive/character/load \
  -H "Content-Type: application/json" \
  -d '{"character_id": "demo_secretary"}'

# Start autonomous business tips
curl -X POST http://localhost:5001/api/v1/reactive/mode/autonomous/start \
  -H "Content-Type: application/json" \
  -d '{"topic": "productivity strategies"}'
```

## 🛠️ **Character Configuration**

### **Autonomous Behavior Structure**
Each character includes these autonomous configuration fields:

```json
{
  "autonomous_enabled": true,
  "autonomous_behaviors": {
    "description": "Behavior description for autonomous mode",
    "rules": [
      "Rule 1 for autonomous content generation",
      "Rule 2 for maintaining character consistency"
    ],
    "content_style": "Style description for autonomous content"
  },
  "autonomous_topics": [
    "topic1",
    "topic2", 
    "topic3"
  ],
  "autonomous_interval": 45.0
}
```

### **Creating Autonomous-Enabled Characters**
```bash
curl -X POST http://localhost:5001/api/v1/reactive/character/create \
  -H "Content-Type: application/json" \
  -d '{
    "id": "fitness_coach",
    "name": "Fitness Coach",
    "role": "Health & Fitness Expert",
    "personality_traits": ["motivational", "knowledgeable", "encouraging"],
    "autonomous_enabled": true,
    "autonomous_behaviors": {
      "description": "Continuously provide fitness tips, workout suggestions, and health advice",
      "rules": [
        "Share different workout routines and exercises",
        "Provide nutrition and health tips",
        "Motivate with inspirational fitness content",
        "Include safety reminders and proper form guidance"
      ],
      "content_style": "Motivational and educational with safety focus"
    },
    "autonomous_topics": [
      "workout routines",
      "nutrition tips", 
      "fitness motivation",
      "health advice"
    ],
    "autonomous_interval": 30.0
  }'
```

## 🎯 **Autonomous vs Reactive Behavior Examples**

### **Teacher Character:**

**Reactive Mode:**
- User: "What is photosynthesis?"
- Teacher: "Photosynthesis is the process by which plants convert light energy..."

**Autonomous Mode:**
- Teacher: "Let's explore the fascinating world of mathematics! Today, let's start with the revolutionary concept of zero..."
- *[45 seconds later]*
- Teacher: "Building on our discussion of zero, let's examine how place value systems work..."
- *[45 seconds later]*  
- Teacher: "Now that we understand place value, let's explore basic arithmetic operations..."

### **Secretary Character:**

**Reactive Mode:**
- User: "How should I organize my day?"
- Secretary: "I recommend using the Eisenhower Matrix to prioritize tasks..."

**Autonomous Mode:**
- Secretary: "Here's a productivity tip: Try the Pomodoro Technique - work for 25 minutes, then take a 5-minute break..."
- *[40 seconds later]*
- Secretary: "Email management tip: Use the 2-minute rule - if an email takes less than 2 minutes to respond to, do it immediately..."

## 🔄 **Mode Workflow**

### **Complete Autonomous Session Workflow:**
1. **Character Selection** → Choose appropriate character for your use case
2. **Mode Switch** → Switch to autonomous mode
3. **Topic Setting** → Optionally specify a topic focus
4. **Start Generation** → Begin autonomous content generation
5. **Monitor Content** → Characters generate content at their configured intervals
6. **Reactive Interaction** → You can still chat reactively while autonomous mode is active
7. **Stop & Switch** → Stop autonomous mode and return to reactive when desired

### **Hybrid Usage:**
- Autonomous mode can run in the background
- Reactive chat still works during autonomous mode
- Characters maintain personality consistency across both modes
- Mode history is tracked for session management

## 🚀 **Advanced Features**

### **Anti-Repetition System**
- Characters track their recent autonomous content
- Similarity detection prevents repetitive content
- Content regeneration if repetition is detected
- Configurable similarity thresholds per character

### **Topic Progression**
- Characters can focus on specific topics or use their default expertise areas
- Content builds progressively (e.g., teacher starts with fundamentals and adds complexity)
- Topic switching supported during autonomous sessions

### **Interval Configuration**
- Each character has customizable autonomous content intervals
- Default intervals: Teacher (45s), Secretary (40s), Assistant (35s)
- Intervals can be adjusted per character configuration

## 📊 **System Status Monitoring**

### **Mode Information in System Status**
```bash
curl -X GET http://localhost:5001/api/v1/reactive/status
```
**Response includes mode information:**
```json
{
  "character": {
    "id": "demo_teacher",
    "name": "Professor Smith", 
    "autonomous_enabled": true
  },
  "mode": {
    "current_mode": "autonomous",
    "autonomous_active": true,
    "autonomous_content_count": 3
  },
  "status": "operational"
}
```

## ⚡ **Performance Considerations**

- **Resource Usage:** Autonomous mode generates more LLM requests
- **Rate Limiting:** Consider API rate limits when using autonomous mode extensively
- **Content Storage:** Recent autonomous content is stored in memory for anti-repetition
- **Background Processing:** Autonomous generation runs in background tasks

## 🎭 **Character Development for Autonomous Mode**

### **Best Practices:**
1. **Define Clear Autonomous Behaviors:** Specify what the character should do when not prompted
2. **Set Appropriate Intervals:** Balance content frequency with user experience
3. **Create Topic Progressions:** Design content that builds systematically
4. **Test Anti-Repetition:** Ensure characters don't repeat content patterns
5. **Maintain Personality:** Keep character voice consistent across modes

### **Content Guidelines:**
- **Educational Characters:** Progress from basic to advanced concepts
- **Assistant Characters:** Provide varied practical tips and suggestions  
- **Specialist Characters:** Cycle through different aspects of their expertise
- **Entertainment Characters:** Vary content types and engagement styles

---

**Autonomous mode enables characters to take initiative and provide continuous value, creating more engaging and dynamic AI interactions that adapt to different use cases and user preferences.** 