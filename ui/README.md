# Autonomy UI - Responsive Web Interface

A containerized Bottle web application that provides a responsive UI for monitoring and controlling the autonomous agent system.

## Features

- **Real-time Agent Monitoring**: Live dashboard showing agent status, performance metrics, and activities
- **System Health Checks**: Comprehensive monitoring of all backend services
- **Interactive Command Center**: Send commands and stimuli to agents
- **Semantic Graph Visualization**: D3.js-powered knowledge graph viewer
- **Character Management**: Configure agent personalities and behavior
- **API Proxy**: Secure proxy to backend services with error handling
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Containerized Deployment**: Easy Docker-based deployment

## Architecture

```
Frontend (HTML/CSS/JS) → Bottle Web Server → Backend APIs
                           ↓
                    API Proxy Endpoints
                           ↓
              AutoGen | GraphFlow | NeuroSync
```

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Build and start the UI
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the UI
docker-compose down
```

The UI will be available at `http://localhost:3000`

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

## Configuration

Environment variables:

- `UI_HOST`: Server host (default: 0.0.0.0)
- `UI_PORT`: Server port (default: 3000)
- `AUTOGEN_URL`: AutoGen service URL (default: http://autogen-agent:8000)
- `GRAPHFLOW_URL`: GraphFlow service URL (default: http://graphflow-gateway:8080)
- `NEUROSYNC_URL`: NeuroSync service URL (default: http://neurosync:5001)
- `NEUROSYNC_LOCAL_URL`: NeuroSync Local service URL (default: http://neurosync-local:5000)
- `API_TIMEOUT`: API request timeout in seconds (default: 10)
- `DEBUG`: Enable debug mode (default: false)

## API Proxy Endpoints

The UI provides proxy endpoints to securely access backend services:

### Health Checks
- `GET /api/proxy/health/autogen` - AutoGen health status
- `GET /api/proxy/health/graphflow` - GraphFlow health status  
- `GET /api/proxy/health/neurosync` - NeuroSync health status

### Agent Operations
- `GET /api/proxy/autogen/statistics` - Agent statistics
- `GET /api/proxy/autogen/performance` - Performance analytics
- `GET /api/proxy/autogen/gpu-status` - GPU utilization
- `GET /api/proxy/autogen/agents` - Agent learning status
- `GET /api/proxy/autogen/persona` - Persona configuration

### Stimuli Processing
- `POST /api/proxy/autogen/stimuli/submit` - Submit stimuli
- `GET /api/proxy/autogen/stimuli/status` - Stimuli processing status
- `POST /api/proxy/autogen/emergency-stop` - Emergency stop

### Semantic Graph
- `GET /api/proxy/semantic/export?format=d3js` - Export graph data
- `GET /api/proxy/semantic/metrics` - Graph metrics
- `POST /api/proxy/semantic/search` - Search knowledge graph

### Character Management
- `GET /api/proxy/neurosync/character/current` - Current character info

### System Info
- `GET /api/system/info` - UI system information
- `GET /health` - UI service health check

## UI Components

### Dashboard
- Live agent status grid with health indicators
- Real-time activity feed
- System performance charts (CPU, memory, throughput)
- Agent conversation interface

### Character Customization
- Personality trait sliders
- Voice and appearance configuration
- Behavior settings

### Command Center
- Text input for agent commands
- Target selection (specific agents or all)
- Priority levels
- Command history with status tracking

### Health Monitoring
- Service status overview
- Performance sparklines
- Error rate monitoring
- Network latency tracking

### Knowledge Graph
- Interactive D3.js visualization
- Real-time semantic relationships
- Search and filtering
- Export capabilities

## Development

### File Structure
```
/ui/
├── app.py              # Main Bottle web application
├── index.html          # Main UI template
├── styles.css          # Responsive styles with sci-fi theme
├── app.js              # Frontend JavaScript logic
├── api-client.js       # API integration layer
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container definition
├── docker-compose.yml  # Container orchestration
└── README.md          # This file
```

### Adding New Features

1. **Backend Integration**: Add proxy endpoints in `app.py`
2. **Frontend Logic**: Update `app.js` for UI interactions
3. **API Calls**: Extend `api-client.js` for new endpoints
4. **Styling**: Modify `styles.css` for visual changes

### Error Handling

The UI includes comprehensive error handling:
- API timeouts with configurable limits
- Connection failure fallbacks
- User-friendly error messages
- Automatic retry logic for WebSocket connections

## Security

- CORS support for cross-origin requests
- API proxy prevents direct backend access
- Input validation and sanitization
- Non-root container user

## Monitoring

Health checks available at:
- `/health` - UI service health
- Container health checks via Docker
- Real-time connection status in UI header

## Performance

- Asynchronous API calls
- Connection pooling for backend requests  
- Efficient WebSocket management
- Responsive design with minimal resource usage

## Troubleshooting

### Common Issues

1. **Backend Connection Errors**
   - Check service URLs in environment variables
   - Verify network connectivity between containers
   - Review API proxy logs

2. **UI Not Loading**
   - Check port mapping (3000:3000)
   - Verify container is running: `docker-compose ps`
   - Check logs: `docker-compose logs autonomy-ui`

3. **Real-time Updates Not Working**
   - WebSocket connections may need reconnection
   - Check browser console for errors
   - Verify backend WebSocket endpoints

### Debugging

Enable debug mode:
```bash
export DEBUG=true
python app.py
```

View detailed logs:
```bash
docker-compose logs -f autonomy-ui
```

## License

Part of the Autonomy project. See main project license.