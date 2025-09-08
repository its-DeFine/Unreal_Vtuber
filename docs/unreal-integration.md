# Unreal Engine Pixel Streaming Integration for VTuber

*Created: 2025-09-08*
*Last Updated: 2025-09-08*

## Overview

This document describes the integration of Unreal Engine with Pixel Streaming capabilities into the VTuber system, enabling high-quality 3D avatar rendering with WebRTC streaming.

## Architecture

The integration adds two new services to the VTuber stack:

1. **Signaling Server** (`unreal-signaling`): Handles WebRTC signaling and provides web interface
2. **Unreal Game** (`unreal-game`): Runs the Embody game in headless mode with Pixel Streaming

### Network Communication

```
VTuber System (neurosync_s1)
    ↓ TCP Commands (port 7777)
Unreal Game Container
    ↓ Pixel Streaming (WebRTC)
Signaling Server
    ↓ WebSocket/HTTP
Web Browser Client
```

## Setup Instructions

### Prerequisites

1. Unreal Engine Linux build of the Embody game at `/home/geo/embody/Embody`
2. Unreal Engine installation at `/home/geo/embody/Engine`
3. Docker and Docker Compose installed
4. (Optional) NVIDIA GPU with drivers for hardware acceleration

### Configuration

1. **Copy the environment file template:**
   ```bash
   cp .env.unreal.example .env.unreal
   ```

2. **Edit `.env.unreal` with your settings:**
   - Set `GAME_PATH` to your Embody game location
   - Set `ENGINE_PATH` to your Unreal Engine location
   - Configure `PUBLIC_IP` for external access (or use `localhost` for local testing)
   - Adjust performance settings (`FPS`, `RESOLUTION`) as needed

3. **Update main `.env` file:**
   ```bash
   # Add to your main .env file:
   UNREAL_TCP_HOST=unreal-game
   UNREAL_TCP_PORT=7777
   ```

### Running the Integration

1. **Start all services with Unreal integration:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.unreal.yml up -d
   ```

2. **Check service health:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.unreal.yml ps
   ```

3. **View logs:**
   ```bash
   # Signaling server logs
   docker logs vtuber-unreal-signaling

   # Game logs
   docker logs vtuber-unreal-game

   # VTuber logs
   docker logs neurosync_s1
   ```

### Accessing the Stream

1. **Web Interface:** Open browser to `http://localhost:8080`
2. **Direct WebRTC:** Connect to signaling server at `ws://localhost:8888`

## TCP Command Protocol

The Unreal game listens on port 7777 for VTuber commands. The existing TCP protocol is maintained:

### Visual Identity Commands
- `HCR.<index>.<duration>` - Hair color/style change
- `OCR.<index>.<duration>` - Outfit change
- `ECR.<index>.<duration>` - Eye color change
- `SCR.<index>.<duration>` - Skin tone change

### Animation Commands
- `ANIM.<animation_name>` - Trigger animation
- `BLEND.<shape>.<value>` - Set blend shape value
- `POSE.<pose_name>` - Set character pose

## File Structure

```
autonomy/
├── docker-compose.unreal.yml       # Unreal services definition
├── .env.unreal                     # Unreal-specific environment variables
├── docker/
│   └── unreal-streaming/
│       ├── signaling/
│       │   └── Dockerfile.signaling
│       └── game/
│           ├── Dockerfile.embody
│           ├── supervisord.conf
│           ├── start_game.sh
│           └── tcp_server.sh
└── docs/
    └── unreal-integration.md      # This file
```

## Troubleshooting

### Common Issues

1. **Game not starting:**
   - Check that game files are properly mounted
   - Verify paths in `.env.unreal`
   - Check container logs: `docker logs vtuber-unreal-game`

2. **No video stream:**
   - Ensure signaling server is healthy
   - Check firewall rules for ports 8080, 8888, 8889
   - Verify WebRTC STUN/TURN configuration

3. **TCP commands not working:**
   - Verify port 7777 is exposed
   - Check network connectivity between containers
   - Test with: `docker exec neurosync_s1 nc -zv unreal-game 7777`

4. **Performance issues:**
   - Reduce resolution in `.env.unreal`
   - Lower FPS setting
   - Enable GPU acceleration if available

### Debug Commands

```bash
# Test TCP connection
docker exec neurosync_s1 python -c "
import socket
s = socket.socket()
s.connect(('unreal-game', 7777))
s.send(b'HCR.1.2.0\n')
print(s.recv(1024))
s.close()
"

# Check Xvfb display
docker exec vtuber-unreal-game bash -c "DISPLAY=:99 xdpyinfo"

# Monitor resource usage
docker stats vtuber-unreal-game vtuber-unreal-signaling
```

## Performance Optimization

### CPU-only (Software Rendering)
- Uses Mesa/LLVMpipe for software rendering
- Suitable for development and testing
- Lower quality but works on any Linux system

### GPU-accelerated (NVIDIA)
- Requires NVIDIA GPU and drivers
- Significantly better performance and quality
- Enable in docker-compose with GPU reservation

### Network Optimization
- Use local TURN server for production
- Configure appropriate bitrates based on bandwidth
- Consider using VP9 or H.265 for better compression

## Security Considerations

1. **Network Isolation:** Services communicate on internal Docker network
2. **Read-only Game Files:** Game directory mounted as read-only
3. **Non-root Execution:** Game runs as unprivileged user
4. **Port Restrictions:** Only necessary ports exposed

## Integration Points

The Unreal integration connects with:

- **NeuroSync S1:** Receives avatar commands via TCP
- **SCB (Redis):** Shares state for coordinated actions
- **AutoGen S2:** Can trigger visual changes based on context
- **Monitoring:** Prometheus metrics available

## Future Enhancements

- [ ] Multi-user support with SFU
- [ ] Dynamic quality adjustment based on bandwidth
- [ ] Recording and replay functionality
- [ ] Cloud deployment with auto-scaling
- [ ] Mobile client support
- [ ] VR/AR integration