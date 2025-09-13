# LiveKit VTuber Agent

## Overview

A next-generation VTuber streaming platform built on LiveKit's real-time communication framework. This system replaces complex multi-container architectures with a streamlined, efficient solution that provides:

- **Real-time audio/video processing** with WebRTC
- **Continuous conversation loops** (not request/response)
- **Synchronized blendshape facial animations**
- **Platform integration** (Twitch/YouTube)
- **Intelligent behavior** with LLM integration
- **Automatic memory consolidation**

## Architecture Comparison

### Traditional Architecture (25+ containers)
```
autogen_agent → scb_gateway → kokoro_tts → neurosync_s1
     ↓              ↓             ↓            ↓
  postgres       redis        nginx_rtmp    TCP:5001
     ↓              ↓             ↓            ↓
   neo4j      monitoring     platforms      game
```

### LiveKit Architecture (8-10 containers)
```
LiveKit Server ← → VTuber Agent → neurosync_s1
       ↓               ↓              ↓
    WebRTC          Ollama       TCP:5001
       ↓               ↓              ↓
   Platforms        Redis         Render
```

## Key Benefits

1. **50% Fewer Containers**: From 17+ essential containers to 8-10
2. **Real-time Synchronization**: Audio, video, and blendshapes perfectly synced
3. **Built-in Interruption Handling**: Natural conversation flow
4. **Native WebRTC**: Better quality than RTMP streaming
5. **Unified Agent**: Single intelligent controller vs complex multi-agent system
6. **No Separate TTS**: LiveKit handles audio pipeline (can remove kokoro_tts)

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB RAM minimum
- Ports: 7880-7882 (LiveKit), 5001 (TCP), 11434 (Ollama)

### Installation

1. Clone the repository:
```bash
git clone <repository>
cd livekit-vtuber-agent
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Deploy:
```bash
./deploy.sh deploy
```

4. Load AI models:
```bash
./deploy.sh models
```

5. Check status:
```bash
./deploy.sh status
```

## Configuration

### Agent Personality
Edit `config/agent.yaml`:
```yaml
agent:
  name: Luna
  personality: friendly, energetic streamer
  voice_model: nova
```

### Platform Integration
Set in `.env`:
```bash
# Twitch
TWITCH_CLIENT_ID=your_client_id
TWITCH_CHANNEL=your_channel

# YouTube
YOUTUBE_API_KEY=your_api_key
YOUTUBE_CHANNEL_ID=your_channel_id
```

### Behavior Settings
```yaml
behavior:
  chat_response_rate: 0.3  # Respond to 30% of messages
  mention_response_rate: 0.9  # Respond to 90% of mentions
  donation_threshold: 5.00  # React to donations > $5
```

## Components

### LiveKit VTuber Agent (`src/vtuber_agent.py`)
- Main intelligence and coordination
- STT → LLM → TTS pipeline
- Platform chat integration
- Memory management
- Behavior engine

### Blendshape Controller (`src/blendshape_controller.py`)
- Converts audio/text to facial animations
- Phoneme to viseme mapping
- Emotion-based expressions
- Smooth interpolation

### TCP Client (`src/tcp_client.py`)
- Controls neurosync_s1 avatar
- Sends facial expressions and animations
- Command queuing and batching

### Platform Integration (`src/platform_integration.py`)
- Twitch chat monitoring
- YouTube Live chat
- Unified message handling
- Bidirectional communication

### Memory Manager (`src/memory_manager.py`)
- Session-based memory (1 hour)
- Automatic consolidation
- Central Manager integration
- Context management

## How It Works

### 1. Real-time Audio Loop
```python
# LiveKit handles the continuous audio/video loop
assistant = VoiceAssistant(
    vad=vad.SileroVAD(),      # Voice activity detection
    stt=stt.DeepgramSTT(),     # Speech to text
    llm=llm.OpenAI(),          # Language model
    tts=tts.ElevenLabs(),      # Text to speech
)
```

### 2. Blendshape Generation
```python
# Audio → Phonemes → Blendshapes → TCP Commands
blendshapes = blendshape_controller.generate_from_audio(audio)
for shape in blendshapes:
    tcp_client.send_blendshape(shape)
