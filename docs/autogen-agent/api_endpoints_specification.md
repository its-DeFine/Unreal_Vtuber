# API Endpoints Specification for UI Development

## Overview

This document provides comprehensive API specifications for building the autonomous agent UI. The system operates across multiple servers with distinct responsibilities, providing extensive monitoring, statistics, and utility endpoints.

## Server Architecture

### Primary Servers
- **AutoGen Agent**: `http://autogen-agent:8000` (Main agent system)
- **GraphFlow Stimuli**: `http://graphflow-gateway:8080` (External stimuli processing)
- **NeuroSync Player**: `http://neurosync:5001` (Avatar/VTuber control)
- **NeuroSync Local**: `http://neurosync-local:5000` (Audio processing & SCB)

## Core Statistics & Monitoring Endpoints

### AutoGen Agent System (Port 8000)

#### Health & System Status
```
GET /health
Response: {
  "status": "healthy",
  "gpu_status": {...},
  "stimuli_processing": true,
  "analytics": {...}
}

GET /api/gpu-status
Response: {
  "gpu_utilization": 45,
  "vram_used": 2048,
  "vram_total": 8192,
  "temperature": 65
}

GET /api/gpu-summary
Response: {
  "summary": "GPU operating normally",
  "uptime": "24h 15m",
  "status": "healthy"
}
```

#### Statistics & Analytics
```
GET /api/statistics/detailed?timeframe=1h&agent_filter=cognitive
Response: {
  "cycles": {...},
  "tools": {...},
  "performance": {...},
  "agents": {...}
}

GET /api/analytics/performance
Response: {
  "average_response_time": 1.2,
  "success_rate": 98.5,
  "tool_usage": {...},
  "memory_usage": {...}
}

GET /api/tools/usage
Response: {
  "tools": [
    {
      "name": "web_search",
      "usage_count": 45,
      "avg_execution_time": 0.8,
      "success_rate": 95.2
    }
  ]
}
```

#### Agent Operations
```
GET /api/agent-learning
Response: {
  "teachable_agents": [...],
  "learning_status": "active",
  "memory_entries": 1234
}

GET /api/persona/status
Response: {
  "current_persona": "helpful_assistant",
  "adaptation_level": "high",
  "context_awareness": true
}
```

#### Semantic Graph Integration
```
GET /api/semantic-map/status
Response: {
  "neo4j_status": "connected",
  "graph_size": 5432,
  "consolidation_status": "running"
}

GET /api/semantic-map/metrics
Response: {
  "nodes": 5432,
  "relationships": 12890,
  "graph_density": 0.45,
  "centrality_metrics": {...}
}

POST /api/semantic-map/search
Body: {
  "query": "programming concepts",
  "limit": 10
}
Response: {
  "results": [...],
  "total_count": 45
}

GET /api/semantic-map/export?format=d3js
Response: {
  "nodes": [...],
  "links": [...],
  "metadata": {...}
}
```

#### Goal Management
```
POST /api/goals/create
Body: {
  "title": "Improve response time",
  "description": "Reduce average response time by 20%",
  "target_date": "2024-01-15"
}

POST /api/goals/progress
Body: {
  "goal_id": "goal_123",
  "progress": 65,
  "notes": "Optimization in progress"
}
```

#### Evolution & Code Analysis
```
POST /api/evolution/analyze
Body: {
  "code_snippet": "...",
  "analysis_type": "performance"
}

GET /api/evolution/history?limit=50
Response: {
  "changes": [
    {
      "timestamp": "2024-01-01T10:00:00Z",
      "type": "optimization",
      "impact": "positive",
      "performance_delta": 0.15
    }
  ]
}
```

#### Stimuli Processing
```
POST /api/stimuli/receive
Body: {
  "type": "user_message",
  "content": "Hello, how are you?",
  "priority": "normal"
}

GET /api/stimuli/status
Response: {
  "orchestrator_status": "active",
  "queue_length": 3,
  "processing_rate": 2.5
}

POST /api/stimuli/control/pause
POST /api/stimuli/control/resume
```

#### Memory Management
```
POST /api/memory/store
Body: {
  "content": "Important information to remember",
  "category": "user_preference"
}

POST /api/memory/search
Body: {
  "query": "user preferences",
  "limit": 10
}
```

#### Reports Generation
```
POST /api/reports/generate
Body: {
  "type": "performance_summary",
  "timeframe": "7d",
  "include_charts": true
}
Response: {
  "report_id": "report_123",
  "download_url": "/api/reports/download/report_123"
}
```

### GraphFlow Stimuli System (Port 8080)

#### Stimuli Management
```
POST /api/v1/stimuli/submit
Headers: {
  "X-API-Key": "your-api-key"
}
Body: {
  "content": "External stimuli content",
  "type": "notification",
  "priority": "high"
}

GET /api/v1/stimuli/{stimuli_id}/status
Response: {
  "id": "stimuli_123",
  "status": "processed",
  "result": {...}
}
```

#### System Health
```
GET /api/v1/health
Response: {
  "status": "healthy",
  "uptime": "5d 12h",
  "processed_stimuli": 1234
}

GET /api/v1/status
Response: {
  "authentication": "enabled",
  "rate_limiting": "active",
  "queue_status": {...}
}
```

