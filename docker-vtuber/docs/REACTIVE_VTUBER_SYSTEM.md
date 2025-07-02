# Reactive VTuber System Documentation

## Overview

The Reactive VTuber System is a streamlined, character-driven virtual avatar system that responds intelligently to external inputs while maintaining consistent personality and contextual awareness. It represents a significant simplification over the complex multi-agent AutoGen system, focusing on practical reactive responses based on well-defined character profiles.

## Key Features

- **Character-Driven Behavior**: All responses stem from comprehensive character profiles
- **Hot-Reload Character Files**: Modify characters without restarting the system
- **External Event Handling**: React to emails, calendar events, tasks, and more
- **SCB Memory Integration**: Leverage shared contextual memory for coherent responses
- **Anti-Repetition System**: Avoid boring, repeated responses
- **RESTful API**: Easy integration with external systems

## Architecture

```
┌─────────────────────────────────────┐
│        External Events              │
│  (Email, Calendar, Chat, System)    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      Reactive Orchestrator          │
│  - Event Queue Management           │
│  - Character Context Assembly       │
│  - Response Generation              │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      Character Manager              │
│  - Character Profiles               │
│  - Hot-Reload System                │
│  - State Persistence                │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│        LLM Integration              │
│  - Prompt Engineering               │
│  - Response Generation              │
│  - Anti-Repetition                 │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      TTS & Animation Pipeline       │
│  - Speech Synthesis                 │
│  - Facial Animation                 │
│  - RTMP Streaming                  │
└─────────────────────────────────────┘
```

## Quick Start

### 1. Set Environment Variable

```bash
# In your docker-compose file or .env
ORCHESTRATOR_VERSION=reactive
```

### 2. Start the System

```bash
docker-compose up -d neurosync
```

### 3. Test the System

```bash
# Run the example script
python reactive_example.py
```

## Character Configuration

### Character Profile Structure

Characters are defined in JSON or YAML files in the `characters/` directory:

```json
{
  "id": "secretary_ai",
  "name": "Ava",
  "role": "Executive Assistant",
  
  "personality_traits": [
    "professional",
    "efficient",
    "proactive",
    "friendly"
  ],
  
  "communication_style": "formal but approachable",
  "emotional_range": "calm and supportive",
  
  "domain_expertise": [
    "calendar management",
    "email prioritization",
    "meeting coordination",
    "task organization"
  ],
  
  "response_patterns": {
    "email_notification": "You have a new {priority} email from {sender} regarding {subject}",
    "meeting_reminder": "Your {meeting_type} with {attendees} starts in {time}",
    "task_update": "Task '{task_name}' has been {status}"
  },
  
  "behavioral_rules": [
    "Always prioritize urgent matters",
    "Summarize long emails to key points",
    "Proactively suggest time optimizations",
    "Maintain professional boundaries"
  ],
  
  "scb_context_lines": 50,
  "conversation_history_size": 100,
  "priority_topics": ["meetings", "deadlines", "urgent emails"]
}
```

### Creating Custom Characters

1. Create a new JSON file in `characters/` directory
2. Define the character following the structure above
3. The system will automatically detect and load it
4. Switch to your character via API

## API Reference

### Character Management

#### List Characters
```http
GET /api/v1/reactive/character/list
```

#### Get Current Character
```http
GET /api/v1/reactive/character/current
```

#### Load Character
```http
POST /api/v1/reactive/character/load
Content-Type: application/json

{
  "character_id": "secretary_ai"
}
```

#### Create Character
```http
POST /api/v1/reactive/character/create
Content-Type: application/json

{
  "id": "custom_character",
  "name": "Custom Name",
  "role": "Custom Role",
  ...
}
```

### External Events

#### Submit Event
```http
POST /api/v1/reactive/event/submit
Content-Type: application/json

{
  "type": "email",
  "source": "gmail",
  "priority": "high",
  "data": {
    "sender": "boss@company.com",
    "subject": "Important Meeting"
  }
}
```

#### Chat Message
```http
POST /api/v1/reactive/event/chat
Content-Type: application/json

{
  "message": "What's my schedule today?"
}
```

### System Status

#### Get Status
```http
GET /api/v1/reactive/status
```

