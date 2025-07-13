# S1 System Testing Suite

This directory contains comprehensive tests for the S1 (NeuroSync Player) system, covering performance, functionality, and RTMP streaming capabilities.

## Test Structure

```
tests/s1/
├── perf/                    # Performance & Latency Tests
│   ├── test_s1_latency.py          # Core latency benchmark (interrupt mode)
│   └── test_s1_queue_latency.py    # Queue mode latency benchmark
├── functional/              # Functional Feature Tests
│   └── test_s1_speech_control.py   # Speech control API tests
├── rtmp/                    # RTMP Streaming Tests
│   └── test_rtmp_stream.py         # RTMP output verification
└── README.md               # This file
```

## Performance Tests

### Core Latency Test (`test_s1_latency.py`)
- **Purpose**: Measures end-to-end latency from `/process_text` to `S1_WAV_READY`
- **Mode**: Interrupt (default) - new requests flush previous audio
- **Target**: P95 latency < 1.0 seconds
- **Usage**: `python test_s1_latency.py --requests 10 --threshold 1.0`

### Queue Mode Latency Test (`test_s1_queue_latency.py`)
- **Purpose**: Measures latency with sequential processing (no interruption)
- **Mode**: Queue - requests wait for previous to complete
- **Target**: P95 latency < 1.5 seconds (higher due to sequential processing)
- **Usage**: `python test_s1_queue_latency.py --requests 10 --threshold 1.5`

## Functional Tests

### Speech Control Test (`test_s1_speech_control.py`)
- **Purpose**: Validates speech control API functionality
- **Features Tested**:
  - Stop command (flush queues, halt playback)
  - Pause/Resume commands (temporary halt/continue)
  - Invalid command handling
- **Usage**: `python test_s1_speech_control.py --url http://localhost:5001`

## RTMP Tests

### RTMP Stream Test (`test_rtmp_stream.py`)
- **Purpose**: Verifies RTMP output timing and quality
- **Target**: Audio frames appear < 300ms after `S1_WAV_READY`
- **Usage**: `python test_rtmp_stream.py --rtmp-url rtmp://localhost/live/test`

## Interaction Modes

The S1 system supports two interaction modes via the `interaction_mode` parameter:

### Interrupt Mode (Default)
```json
{
  "text": "Hello world",
  "interaction_mode": "interrupt"  // or omit for default
}
```
- New requests immediately flush audio queues
- Current speech stops, new speech begins
- Fastest response time, but may cut off ongoing speech
- Used by core latency benchmark

### Queue Mode
```json
{
  "text": "Hello world", 
  "interaction_mode": "queue"
}
```
- New requests wait for current speech to complete
- Sequential processing ensures all speech completes
- Higher latency but no speech interruption
- Mimics polite human conversation patterns

## Speech Control API

New `/speech/control` endpoint for runtime speech management:

```bash
# Stop current speech (flush all queues)
curl -X POST http://localhost:5001/speech/control \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'

# Pause current playback
curl -X POST http://localhost:5001/speech/control \
  -H "Content-Type: application/json" \
  -d '{"action": "pause"}'

# Resume paused playback  
curl -X POST http://localhost:5001/speech/control \
  -H "Content-Type: application/json" \
  -d '{"action": "resume"}'
```

## Running Tests

### Individual Tests
```bash
# Core latency benchmark
python tests/s1/perf/test_s1_latency.py --requests 10

# Queue mode latency  
python tests/s1/perf/test_s1_queue_latency.py --requests 10

# Speech control functionality
python tests/s1/functional/test_s1_speech_control.py

# RTMP streaming
python tests/s1/rtmp/test_rtmp_stream.py
```

### Batch Testing
```bash
# Run all S1 performance tests
cd tests/s1/perf
python test_s1_latency.py --requests 5
python test_s1_queue_latency.py --requests 5

# Run all functional tests
cd tests/s1/functional  
python test_s1_speech_control.py
```

## Test Results

All tests save results to `logs/s1/` with subdirectories:
- `logs/s1/summaries/` - CSV summaries for performance tests
- `logs/s1/raw/` - Complete JSON results with metadata
- `logs/s1/queue/` - Queue mode specific results
- `logs/s1/functional/` - Functional test results

## Performance Targets

| Test Type | Mode | Target | Description |
|-----------|------|--------|-------------|
| Core Latency | Interrupt | P95 < 1.0s | Fast response, may interrupt |
| Queue Latency | Queue | P95 < 1.5s | Sequential, no interruption |
| RTMP Delay | Both | < 300ms | Stream output after WAV ready |
| Speech Control | N/A | 100% pass | All control commands work |

## Integration with CI/CD

These tests are designed for automated CI/CD pipelines:
- Exit code 0 = success, 1 = failure
- JSON output for parsing by automation tools
- Docker log integration for container environments
- Configurable thresholds for different environments

## Human-Like Speech Patterns

The new interaction modes support human-like conversation patterns:

**Interrupt Mode** - Like urgent interruptions:
- "Actually, let me stop you there..."
- Immediate response, cuts off current speech
- Good for corrections or urgent information

**Queue Mode** - Like polite conversation:
- Wait for current thought to complete
- Then respond with new information
- Maintains conversational flow and context

**Speech Control** - Like natural pauses:
- Stop: "Let me think about that..."
- Pause: "Hold on, someone's at the door"
- Resume: "Okay, where were we?"

This enables more natural, human-like interactions with the VTuber system. 