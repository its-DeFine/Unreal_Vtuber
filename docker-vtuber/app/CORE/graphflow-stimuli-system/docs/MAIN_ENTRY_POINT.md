# GraphFlow External Stimuli System - Main Entry Point Documentation

## Overview

The GraphFlow External Stimuli System provides a production-ready service for processing external stimuli through an intelligent decision-making pipeline. The system consists of:

1. **Main Application** (`src/main.py`) - Orchestrates all components
2. **API Server** (`src/api_server.py`) - Provides REST and WebSocket APIs
3. **Background Tasks** (`src/background_tasks.py`) - Manages system health and cleanup
4. **Runner Script** (`run.py`) - Convenient entry point with environment management

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Main Application                      │
│                  (GraphFlowApplication)                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────┐│
│  │ Gateway Agent   │  │  API Server  │  │ Background ││
│  │                 │  │              │  │   Tasks    ││
│  │ - Process flow  │  │ - REST API   │  │            ││
│  │ - Decision eng. │  │ - WebSocket  │  │ - Health   ││
│  │ - Integration   │  │ - Auth       │  │ - Metrics  ││
│  └─────────────────┘  └──────────────┘  └────────────┘│
└─────────────────────────────────────────────────────────┘
```

## Running the Application

### Using the Runner Script (Recommended)

```bash
# Development mode with auto-reload
python run.py dev

# Production mode
python run.py prod

# Run tests
python run.py test

# Build Docker image
python run.py docker-build

# Run with docker-compose
python run.py docker --env production
```

### Direct Execution

```bash
# Run with default settings
python -m src.main

# Run with custom settings
python -m src.main --host 0.0.0.0 --port 8080 --env production
```

### Docker

```bash
# Build image
docker build -f docker/Dockerfile -t graphflow-stimuli-system:latest .

# Run container
docker run -p 8080:8080 -p 9090:9090 \
  -v $(pwd)/config:/app/config \
  -e ENVIRONMENT=production \
  graphflow-stimuli-system:latest
```

## API Endpoints

### REST API

- `POST /api/v1/stimuli/submit` - Submit external stimuli
- `GET /api/v1/status` - Get system status
- `GET /api/v1/stimuli/{stimuli_id}/status` - Get stimuli status
- `GET /api/v1/health` - Health check (no auth)
- `GET /metrics` - Prometheus metrics (no auth)

### WebSocket

- `/ws/stimuli?token=<api-key>` - Real-time stimuli submission

## Authentication

The API uses Bearer token authentication. Include your API key in the Authorization header:

```
Authorization: Bearer your-api-key-here
```

API keys are configured in `/app/config/api_keys.json`.

## Background Tasks

The system runs several background tasks:

1. **Health Checks** - Every 30 seconds
2. **Metrics Aggregation** - Every 60 seconds
3. **Cleanup** - Every 5 minutes
4. **State Synchronization** - Every 2 minutes
5. **System Monitoring** - Every 15 seconds
6. **Performance Optimization** - Every 10 minutes

## Configuration

Environment variables are loaded from:
- `/app/config/development.env` (development)
- `/app/config/testing.env` (testing)
- `/app/config/production.env` (production)

Key configuration options:
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENABLE_DETAILED_LOGGING` - Enable JSON structured logging
- `OPENAI_API_KEY` - OpenAI API key for LLM operations
- `REDIS_URL` - Redis connection URL (optional)
- `DATABASE_URL` - Database connection URL (optional)

## Monitoring

### Health Check
```bash
curl http://localhost:8080/api/v1/health
```

### Prometheus Metrics
```bash
curl http://localhost:8080/metrics
```

### System Status
```bash
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8080/api/v1/status
```

## Graceful Shutdown

The application handles graceful shutdown on SIGINT (Ctrl+C) and SIGTERM signals:

1. Stops accepting new requests
2. Completes processing of in-flight requests
3. Saves system state
4. Stops background tasks
5. Closes all connections
6. Exits cleanly

## Error Handling

The system implements comprehensive error handling:

- Request validation errors return 422
- Authentication errors return 401
- Authorization errors return 403
- Server errors return 500 with error details
- All errors are logged with context

## Production Deployment

For production deployment:

1. Use the production Dockerfile
2. Set appropriate resource limits
3. Configure monitoring and alerting
4. Use a reverse proxy (nginx, traefik)
5. Enable SSL/TLS
6. Set up log aggregation
7. Configure backup and recovery

## Development

### Running Tests
```bash
python run.py test
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Adding New Features

1. Implement feature in appropriate module
2. Add tests in `tests/`
3. Update API documentation
4. Add background tasks if needed
5. Update configuration options

## Troubleshooting

### Common Issues

1. **Port already in use**
   - Change port with `--port` flag
   - Kill existing process on port 8080

2. **Gateway initialization failed**
   - Check OpenAI API key
   - Verify configuration files
   - Check logs in `/app/logs/`

3. **High memory usage**
   - Adjust cleanup intervals
   - Reduce cache sizes
   - Check for memory leaks

4. **Slow processing**
   - Check system resources
   - Review performance metrics
   - Optimize decision rules

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python run.py dev
```

## Support

For issues and questions:
1. Check logs in `/app/logs/`
2. Review metrics dashboard
3. Consult API documentation
4. Check system health status