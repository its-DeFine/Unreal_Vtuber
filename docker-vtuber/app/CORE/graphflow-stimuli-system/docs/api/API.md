# GraphFlow External Stimuli System - API Documentation

## Overview

The GraphFlow External Stimuli System provides a comprehensive API for submitting and processing external stimuli through both REST and WebSocket interfaces. All endpoints require authentication via API keys unless otherwise specified.

## Base URL

```
http://localhost:8080
```

## Authentication

### API Key Authentication

All API requests must include an API key in the Authorization header:

```http
Authorization: Bearer YOUR_API_KEY
```

API keys are configured in `/app/config/api_keys.json` with the following structure:

```json
{
  "api_keys": [
    {
      "key": "your-api-key-here",
      "name": "Client Name",
      "permissions": ["read", "write", "admin"],
      "rate_limit": 100
    }
  ]
}
```

### Permissions

- **read**: Can query status and retrieve information
- **write**: Can submit stimuli for processing
- **admin**: Full access to all endpoints and operations

## REST API Endpoints

### Submit Stimuli

Submit external stimuli for processing through the GraphFlow pipeline.

**Endpoint:** `POST /api/v1/stimuli/submit`  
**Permission Required:** `write`

#### Request Body

```json
{
  "content": "Hello, how are you today?",
  "source": "user_chat",
  "priority": "medium",
  "metadata": {
    "user_id": "user123",
    "platform": "discord",
    "channel": "general"
  },
  "request_id": "client-request-123"
}
```

#### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| content | string | Yes | The content of the external stimuli |
| source | string | Yes | The source system or component |
| priority | string | No | Priority level: `low`, `medium`, `high`, `critical` (default: `medium`) |
| metadata | object | No | Additional context data |
| request_id | string | No | Client-provided ID for tracking |

#### Response

```json
{
  "success": true,
  "stimuli_id": "550e8400-e29b-41d4-a716-446655440000",
  "request_id": "client-request-123",
  "processing_status": "completed",
  "estimated_processing_time": 1.234,
  "message": "Processed with decision: AVATAR_AND_ANALYSIS",
  "timestamp": "2025-01-03T10:30:00Z"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether processing succeeded |
| stimuli_id | string | Unique identifier for the stimuli |
| request_id | string | Echo of client request ID if provided |
| processing_status | string | Status: `completed`, `failed`, `queued` |
| estimated_processing_time | float | Processing time in seconds |
| message | string | Human-readable status message |
| timestamp | string | ISO 8601 timestamp |

#### Example

```bash
curl -X POST http://localhost:8080/api/v1/stimuli/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "content": "Tell me about the weather",
    "source": "discord_bot",
    "priority": "medium",
    "metadata": {
      "user_id": "discord_user_123",
      "channel": "weather-chat"
    }
  }'
```

### Get System Status

Retrieve the overall system status and component health.

**Endpoint:** `GET /api/v1/status`  
**Permission Required:** `read`

#### Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "components": {
    "system1": {
      "status": "healthy",
      "details": {
        "avatar_state": "idle",
        "last_activity": "2025-01-03T10:25:00Z"
      }
    },
    "system2": {
      "status": "healthy",
      "active_agents": 3
    },
    "stimuli_flow": {
      "status": "healthy"
    },
    "decision_flow": {
      "status": "healthy"
    }
  },
  "active_requests": 2,
  "total_processed": 1523,
  "timestamp": "2025-01-03T10:30:00Z"
}
```

### Get Stimuli Status

Query the status of a specific stimuli by ID.

**Endpoint:** `GET /api/v1/stimuli/{stimuli_id}/status`  
**Permission Required:** `read`

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| stimuli_id | string | The unique stimuli identifier |

#### Response

```json
{
  "stimuli_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "decision": "AVATAR_AND_ANALYSIS",
  "processing_time": 1.234,
  "created_at": "2025-01-03T10:29:00Z",
  "updated_at": "2025-01-03T10:29:01Z",
  "metadata": {
    "category": "USER_INTERACTION",
    "confidence_scores": {
      "categorization": 0.95,
      "routing": 0.88,
      "context": 0.72
    }
  }
}
```

### Health Check

Basic health check endpoint (no authentication required).

**Endpoint:** `GET /api/v1/health`  
**Permission Required:** None

#### Response

```json
{
  "status": "healthy",
  "checks": {
    "gateway": true,
    "api": true,
    "system1": true,
    "system2": true
  },
  "message": "All systems operational",
  "timestamp": "2025-01-03T10:30:00Z"
}
```

### Prometheus Metrics

Expose metrics for Prometheus scraping (no authentication required).

**Endpoint:** `GET /metrics`  
**Permission Required:** None

#### Response

