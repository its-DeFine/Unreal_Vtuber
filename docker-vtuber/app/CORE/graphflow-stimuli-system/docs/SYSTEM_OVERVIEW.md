# GraphFlow External Stimuli System Overview

## 🎯 Purpose
The GraphFlow External Stimuli System is a sophisticated pipeline for processing external inputs (stimuli) that need to trigger responses in the VTuber system. It acts as an intelligent gateway between external events and the avatar/agent systems.

## 🏗️ Architecture

### Core Components

1. **API Server** (`src/api_server.py`)
   - FastAPI-based REST API
   - WebSocket support for real-time updates
   - Authentication via API keys
   - Prometheus metrics integration
   - Endpoints:
     - `/api/v1/stimuli/submit` - Submit new stimuli
     - `/api/v1/stimuli/{id}/status` - Check stimuli status
     - `/api/v1/system/status` - System status
     - `/api/health` - Health check
     - `/ws/stimuli` - WebSocket for real-time updates

2. **Gateway Agent** (`src/gateway/gateway_agent.py`)
   - Main orchestrator for the processing pipeline
   - Integrates with AutoGen for multi-agent processing
   - Manages flow through all processing stages
   - Handles system integration (System1/System2)

3. **Processing Pipeline Nodes**
   - **Categorizer Node** - Classifies stimuli into categories
   - **Analyzer Node** - Performs context analysis
   - **Router Node** - Determines processing path
   - **Executor Node** - Executes decisions

### Data Flow

```
External Stimuli → API Server → Gateway Agent → Processing Pipeline
                                                 ↓
                                          Categorizer Node
                                                 ↓
                                           Analyzer Node
                                                 ↓
                                            Router Node
                                                 ↓
                                           Executor Node
                                                 ↓
                                    System1/System2 Integration
```

## 📊 Stimuli Categories

1. **DIRECT_ADMIN** - Direct commands from administrators
2. **USER_INTERACTION** - User chat or interactions
3. **SYSTEM_NOTIFICATION** - Avatar state notifications
4. **SOCIAL_MEDIA** - Social media mentions
5. **AUTONOMOUS_TRIGGER** - Autonomous mode triggers
6. **EMERGENCY** - High-priority events
7. **CONTEXTUAL_UPDATE** - Context/environment updates
8. **UNKNOWN** - Uncategorized stimuli

## 🔑 Key Features

### 1. **Intelligent Categorization**
- LLM-based analysis for smart categorization
- Keyword pattern matching as fallback
- Caching for performance

### 2. **Context-Aware Processing**
- Multi-dimensional context analysis
- System state awareness
- User context tracking
- Resource monitoring

### 3. **Flexible Routing**
- Decision matrix for routing logic
- Priority-based processing
- Graceful degradation support

### 4. **System Integration**
- **System1** - Avatar/VTuber control (speech, expressions)
- **System2** - Multi-agent system (AutoGen)
- Fallback mechanisms for system failures

### 5. **Monitoring & Metrics**
- Prometheus metrics collection
- Structured logging
- Performance tracking
- Real-time monitoring via WebSocket

## 🚀 Usage Examples

### 1. Submit a Stimuli
```python
POST /api/v1/stimuli/submit
{
    "content": "Hello, can you help me?",
    "source": "user_chat",
    "priority": "medium",
    "metadata": {
        "user_id": "user123",
        "platform": "web"
    }
}
```

### 2. Emergency Stimuli
```python
POST /api/v1/stimuli/submit
{
    "content": "System overload detected!",
    "source": "system_monitor",
    "priority": "critical",
    "metadata": {
        "alert_type": "performance",
        "threshold_exceeded": "cpu_usage"
    }
}
```

### 3. Admin Command
```python
POST /api/v1/stimuli/submit
{
    "content": "/switch_character doctor",
    "source": "admin_console",
    "priority": "high",
    "metadata": {
        "admin_id": "admin001",
        "command_type": "character_switch"
    }
}
```

## 🔧 Configuration

The system uses environment-based configuration:
- `development.env` - Development settings
- `production.env` - Production settings
- `testing.env` - Test settings

Key configuration areas:
- API authentication
- System endpoints
- Processing thresholds
- LLM settings
- Monitoring configuration

## 🏃 Running the System

### Development Mode
```bash
python src/main.py --env development --port 8080
```

### Production Mode
```bash
python src/main.py --env production --port 8080
```

### Docker Mode
```bash
docker-compose up
```

## 📈 Performance Characteristics

- **Async Processing** - All operations are asynchronous
- **Caching** - Intelligent caching for repeated stimuli
- **Rate Limiting** - API rate limiting for protection
- **Graceful Degradation** - Continues operating if subsystems fail
- **Horizontal Scaling** - Can be scaled with multiple instances

## 🔗 Integration Points

1. **AutoGen Integration** - For multi-agent processing
2. **VTuber System** - For avatar control
3. **Monitoring Stack** - Prometheus/Grafana
4. **External APIs** - Extensible for new integrations

This system serves as the intelligent gateway for all external inputs to the VTuber ecosystem, ensuring appropriate processing and response generation.