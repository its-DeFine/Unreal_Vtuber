# GraphFlow External Stimuli System - Quick Start Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Redis (optional, for caching)
- PostgreSQL (optional, for persistence)
- Docker (optional, for containerized deployment)

### 1. Clone and Setup

```bash
# Navigate to the GraphFlow directory
cd /home/geo/directories/autonomy/docker-vtuber/app/CORE/graphflow-stimuli-system

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp config/development.env.example config/development.env
```

### 2. Configure Environment

Edit `config/development.env` with your settings:

```bash
# Minimal configuration needed:
GRAPHFLOW_LOG_LEVEL=INFO
SYSTEM1_VTUBER_ENDPOINT=http://localhost:5001
SYSTEM2_AUTOGEN_ENDPOINT=http://localhost:3100
```

### 3. Run the System

#### Development Mode (with auto-reload)
```bash
python run.py dev
```

#### Production Mode
```bash
python run.py prod
```

#### Using Docker
```bash
# Build image
python run.py docker-build

# Run with docker-compose
python run.py docker --env development
```

### 4. Test the API

The system will be available at `http://localhost:8080`

#### Check Health
```bash
curl http://localhost:8080/api/health
```

#### Submit a Test Stimuli
```bash
curl -X POST http://localhost:8080/api/v1/stimuli/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "content": "Hello GraphFlow!",
    "source": "test_client",
    "priority": "medium"
  }'
```

#### View API Documentation
Open your browser to: `http://localhost:8080/api/docs`

## 📝 Common Use Cases

### 1. User Chat Message
```python
import requests

response = requests.post(
    "http://localhost:8080/api/v1/stimuli/submit",
    headers={"X-API-Key": "your-api-key"},
    json={
        "content": "What's the weather like today?",
        "source": "user_chat",
        "priority": "medium",
        "metadata": {
            "user_id": "user123",
            "channel": "web"
        }
    }
)

print(response.json())
```

### 2. Admin Command
```python
response = requests.post(
    "http://localhost:8080/api/v1/stimuli/submit",
    headers={"X-API-Key": "admin-api-key"},
    json={
        "content": "/switch_character weather_presenter",
        "source": "admin_console",
        "priority": "high",
        "metadata": {
            "command_type": "character_switch"
        }
    }
)
```

### 3. WebSocket Real-time Updates
```python
import websockets
import asyncio

async def listen_updates():
    uri = "ws://localhost:8080/ws/stimuli"
    async with websockets.connect(uri) as websocket:
        # Send authentication
        await websocket.send('{"api_key": "your-api-key"}')
        
        # Listen for updates
        while True:
            message = await websocket.recv()
            print(f"Update: {message}")

asyncio.run(listen_updates())
```

## 🔧 Configuration Options

### Priority Levels
- `critical` - Immediate processing
- `high` - High priority
- `medium` - Normal priority (default)
- `low` - Low priority
- `minimal` - Background processing

### Stimuli Categories (auto-detected)
- `DIRECT_ADMIN` - Admin commands
- `USER_INTERACTION` - User messages
- `SYSTEM_NOTIFICATION` - System events
- `SOCIAL_MEDIA` - Social mentions
- `EMERGENCY` - Critical events
- `CONTEXTUAL_UPDATE` - Context changes

## 🐛 Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if the service is running: `ps aux | grep graphflow`
   - Verify the port is available: `lsof -i :8080`

2. **Authentication Failed**
   - Ensure API key is configured in `config/api_keys.json`
   - Check API key header: `X-API-Key`

3. **System Integration Failed**
   - Verify System1/System2 endpoints are accessible
   - Check integration API keys are configured

### Logs

Check logs for detailed information:
```bash
# Development logs (console)
python run.py dev

# Production logs (file)
tail -f logs/graphflow.log
```

## 📚 Next Steps

1. Read the [Architecture Overview](ARCHITECTURE_DIAGRAM.md)
2. Check the [API Documentation](docs/api/API.md)
3. Review [Configuration Guide](docs/guides/CONFIGURATION.md)
4. Explore [Integration Examples](examples/)

## 🤝 Integration Points

### System1 (VTuber/Avatar)
- Endpoint: `http://localhost:5001`
- Handles: Speech, expressions, movements

### System2 (AutoGen Agents)
- Endpoint: `http://localhost:3100`
- Handles: Complex reasoning, multi-agent tasks

### Monitoring
- Prometheus metrics: `http://localhost:9090/metrics`
- Health check: `http://localhost:8080/api/health`

## 💡 Tips

1. **Development**: Use `MOCK_INTEGRATIONS=true` to test without external systems
2. **Performance**: Enable Redis for caching frequently processed stimuli
3. **Debugging**: Set `GRAPHFLOW_LOG_LEVEL=DEBUG` for detailed logs
4. **Security**: Always use API keys in production

Happy coding with GraphFlow! 🎉