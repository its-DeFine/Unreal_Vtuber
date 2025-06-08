# Single Container RTMP Voice Streaming Server

A unified, self-contained Docker container that provides real-time RTMP streaming with advanced audio processing, multi-quality output, and web monitoring interface.

## 🏗️ Architecture

This is a **single container solution** that integrates:

- **Nginx with RTMP module** - Stream ingestion and distribution
- **GStreamer** - Real-time audio/video processing pipeline
- **FFmpeg** - Multi-quality transcoding
- **Python scripts** - Advanced audio enhancement and noise reduction  
- **Web interface** - Real-time monitoring and stream management
- **HLS/DASH output** - Web-compatible streaming formats

## ✨ Features

### Core Streaming
- ✅ RTMP server on port 1935
- ✅ Multiple streaming applications (live, voice, test, relay)
- ✅ Multi-quality output (240p, 480p, 720p, 1080p)
- ✅ Adaptive bitrate streaming
- ✅ Sub-200ms latency optimization

### Audio Enhancement
- ✅ Real-time voice enhancement and noise reduction
- ✅ Voice Activity Detection (VAD)
- ✅ Dynamic range compression
- ✅ Audio level normalization
- ✅ Spectral noise profiling

### Monitoring & Management
- ✅ Web interface with HLS.js player
- ✅ Real-time statistics and stream health
- ✅ Stream recording capabilities
- ✅ Comprehensive health checks
- ✅ RESTful control endpoints

## 🚀 Quick Start

### Prerequisites
- Docker
- Docker Compose (optional)
- 4GB+ RAM recommended
- Hardware with GPU support (optional, for acceleration)

### Build and Run

```bash
# Clone and navigate
cd voice_app/services/rtmp-server

# Build the image
./build.sh build

# Run the container  
./build.sh run

# Test the server
./build.sh test
```

### Alternative: Direct Docker Commands

```bash
# Build image
docker build -t rtmp-voice-server .

# Run container
docker run -d \
  --name rtmp-voice-server \
  -p 1935:1935 \
  -p 8080:8080 \
  -v $(pwd)/recordings:/var/recordings \
  rtmp-voice-server
```

### Alternative: Docker Compose

```bash
# Start the service
docker-compose up -d

# Stop the service
docker-compose down
```

## 📡 Usage

### Streaming to the Server

**RTMP URL Format:**
```
rtmp://localhost:1935/[application]/[stream_name]
```

**Available Applications:**
- `live` - Full video/audio streaming with multi-quality output
- `voice` - Audio-optimized streaming with voice enhancement
- `test` - Development testing environment
- `relay` - Remote streaming relay

**Example OBS Studio Setup:**
- Server: `rtmp://localhost:1935/live`
- Stream Key: `your_stream_name`

**Example FFmpeg Streaming:**
```bash
# Stream a video file
ffmpeg -re -i input.mp4 -c copy -f flv rtmp://localhost:1935/live/test_stream

# Stream webcam (Linux)
ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -c:a aac -f flv rtmp://localhost:1935/live/webcam

# Stream audio only to voice application
ffmpeg -f alsa -i default -c:a aac -f flv rtmp://localhost:1935/voice/audio_stream
```

### Viewing Streams

**Web Interface:**
- Main Player: http://localhost:8080
- Statistics: http://localhost:8080/stats
- Health Check: http://localhost:8080/health

**HLS Playback URLs:**
```
# Auto quality
http://localhost:8080/hls/live/stream_name/index.m3u8

# Specific quality
http://localhost:8080/hls/live/stream_name_720p/index.m3u8

# Voice streams
http://localhost:8080/hls/voice/audio_stream/index.m3u8
```

## 🔧 Management Commands

```bash
# View logs
./build.sh logs

# Access container shell
./build.sh shell

# Restart service
./build.sh restart

# Stop service
./build.sh stop

# Clean up
./build.sh clean
```

## 📊 Monitoring

