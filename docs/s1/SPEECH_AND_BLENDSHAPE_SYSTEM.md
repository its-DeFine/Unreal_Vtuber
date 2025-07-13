# S1 Speech and Blendshape System Architecture

## Overview

The S1 (NeuroSync Player) system processes text input and converts it into synchronized audio and facial animations that are streamed via RTMP. This document explains the complete pipeline from text input to audio/visual output.

## System Architecture

```
Text Input → LLM Processing → TTS Generation → Audio Queue → Face Animation → RTMP Stream
     ↓              ↓              ↓             ↓              ↓              ↓
Process Text    Chunk Queue    Audio Bytes   Blendshapes   GStreamer    RTMP Server
```

## Core Components

### 1. Text Processing Pipeline (`llm_to_face.py`)

**Entry Point**: `/process_text` endpoint
- Accepts text input via HTTP POST
- Supports `interaction_mode` parameter:
  - `"interrupt"` (default): New requests flush queues and stop current speech
  - `"queue"`: Sequential processing, requests wait for completion

**Processing Flow**:
1. Text → LLM processing (OpenAI/Ollama/etc.)
2. LLM response → Sentence building
3. Sentences → TTS generation
4. Audio bytes → Audio queue

### 2. Queue System

**Chunk Queue**: Holds text chunks waiting for TTS processing
**Audio Queue**: Holds generated audio bytes waiting for face animation

### 3. TTS (Text-to-Speech) Workers

**Location**: `utils/tts/`
**Supported Providers**:
- ElevenLabs (cloud)
- Kokoro (local)
- OpenAI (cloud)
- Local TTS models

**Process**:
1. Retrieves text chunks from chunk_queue
2. Generates audio bytes using configured TTS provider
3. Queues audio bytes in audio_queue

### 4. Audio Face Workers (`utils/audio_face_workers.py`)

**Primary Function**: `audio_face_queue_worker()`
**Process**:
1. Retrieves audio bytes from audio_queue
2. Saves audio to temporary WAV file
3. Sends audio to blendshape service
4. Calls `run_audio_animation()` with audio path
5. Cleans up temporary files

### 5. Blendshape Generation

**Endpoint**: `/audio_to_blendshapes`
**Process**:
1. Receives audio bytes
2. Analyzes audio for lip-sync data
3. Generates facial animation blendshapes
4. Returns blendshape data for avatar animation

### 6. Audio Streaming (`utils/audio/`)

**Components**:
- `play_audio.py`: Main audio playback coordinator
- `gst_stream.py`: GStreamer RTMP streaming
- `pygame_player.py`: Local playback (deprecated)

**GStreamer Pipeline**:
```
WAV File → audioconvert → audioresample → voaacenc → flvmux → rtmpsink
```

**RTMP Configuration**:
- Target: `rtmp://nginx_rtmp:1935/live/mystream`
- Format: FLV with AAC audio
- Blocking: True (streams entire file)

## Speech Control System

### Control Endpoint: `/speech/control`

**Actions**:
- `"stop"`: Interrupts active speech, flushes all queues
- `"pause"`: Not supported in RTMP mode (returns 400)
- `"resume"`: Not supported in RTMP mode (returns 400)
- `"status"`: Returns current queue sizes and active stream count

**Stop Process**:
1. Flush chunk_queue (stops new TTS generation)
2. Flush audio_queue (stops new face animations)
3. Send EOS (End of Stream) events to active GStreamer pipelines
4. Allow audio threads to complete gracefully
5. Return count of stopped streams

### Pipeline Management

**Active Pipeline Tracking**:
- Global `_active_pipelines` list in `gst_stream.py`
- Thread-safe operations with locks
- Automatic cleanup on completion

**EOS (End of Stream) Handling**:
- Signals GStreamer pipeline to finish current stream
- Allows `bus.timed_pop_filtered()` to exit cleanly
- Prevents thread deadlock during stop operations

## Threading Architecture

### Main Threads