#### Metrics (Prometheus)
```
GET /metrics
Response: Prometheus format metrics
```

#### WebSocket Integration
```
WebSocket /ws/stimuli
Headers: {
  "X-API-Key": "your-api-key"
}
Messages: {
  "type": "stimuli_update",
  "data": {...}
}
```

### NeuroSync Player (Port 5001)

#### Avatar Control
```
POST /process_text
Body: {
  "text": "Hello, I'm your AI assistant",
  "voice_config": {...}
}

POST /game_control
Body: {
  "action": "wave_hand",
  "parameters": {...}
}

GET /game_control/health
GET /game_control/features
```

#### Character Management
```
GET /character/list
Response: {
  "characters": [
    {
      "id": "char_1",
      "name": "Assistant",
      "voice_model": "neural_voice_1"
    }
  ]
}

GET /character/current
POST /character/switch
POST /character/create
```

#### Reactive API
```
GET /api/v1/reactive/status
Response: {
  "mode": "autonomous",
  "character": "assistant",
  "system_health": "good"
}

POST /api/v1/reactive/mode/switch
Body: {
  "mode": "reactive"
}

POST /api/v1/reactive/event/chat
Body: {
  "message": "Hello",
  "user_id": "user_123"
}
```

### NeuroSync Local (Port 5000)

#### SCB (Shared Cognitive Blackboard)
```
GET /scb/ping
Response: {
  "status": "healthy",
  "uptime": "2d 5h"
}

GET /scb/slice
Response: {
  "summary": {...},
  "recent_events": [...],
  "window_size": 100
}

POST /scb/event
Body: {
  "event_type": "user_interaction",
  "data": {...}
}

POST /scb/directive
Body: {
  "directive": "Prioritize user questions",
  "priority": "high"
}
```

#### Audio Processing
```
POST /audio_to_blendshapes
Body: {
  "audio_data": "base64_encoded_audio",
  "format": "wav"
}
Response: {
  "blendshapes": [...],
  "timing": [...]
}
```

## Proposed Additional Utility Endpoints

### Real-time Dashboard
```
GET /api/dashboard/overview
Response: {
  "active_agents": 5,
  "queue_length": 3,
  "system_load": 0.45,
  "memory_usage": 67
}

WebSocket /ws/dashboard
Messages: {
  "type": "system_update",
  "data": {...}
}
```

### Agent Management
```
POST /api/agents/restart
Body: {
  "agent_id": "cognitive_agent"
}

POST /api/agents/pause
POST /api/agents/resume

GET /api/agents/logs/{agent_id}?limit=100
Response: {
  "logs": [...],
  "total_count": 1234
}
```

### System Administration
```
POST /api/admin/backup
Response: {
  "backup_id": "backup_123",
  "status": "in_progress"
}

POST /api/admin/restore
Body: {
  "backup_id": "backup_123"
}

GET /api/admin/logs?level=error&limit=50
Response: {
  "logs": [...],
  "filters_applied": {...}
}

POST /api/admin/maintenance
Body: {
  "enabled": true,
  "message": "System maintenance in progress"
}
```

### Resource Management
```
GET /api/resources/usage
Response: {
  "cpu_usage": 45.2,
  "memory_usage": 67.8,
  "disk_usage": 23.1,
  "gpu_usage": 89.5
}

POST /api/resources/cleanup
Response: {
  "cleaned_items": 45,
  "freed_space": "1.2GB"
}
```

### Configuration Management
```
GET /api/config/current
Response: {
  "agent_config": {...},
  "system_config": {...},
  "ui_config": {...}
}

POST /api/config/update
Body: {
  "section": "agent_config",
  "updates": {...}
}

POST /api/config/validate
Body: {
  "config": {...}
}
Response: {
  "valid": true,
  "warnings": [...],
  "errors": [...]
}
```

## Authentication & Security

### API Keys
- GraphFlow endpoints require `X-API-Key` header
- Other endpoints currently open (consider adding authentication)

### Rate Limiting
- GraphFlow has built-in rate limiting
- Implement rate limiting for other endpoints as needed

### CORS Configuration
- Configure CORS headers for web UI integration
- Allow specific origins for production deployment

## WebSocket Integration

### Real-time Updates
```javascript
// Dashboard updates
const ws = new WebSocket('ws://autogen-agent:8000/ws/dashboard');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  // Handle real-time updates
};

// Stimuli processing
const stimuliWs = new WebSocket('ws://graphflow-gateway:8080/ws/stimuli');
stimuliWs.onmessage = (event) => {
  const stimuliUpdate = JSON.parse(event.data);
  // Handle stimuli updates
};
```

## Error Handling

### Standard Error Response Format
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid request parameters",
    "details": {...}
  }
}
```

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `429`: Too Many Requests
- `500`: Internal Server Error

## Implementation Notes

1. **Existing Infrastructure**: The system already has comprehensive monitoring and statistics collection
2. **Database Integration**: PostgreSQL for persistence, Redis for caching, Neo4j for semantic data
3. **Monitoring Stack**: Prometheus/Grafana integration available
4. **Scalability**: Designed for concurrent multi-agent operations
5. **Real-time Features**: WebSocket support for live updates

This specification provides the foundation for building a comprehensive UI that can monitor, control, and interact with the autonomous agent system effectively.