```text
# HELP graphflow_api_requests_total Total API requests
# TYPE graphflow_api_requests_total counter
graphflow_api_requests_total{method="POST",endpoint="/api/v1/stimuli/submit",status="200"} 1523.0

# HELP graphflow_stimuli_processed_total Total stimuli processed
# TYPE graphflow_stimuli_processed_total counter
graphflow_stimuli_processed_total{category="USER_INTERACTION",decision="AVATAR_AND_ANALYSIS",success="true"} 523.0

# HELP graphflow_processing_time_seconds Processing time histogram
# TYPE graphflow_processing_time_seconds histogram
graphflow_processing_time_seconds_bucket{le="0.5"} 234.0
graphflow_processing_time_seconds_bucket{le="1.0"} 456.0
graphflow_processing_time_seconds_bucket{le="2.0"} 678.0
```

## WebSocket API

### Connection

Connect to the WebSocket endpoint with authentication:

```
ws://localhost:8080/ws/stimuli?token=YOUR_API_KEY
```

### Connection Example

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/stimuli?token=your-api-key');

ws.onopen = () => {
  console.log('Connected to GraphFlow WebSocket');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

### Message Types

#### Connection Established

Sent by server upon successful connection:

```json
{
  "type": "connection_established",
  "message": "Connected as Client Name",
  "timestamp": "2025-01-03T10:30:00Z"
}
```

#### Submit Stimuli

Submit stimuli through WebSocket (requires `write` permission):

```json
{
  "type": "submit_stimuli",
  "data": {
    "content": "Hello from WebSocket",
    "source": "websocket_client",
    "priority": "medium",
    "metadata": {
      "session_id": "ws-session-123"
    }
  }
}
```

#### Stimuli Response

Server response after processing:

```json
{
  "type": "stimuli_response",
  "stimuli_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "data": {
    "decision": "AVATAR_AND_ANALYSIS",
    "processing_time": 1.234,
    "confidence_scores": {
      "categorization": 0.95,
      "routing": 0.88,
      "context": 0.72
    }
  },
  "timestamp": "2025-01-03T10:30:01Z"
}
```

#### Stimuli Update

Broadcast updates about processed stimuli:

```json
{
  "type": "stimuli_update",
  "stimuli_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "status": "completed",
    "decision": "ANALYSIS_ONLY",
    "source": "api_client",
    "processing_time": 0.567
  },
  "timestamp": "2025-01-03T10:30:02Z"
}
```

#### Ping/Pong

Keep connection alive:

```json
// Client sends:
{
  "type": "ping"
}

// Server responds:
{
  "type": "pong",
  "timestamp": "2025-01-03T10:30:00Z"
}
```

#### Error Messages

```json
{
  "type": "error",
  "message": "Invalid message type or insufficient permissions",
  "timestamp": "2025-01-03T10:30:00Z"
}
```

## Error Responses

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input data |
| 401 | Unauthorized - Invalid or missing API key |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable - System not ready |

### Error Response Format

```json
{
  "detail": "Detailed error message",
  "type": "error_type",
  "instance": "/api/v1/stimuli/submit",
  "timestamp": "2025-01-03T10:30:00Z"
}
```

## Rate Limiting

Rate limits are applied per API key based on configuration:

- Default: 100 requests per minute
- Rate limit headers included in responses:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

## Example Integration

### Python Client

```python
import requests
import json

class GraphFlowClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def submit_stimuli(self, content, source, priority="medium", metadata=None):
        url = f"{self.base_url}/api/v1/stimuli/submit"
        payload = {
            "content": content,
            "source": source,
            "priority": priority,
            "metadata": metadata or {}
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_status(self):
        url = f"{self.base_url}/api/v1/status"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

# Usage
client = GraphFlowClient("http://localhost:8080", "your-api-key")
result = client.submit_stimuli(
    content="Process this message",
    source="python_client",
    metadata={"user": "test123"}
)
print(f"Stimuli ID: {result['stimuli_id']}")
```

### JavaScript/Node.js Client

```javascript
class GraphFlowClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async submitStimuli(content, source, priority = 'medium', metadata = {}) {
    const response = await fetch(`${this.baseUrl}/api/v1/stimuli/submit`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        content,
        source,
        priority,
        metadata
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  connectWebSocket() {
    const ws = new WebSocket(`${this.baseUrl.replace('http', 'ws')}/ws/stimuli?token=${this.apiKey}`);
    
    ws.on('open', () => {
      console.log('Connected to GraphFlow');
    });

    ws.on('message', (data) => {
      const message = JSON.parse(data);
      console.log('Received:', message);
    });

    return ws;
  }
}

// Usage
const client = new GraphFlowClient('http://localhost:8080', 'your-api-key');
const result = await client.submitStimuli(
  'Process this message',
  'nodejs_client',
  'medium',
  { user: 'test123' }
);
console.log(`Stimuli ID: ${result.stimuli_id}`);
```