# API Reference - Autonomous VTuber System

## Overview

The Autonomous VTuber System provides a comprehensive REST API through the S2 AutoGen container. All endpoints are accessible via the S2 API server running on port 8200.

**Base URL**: `http://localhost:8200`
**API Documentation**: `http://localhost:8200/docs` (FastAPI Swagger UI)

## Authentication

Currently, the system uses basic authentication. For production deployments, API keys should be configured.

```bash
# Example authenticated request
curl -H "Authorization: Bearer <api-key>" \
     http://localhost:8200/api/stimuli/receive
```

## Core System Endpoints

### S1 Speech Control (NeuroSync Player)

#### POST /process_text
**Description**: Process text input and generate speech with facial animations
**Target**: S1 NeuroSync Player (port 5001)
**URL**: `http://localhost:5001/process_text`

```bash
curl -X POST http://localhost:5001/process_text \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello, this is a test message", "interaction_mode": "interrupt"}'
```

**Request Body**:
```json
{
  "text": "Text to be spoken by the avatar",
  "interaction_mode": "interrupt"  // Optional: "interrupt" (default) or "queue"
}
```

**Parameters**:
- `text` (string, required): Text to be processed and spoken
- `interaction_mode` (string, optional): 
  - `"interrupt"` (default): New requests flush queues and stop current speech
  - `"queue"`: Sequential processing, requests wait for completion

**Response**: Processing confirmation with status

#### POST /speech/control
**Description**: Control active speech playback (stop, pause, resume, status)
**Target**: S1 NeuroSync Player (port 5001)
**URL**: `http://localhost:5001/speech/control`

```bash
# Stop current speech
curl -X POST http://localhost:5001/speech/control \
     -H "Content-Type: application/json" \
     -d '{"action": "stop"}'

# Check system status
curl -X POST http://localhost:5001/speech/control \
     -H "Content-Type: application/json" \
     -d '{"action": "status"}'
```

**Request Body**:
```json
{
  "action": "stop"  // "stop", "pause", "resume", or "status"
}
```

**Actions**:
- `"stop"`: Interrupts active speech, flushes all queues, stops GStreamer pipelines
- `"pause"`: Not supported in RTMP mode (returns 400 error)
- `"resume"`: Not supported in RTMP mode (returns 400 error)  
- `"status"`: Returns current system status and queue information

**Response Examples**:

*Stop Response*:
```json
{
  "status": "stopped",
  "streams_stopped": 1,
  "queues_flushed": true
}
```

*Status Response*:
```json
{
  "status": "idle",
  "active_streams": 0,
  "audio_queue_size": 0,
  "chunk_queue_size": 0
}
```

**Error Responses**:
- `400`: Invalid action or unsupported operation (pause/resume in RTMP mode)
- `500`: Internal server error

### Health and Status

#### GET /health
**Description**: Comprehensive system health check
**Response**: System health status with component details

```bash
curl http://localhost:8200/health
```

