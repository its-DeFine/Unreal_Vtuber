# GraphFlow-Based External Stimuli Handling System

## Project Description

The GraphFlow External Stimuli System is a production-ready, intelligent gateway that processes external inputs through a sophisticated pipeline using Microsoft AutoGen's GraphFlow architecture. It serves as an enhanced decision-making layer that bridges external stimuli with your existing VTuber avatar system (System1) and multi-agent analysis framework (System2).

### Key Capabilities

- **Intelligent Routing**: Automatically categorizes and routes stimuli to appropriate processing paths
- **Real-time Processing**: Handles concurrent stimuli with sub-2-second response times
- **Flexible Integration**: Seamlessly connects with existing NeuroSync VTuber and AutoGen agent systems
- **Production-Ready**: Built with monitoring, scaling, and reliability in mind
- **Extensible Architecture**: Easy to add new processing nodes and decision rules

## Quick Start

### 1. Clone and Install

```bash
cd docker-vtuber/app/CORE/graphflow-stimuli-system
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp config/development.env.example config/development.env
cp config/api_keys.json.example config/api_keys.json
# Edit files with your configuration
```

### 3. Start Services

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or run locally
python -m src.main
```

### 4. Test the System

```bash
# Submit a test stimuli
curl -X POST http://localhost:8080/api/v1/stimuli/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-123" \
  -d '{
    "content": "Hello, how are you today?",
    "source": "test_client",
    "priority": "medium"
  }'
```

## Features

## Architecture Summary

The system implements a sophisticated GraphFlow pipeline that processes external stimuli through four main stages:

```
External Stimuli → GraphFlow Gateway → Decision Matrix → Execution Paths
                      ↓
            [Categorizer] → [Analyzer] → [Router] → [Executor]
                      ↓                              ↓
       [Option A: Avatar + Analysis]  [Option B: Analysis Only]  [Option C: Log Only]
```

### Processing Pipeline

1. **Categorization**: LLM-powered classification into meaningful categories
2. **Analysis**: Deep contextual analysis with entity extraction and sentiment
3. **Routing**: Decision matrix evaluation for optimal processing path
4. **Execution**: Coordinated execution with System1/System2 integration

For detailed architecture information, see the [Architecture Overview](docs/ARCHITECTURE.md).

## Key Features

- **Intelligent Categorization**: LLM-powered classification of external stimuli into meaningful categories
- **Context-Aware Decision Making**: Considers system state, user history, and environmental factors
- **GraphFlow Processing**: Uses AutoGen's GraphFlow for sophisticated routing and processing
- **Multi-Path Execution**: Supports three distinct processing paths based on stimuli analysis
- **System Integration**: Seamless integration with existing System1 (avatar/speech) and System2 (multi-agent) components
- **Performance Monitoring**: Comprehensive metrics and observability for production deployment

## Stimuli Categories

- **DIRECT_ADMIN**: Administrative commands requiring immediate attention
- **USER_INTERACTION**: Chat messages, comments, questions from users
- **SYSTEM_NOTIFICATION**: Environment changes, status updates, system events
- **SOCIAL_MEDIA**: Tweets, mentions, shares from social platforms
- **AUTONOMOUS_TRIGGER**: Self-generated events based on idle thresholds
- **EMERGENCY**: Critical system alerts requiring immediate override
- **CONTEXTUAL_UPDATE**: Background information for context building

## Processing Decisions

- **Option A - Avatar + Analysis**: High-engagement stimuli that warrant both immediate avatar response and deeper analysis
- **Option B - Analysis Only**: Important stimuli that need multi-agent processing but no immediate avatar response
- **Option C - Log Only**: Low-priority information that should be stored for context but requires no active processing

## Quick Start

### Prerequisites

- Python 3.10+
- Microsoft AutoGen 0.4+ with GraphFlow support
- Redis for state management
- PostgreSQL for persistent storage
- Docker and Docker Compose for containerization

### Installation

1. **Clone and Setup**:
   ```bash
   cd docker-vtuber/app/CORE/graphflow-stimuli-system
   pip install -r requirements.txt
   ```

2. **Configuration**:
   ```bash
   cp config/development.env.example config/development.env
   # Edit configuration as needed
   ```

3. **Start Dependencies**:
   ```bash
   docker-compose up -d redis postgres
   ```

4. **Run the Gateway**:
   ```bash
   python -m src.main
   ```

### Testing the System

```bash
# Submit a test stimuli via API
curl -X POST http://localhost:8080/api/v1/stimuli/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "content": "Hello, how are you today?",
    "source": "user_chat",
    "priority": "medium"
  }'

