# S2 API Reference

## Base URL
```
http://localhost:8200
```

## Authentication
No authentication required for local development. Production deployments should implement proper authentication.

## Endpoints

### Stimuli Processing

#### POST /api/stimuli/receive
Submit stimuli for processing by S2 teams.

**Request Body**:
```json
{
  "stimuli_id": "string",          // Unique identifier for the stimuli
  "content": "string",             // Content of the stimuli
  "source": "string",              // Source of the stimuli (e.g., 'admin_console', 'api_test')
  "priority": "string",            // Priority level: low, medium, high, critical, emergency
  "category": "string",            // Optional: Stimuli category
  "confidence": 0.95,              // Optional: Confidence score (0-1)
  "metadata": {}                   // Optional: Additional metadata
}
```

**Response**:
```json
{
  "success": true,
  "stimuli_id": "string",
  "processing_time": 0.000237,
  "tools_triggered": ["market_data", "trading_analysis"],
  "agent_decision": "queued_for_s2_processing",
  "response_content": "string",
  "error_message": null,
  "timestamp": "2025-07-13T13:44:38.559196"
}
```

**Example**:
```bash
curl -X POST http://localhost:8200/api/stimuli/receive \
  -H "Content-Type: application/json" \
  -d '{
    "stimuli_id": "test_123",
    "content": "Analyze AAPL stock and assess risk for $10000 investment",
    "source": "api_test",
    "priority": "high"
  }'
```

### System Status

#### GET /api/stimuli/status
Get current status of the stimuli orchestrator.

**Response**:
```json
{
  "autonomous_state": "running",
  "current_stimuli": null,
  "statistics": {
    "total_received": 6,
    "total_queued": 6,
    "total_errors": 0,
    "start_time": "2025-07-13T13:34:06.421166"
  },
  "queue_size": 0,
  "uptime": "N/A"
}
```

**Example**:
```bash
curl -s http://localhost:8200/api/stimuli/status | jq '.'
```

### Tool Management

#### GET /api/stimuli/tools
List all available tools across all teams.

**Response**:
```json
{
  "total_tools": 12,
  "teams": {
    "trader": 6,
    "educator": 3,
    "streamer": 6
  },
  "tool_details": {
    "market_data": {
      "description": "Retrieve market data and basic technical analysis",
      "parameters": 3,
      "required_params": ["symbol"],
      "teams": ["trader"]
    },
    // ... other tools
  }
}
```

**Example**:
```bash
curl -s http://localhost:8200/api/stimuli/tools | jq '.tool_details'
```

### Queue Management

#### GET /api/queue/health
Check queue health status.

**Response**:
```json
{
  "status": "healthy",
  "queue_size": 0,
  "processing_rate": "normal",
  "last_processed": "2025-07-13T13:45:30.123456"
}
```

#### POST /api/queue/restart
Restart queue processing.

**Response**:
```json
{
  "success": true,
  "message": "Queue processing restarted",
  "timestamp": "2025-07-13T13:45:30.123456"
}
```

**Example**:
```bash
curl -X POST http://localhost:8200/api/queue/restart
```

### Control Operations

#### POST /api/stimuli/control/pause
Pause autonomous operations.

**Response**:
```json
{
  "success": true,
  "message": "Autonomous mode paused"
}
```

#### POST /api/stimuli/control/resume
Resume autonomous operations.

**Response**:
```json
{
  "success": true,
  "message": "Autonomous mode resumed"
}
```

### Admin Control Panel

#### GET /api/admin/control-panel
Get admin control panel data including operation history and system status.

**Response**:
```json
{
  "timestamp": "2025-07-13T13:45:30.123456",
  "admin_operations": {},
  "s1_characters": {
    "active_character": "default",
    "available_characters": ["demo_teacher", "demo_secretary"]
  },
  "consolidation_stats": {},
  "system_capacity": {},
  "pending_operations": 0,
  "design_note": "Admin operations are processed silently by default. Use 'announce:' prefix for S1 speech output."
}
```