**Response Example**:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-13T10:52:04.014402",
  "s2_teams_enabled": true,
  "s2_teams_status": {
    "enabled": true,
    "queue_consumer": true,
    "orchestrator": true,
    "queue_file": "/tmp/s2_queue/s2_processing_queue.json",
    "queue_stats": {
      "running": true,
      "processed": 0,
      "failed": 0,
      "teams_available": ["trader", "educator", "streamer"]
    }
  },
  "stimuli_processing": {
    "stimuli_processing": true,
    "ready_for_stimuli": true,
    "autonomous_state": "running"
  }
}
```

#### GET /status
**Description**: Detailed system status with metrics
**Response**: Comprehensive system information

```bash
curl http://localhost:8200/api/stimuli/status
```

**Response Example**:
```json
{
  "status": "running",
  "timestamp": "2025-07-13T12:00:00Z",
  "system_info": {
    "mode": "simplified",
    "version": "2.0.0",
    "uptime": 3600
  },
  "component_stats": {
    "processed_requests": 150,
    "active_sessions": 5,
    "queue_depth": 2
  }
}
```

#### GET /metrics
**Description**: Prometheus-compatible metrics endpoint
**Response**: Metrics in Prometheus format

```bash
curl http://localhost:8200/metrics
```

## Stimuli Processing API

### Primary Stimuli Endpoint

#### POST /api/stimuli/receive
**Description**: Unified stimuli processing with intelligent routing
**Content-Type**: `application/json`

**Request Body**:
```json
{
  "stimuli_id": "unique-id-123",
  "content": "Analyze current Bitcoin market trends",
  "source": "api_client",
  "priority": "medium",
  "processing_mode": "auto",
  "team_preference": "trader",
  "character_type": "gordon_trader_template",
  "metadata": {
    "user_id": "user123",
    "session_id": "session456"
  }
}
```

**Parameters**:
- `stimuli_id` (string, required): Unique identifier for the request
- `content` (string, required): The stimuli content to process
- `source` (string, required): Source of the stimuli (e.g., "api_client", "webhook")
- `priority` (string, optional): Priority level ("low", "medium", "high", "critical")
- `processing_mode` (string, optional): How to process ("auto", "s1_only", "s2_only", "s1_and_s2")
- `team_preference` (string, optional): Preferred S2 team ("trader", "educator", "streamer")
- `character_type` (string, optional): Specific character to use
- `metadata` (object, optional): Additional context data

**Response Example**:
```json
{
  "stimuli_id": "unique-id-123",
  "status": "success",
  "processing_mode": "s2_only",
  "team_type": "trader",
  "processing_time": 1.25,
  "queued": true,
  "message_id": "msg-abc-123",
  "response_content": "Bitcoin market analysis initiated by trader team",
  "analysis": {
    "routing_reason": "content_keywords",
    "confidence": 0.95,
    "estimated_completion": "30s"
  }
}
```

**Processing Modes**:
- `auto`: Intelligent routing based on content analysis
- `s1_only`: Direct to avatar/speech system only (bypasses S2)
- `s2_only`: AutoGen team processing only (no speech output)
- `s1_and_s2`: Process with S2 first, then forward to S1 for speech

**Important**: When using `s1_and_s2` mode, the S2 system processes the stimuli first, extracts insights, and then forwards the enhanced content to S1 for speech generation with the specified character.

**Example Requests**:

```bash
# Auto routing for market analysis
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "market-001",
    "content": "What are the current cryptocurrency market trends?",
    "source": "api_client",
    "processing_mode": "auto"
  }'

# Force S1 avatar response
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "speech-001", 
    "content": "Say hello to the audience",
    "source": "streaming_app",
    "processing_mode": "s1_only",
    "character_type": "alex_streamer_template"
  }'

# S2 team analysis
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "analysis-001",
    "content": "Create a trading strategy for volatile markets",
    "source": "trading_client",
    "processing_mode": "s2_only", 
    "team_preference": "trader",
    "priority": "high"
  }'
```

### Stimuli Control Endpoints

#### GET /api/stimuli/status
**Description**: Get current stimuli processing status and statistics

```bash
curl http://localhost:8200/api/stimuli/status
```

**Response Example**:
```json
{
  "autonomous_state": "running",
  "current_stimuli": null,
  "statistics": {
    "total_received": 4,
    "total_queued": 4,
    "total_errors": 0,
    "start_time": "2025-07-13T10:51:26.399627"
  },
  "queue_size": 4,
  "uptime": "N/A"
}
```

#### POST /api/stimuli/control/pause
**Description**: Pause autonomous stimuli processing

```bash
curl -X POST http://localhost:8200/api/stimuli/control/pause
```

#### POST /api/stimuli/control/resume
**Description**: Resume autonomous stimuli processing

```bash
curl -X POST http://localhost:8200/api/stimuli/control/resume
```

#### POST /api/stimuli/control/clear
**Description**: Clear the stimuli processing queue

```bash
curl -X POST http://localhost:8200/api/stimuli/control/clear
```

### Queue Management Endpoints

#### GET /api/queue/health
**Description**: Get queue consumer health status

```bash
curl http://localhost:8200/api/queue/health
```

**Response Example**:
```json
{
  "consumer_running": true,
  "task_exists": true,
  "task_status": "running",
  "teams_count": 3,
  "queue_exists": true,
  "restart_available": true,
  "overall_health": "healthy"
}
```

#### POST /api/queue/restart
**Description**: Restart the queue consumer

```bash
curl -X POST http://localhost:8200/api/queue/restart
```

**Response Example**:
```json
{
  "success": true,
  "message": "Queue processing task restarted successfully",
  "timestamp": "2025-07-13T10:53:02.055039"
}
```

### Legacy Compatibility Endpoint

#### POST /api/stimuli/s2
**Description**: Legacy S2 processing endpoint for backward compatibility

**Request Parameters**:
- `content` (string, required): Stimuli content
- `character_type` (string, optional): Character type hint
- `priority` (string, optional): Processing priority

```bash
curl -X POST "http://localhost:8200/api/stimuli/s2?content=Analyze%20market%20data&character_type=trader"
```

## Character Management API

### List Characters

#### GET /api/characters
**Description**: List all registered characters with current status

```bash
curl http://localhost:8200/api/characters
```

**Response Example**:
```json
{
  "characters": [
    {
      "id": "gordon_trader_template",
      "name": "Gordon Trader", 
      "template": "gordon_trader_template",
      "mission_type": "trading",
      "system_assignment": "s2",
      "capabilities": ["market_analysis", "risk_assessment", "trading_strategies"],
      "current_state": "available",
      "current_mission": null,
      "active_sessions": 0,
      "error_count": 0
    },
    {
      "id": "emma_teacher_template",
      "name": "Emma Teacher",
      "template": "emma_teacher_template", 
      "mission_type": "education",
      "system_assignment": "s1",
      "capabilities": ["lesson_planning", "curriculum_design", "student_assessment"],
      "current_state": "busy",
      "current_mission": "lesson-001",
      "active_sessions": 2,
      "error_count": 0
    }
  ]
}
```

### Available Characters

#### GET /api/characters/available
**Description**: Get characters available for assignment

**Query Parameters**:
- `mission_type` (string, optional): Filter by mission type
- `system` (string, optional): Filter by system assignment

```bash
# Get all available characters
curl http://localhost:8200/api/characters/available