#### Get Configuration
```http
GET /api/v1/reactive/config
```

## Use Cases

### 1. Secretary VTuber

```python
# Configure secretary character
secretary = {
    "id": "executive_secretary",
    "domain_expertise": ["calendar", "email", "tasks"],
    "response_patterns": {
        "email_notification": "New {priority} email from {sender}",
        "meeting_reminder": "{meeting_type} in {time}"
    }
}

# Handle email notification
event = {
    "type": "email",
    "data": {
        "sender": "CEO",
        "subject": "Quarterly Review"
    }
}
# Response: "New high priority email from CEO about Quarterly Review"
```

### 2. Teacher VTuber

```python
# Configure teacher character
teacher = {
    "id": "math_teacher",
    "personality_traits": ["patient", "encouraging"],
    "behavioral_rules": [
        "Adapt to student level",
        "Use examples",
        "Encourage questions"
    ]
}

# Student interaction
message = "I don't understand quadratic equations"
# Response: "Let me break down quadratic equations step by step..."
```

### 3. Customer Service VTuber

```python
# Configure service character
service = {
    "id": "support_agent",
    "communication_style": "helpful and empathetic",
    "domain_expertise": ["troubleshooting", "product knowledge"]
}
```

## Configuration Options

### Environment Variables

```bash
# Timing Configuration
MIN_SPEECH_GAP=2.5              # Minimum seconds between speeches
RESPONSE_TIMEOUT=30.0           # Maximum response generation time

# Anti-Repetition
ANTI_REPETITION_ENABLED=true    # Enable anti-repetition system
SIMILARITY_THRESHOLD=0.85       # Similarity threshold for repetition

# SCB Integration
SCB_INTEGRATION_ENABLED=true    # Enable memory integration
```

### Character Preferences

Each character can configure:
- `scb_context_lines`: How many lines of memory context to use
- `conversation_history_size`: How many conversation turns to remember
- `priority_topics`: Topics to prioritize in memory retrieval

## Troubleshooting

### Character Not Loading
- Check file format (JSON/YAML)
- Verify JSON syntax
- Check file permissions
- Look at logs for parsing errors

### Responses Not Generated
- Verify LLM API keys are set
- Check LLM provider configuration
- Ensure character has valid profile
- Check network connectivity

### Repetitive Responses
- Increase `conversation_history_size`
- Enable anti-repetition system
- Adjust `similarity_threshold`
- Add more variety to `response_patterns`

## Migration from AutoGen

If migrating from AutoGen orchestrator:

1. Set `ORCHESTRATOR_VERSION=reactive`
2. Create character profiles for your use cases
3. Update API calls to use new endpoints
4. Remove AutoGen-specific configuration

## Performance Considerations

- Character files are cached in memory
- Hot-reload only triggers on file changes
- Event queue processes sequentially
- Response generation is async
- SCB queries are optimized by line limit

## Development

### Adding New Event Types

1. Add handler in `reactive_orchestrator.py`:
```python
async def _handle_custom_event(self, event, character):
    # Custom event handling logic
    return response
```

2. Register in event handlers:
```python
self.event_handlers['custom'] = self._handle_custom_event
```

### Extending Character Profiles

Add new fields to `CharacterProfile` dataclass:
```python
@dataclass
class CharacterProfile:
    # ... existing fields ...
    custom_field: str = "default_value"
```

## Best Practices

1. **Character Design**
   - Keep personality traits consistent
   - Define clear behavioral rules
   - Provide diverse response patterns
   - Set appropriate memory limits

2. **Event Handling**
   - Use appropriate priority levels
   - Include relevant context in event data
   - Process high-priority events immediately
   - Clean up old processed events

3. **Memory Management**
   - Configure SCB lines based on character needs
   - Prioritize relevant topics
   - Clear conversation history periodically
   - Monitor memory usage

4. **API Usage**
   - Cache character IDs
   - Batch events when possible
   - Handle API errors gracefully
   - Implement retry logic

## Conclusion

The Reactive VTuber System provides a practical, maintainable solution for creating intelligent virtual avatars. By focusing on character-driven responses and external event handling, it delivers engaging interactions without the complexity of multi-agent systems. 