### Real-time Statistics
- Active streams and viewer counts
- Server uptime and resource usage
- Bandwidth monitoring
- Stream quality metrics

### Health Checks
- Nginx process monitoring
- Port accessibility checks
- Disk space monitoring
- Memory usage alerts

### Log Files (in container)
- `/var/log/nginx/access.log` - HTTP access logs
- `/var/log/nginx/error.log` - Nginx error logs
- `/var/log/gstreamer_processor.log` - GStreamer processing logs
- `/var/log/audio_processor.log` - Audio enhancement logs

## ⚙️ Configuration

### Environment Variables
```bash
# Resource limits
NGINX_WORKER_PROCESSES=auto
RTMP_MAX_STREAMS=1024

# Audio processing
VOICE_ENHANCEMENT_ENABLED=true
NOISE_REDUCTION_LEVEL=0.95
VAD_THRESHOLD=0.02
```

### Custom Configuration
Mount custom nginx.conf:
```bash
docker run -v ./custom-nginx.conf:/etc/nginx/nginx.conf:ro rtmp-voice-server
```

### Persistent Storage
Recordings are saved to `/var/recordings` in the container. Mount a volume for persistence:
```bash
-v $(pwd)/recordings:/var/recordings
```

## 🎯 Quality Settings

| Quality | Resolution | Video Bitrate | Audio Bitrate | Framerate |
|---------|------------|---------------|---------------|-----------|
| 240p    | 426x240    | 400k         | 64k          | 15fps     |
| 480p    | 854x480    | 1000k        | 96k          | 25fps     |
| 720p    | 1280x720   | 2500k        | 128k         | 30fps     |
| 1080p   | 1920x1080  | 5000k        | 192k         | 30fps     |

## 🔬 Testing

### Health Check
```bash
curl http://localhost:8080/health
# Expected: "healthy"
```

### Statistics API
```bash
curl http://localhost:8080/stats
# Returns XML statistics
```

### Stream Test with FFmpeg
```bash
# Generate test pattern
ffmpeg -f lavfi -i testsrc=duration=60:size=1280x720:rate=30 \
  -f lavfi -i sine=frequency=1000:duration=60 \
  -c:v libx264 -c:a aac -f flv \
  rtmp://localhost:1935/test/test_pattern
```

## 🛠️ Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
./build.sh logs

# Verify ports aren't in use
netstat -tulpn | grep -E "1935|8080"
```

**Stream not appearing:**
```bash
# Check RTMP connection
nc -v localhost 1935

# Verify stream in stats
curl http://localhost:8080/stats
```

**Audio processing not working:**
```bash
# Check processing logs
docker exec rtmp-voice-server tail -f /var/log/audio_processor.log
```

### Performance Tuning

**For high load:**
- Increase `RTMP_MAX_STREAMS`
- Adjust Docker resource limits
- Enable hardware acceleration if available

**For low latency:**
- Reduce HLS fragment size
- Optimize encoding presets
- Use UDP transport where possible

## 📁 Directory Structure

```
voice_app/services/rtmp-server/
├── Dockerfile              # Single container build
├── docker-compose.yml      # Single service deployment
├── build.sh                # Build and management script
├── nginx.conf              # RTMP and HTTP configuration
├── entrypoint.sh           # Container startup script
├── health_check.sh         # Health monitoring script
├── stat.xsl                # Statistics stylesheet
├── scripts/                # Processing scripts
│   ├── gstreamer_processor.py   # Real-time stream processing
│   ├── audio_processor.py       # Voice enhancement
│   └── stream_processor.sh      # Multi-quality transcoding
├── www/                    # Web interface
│   └── index.html          # HLS player and monitoring
└── recordings/             # Stream recordings (mounted volume)
```

## 🔐 Security Notes

- Change default admin password in production
- Configure IP whitelisting for publishing
- Use HTTPS for web interface in production
- Regularly update base image and dependencies

## 📄 License

This project is part of the Docker VT real-time voice streaming platform.

---

**Single Container Deployment** - No docker-compose dependencies required, runs as unified service. 