# Check system status
curl http://localhost:8080/api/v1/status
```

## Development

### Project Structure

```
src/
├── gateway/
│   ├── gateway_agent.py          # Main GraphFlow gateway
│   ├── nodes/                    # GraphFlow processing nodes
│   └── flows/                    # GraphFlow workflows
├── models/                       # Data models
├── integrations/                 # System1/System2 interfaces
├── config/                       # Configuration management
└── utils/                        # Utilities and helpers

tests/
├── unit/                         # Unit tests
├── integration/                  # Integration tests
└── e2e/                         # End-to-end tests

docker/
├── Dockerfile                   # Container definition
├── docker-compose.yml          # Development environment
└── docker-compose.test.yml     # Testing environment
```

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/

# Load testing
pytest tests/performance/
```

## Configuration

### Environment Variables

```bash
# Core settings
GRAPHFLOW_LOG_LEVEL=INFO
GRAPHFLOW_MAX_CONCURRENT_STIMULI=50
GRAPHFLOW_PROCESSING_TIMEOUT=30.0

# LLM settings
GRAPHFLOW_LLM_PROVIDER=ollama
GRAPHFLOW_LLM_MODEL=llama3.2:3b
GRAPHFLOW_LLM_ENDPOINT=http://ollama:11434

# Integration endpoints
SYSTEM1_VTUBER_ENDPOINT=http://neurosync:5001
SYSTEM2_AUTOGEN_ENDPOINT=http://autogen-agent:3100

# Database connections
REDIS_URL=redis://redis:6379
POSTGRES_URL=postgresql://postgres:password@postgres:5432/graphflow
```

### Decision Matrix

The system uses a configurable decision matrix to determine how stimuli should be processed. See `config/decision_matrix.py` for detailed rules and customization options.

## API Reference

### Submit Stimuli

```http
POST /api/v1/stimuli/submit
Content-Type: application/json
Authorization: Bearer <api_key>

{
  "content": "string",           // Required: Stimuli content
  "source": "string",            // Required: Source identifier
  "priority": "high|medium|low", // Optional: Priority level
  "metadata": {                  // Optional: Additional context
    "user_id": "string",
    "platform": "string"
  }
}
```

### Check Status

```http
GET /api/v1/status

Response:
{
  "system_status": "healthy|degraded|down",
  "gateway_agent_status": "active|inactive|error",
  "processing_queue_size": number,
  "average_processing_time": number
}
```

### WebSocket Streaming

```javascript
// Connect to WebSocket
ws://localhost:8080/ws/stimuli

// Submit stimuli
{
  "type": "submit_stimuli",
  "data": {
    "content": "Hello world",
    "source": "websocket_client"
  }
}
```

## Integration with Existing Systems

### System1 Integration (Avatar/Speech)

The gateway integrates with your existing NeuroSync VTuber system for immediate avatar responses:

```python
# Automatic integration via System1Interface
system1_interface.trigger_avatar_response(
    content="Response text",
    metadata={"source": "stimuli_gateway"}
)
```

### System2 Integration (Multi-Agent AutoGen)

Seamless integration with your existing AutoGen agents:

```python
# Automatic routing to existing agents
system2_interface.submit_for_analysis(analyzed_stimuli)
# Routes to: cognitive_ai_agent, programmer_agent, observer_agent
```

## Performance Targets

- **Stimuli Categorization**: < 500ms
- **Decision Routing**: < 1 second
- **Avatar Tool Triggering**: < 2 seconds
- **End-to-End Processing**: < 2 seconds (95th percentile)
- **Concurrent Processing**: 50 stimuli simultaneously
- **Peak Throughput**: 1000 stimuli per hour