# Get available traders
curl "http://localhost:8200/api/characters/available?mission_type=trading"

# Get available S1 characters  
curl "http://localhost:8200/api/characters/available?system=s1"
```

**Response Example**:
```json
{
  "available_characters": [
    {
      "id": "gordon_trader_template",
      "name": "Gordon Trader",
      "mission_type": "trading", 
      "capabilities": ["market_analysis", "risk_assessment"]
    }
  ]
}
```

## Queue Management API

### Queue Statistics

#### GET /api/queues/stats
**Description**: Get queue statistics and health

```bash
curl http://localhost:8200/api/queues/stats
```

**Response Example**:
```json
{
  "queue_stats": {
    "s2_trader": {
      "size": 3,
      "processing": 1,
      "completed_today": 45,
      "average_processing_time": 25.3
    },
    "s2_educator": {
      "size": 1, 
      "processing": 0,
      "completed_today": 12,
      "average_processing_time": 18.7
    },
    "s2_streamer": {
      "size": 0,
      "processing": 0, 
      "completed_today": 8,
      "average_processing_time": 15.2
    }
  }
}
```

### Purge Queue

#### POST /api/queues/{queue_name}/purge
**Description**: Purge all messages from a specific queue

```bash
# Purge trader queue
curl -X POST http://localhost:8200/api/queues/s2_trader/purge

# Purge educator queue  
curl -X POST http://localhost:8200/api/queues/s2_educator/purge
```

**Response Example**:
```json
{
  "purged_messages": 5
}
```

## Statistics and Monitoring API

### Processing Statistics

#### GET /api/stats
**Description**: Get comprehensive processing statistics

```bash
curl http://localhost:8200/api/stats
```

**Response Example**:
```json
{
  "processing": {
    "total_processed": 1250,
    "successful": 1180,
    "failed": 70,
    "by_mode": {
      "s1_only": 450,
      "s2_only": 600, 
      "s1_and_s2": 200
    },
    "by_team": {
      "trader": 400,
      "educator": 200,
      "streamer": 150
    },
    "average_processing_time": 18.5
  },
  "characters": {
    "total_characters": 14,
    "active_characters": 8,
    "by_system": {
      "s1": 6,
      "s2": 8
    }
  },
  "queues": {
    "total_messages": 4,
    "processing": 1,
    "completed_today": 65
  },
  "errors": {
    "total_errors": 12,
    "error_rate": 0.96,
    "common_errors": [
      "llm_timeout",
      "queue_full",
      "character_unavailable"
    ]
  }
}
```

## Configuration API

### System Configuration

#### GET /api/config
**Description**: Get current system configuration

```bash
curl http://localhost:8200/api/config
```

**Response Example**:
```json
{
  "system_mode": "simplified",
  "environment": "development",
  "debug": true,
  "queue_type": "redis",
  "api_host": "0.0.0.0",
  "api_port": 8000,
  "features": {
    "s1_enabled": true,
    "s2_enabled": true, 
    "neo4j_enabled": true,
    "scb_enabled": true
  }
}
```

## WebSocket API (Future Enhancement)

### Real-time Updates

#### WS /ws/stimuli/{stimuli_id}
**Description**: Subscribe to real-time processing updates

```javascript
// JavaScript WebSocket example
const ws = new WebSocket('ws://localhost:8200/ws/stimuli/unique-id-123');

