# Real-Time AI Voice Streaming Platform

A complete real-time voice streaming platform that runs on a single Linux server, providing AI-powered text-to-speech, large language model inference, and RTMP streaming capabilities with minimal latency.

## 🚀 Features

- **Local AI Models**: Ollama (Llama 3.2), Coqui TTS, Whisper STT with CUDA 12.1 optimization
- **Real-time Voice Interface**: WebRTC audio capture, push-to-talk, voice activity detection
- **RTMP Streaming**: nginx-rtmp server with GStreamer backend for sub-200ms latency
- **Web Application**: React frontend with WebSocket integration
- **Remote RTMP Relay**: Stream to multiple remote RTMP servers simultaneously
- **GPU Optimization**: Efficient GPU memory management and model switching
- **Monitoring**: Comprehensive system monitoring and performance metrics

## 📋 Requirements

### Hardware
- NVIDIA GPU with CUDA 12.1+ support
- Minimum 16GB RAM (32GB recommended)
- Minimum 50GB free disk space
- Stable internet connection

### Software
- Ubuntu 20.04+ (22.04 recommended)
- User account with sudo privileges
- Internet access for downloading models and dependencies

## 🛠️ Installation

### Quick Start

```bash
# Clone or download the project
cd voice_app

# Run the deployment script
./deploy_voice_platform.sh --install
```

### Step-by-Step Installation

1. **System Preparation**
   ```bash
   ./deploy_voice_platform.sh --install
   ```
   This will:
   - Install NVIDIA drivers and CUDA 12.1
   - Set up Docker with GPU support
   - Install system dependencies

2. **Configuration**
   ```bash
   ./deploy_voice_platform.sh --configure
   ```

3. **Start Services**
   ```bash
   ./deploy_voice_platform.sh --start
   ```

## 🎮 Usage

### Command Line Options

```bash
./deploy_voice_platform.sh [OPTION]

OPTIONS:
  --install       Install the complete voice streaming platform
  --configure     Configure platform services and settings
  --start         Start all platform services
  --stop          Stop all platform services  
  --status        Show current platform status
  --update        Update platform components
  --uninstall     Remove the platform completely
  --help          Show help message
```

### Web Interface

Once installed and started, access the web interface at:
- **Main Interface**: http://localhost:8080
- **API Documentation**: http://localhost:5000/docs
- **Monitoring Dashboard**: http://localhost:3000

### RTMP Streaming

- **Local RTMP Server**: rtmp://localhost:1935/live/stream
- **Stream Key**: Configure in web interface
- **Remote Relay**: Configure remote RTMP destinations in settings

## 🏗️ Architecture

```
voice_app/
├── deploy_voice_platform.sh    # Main deployment script
├── modules/                     # Installation modules
│   ├── system_prep.sh          # System preparation
│   ├── model_setup.sh          # AI model setup
│   ├── app_deployment.sh       # Application deployment
│   └── ...
├── services/                    # Application services
│   ├── ai-models/              # AI model management
│   ├── web-app/                # Web application
│   │   ├── frontend/           # React frontend
│   │   └── backend/            # FastAPI backend
│   ├── rtmp-server/            # RTMP streaming server
│   └── monitoring/             # System monitoring
├── config/                     # Configuration files
├── scripts/                    # Utility scripts
├── docs/                       # Documentation
├── logs/                       # Application logs
└── data/                       # Application data
```

## 🔧 Configuration

### Environment Variables

Key configuration options can be set in `config/platform.env`:

```bash
# AI Models
CUDA_VISIBLE_DEVICES=0
MODEL_CACHE_DIR=/opt/models
TTS_MODEL=tts_models/en/ljspeech/tacotron2-DDC
STT_MODEL=base

# Streaming
RTMP_PORT=1935
WEB_PORT=8080
API_PORT=5000
WEBSOCKET_PORT=8081

# Performance
MAX_CONCURRENT_REQUESTS=10
GPU_MEMORY_LIMIT=0.9
```

### Remote RTMP Configuration

Configure remote RTMP destinations in the web interface or via API:

```json
{
  "destinations": [
    {
      "name": "Production Server",
      "url": "rtmp://your-server.com:1935/live",
      "key": "your-stream-key",
      "enabled": true
    }
  ]
}
```

## 📊 Monitoring

### System Status

Check system status:
```bash
./deploy_voice_platform.sh --status
```

### Performance Metrics

- **Latency Monitoring**: End-to-end latency tracking
- **GPU Utilization**: Real-time GPU memory and compute usage
- **Stream Health**: RTMP stream quality and connection status
- **API Performance**: Request/response times and error rates

### Logs

- **Deployment Logs**: `logs/deployment_*.log`
- **Application Logs**: `logs/app_*.log`
- **Error Logs**: `logs/deployment_errors_*.log`

## 🔍 Troubleshooting

### Common Issues

1. **CUDA Not Found**
   ```bash
   # Check NVIDIA driver installation
   nvidia-smi
   
   # Reinstall CUDA if needed
   ./deploy_voice_platform.sh --install
   ```

2. **Port Already in Use**
   ```bash
   # Check which process is using the port
   sudo netstat -tulpn | grep :1935
   
   # Stop conflicting service or change port in config
   ```

3. **GPU Memory Issues**
   ```bash
   # Check GPU memory usage
   nvidia-smi
   
   # Adjust GPU_MEMORY_LIMIT in config
   ```

### Getting Help

- Check logs in `logs/` directory
- Review configuration in `config/` directory
- Run system status check: `./deploy_voice_platform.sh --status`

## 🚧 Development

### Project Structure

The project follows a modular architecture:

- **Modules**: Self-contained installation and configuration scripts
- **Services**: Microservices for different platform components
- **Configuration**: Centralized configuration management
- **Monitoring**: Comprehensive system monitoring and alerting

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- NVIDIA for CUDA and GPU computing support
- Ollama for local LLM inference
- Coqui for open-source TTS
- OpenAI for Whisper STT
- nginx-rtmp for streaming infrastructure
- GStreamer for multimedia processing

---

For detailed technical documentation, see the `docs/` directory. 