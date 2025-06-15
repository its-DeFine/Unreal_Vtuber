# Configurable Capability Tester

This document explains how to use the configurable capability testing system for Livepeer Gateway.

## Overview

The system provides:
1. **GPU Check Capability** - Server-side capability that checks GPU status, compute capability, memory usage, and utilization
2. **Configurable Test Script** - Client-side script that sends x packets for y different capabilities every z seconds
3. **Comprehensive Logging** - Detailed statistics and performance tracking

## Server-Side Capabilities

### GPU Check Capability

The server now supports a GPU check capability that returns comprehensive GPU information:

```json
{
  "status": "success",
  "timestamp": 1234567890.123,
  "gpu_count": 1,
  "devices": {
    "0": {
      "device_id": 0,
      "uuid": "GPU-12345678-1234-1234-1234-123456789012",
      "name": "NVIDIA RTX 4090",
      "memory": {
        "total_bytes": 17179869184,
        "free_bytes": 15179869184,
        "used_bytes": 2000000000,
        "usage_percentage": 11.64
      },
      "compute_capability": {
        "major": 8,
        "minor": 9,
        "version": "8.9"
      },
      "utilization": {
        "gpu_percent": 15,
        "memory_percent": 8
      }
    }
  },
  "system_info": {
    "capability": "gpu-check",
    "version": "1.0",
    "routed_via": "agent-net"
  }
}
```

### Available Capabilities

1. **text-to-image** - Text-to-image generation (echo mode)
2. **prompt-enhance** - Prompt enhancement (echo mode)  
3. **gpu-check** - GPU status and information checking

## Client-Side Testing

### Configurable Capability Tester

Use the `configurable_capability_tester.py` script to send configurable requests:

```bash
# Basic usage: 5 packets, 2 capabilities, every 10 seconds
./configurable_capability_tester.py -x 5 -y text-to-image gpu-check -z 10

# All capabilities every 30 seconds
./configurable_capability_tester.py -x 10 -y text-to-image prompt-enhance gpu-check -z 30

# Quick GPU check test
./configurable_capability_tester.py -x 3 -y gpu-check -z 5
```

#### Parameters

- `-x, --packets`: Number of packets to send per cycle (default: 5)
- `-y, --capabilities`: List of capabilities to test (choices: text-to-image, prompt-enhance, gpu-check)
- `-z, --interval`: Interval between cycles in seconds (default: 10)

### Simple GPU Test

Use the `test_gpu_capability.py` script for a quick GPU capability test:

```bash
./test_gpu_capability.py
```

## Example Usage

### Example 1: Load Testing Multiple Capabilities

```bash
# Send 20 packets across all capabilities every 15 seconds
./configurable_capability_tester.py -x 20 -y text-to-image prompt-enhance gpu-check -z 15
```

Output:
```
🎯 CONFIGURABLE CAPABILITY TESTER STARTED
📦 Packets per cycle: 20
🎪 Capabilities: text-to-image, prompt-enhance, gpu-check
⏰ Interval: 15 seconds
🚀 Starting at: 2024-01-15 14:30:25
================================================================================

🚀 Cycle 1 - Sending 20 packets across 3 capabilities
📅 Time: 2024-01-15 14:30:25
  ✅ text-to-image: 200 (1234ms)
  ✅ gpu-check: 200 (567ms)
  ✅ prompt-enhance: 200 (890ms)
  ...

📊 STATISTICS SUMMARY (After 1 cycles)
================================================================================
🕐 Total Runtime: 3.2s
🔄 Cycles Completed: 1
⚡ Avg Time Between Cycles: 3.2s

🎯 TEXT-TO-IMAGE
----------------------------------------
  📤 Total Requests: 7
  ✅ Successful: 7
  ❌ Failed: 0
  📈 Success Rate: 100.00%
  ⏱️  Avg Response Time: 1150.25ms
  🏃 Min/Max: 1023.45ms / 1278.90ms
  📊 Status Codes: {200: 7}
```

### Example 2: GPU-Only Monitoring

```bash
# Monitor GPU every 5 seconds with 1 request per cycle
./configurable_capability_tester.py -x 1 -y gpu-check -z 5
```

### Example 3: High-Frequency Testing

```bash
# Send 50 packets every 2 seconds for stress testing
./configurable_capability_tester.py -x 50 -y text-to-image gpu-check -z 2
```

## Features

### Statistics Tracking
- Total requests per capability
- Success/failure rates
- Response time statistics (min, max, average)
- Status code distribution
- Recent error tracking

### Parallel Processing
- Uses ThreadPoolExecutor for concurrent requests
- Configurable worker limits
- Timeout handling

### Signal Handling
- Graceful shutdown on Ctrl+C
- Final statistics display
- Proper cleanup

### Flexible Configuration
- Support for any combination of capabilities
- Configurable packet counts and intervals
- Extensible capability definitions

## Docker Integration

To test with Docker containers:

1. **Start the service:**
```bash
cd livepeer-app-pipelines/image-gen
docker-compose up -d
```

2. **Run tests:**
```bash
# Wait for services to be ready
sleep 10

# Run GPU capability test
./test_gpu_capability.py

# Run configurable load test
./configurable_capability_tester.py -x 10 -y gpu-check text-to-image -z 15
```

3. **Monitor logs:**
```bash
# Watch worker logs
docker-compose logs -f worker

# Watch gateway logs  
docker-compose logs -f gateway
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure the gateway is running on port 8088
2. **GPU Check Fails**: Verify NVIDIA drivers and hardware
3. **Timeout Errors**: Increase timeout in capability config
4. **Memory Issues**: Reduce packet count for high-frequency tests

### Debug Mode

Add logging to see detailed request/response data:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

Verify service health:
```bash
curl http://localhost:8088/health
curl http://localhost:9876/health
```

## Advanced Configuration

### Custom Capabilities

Add new capabilities to `CAPABILITIES` dict in `configurable_capability_tester.py`:

```python
"my-custom-capability": {
    "endpoint": "http://localhost:8088/gateway/process/request/agent-net",
    "capability_name": "agent-net",
    "run_command": "agent-net", 
    "payload_generator": lambda: {
        "action": "my-custom-action",
        "param1": "value1"
    }
}
```

### Performance Tuning

- Adjust `ThreadPoolExecutor` max_workers for concurrency
- Modify timeout values for slow operations
- Use shorter intervals for real-time monitoring
- Increase packet counts for load testing

## Logs and Monitoring

The system provides comprehensive logging with emojis for easy visual scanning:

- 🚀 Cycle start
- ✅ Successful requests  
- ❌ Failed requests
- 📊 Statistics summaries
- ⏰ Timing information
- 🎯 Capability-specific data

Use these logs to monitor system performance and identify issues. 