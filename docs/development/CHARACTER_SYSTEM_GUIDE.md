# 🎭 Character System Guide

The NeuroSync Player includes a sophisticated character system that allows you to create, manage, and switch between different AI personalities. Each character has unique traits, communication styles, and behavioral patterns.

## 📋 **Available Characters**

The system comes with several pre-configured characters:

### **1. Reactive Assistant** (`reactive_default`)
- **Role:** General Purpose Assistant
- **Personality:** Helpful, responsive, adaptive
- **Style:** Clear and friendly
- **Use Case:** Default conversational AI assistant

### **2. Professor Smith** (`demo_teacher`) 
- **Role:** Interactive Teacher
- **Personality:** Patient, encouraging, knowledgeable
- **Style:** Clear and educational
- **Expertise:** Mathematics, physics, general science
- **Use Case:** Educational content and tutoring

### **3. Alice** (`demo_secretary`)
- **Role:** Executive Secretary
- **Personality:** Professional, efficient, friendly
- **Style:** Formal but warm
- **Expertise:** Scheduling, email management, task prioritization
- **Use Case:** Business assistance and organization

### **4. Educational Assistant** (`teacher_template`)
- **Role:** Interactive Teacher (Template)
- **Personality:** Patient, encouraging, knowledgeable, adaptive
- **Style:** Clear and educational
- **Use Case:** Teaching and learning support

### **5. Executive Assistant** (`secretary_template`)
- **Role:** Professional Secretary (Template)
- **Personality:** Professional, efficient, proactive, organized
- **Style:** Formal but approachable
- **Use Case:** Professional business support

## 🔌 **API Endpoints**

All character management endpoints are available at: `http://localhost:5001/api/v1/reactive/character/`

### **List Characters**
```bash
GET /api/v1/reactive/character/list
```
**Response:**
```json
{
  "characters": [
    {
      "id": "reactive_default",
      "name": "Reactive Assistant", 
      "role": "General Purpose Assistant",
      "is_current": true
    }
  ],
  "current_character_id": "reactive_default"
}
```

### **Get Current Character**
```bash
GET /api/v1/reactive/character/current
```
**Response:**
```json
{
  "id": "reactive_default",
  "name": "Reactive Assistant",
  "role": "General Purpose Assistant",
  "personality_traits": ["helpful", "responsive", "adaptive"],
  "communication_style": "clear and friendly",
  "scb_context_lines": 50,
  "conversation_history_size": 100
}
```

### **Switch Character**
```bash
POST /api/v1/reactive/character/load
Content-Type: application/json

{
  "character_id": "demo_teacher"
}
```
**Response:**
```json
{
  "success": true,
  "character": {
    "id": "demo_teacher",
    "name": "Professor Smith",
    "role": "Interactive Teacher"
  }
}
```

### **Create New Character**
```bash
POST /api/v1/reactive/character/create
Content-Type: application/json

{
  "id": "my_custom_character",
  "name": "Custom Assistant",
  "role": "Specialized Helper",
  "personality_traits": ["creative", "analytical", "friendly"],
  "communication_style": "casual and engaging",
  "emotional_range": "enthusiastic and positive",
  "domain_expertise": ["coding", "design", "problem-solving"],
  "behavioral_rules": [
    "Always provide practical examples",
    "Encourage creativity and experimentation",
    "Break down complex problems into steps"
  ]
}
```

### **Update Character**
```bash
PUT /api/v1/reactive/character/update
Content-Type: application/json

{
  "personality_traits": ["helpful", "patient", "detailed"],
  "communication_style": "thorough and supportive",
  "scb_context_lines": 75
}
```

### **Delete Character**
```bash
DELETE /api/v1/reactive/character/delete/character_id
```

## 🛠️ **Character Structure**

Each character is defined by these key properties:

### **Basic Information**
- `id`: Unique identifier
- `name`: Display name
- `role`: Character's primary function
- `version`: Character definition version

### **Personality & Behavior**
- `personality_traits`: List of personality characteristics
- `communication_style`: How the character communicates
- `emotional_range`: Emotional spectrum and responses
- `behavioral_rules`: Rules governing character behavior
- `forbidden_topics`: Topics the character avoids

### **Expertise & Knowledge**
- `domain_expertise`: Areas of specialization
- `knowledge_areas`: General knowledge domains
- `priority_topics`: Topics the character prioritizes

### **Response Patterns**
- `response_patterns`: Template responses for specific scenarios
- `greeting_templates`: Various greeting options
- `farewell_templates`: Different ways to say goodbye

### **Configuration**
- `scb_context_lines`: Memory context lines to use
- `conversation_history_size`: Conversation memory limit
- `formality_level`: formal/neutral/casual
- `humor_level`: none/low/moderate/high
- `technical_level`: simple/moderate/technical/adaptive

## 💡 **Usage Examples**

### **1. List All Available Characters**
```bash
curl -X GET http://localhost:5001/api/v1/reactive/character/list
```