```

### 3. Platform Integration
```python
# Chat messages injected into conversation
message = await platform_chat.get_message()
if should_respond(message):
    response = await generate_response(message)
    await speak(response)
```

## Deployment Options

### Basic (LiveKit + Agent only)
```bash
docker-compose up livekit-server livekit-vtuber-agent neurosync_s1 ollama redis
```

### With Livepeer (for orchestrator network)
```bash
docker-compose up
```

### With Traditional Streaming (RTMP)
```bash
docker-compose --profile rtmp up
```

### With Unreal Game
```bash
docker-compose --profile unreal up
```

## API Endpoints

### Agent Health
```
GET http://localhost:8080/health
```

### WebSocket Events
```
ws://localhost:8080/ws
```

### Central Manager Integration
```
POST http://localhost:8080/config
POST http://localhost:8080/command
GET http://localhost:8080/memory
```

## TCP Commands

The agent sends these commands to neurosync_s1:

### Facial Expressions
- `FACE.Happy`, `FACE.Sad`, `FACE.Angry`, `FACE.Surprised`
- `FACE.Love`, `FACE.Thinking`, `FACE.Excited`, `FACE.Neutral`

### Emotes
- `EMOTE.Wave`, `EMOTE.Dance2`, `EMOTE.Celebrate`
- `EMOTE.ThumbsUp`, `EMOTE.Heart`, `EMOTE.Bow`

### Blendshapes
- `BS_mouthOpen_0.5` - Mouth opening (0-1)
- `BS_eyeSquint_0.3` - Eye squinting
- `MT_HeadTop_0.5` - Morph targets

### Control
- `startspeaking` - Begin talking animation
- `stopspeaking` - End talking animation
- `NEW.Character_Female2` - Change character

## Monitoring

### View Logs
```bash
# All services
./deploy.sh logs

# Specific service
./deploy.sh logs livekit-vtuber-agent
```

### Test Connections
```bash
./deploy.sh test
```

### Service Status
```bash
./deploy.sh status
```

## Troubleshooting

### Agent not responding
1. Check LiveKit server: `curl http://localhost:7881/health`
2. Check TCP connection: `nc -zv localhost 5001`
3. View agent logs: `./deploy.sh logs agent`

### No audio output
1. Verify TTS configuration in agent.yaml
2. Check LiveKit room connection
3. Ensure neurosync_s1 is receiving commands

### Platform chat not working
1. Verify API credentials in .env
2. Check platform-specific logs
3. Ensure bot has proper permissions

### Memory issues
1. Reduce Ollama model size
2. Adjust Redis memory limits
3. Use consolidation more frequently

## Performance

### Resource Usage
- **Memory**: ~4GB (vs 10GB traditional)
- **CPU**: 25-40% during streaming
- **Network**: WebRTC optimized bandwidth

### Latency
- **Speech recognition**: < 200ms
- **LLM response**: < 500ms
- **Blendshape sync**: < 50ms
- **Total loop**: < 1 second

## Development

### Adding Custom Behaviors
```python
# In vtuber_agent.py
@function_tool
async def custom_action(context: RunContext, param: str):
    """Custom VTuber action"""
    await tcp_client.send_command(f"CUSTOM.{param}")
```

### Custom Blendshapes
```python
# In blendshape_controller.py
CUSTOM_PHONEME_MAP = {
    'custom': {'customShape': 0.7}
}
```

### Platform Extensions
```python
# In platform_integration.py
class DiscordIntegration(BasePlatform):
    async def connect(self):
        # Discord bot logic
```

## Migration from Traditional Architecture

1. **Stop old services**: `docker-compose -f docker-compose.yml down`
2. **Backup data**: Export Redis/PostgreSQL if needed
3. **Deploy LiveKit**: `./deploy.sh deploy`
4. **Migrate configuration**: Transfer personality settings
5. **Test integration**: Verify TCP commands work
6. **Switch streams**: Update stream keys/endpoints

## License

Proprietary - Embody Network

## Support

For issues and support, contact the development team.