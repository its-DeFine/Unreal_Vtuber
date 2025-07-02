# Reactive Orchestrator Package

A well-organized, modular reactive orchestrator system for NeuroSync Player that handles character-driven responses to external events.

## 🏗️ Package Structure

```
orchestrator/
├── __init__.py                 # Main package exports
├── core/                      # Core orchestrator logic  
│   ├── __init__.py           
│   ├── orchestrator.py       # Main ReactiveOrchestrator class
│   ├── events.py            # Event management classes
│   └── conversation.py      # Conversation history management
├── api/                      # API routes and endpoints
│   ├── __init__.py
│   └── routes.py            # Flask routes for the orchestrator  
└── character/               # Character management (future expansion)
    └── __init__.py
```

## 🚀 Quick Start

### Basic Usage

```python
from orchestrator import ReactiveOrchestrator

# Initialize orchestrator
config = {
    'timing': {'min_speech_gap': 2.5},
    'anti_repetition': {'enabled': True}
}
orchestrator = ReactiveOrchestrator(config)

# Add external event
await orchestrator.add_external_event({
    'type': 'chat',
    'source': 'api',
    'priority': 'high',
    'data': {'message': 'Hello!'}
})
```

### API Usage

```bash
# Get system status
curl http://localhost:5001/api/v1/reactive/status

# Send chat message
curl -X POST http://localhost:5001/api/v1/reactive/event/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello there!"}'
```

## 📦 Core Modules

### `core/orchestrator.py`
The main `ReactiveOrchestrator` class that:
- Manages external events and responses
- Integrates with character management
- Handles LLM communication
- Provides anti-repetition logic
- Manages conversation history

### `core/events.py`
Event management classes:
- `ExternalEvent`: Represents external input events
- `ReactiveState`: Tracks current system state

### `core/conversation.py`
Conversation history management:
- `ConversationHistory`: Stores and retrieves conversation turns
- Format conversation for prompts
- Export conversation data

### `api/routes.py`
Flask API endpoints:
- `/character/*` - Character management
- `/event/*` - Event processing
- `/status` - System status
- `/config` - Configuration management

## 🔧 Configuration

The orchestrator accepts a configuration dictionary with:

```python
config = {
    'timing': {
        'min_speech_gap': 2.5,      # Minimum seconds between responses
        'response_timeout': 30.0     # Response generation timeout
    },
    'anti_repetition': {
        'enabled': True,             # Enable anti-repetition checking
        'threshold': 0.85           # Similarity threshold
    },
    'llm_config': {
        # LLM-specific configuration overrides
    },
    'scb_client': None              # Optional SCB client instance
}
```

## 🎭 Character Integration

The orchestrator integrates with the character management system to:
- Load and switch between characters
- Use character-specific response patterns
- Include character context in LLM prompts
- Maintain character consistency

## 🔄 Event Processing Flow

1. **Event Creation**: External events are added to the queue
2. **Priority Handling**: High-priority events are processed immediately
3. **Handler Selection**: Appropriate handler is selected by event type
4. **Response Generation**: LLM generates character-appropriate response
5. **Anti-Repetition**: Checks for similar recent responses
6. **State Updates**: Updates conversation history and system state

## 📡 API Endpoints

### Character Management
- `GET /character/list` - List all characters
- `GET /character/current` - Get current character
- `POST /character/load` - Switch character

### Event Processing  
- `POST /event/chat` - Process chat message
- `GET /event/queue` - Get event queue status

### System Status
- `GET /status` - Get system status
- `GET /config` - Get configuration
- `PUT /config` - Update configuration

## 🧪 Testing

The orchestrator includes comprehensive logging for debugging:

```python
import logging
logging.getLogger('orchestrator').setLevel(logging.DEBUG)
```

## 🔮 Future Enhancements

- Enhanced character personality modeling
- Event priority queuing with complex rules
- Plugin system for custom event handlers
- Metrics and analytics collection
- Multi-language support
- Voice synthesis integration

## 🤝 Contributing

When adding new functionality:
1. Follow the modular structure
2. Add appropriate logging
3. Update documentation
4. Include tests for new features
5. Maintain backwards compatibility

## 📄 License

Part of the NeuroSync Player system. See main project license for details. 