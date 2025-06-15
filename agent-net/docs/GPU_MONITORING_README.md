# GPU Uptime Monitoring System

## Overview

The GPU Uptime Monitoring System is designed to ensure orchestrator machines on the Livepeer Network maintain high GPU availability for AI agent jobs. It implements a sophisticated payment delay mechanism that penalizes nodes with poor GPU uptime while providing recovery paths for temporary issues.

## Key Features

### 1. Multi-Window Uptime Tracking
- **Short-term (5 minutes)**: Catches immediate GPU issues
- **Medium-term (30 minutes)**: Identifies sustained problems
- **Long-term (2 hours)**: Ensures consistent performance

### 2. Smart Payment Delays
- Base delay: 10x normal payment interval for first failure
- Escalating delays: 1.5x multiplier for consecutive failures
- Maximum delay cap: 100x to prevent indefinite delays
- Automatic recovery when uptime improves

### 3. Comprehensive Health Checks
- VRAM availability (minimum 30GB required)
- GPU utilization monitoring
- Memory utilization tracking
- Temperature monitoring (when available)
- Free memory checks

### 4. Real-time Observability
- `/gpu/uptime` - Current uptime status across all windows
- `/gpu/payment-delays` - Active payment delays summary
- `/gpu/monitoring/summary` - Complete monitoring overview
- `/gpu/check-payment-delay` - Test payment delay logic

## Configuration

All settings are configurable via environment variables:

### Uptime Thresholds
```bash
GPU_SHORT_TERM_UPTIME_THRESHOLD=99.0    # Short-term window threshold (%)
GPU_MEDIUM_TERM_UPTIME_THRESHOLD=99.0   # Medium-term window threshold (%)
GPU_LONG_TERM_UPTIME_THRESHOLD=99.0     # Long-term window threshold (%)
```

### Time Windows
```bash
GPU_SHORT_TERM_WINDOW=300               # 5 minutes
GPU_MEDIUM_TERM_WINDOW=1800             # 30 minutes
GPU_LONG_TERM_WINDOW=7200               # 2 hours
```

### Payment Delays
```bash
GPU_BASE_DELAY_MULTIPLIER=10.0          # Base delay multiplier
GPU_MAX_DELAY_MULTIPLIER=100.0          # Maximum delay multiplier
GPU_DELAY_ESCALATION_FACTOR=1.5         # Escalation factor for consecutive failures
```

### Health Thresholds
```bash
GPU_MIN_VRAM_GB=30.0                    # Minimum VRAM required (GB)
GPU_MAX_GPU_UTILIZATION=95.0            # Maximum GPU utilization (%)
GPU_MAX_MEMORY_UTILIZATION=95.0         # Maximum memory utilization (%)
GPU_MAX_TEMPERATURE=85.0                # Maximum temperature (°C)
GPU_MIN_FREE_MEMORY_MB=1024.0           # Minimum free memory (MB)
```

### Monitoring Settings
```bash
GPU_HEALTH_CHECK_INTERVAL=5             # Health check interval (seconds)
GPU_STATUS_REPORT_INTERVAL=60           # Status report interval (seconds)
GPU_PERSISTENCE_FILE=gpu_monitoring_data.json  # Data persistence file
GPU_ENABLE_DETAILED_LOGGING=false       # Enable detailed logging
```

### Alert Thresholds
```bash
GPU_ALERT_CONSECUTIVE_FAILURES=3        # Alert after N consecutive failures
GPU_ALERT_UPTIME_BELOW=95.0            # Alert when uptime drops below (%)
```

## How It Works

### 1. Continuous Monitoring
The system continuously monitors GPU health every 5 seconds (configurable), recording:
- GPU and memory utilization
- Available VRAM
- Temperature and power metrics (when available)
- Overall health status

### 2. Uptime Calculation
For each time window, the system calculates:
```
Uptime % = (Healthy Samples / Total Samples) × 100
```

A GPU is considered healthy when it meets all configured thresholds.

### 3. Payment Delay Logic

When a capability request arrives:

