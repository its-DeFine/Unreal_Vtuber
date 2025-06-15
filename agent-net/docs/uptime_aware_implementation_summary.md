# Uptime-Aware Job Runner Implementation Summary

## Overview

This document summarizes the complete implementation of the client-side punishment logic for the Livepeer BYOC GPU pipeline monitoring system. The system adjusts job submission rates based on agent GPU uptime to ensure efficient resource utilization and payment management.

## Architecture

### Component Separation

1. **Agent Containers (Monitoring Only)**
   - Run `AgentSelfMonitor` to track GPU availability
   - Expose `/agent/uptime-since-last-ping` endpoint
   - NO punishment or payment logic
   - Pure data collection and reporting

2. **Ping Monitoring System (Coordination Only)**
   - Pings agents at dynamic intervals
   - Records uptime history
   - Provides API for uptime queries
   - NO job scheduling decisions

3. **Job Runner Client (Business Logic)**
   - `uptime_aware_capability_tester.py` - Implements punishment logic
   - Queries ping system for agent uptime
   - Calculates job rates based on uptime thresholds
   - Controls job submission to gateway

## Key Components

### 1. Uptime-Aware Capability Tester
**File**: `scripts/single-orch/uptime_aware_capability_tester.py`

**Features**:
- Asynchronous uptime monitoring
- Dynamic job rate calculation
- Real-time statistics tracking
- Multiple capability support

**Punishment Strategy**:
```
99%+ uptime  → 100% job rate (base rate)
95-99% uptime → 50% job rate  
90-95% uptime → 10% job rate
<90% uptime   → 0% job rate (full punishment)
```

### 2. Agent Uptime Query Flow

```python
async def get_agent_uptime(self) -> Optional[UptimeInfo]:
    # 1. Query ping system for agent list
    GET /ping-system/agents
    
    # 2. Find target agent in list
    
    # 3. Get detailed history
    GET /ping-system/agents/{agent_id}/history?hours=1
    
    # 4. Calculate average uptime from recent pings
    
    # 5. Return UptimeInfo object
```

### 3. Job Rate Adjustment

```python
def calculate_job_rate(self, uptime_percent: float) -> int:
    if uptime_percent >= 99.0:
        return self.base_jobs_per_minute
    elif uptime_percent >= 95.0:
        return int(self.base_jobs_per_minute * 0.5)
    elif uptime_percent >= 90.0:
        return int(self.base_jobs_per_minute * 0.1)
    else:
        return 0
```

## Usage

### Basic Usage

```bash
# Test with 60 jobs/min base rate for agent-001
python uptime_aware_capability_tester.py --agent agent-001 --rate 60

# Test multiple capabilities
python uptime_aware_capability_tester.py \
    --agent agent-001 \
    --rate 30 \
    --capabilities gpu-check text-to-image \
    --ping-url http://localhost:8000

# Frequent uptime checks (every 10 seconds)
python uptime_aware_capability_tester.py \
    --agent agent-001 \
    --rate 60 \
    --uptime-interval 10
```

### Command Line Options

- `--agent`: Target agent ID to monitor (required)
- `--rate`: Base jobs per minute for 99%+ uptime (default: 60)
- `--capabilities`: List of capabilities to test
- `--ping-url`: Ping monitoring system URL
- `--gateway-url`: Livepeer gateway URL
- `--uptime-interval`: How often to query uptime in seconds

## Integration with Existing System

### 1. Compatible with configurable_capability_tester.py

The uptime-aware tester extends the existing capability tester with:
- Same capability definitions
- Same Livepeer header format
- Same request/response handling
- Added uptime monitoring layer

### 2. Works with Mock Testing

```bash
# Run with mock ping monitoring
python scripts/test_ping_monitoring_mock.py

# Run uptime-aware tester against mock
python uptime_aware_capability_tester.py \
    --agent agent-001 \
    --ping-url http://localhost:8888
```

### 3. Production Deployment

```bash
# 1. Ensure ping monitoring system is running
python server/server.py  # Monitoring mode

# 2. Ensure agents are running with self-monitoring
AGENT_MODE=true AGENT_ID=agent-001 python server/server.py

# 3. Start ping orchestrator
python scripts/ping_system.py --server-url http://localhost:8000

# 4. Run uptime-aware job runner
python scripts/single-orch/uptime_aware_capability_tester.py \
    --agent agent-001 \
    --rate 60 \
    --ping-url http://localhost:8000 \
    --gateway-url http://your-gateway:8088
```

## Statistics and Monitoring

### Real-time Output

The tester provides real-time feedback:
```
✅ [14:32:15] gpu-check: 200 (45ms) | Rate: 60/min | Uptime: 99.5%
✅ [14:32:16] gpu-check: 200 (52ms) | Rate: 60/min | Uptime: 99.5%
📊 Job rate changed: 60 → 30 jobs/min
   Uptime: 96.2%
```

### Detailed Statistics

Every 50 requests, detailed statistics are displayed:
```
📊 STATISTICS SUMMARY
=====================================
🕐 Total Runtime: 120.5s
📤 Total Jobs Sent: 95
⚡ Current Job Rate: 30 jobs/min

🖥️  AGENT STATUS
-----------------------------------------
  🆔 Agent ID: agent-001
  📈 Uptime: 96.25%
  ⚠️  Consecutive Poor: 0
  ⏱️  Ping Interval: 15 min
  📊 Total Pings: 8

🎯 GPU-CHECK
-----------------------------------------
  📤 Total Attempts: 95
  ✅ Successful: 93
  ❌ Failed: 2
  ⏳ Delayed (Punished): 25
  📈 Success Rate: 97.89%
  ⏱️  Avg Response Time: 48.3ms
  🏃 Min/Max: 35.2ms / 125.6ms
  📊 Status Codes: {200: 93, 500: 2}
```

## Benefits

1. **Efficient Resource Utilization**
   - No wasted jobs on poorly performing agents
   - Automatic recovery when agents improve

2. **Fair Payment Distribution**
   - Agents maintaining high uptime receive full payment
   - Poor performers receive reduced or no payment

3. **System Stability**
   - Prevents overloading of degraded agents
   - Maintains overall system reliability

4. **Transparency**
   - Clear punishment thresholds
   - Real-time monitoring and feedback
   - Detailed statistics for analysis

## Testing

### Unit Testing
```bash
# Test uptime query logic
pytest tests/test_uptime_aware_runner.py::test_uptime_query

# Test job rate calculation
pytest tests/test_uptime_aware_runner.py::test_job_rate_calculation

# Test punishment application
pytest tests/test_uptime_aware_runner.py::test_punishment_logic
```

### Integration Testing
```bash
# Run demo with mock agents
python scripts/demo_uptime_aware_testing.py

# Test with real ping system
python scripts/test_e2e_punishment_flow.py
```

## Future Enhancements

1. **Configurable Punishment Thresholds**
   - Allow custom uptime thresholds via config
   - Support different punishment strategies

2. **Historical Analysis**
   - Track punishment effectiveness over time
   - Optimize thresholds based on data

3. **Multi-Agent Support**
   - Monitor multiple agents simultaneously
   - Distribute jobs based on relative performance

4. **Advanced Metrics**
   - Cost analysis (jobs sent vs payment)
   - ROI calculations per agent
   - Predictive uptime modeling