1. **HTTP Server Thread**: Handles `/process_text` and `/speech/control` requests
2. **TTS Worker Threads**: Process chunk_queue → audio generation
3. **Audio Face Worker Thread**: Process audio_queue → face animation
4. **GStreamer Threads**: Handle RTMP streaming (created per audio file)

### Thread Communication

- **Queues**: Thread-safe communication between components
- **Events**: Coordination between processing stages
- **Locks**: Protect shared resources (pipeline list, etc.)

## Configuration

### Environment Variables

```bash
# TTS Provider
TTS_PROVIDER=elevenlabs|kokoro|openai

# Audio Output
AUDIO_OUTPUT_MODE=rtmp|pygame
RTMP_URL=rtmp://nginx_rtmp:1935/live/mystream

# API Keys
ELEVENLABS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

### Provider Configuration

**ElevenLabs**:
- Voice ID configurable
- Streaming support
- Cloud-based processing

**Kokoro**:
- Local processing
- Lower latency
- No API key required

## Performance Characteristics

### Latency Breakdown

1. **LLM Processing**: 1-3 seconds (depends on model/provider)
2. **TTS Generation**: 0.5-2 seconds (depends on provider)
3. **Blendshape Generation**: 0.1-0.5 seconds
4. **Audio Streaming**: Real-time (duration of audio)

### Optimization Features

- **Parallel Processing**: TTS and blendshape generation run concurrently
- **Queue-based Architecture**: Enables streaming and interruption
- **Temporary File Management**: Automatic cleanup prevents disk bloat
- **Connection Pooling**: Reuses HTTP connections for API calls

## Error Handling

### Robust Worker Design

- **Exception Isolation**: Worker threads catch and log errors without dying
- **Graceful Degradation**: System continues operating even if components fail
- **Resource Cleanup**: Temporary files always cleaned up in finally blocks

### Common Issues and Solutions

**TTS API Failures**:
- Automatic retry with exponential backoff
- Fallback to alternative providers
- Error logging for debugging

**GStreamer Pipeline Errors**:
- Pipeline state validation
- Automatic resource cleanup
- EOS handling for graceful shutdown

**Queue Overflow**:
- Configurable queue size limits
- Automatic flushing on overflow
- Memory usage monitoring

## Monitoring and Debugging

### Logging

**Log Levels**:
- INFO: Normal operation events
- WARNING: Recoverable errors
- ERROR: Serious issues requiring attention

**Key Log Messages**:
- `✅ Audio generated successfully`: TTS completion
- `🎵 [GStreamer] Streaming`: Audio streaming start
- `✅ [GStreamer] Audio streaming completed`: Stream completion
- `🛑 Stopped GStreamer pipeline`: Successful interruption

### Health Checks

**System Status**: Check `/speech/control` with `"action": "status"`
**Queue Monitoring**: Returns current queue sizes
**Pipeline Tracking**: Shows active stream count

## Integration Points

### External Services

1. **LLM Providers**: OpenAI, Ollama, Anthropic, etc.
2. **TTS Providers**: ElevenLabs, OpenAI, local models
3. **RTMP Server**: nginx_rtmp for video streaming
4. **Blendshape Service**: Internal facial animation service

### API Endpoints

- `POST /process_text`: Main text processing
- `POST /speech/control`: Speech control operations
- `POST /audio_to_blendshapes`: Facial animation generation
- `GET /health`: System health check

## Future Enhancements

### Planned Features

1. **Real-time Streaming**: Sentence-by-sentence audio streaming
2. **Voice Cloning**: Custom voice model support
3. **Emotion Control**: Emotional tone in TTS and blendshapes
4. **Multi-language**: Support for multiple languages
5. **WebRTC**: Direct browser streaming without RTMP

### Performance Improvements

1. **GPU Acceleration**: CUDA support for local TTS models
2. **Audio Caching**: Cache frequently used audio segments
3. **Predictive Loading**: Pre-generate common responses
4. **Compression**: Optimize audio quality vs. bandwidth 