# 🎛️ Client Activation Control Guide

## Overview

The AutoGen autonomous agent system now features **conditional client activation** to provide precise control over when external services are accessed:

- **🎭 VTuber Client**: Only sends messages when explicitly activated via tool
- **🔗 SCB Client**: Only publishes state when AgentNet is enabled

## 🎭 VTuber Control System

### Default Behavior
- **VTuber is DISABLED by default** for autonomous cycles
- Messages are logged only, not sent to VTuber endpoint
- Must be explicitly activated to send messages

### Activation Methods

#### 1. Via Advanced VTuber Control Tool
```python
# Tool context for activation
context = {
    "control_vtuber_instance": True,
    "vtuber_action": "activate",
    "message": "Hello viewers!",  # Optional
    "duration_minutes": 30        # Optional
}
```

#### 2. Via API Endpoint
```bash
# Activate VTuber
curl "http://localhost:8000/vtuber/control?action=activate&message=Hello&duration=30"

# Send message (bypasses activation check)
curl "http://localhost:8000/vtuber/control?action=send_message&message=Special announcement"

# Deactivate VTuber
curl "http://localhost:8000/vtuber/control?action=deactivate"

# Check status
curl "http://localhost:8000/vtuber/control?action=status"
```

### Available Actions
- `activate`: Enable VTuber message sending
- `deactivate`: Disable VTuber message sending
- `send_message`: Send specific message (bypasses activation check)
- `status`: Check current VTuber activation status

### Client Methods
```python
# Programmatic control
vtuber_client.activate_vtuber()
vtuber_client.deactivate_vtuber() 
vtuber_client.is_vtuber_activated()
vtuber_client.post_message("msg", force_send=True)  # Bypass activation
```

## 🔗 SCB/AgentNet Control System

### Default Behavior
- **AgentNet is DISABLED by default** (`AGENTNET_ENABLED=false`)
- State updates are logged only, not published to Redis
- Must be explicitly enabled to publish state

### Environment Configuration
```bash
# Enable AgentNet
AGENTNET_ENABLED=true

# Disable AgentNet (default)
AGENTNET_ENABLED=false
```

### Activation Methods

#### 1. Via API Endpoint
```bash
# Enable AgentNet
curl "http://localhost:8000/scb/control?action=enable"

# Disable AgentNet
curl "http://localhost:8000/scb/control?action=disable"

# Check status
curl "http://localhost:8000/scb/control?action=status"
```

#### 2. Programmatic Control
```python
# Enable/disable AgentNet
scb_client.enable_agentnet()
scb_client.disable_agentnet()
scb_client.is_agentnet_enabled()
scb_client.publish_state(data, force_publish=True)  # Bypass activation
```

## 📋 Current Status Check

### VTuber Status
```python
status = vtuber_client.get_status()
# Returns: {"enabled": bool, "activated": bool, "endpoint": str}
```

### SCB Status
```python
status = scb_client.get_status()
# Returns: {"enabled": bool, "agentnet_enabled": bool, "redis_connected": bool, "url": str}
```

### System Health Check
```bash
curl "http://localhost:8000/health"
```

## 🔧 Implementation Details

### Message Flow Control

#### VTuber Messages
```python
# Autonomous cycles - respects activation state
vtuber.post_message(message)  # Only sends if activated

# Tool-initiated messages - bypasses activation
vtuber.post_message(message, force_send=True)  # Always sends
```

#### SCB State Updates
```python
# Autonomous cycles - respects AgentNet state
scb.publish_state(state)  # Only publishes if AgentNet enabled

# Critical state updates - bypasses activation
scb.publish_state(state, force_publish=True)  # Always publishes
```

### Standalone Mode Behavior
When services are not available (standalone mode):
- **VTuber**: Messages logged with activation status
- **SCB**: State logged with AgentNet status
- No network calls attempted

## 🎯 Use Cases

### Development Mode
- Keep both VTuber and AgentNet disabled
- Focus on core autonomous logic
- Avoid external service dependencies

### Testing Mode
- Enable VTuber for specific tests via API
- Enable AgentNet for multi-agent coordination tests
- Precise control over service activation

### Production Mode
- Use tool-based VTuber activation for user interactions
- Enable AgentNet for distributed agent networks
- Conditional activation based on user preferences

## 🚨 Important Notes

1. **Default State**: Both VTuber and AgentNet start DISABLED
2. **Autonomous Respect**: Autonomous cycles respect activation states
3. **Tool Override**: Tools can bypass activation with `force_send`/`force_publish`
4. **API Control**: External control via REST endpoints
5. **Environment Config**: AgentNet controlled via `AGENTNET_ENABLED`
6. **Graceful Degradation**: Works in standalone mode without external services

This system provides fine-grained control over when the autonomous agent interacts with external services, enabling focused development and testing scenarios. 