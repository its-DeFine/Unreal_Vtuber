# GPU Ping-Based Monitoring System Guide

## Overview

The GPU Ping-Based Monitoring System enhances the Livepeer BYOC pipeline to support reliable 24/7 autonomous agent hosting. It implements intelligent ping intervals with escalating delays for nodes that fail to maintain adequate GPU uptime.

## Architecture

### Components

1. **PingBasedMonitor** - Core monitoring logic
   - Tracks agent ping history
   - Manages escalating intervals
   - Persists monitoring data

2. **AutonomousAgentRegistry** - Agent management
   - Registers and tracks agents
   - Health checking
   - Agent discovery

3. **AgentSelfMonitor** - Runs inside GPU containers
   - Monitors GPU availability
   - Tracks uptime between pings
   - Reports status when pinged

4. **External Ping System** - Orchestrates pings
   - Schedules pings based on intervals
   - Handles concurrent agent monitoring
   - Provides dashboard interface

## Configuration

### Environment Variables

```bash
# Ping monitoring settings
PING_BASE_INTERVAL_MINUTES=15          # Base ping interval (default: 15)
PING_UPTIME_THRESHOLD=99.0            # Uptime threshold percentage (default: 99%)
PING_ESCALATION_MULTIPLIER=2.0        # Interval multiplier for poor uptime (default: 2x)
PING_MAX_INTERVAL_HOURS=24            # Maximum ping interval (default: 24 hours)
PING_RECOVERY_THRESHOLD_PINGS=3       # Good pings needed to recover (default: 3)
PING_FIRST_PING_GRACE_PERIOD=true     # First ping grace period (default: true)
PING_RESPONSE_TIMEOUT_SECONDS=10      # Ping timeout (default: 10s)
PING_MAX_CONCURRENT_AGENTS=100        # Max concurrent agents (default: 100)

# Agent self-monitoring settings
AGENT_GPU_CHECK_INTERVAL_SECONDS=5    # GPU check interval (default: 5s)
AGENT_MAX_HISTORY_SIZE=10000          # Max history entries (default: 10000)
AGENT_CHECKPOINT_INTERVAL=100         # Checkpoint save interval (default: 100)

# Agent mode settings (for containers running as agents)
AGENT_MODE=true                       # Enable agent mode
AGENT_ID=agent-001                    # Unique agent identifier
```

## API Endpoints

### Ping System Endpoints

#### Register Agent
```bash
POST /ping-system/agents/register
Content-Type: application/json

{
  "agent_id": "agent-001",
  "agent_url": "http://agent-host:8001",
  "capabilities": ["gpu-compute", "image-generation"],
  "metadata": {"gpu_model": "RTX 4090"}
}
```

#### List Agents
```bash
GET /ping-system/agents
```

#### Get Agents Due for Ping
```bash
GET /ping-system/agents/due-for-ping
```

#### Execute Ping
```bash
POST /ping-system/agents/{agent_id}/ping
```

#### Get Agent Ping History
```bash
GET /ping-system/agents/{agent_id}/history?hours=24
```

#### Get Dashboard
```bash
GET /ping-system/dashboard
```

### Agent Endpoints (Inside GPU containers)

#### Report Uptime Since Last Ping
```bash
GET /agent/uptime-since-last-ping
```

#### Get GPU Status
```bash
GET /agent/gpu-status
```

#### Agent Health Check
```bash
GET /agent/health
```

## Usage Examples

### 1. Running the Monitoring Server

```bash
# Standard worker mode (monitoring server)
python server/server.py
```

### 2. Running an Autonomous Agent

```bash
# Agent mode with GPU self-monitoring
AGENT_MODE=true AGENT_ID=agent-001 python server/server.py
```

### 3. Running the External Ping System

```bash
# Start ping orchestrator
python scripts/ping_system.py --server-url http://localhost:8000

# With test agents registration
python scripts/ping_system.py --register-agents --dashboard-interval 30
```

### 4. Viewing the Dashboard

Open `scripts/monitoring_dashboard.html` in a web browser.

## Ping Interval Logic

### First Ping
- Checks GPU existence only
- Always uses base interval (15 minutes)
- No uptime verification

### Subsequent Pings
- Verifies uptime since last ping
- Uptime >= 99%: Base interval maintained
- Uptime < 99%: Interval escalates

### Escalation Formula
```
next_interval = base_interval * (escalation_multiplier ^ consecutive_poor_uptime)
```

### Recovery Process
- Each ping with good uptime reduces consecutive count by 1
- Need 3 consecutive good pings to fully recover
- Returns to base interval when fully recovered

## Testing

### Unit Tests
```bash
pytest tests/test_ping_based_monitoring.py -v
```

### Integration Tests
```bash
# Start monitoring server first
python server/server.py

# In another terminal
pytest tests/test_gpu_pipeline_integration.py -v
```

### Test Coverage
- ✅ First ping GPU existence check
- ✅ Uptime verification between pings
- ✅ Escalating interval calculation
- ✅ Recovery mechanism
- ✅ Concurrent agent support (100+)
- ✅ Ping response time (<500ms)
- ✅ Agent timeout handling

## Monitoring Flow

```
1. Agent Registration
   └─> Agent added to registry
   └─> Initial ping state created

2. First Ping
   └─> External system pings agent
   └─> Agent reports GPU exists/not exists
   └─> Base interval assigned

3. Subsequent Pings
   └─> Agent calculates uptime since last ping
   └─> Reports uptime percentage
   └─> Interval adjusted based on uptime

4. Poor Uptime Detected
   └─> Interval escalates (2x, 4x, 8x...)
   └─> Capped at 24 hours

5. Recovery
   └─> Good uptime reduces escalation
   └─> 3 consecutive good = full recovery
```

## Performance Considerations

- Supports 100+ concurrent agents
- Ping processing < 10ms per agent
- Async operations for scalability
- Persistent state for reliability
- Minimal memory footprint

## Troubleshooting

### Agent Not Receiving Pings
1. Check agent registration status
2. Verify agent URL is accessible
3. Check ping system logs
4. Ensure agent health endpoint responds

### Incorrect Uptime Calculations
1. Verify GPU monitoring is running
2. Check agent checkpoint files
3. Review GPU check interval settings
4. Validate time synchronization

### Escalating Intervals Not Working
1. Check uptime threshold configuration
2. Verify consecutive poor uptime tracking
3. Review ping history for patterns
4. Check recovery threshold settings