ws.onmessage = function(event) {
  const update = JSON.parse(event.data);
  console.log('Processing update:', update);
};
```

**Update Events**:
- `processing_started`: Processing began
- `team_assigned`: S2 team assigned
- `insights_generated`: New insights available
- `processing_complete`: Processing finished
- `error_occurred`: Error in processing

## Error Handling

### Error Response Format

All endpoints return errors in a consistent format:

```json
{
  "error": {
    "code": "PROCESSING_FAILED",
    "message": "S2 team processing failed due to timeout",
    "details": {
      "stimuli_id": "unique-id-123",
      "team": "trader",
      "processing_time": 60.0
    },
    "timestamp": "2025-07-13T12:00:00Z"
  }
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `VALIDATION_ERROR` | Invalid request parameters | 400 |
| `CHARACTER_UNAVAILABLE` | Requested character is busy | 409 |
| `PROCESSING_FAILED` | Processing encountered error | 500 |
| `QUEUE_FULL` | Processing queue is full | 503 |
| `SERVICE_UNAVAILABLE` | Required service is down | 503 |
| `TIMEOUT` | Processing exceeded time limit | 504 |

### Error Handling Examples

```bash
# Invalid request
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{"content": ""}' # Empty content

# Response: 400 Bad Request
{
  "error": {
    "code": "VALIDATION_ERROR", 
    "message": "Content cannot be empty",
    "details": {"field": "content"}
  }
}
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Default Limit**: 100 requests per minute per IP
- **Headers**: Rate limit info in response headers
- **Burst Handling**: Short bursts allowed up to 20% over limit

**Rate Limit Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1625184000
```

## SDKs and Client Libraries

### Python SDK Example

```python
import requests
import json

class VTuberAPI:
    def __init__(self, base_url="http://localhost:8200"):
        self.base_url = base_url
    
    def process_stimuli(self, content, **kwargs):
        payload = {
            "stimuli_id": f"sdk-{uuid.uuid4()}",
            "content": content,
            "source": "python_sdk",
            **kwargs
        }
        
        response = requests.post(
            f"{self.base_url}/api/stimuli/receive",
            json=payload
        )
        return response.json()
    
    def get_health(self):
        response = requests.get(f"{self.base_url}/health")
        return response.json()

# Usage
api = VTuberAPI()
result = api.process_stimuli(
    "Analyze Bitcoin trends",
    processing_mode="s2_only",
    team_preference="trader"
)
```

### JavaScript SDK Example

```javascript
class VTuberAPI {
    constructor(baseURL = 'http://localhost:8200') {
        this.baseURL = baseURL;
    }
    
    async processStimuli(content, options = {}) {
        const payload = {
            stimuli_id: `js-${Date.now()}`,
            content,
            source: 'javascript_sdk',
            ...options
        };
        
        const response = await fetch(`${this.baseURL}/api/stimuli/receive`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        return response.json();
    }
    
    async getHealth() {
        const response = await fetch(`${this.baseURL}/health`);
        return response.json();
    }
}

// Usage
const api = new VTuberAPI();
const result = await api.processStimuli('Create educational content', {
    processing_mode: 's2_only',
    team_preference: 'educator'
});
```

## Testing the API

### Using cURL

```bash
# Health check
curl http://localhost:8200/health

# Process stimuli
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "test-001",
    "content": "Test message",
    "source": "test"
  }'

# Get stats
curl http://localhost:8000/api/stats
```

### Using HTTPie

```bash
# Install HTTPie
pip install httpie

# Health check
http GET localhost:8000/health

# Process stimuli
http POST localhost:8000/api/stimuli/receive \
  stimuli_id="test-001" \
  content="Test message" \
  source="test"
```

### Using Postman

Import the OpenAPI specification from `http://localhost:8000/openapi.json` into Postman for a complete collection of endpoints with examples.

## API Versioning

The API follows semantic versioning:
- **Current Version**: v1
- **Version Header**: `API-Version: v1`
- **Backward Compatibility**: Maintained for one major version

Future versions will be accessible via:
- Path versioning: `/v2/api/stimuli/receive`
- Header versioning: `API-Version: v2`

---

This API reference provides comprehensive documentation for integrating with the Autonomous VTuber System. For additional examples and interactive testing, visit the Swagger UI at `http://localhost:8000/docs`.