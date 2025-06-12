# Kokoro TTS Integration Setup

This document explains how to set up and use Kokoro TTS as an alternative to ElevenLabs in the NeuroSync Player system.

## Overview

The NeuroSync Player now supports three TTS providers:
- **Local TTS** - Basic local text-to-speech
- **ElevenLabs** - High-quality cloud TTS (requires API key)
- **Kokoro TTS** - High-quality local TTS server (requires separate server)

## Kokoro TTS Server Setup

### Prerequisites

1. **Kokoro TTS Server**: You need to have the Kokoro TTS server running separately. This is typically a Python server that provides TTS functionality via HTTP API.

2. **Server URL**: The Kokoro server should be accessible via HTTP (default: `http://localhost:6006`).

### Supported Voices

The system includes voice mapping for common voice names:
- `Sarah` → `af_sarah` (Adult Female)
- `Adam` → `am_adam` (Adult Male)
- `Emma` → `bf_emma` (British Female)
- `George` → `bm_george` (British Male)
- `Alice` → `af_alice` (Adult Female)
- `Nicole` → `af_nicole` (Adult Female)

## Configuration

### Environment Variables

Set these environment variables to configure Kokoro TTS:

```bash
# Required: Set TTS provider to Kokoro
export TTS_PROVIDER=kokoro

# Optional: Kokoro server configuration
export KOKORO_TTS_SERVER_URL=http://localhost:6006
export KOKORO_DEFAULT_VOICE=af_sarah
export KOKORO_TTS_TIMEOUT=30
export KOKORO_TTS_LANGUAGE=en
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_PROVIDER` | `local` | Set to `kokoro` to use Kokoro TTS |
| `KOKORO_TTS_SERVER_URL` | `http://localhost:6006` | URL of your Kokoro TTS server |
| `KOKORO_DEFAULT_VOICE` | `af_sarah` | Default voice to use |
| `KOKORO_TTS_TIMEOUT` | `30` | Request timeout in seconds |
| `KOKORO_TTS_LANGUAGE` | `en` | Language code for TTS |

## Usage

### 1. Quick Start

```bash
# Set environment variables
export TTS_PROVIDER=kokoro
export KOKORO_TTS_SERVER_URL=http://your-kokoro-server:6006

# Run your NeuroSync Player application
python your_main_script.py
```

### 2. Testing the Integration

Use the provided test script to verify everything is working:

```bash
# Set up environment
export TTS_PROVIDER=kokoro

# Run the test suite
python test_kokoro_integration.py
```

The test script will:
- Verify configuration is loaded correctly
- Test connection to Kokoro server
- Generate test audio with different voices
- Test integration with the TTS worker system

### 3. Voice Selection

You can specify voices in your application code or configuration:

```python
# The system will automatically map common voice names
voice_name = "Sarah"  # Will be mapped to "af_sarah"

# Or use Kokoro voice names directly
voice_name = "af_sarah"
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   ❌ Error connecting to Kokoro server: [Errno 111] Connection refused
   ```
   - **Solution**: Ensure Kokoro TTS server is running and accessible
   - Check the server URL and port

2. **Voice Not Found**
   ```
   ⚠️ Voice 'unknown_voice' not available, using default 'af_sarah'
   ```
   - **Solution**: Use one of the supported voice names
   - Check the voice mapping in `utils/tts/kokoro_tts.py`

3. **Timeout Errors**
   ```
   ❌ Timeout generating TTS audio
   ```
   - **Solution**: Increase `KOKORO_TTS_TIMEOUT` value
   - Check server performance and load

4. **No Audio Generated**
   ```
   ❌ TTS generation failed for chunk: [text]
   ```
   - **Solution**: Check server logs for errors
   - Verify text input is valid
   - Test with simple text first

### Fallback Behavior

The system includes robust fallback mechanisms:

1. **Voice Fallback**: If requested voice is unavailable, uses default voice
2. **Provider Fallback**: If Kokoro fails, you can manually switch to other providers
3. **Error Handling**: Detailed logging helps identify and resolve issues

### Server Health Monitoring

The system automatically checks server health:
- Connection validation on startup
- Request timeout handling
- Automatic retry mechanisms (where appropriate)

## Performance Considerations

- **Latency**: Local Kokoro server typically has lower latency than cloud services
- **Quality**: Kokoro provides high-quality natural-sounding speech
- **Scalability**: Performance depends on your server hardware and configuration
- **Resource Usage**: Monitor server CPU/memory usage under load

## Security Notes

- Kokoro TTS runs locally, so no text data is sent to external services
- Ensure proper network security if running server on different machines
- Consider authentication if exposing server to network

## Migration from Other TTS Providers

### From ElevenLabs

```bash
# Old configuration
export TTS_PROVIDER=elevenlabs
export ELEVENLABS_API_KEY=your_key

# New configuration
export TTS_PROVIDER=kokoro
export KOKORO_TTS_SERVER_URL=http://localhost:6006
```

### From Local TTS

```bash
# Old configuration
export TTS_PROVIDER=local

# New configuration
export TTS_PROVIDER=kokoro
export KOKORO_TTS_SERVER_URL=http://localhost:6006
```

## Advanced Configuration

### Custom Voice Mapping

To add custom voice mappings, edit `utils/tts/kokoro_tts.py`:

```python
VOICE_MAPPING = {
    "Sarah": "af_sarah",
    "Adam": "am_adam",
    # Add your custom mappings here
    "CustomVoice": "custom_voice_id",
}
```

### Server Integration

The Kokoro TTS integration follows the same pattern as other TTS providers:

1. **Text Input**: Receives text chunks from the TTS worker
2. **Audio Generation**: Calls Kokoro server to generate audio
3. **Audio Output**: Returns audio bytes for further processing
4. **Error Handling**: Logs errors and provides fallback options

## Support

If you encounter issues:

1. Run the test script to identify the problem area
2. Check server logs and connectivity
3. Verify environment variable configuration
4. Review the troubleshooting section above

For development and debugging, enable detailed logging by checking the console output from the TTS worker. 