1. **Check Uptime**: System checks if uptime meets thresholds in all windows
2. **Calculate Delay**: If uptime is low:
   - First failure: `delay = base_duration × 10`
   - Subsequent failures: `delay = previous_delay × 1.5`
   - Capped at maximum multiplier (100x)
3. **Apply Delay**: Request returns 429 with retry information
4. **Recovery**: When uptime improves, delays are automatically cleared

### 4. Health Status Levels

- **HEALTHY**: All uptime windows meet thresholds
- **DEGRADED**: Only short-term window below threshold
- **UNHEALTHY**: Multiple windows below threshold
- **UNKNOWN**: Insufficient data

## API Endpoints

### GET /gpu/uptime
Returns current GPU uptime status across all time windows.

```json
{
  "timestamp": 1234567890,
  "overall_status": "healthy",
  "uptime_summary": {
    "short": {
      "uptime_percentage": 99.5,
      "is_full": true,
      "samples": 60
    },
    "medium": {
      "uptime_percentage": 99.8,
      "is_full": true,
      "samples": 360
    },
    "long": {
      "uptime_percentage": 99.9,
      "is_full": false,
      "samples": 500
    }
  },
  "alerts": []
}
```

### GET /gpu/payment-delays
Returns active payment delays for all capabilities.

```json
{
  "timestamp": 1234567890,
  "active_delays_count": 1,
  "active_delays": [
    {
      "capability": "text-to-image",
      "delay_seconds": 300,
      "multiplier": 10,
      "consecutive_failures": 1,
      "can_call_now": false,
      "wait_time": 250
    }
  ]
}
```

### POST /gpu/check-payment-delay
Test if a request would be delayed.

Request:
```json
{
  "capability": "text-to-image",
  "request_id": "req_123"
}
```

Response:
```json
{
  "can_process": false,
  "wait_time_seconds": 250,
  "reason": "Low uptime detected: short-term: 95.2% < 99%"
}
```

## Testing

Use the provided test script to verify the monitoring system:

```bash
# Basic status check
python scripts/test_gpu_monitoring.py

# Simulate GPU degradation
python scripts/test_gpu_monitoring.py --simulate-degradation

# Continuous monitoring
python scripts/test_gpu_monitoring.py --continuous --interval 5
```

## Integration with Livepeer

The system integrates seamlessly with Livepeer's orchestrator/gateway architecture:

1. **Request Processing**: Payment delays are checked before processing capabilities
2. **HTTP 429 Response**: Delayed requests return proper retry information
3. **Recovery Path**: Orchestrators can recover by maintaining good uptime
4. **Observability**: Operators can monitor GPU health and payment efficiency

## Best Practices

1. **Set Realistic Thresholds**: 99% uptime allows for brief maintenance windows
2. **Monitor Alerts**: Watch for consecutive failure alerts
3. **Plan Maintenance**: Schedule updates during low-traffic periods
4. **Monitor Temperatures**: High temperatures often precede failures
5. **Check VRAM Usage**: Ensure sufficient VRAM headroom

## Troubleshooting

### High Payment Delays
- Check GPU utilization and temperature
- Verify VRAM availability
- Review system logs for errors
- Consider adjusting thresholds if too strict

### False Positives
- Ensure monitoring interval aligns with workload patterns
- Check for brief spikes vs sustained issues
- Adjust health thresholds if needed

### Recovery Issues
- Verify GPU health has actually improved
- Check persistence file for stuck states
- Review escalation factor settings

## Architecture

```
┌─────────────────────┐
│   FastAPI Server    │
├─────────────────────┤
│  GPU Monitoring     │
│  ┌───────────────┐  │
│  │ Uptime Tracker│  │──► Multi-window tracking
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │Health Monitor │  │──► Continuous monitoring
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │Payment Manager│  │──► Delay logic
│  └───────────────┘  │
├─────────────────────┤
│  Hardware Info      │──► NVML GPU access
└─────────────────────┘
```

## Future Enhancements

1. **Predictive Alerts**: ML-based failure prediction
2. **Network-wide Analytics**: Aggregate fleet health metrics
3. **Dynamic Thresholds**: Auto-adjust based on network conditions
4. **Payment Integration**: Direct on-chain payment delays
5. **Multi-GPU Support**: Enhanced multi-GPU orchestrator support