## Response Codes

### Success Codes
- **200 OK**: Request successful
- **202 Accepted**: Stimuli accepted for processing

### Error Codes
- **400 Bad Request**: Invalid request format
- **404 Not Found**: Endpoint not found
- **422 Unprocessable Entity**: Invalid stimuli content
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Orchestrator not initialized

## Error Response Format
```json
{
  "detail": "Error description",
  "status_code": 500,
  "timestamp": "2025-07-13T13:45:30.123456"
}
```

## Rate Limiting
No rate limiting currently implemented. Production deployments should implement appropriate rate limiting.

## WebSocket Support
Currently not available. All communication is HTTP-based.

## Tool Execution Flow

### Request Processing
1. **Validation**: Request format and required fields validated
2. **Routing**: Stimuli routed to appropriate team based on content analysis
3. **Processing**: Team agents process stimuli using available tools
4. **Response**: Results compiled and returned

### Tool Invocation Process
1. **Tool Selection**: AutoGen agents select appropriate tools based on context
2. **Parameter Extraction**: Required parameters extracted from conversation context
3. **Execution**: Tool executed through AutoGen tool bridge
4. **Result Integration**: Tool results integrated into agent conversation

## S2 Event Logging

### Event Types
- `S2_RECEIVED`: Stimuli received by orchestrator
- `S2_PROCESSING_START`: Processing initiated
- `S2_TEAM_START`: Team processing started
- `S2_TOOLS_AVAILABLE`: Tools registered and available
- `S2_TOOL_INVOKED`: Individual tool execution started
- `S2_TOOL_COMPLETED`: Individual tool execution finished
- `S2_INSIGHTS_EXTRACTED`: Analysis and insights extracted
- `S2_TEAM_COMPLETE`: Team processing completed
- `S2_PROCESSING_COMPLETE`: Overall processing completed

### Event Monitoring
```bash
# Monitor all S2 events
docker logs autogen_agent | grep "S2_"

# Monitor specific event type
docker logs autogen_agent | grep "S2_TOOL_INVOKED"

# Real-time monitoring
docker logs -f autogen_agent | grep "S2_"
```

## Integration Examples

### Basic Integration
```python
import requests

def submit_stimuli(content: str, priority: str = "medium"):
    response = requests.post(
        "http://localhost:8200/api/stimuli/receive",
        json={
            "stimuli_id": f"api_{int(time.time())}",
            "content": content,
            "source": "python_client",
            "priority": priority
        }
    )
    return response.json()

# Example usage
result = submit_stimuli("Analyze TSLA stock trends", "high")
print(f"Processing time: {result['processing_time']}s")
print(f"Tools used: {result['tools_triggered']}")
```

### Monitoring Integration
```python
import requests
import time

def monitor_system_health():
    status = requests.get("http://localhost:8200/api/stimuli/status").json()
    tools = requests.get("http://localhost:8200/api/stimuli/tools").json()
    
    return {
        "system_state": status["autonomous_state"],
        "queue_size": status["queue_size"],
        "total_tools": tools["total_tools"],
        "processing_stats": status["statistics"]
    }

# Health check loop
while True:
    health = monitor_system_health()
    print(f"System: {health['system_state']}, Queue: {health['queue_size']}")
    time.sleep(30)
```

## Development Endpoints

### Testing Endpoints
For development and testing purposes, additional endpoints may be available:

#### POST /api/test/tool/{tool_name}
Direct tool testing (development only).

#### GET /api/debug/logs
Get recent system logs (development only).

#### POST /api/debug/reset
Reset system state (development only).

## Future API Extensions

### Planned Features
- **Streaming Responses**: WebSocket support for real-time updates
- **Batch Processing**: Submit multiple stimuli in single request
- **Tool Configuration**: Dynamic tool enabling/disabling
- **Performance Metrics**: Detailed performance analytics
- **Authentication**: JWT-based authentication system
- **Rate Limiting**: Configurable rate limiting
- **Webhooks**: Callback support for completion notifications 