## Monitoring and Observability

### Metrics

The system exposes Prometheus metrics at `/metrics`:

- `stimuli_processed_total`: Total stimuli processed
- `stimuli_processing_seconds`: Processing time histogram
- `categorization_accuracy_ratio`: Classification accuracy
- `active_requests_current`: Current active requests
- `processing_queue_size`: Queue size gauge

### Logging

Structured logging with correlation IDs for tracing:

```json
{
  "timestamp": "2025-01-02T10:30:00Z",
  "level": "INFO",
  "service": "graphflow-gateway",
  "stimuli_id": "uuid-123",
  "category": "USER_INTERACTION",
  "decision": "AVATAR_AND_ANALYSIS",
  "processing_time": 1.23,
  "confidence": 0.95
}
```

## Deployment

### Docker Deployment

```bash
# Build and start services
docker-compose up -d

# Scale gateway instances
docker-compose up -d --scale graphflow-gateway=3

# View logs
docker-compose logs -f graphflow-gateway
```

### Health Checks

```bash
# Gateway health
curl http://localhost:8080/health

# Detailed status
curl http://localhost:8080/api/v1/status

# Metrics
curl http://localhost:8080/metrics
```

## Security

- **API Key Authentication**: Required for all external API access
- **Rate Limiting**: Configurable limits per API key
- **Input Validation**: Comprehensive validation and sanitization
- **Audit Logging**: All security-relevant events logged
- **Encryption**: TLS encryption for all external communications

## Troubleshooting

### Common Issues

1. **LLM Connection Errors**:
   ```bash
   # Check LLM endpoint connectivity
   curl http://ollama:11434/api/health
   ```

2. **High Processing Times**:
   ```bash
   # Check system resources
   curl http://localhost:8080/api/v1/status
   # Review queue size and system load
   ```

3. **Integration Failures**:
   ```bash
   # Test System1 connectivity
   curl http://neurosync:5001/health
   
   # Test System2 connectivity  
   curl http://autogen-agent:3100/health
   ```

### Debug Mode

```bash
# Enable debug logging
GRAPHFLOW_LOG_LEVEL=DEBUG python -m src.main

# Enable detailed tracing
GRAPHFLOW_DETAILED_LOGGING=true python -m src.main
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-feature`
3. **Make your changes**
4. **Add tests**: Ensure >95% test coverage
5. **Run tests**: `pytest tests/`
6. **Submit a pull request**

## Documentation

### Core Documentation

- **[Architecture Overview](docs/ARCHITECTURE.md)**: System design, component relationships, and data flow
- **[API Documentation](docs/API.md)**: Complete REST and WebSocket API reference
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)**: Setup, development workflow, and testing
- **[Configuration Guide](docs/CONFIGURATION.md)**: All configuration options and customization
- **[Deployment Guide](docs/DEPLOYMENT.md)**: Docker, Kubernetes, and production deployment
- **[Code Walkthrough](docs/CODE_WALKTHROUGH.md)**: Deep dive into implementation details

### Requirements Documents

- **PRD**: [Product Requirements Document](../../docs/PRD_GraphFlow_External_Stimuli_System.md)
- **FRD**: [Functional Requirements Document](../../docs/FRD_GraphFlow_External_Stimuli_System.md)

### Implementation Guides

- **[Analyzer Node Implementation](docs/ANALYZER_NODE_IMPLEMENTATION.md)**
- **[Main Entry Point](docs/MAIN_ENTRY_POINT.md)**

## License

This project is part of the larger NeuroSync system and follows the same licensing terms.

## Support

For questions, issues, or contributions:
- **Issues**: Create a GitHub issue with detailed description
- **Questions**: Use GitHub Discussions for general questions
- **Security**: Report security issues privately to the maintainers

---

**Note**: This system is designed to work alongside, not replace, your existing autogen-agent system. It provides enhanced external stimuli handling while maintaining full compatibility with your current System1 and System2 infrastructure. 