### **2. Switch to Teacher Character**
```bash
curl -X POST http://localhost:5001/api/v1/reactive/character/load \
  -H "Content-Type: application/json" \
  -d '{"character_id": "demo_teacher"}'
```

### **3. Chat with Current Character**
```bash
curl -X POST http://localhost:5001/api/v1/reactive/event/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! Can you explain quantum physics?"}'
```

### **4. Create a Developer Assistant**
```bash
curl -X POST http://localhost:5001/api/v1/reactive/character/create \
  -H "Content-Type: application/json" \
  -d '{
    "id": "dev_assistant",
    "name": "Code Mentor",
    "role": "Senior Developer",
    "personality_traits": ["analytical", "patient", "thorough"],
    "communication_style": "technical but accessible",
    "domain_expertise": ["programming", "architecture", "debugging"],
    "behavioral_rules": [
      "Always provide code examples",
      "Explain the reasoning behind solutions",
      "Suggest best practices and optimizations"
    ],
    "response_patterns": {
      "code_review": "Looking at your code, I notice {observation}. Here's how to improve it: {suggestion}",
      "debugging": "This error typically occurs when {cause}. Try this solution: {fix}"
    }
  }'
```

## 📁 **File-Based Character Management**

Characters are automatically saved as JSON files in the `characters/` directory:

### **Character File Structure**
```json
{
  "id": "custom_character",
  "name": "My Character",
  "role": "Specialized Assistant",
  "personality_traits": ["trait1", "trait2"],
  "communication_style": "description",
  "emotional_range": "description",
  "domain_expertise": ["area1", "area2"],
  "knowledge_areas": ["knowledge1", "knowledge2"],
  "response_patterns": {
    "pattern_name": "template with {variables}"
  },
  "behavioral_rules": ["rule1", "rule2"],
  "scb_context_lines": 50,
  "conversation_history_size": 100,
  "formality_level": "neutral",
  "humor_level": "moderate",
  "technical_level": "adaptive",
  "created_at": "2025-07-02T14:30:00",
  "updated_at": "2025-07-02T14:30:00"
}
```

### **Hot-Reload Feature**
- Characters are automatically reloaded when their files change
- No need to restart the system when updating character files
- Supports both JSON and YAML formats

## 🎯 **Character Templates**

The system includes built-in templates for common use cases:

### **Secretary Template** (`secretary_template`)
```json
{
  "personality_traits": ["professional", "efficient", "proactive", "organized"],
  "domain_expertise": ["calendar management", "email prioritization", "meeting coordination"],
  "response_patterns": {
    "email_notification": "You have a new {priority} email from {sender} regarding {subject}",
    "meeting_reminder": "Your {meeting_type} with {attendees} starts in {time}"
  },
  "formality_level": "formal"
}
```

### **Teacher Template** (`teacher_template`)
```json
{
  "personality_traits": ["patient", "encouraging", "knowledgeable", "adaptive"],
  "domain_expertise": ["adaptive teaching", "knowledge assessment", "concept explanation"],
  "response_patterns": {
    "correct_answer": "Excellent! You've got it right. {explanation}",
    "incorrect_answer": "Not quite, but good try! Let me help you understand: {hint}"
  },
  "technical_level": "adaptive"
}
```

## 🔄 **Character Switching Workflow**

1. **List available characters** to see options
2. **Switch to desired character** using `/character/load`
3. **Chat with the character** - responses will match their personality
4. **Create custom characters** for specific use cases
5. **Update characters** as needed for different scenarios

## 🚀 **Advanced Features**

### **Response Pattern System**
Characters can have template responses for specific scenarios:
```json
{
  "response_patterns": {
    "email_notification": "New email from {sender}: {subject}",
    "meeting_reminder": "Meeting with {attendees} in {time}",
    "task_completion": "Task '{task}' has been completed successfully"
  }
}
```

### **Behavioral Rules**
Define how characters should behave:
```json
{
  "behavioral_rules": [
    "Always provide examples when explaining concepts",
    "Ask clarifying questions when requests are unclear",
    "Maintain professional tone in business contexts"
  ]
}
```

### **Memory Configuration**
Control how much context characters remember:
```json
{
  "scb_context_lines": 50,
  "conversation_history_size": 100,
  "memory_retention_days": 30,
  "priority_topics": ["urgent tasks", "deadlines", "meetings"]
}
```

## 🎭 **Character Development Tips**

1. **Start with Templates**: Use existing templates as a base
2. **Define Clear Roles**: Give characters specific purposes
3. **Test Interactions**: Chat with characters to refine their responses
4. **Iterate and Improve**: Update characters based on usage patterns
5. **Use Response Patterns**: Create templates for common scenarios
6. **Set Appropriate Context**: Configure memory and context limits

---

**The character system enables rich, personality-driven interactions that adapt to different use cases and user needs. Each character maintains consistent behavior while providing contextually appropriate responses.** 