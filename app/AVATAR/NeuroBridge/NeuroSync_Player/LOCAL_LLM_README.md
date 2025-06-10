# 🤖 Local LLM Integration for VTuber System

This guide explains how to set up and use local Large Language Models (LLMs) with your autonomous VTuber system, replacing expensive OpenAI API calls with efficient local alternatives.

## 🌟 Benefits of Local LLMs

- **💰 Cost Savings**: Eliminate per-token API costs
- **🔒 Privacy**: All conversations stay on your hardware
- **⚡ Speed**: No network latency for responses
- **🎮 Offline Capability**: Works without internet connection
- **🛠️ Customization**: Full control over model behavior

## 🎯 Quick Start with Ollama (Recommended)

### 1. Automatic Setup (Easiest)

```bash
cd NeuroBridge/NeuroSync_Player
./setup_ollama.sh
```

This script will:
- Install and configure Ollama
- Download lightweight models optimized for VTuber interactions
- Update your `.env` configuration
- Test the setup

### 2. Manual Setup

#### Prerequisites
- Docker and Docker Compose
- At least 8GB RAM (16GB+ recommended)
- Optional: NVIDIA GPU for faster processing

#### Step-by-Step

1. **Start Ollama Container**
   ```bash
   # For GPU systems
   docker run -d \
     --name vtuber-ollama \
     --gpus all \
     -p 11434:11434 \
     -v ./ollama_data:/root/.ollama \
     ollama/ollama:latest

   # For CPU-only systems
   docker run -d \
     --name vtuber-ollama-cpu \
     -p 11434:11434 \
     -v ./ollama_data:/root/.ollama \
     ollama/ollama:latest
   ```

2. **Install a Lightweight Model**
   ```bash
   # Install Llama 3.2 3B (recommended for VTuber)
   docker exec vtuber-ollama ollama pull llama3.2:3b
   
   # Alternative lightweight models
   docker exec vtuber-ollama ollama pull phi3:mini      # Microsoft's compact model
   docker exec vtuber-ollama ollama pull qwen2:1.5b     # Very fast responses
   docker exec vtuber-ollama ollama pull gemma2:2b      # Google's efficient model
   ```

3. **Configure Environment**
   
   Create or update your `.env` file:
   ```env
   # Local LLM Configuration
   LLM_PROVIDER=ollama
   OLLAMA_API_ENDPOINT=http://localhost:11434
   OLLAMA_MODEL=llama3.2:3b
   OLLAMA_STREAMING=true
   USE_STREAMING=true
   ```

4. **Test the Setup**
   ```bash
   python test_ollama.py
   ```

## 🎛️ Configuration Options

### Environment Variables

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `LLM_PROVIDER` | LLM provider to use | `openai` | `ollama`, `openai`, `custom_local` |
| `OLLAMA_API_ENDPOINT` | Ollama server URL | `http://localhost:11434` | Any Ollama endpoint |
| `OLLAMA_MODEL` | Model to use | `llama3.2:3b` | Any Ollama model |
| `OLLAMA_STREAMING` | Enable streaming | `true` | `true`, `false` |
| `USE_STREAMING` | Global streaming setting | `true` | `true`, `false` |

### Model Recommendations

#### For Real-time VTuber Interactions (Fast Response)
- **llama3.2:3b** - Best balance of speed and quality
- **qwen2:1.5b** - Fastest responses, good for quick reactions
- **phi3:mini** - Microsoft's efficient model

#### For High-Quality Responses (Slower but Better)
- **llama3.2:7b** - Better quality but needs more resources
- **gemma2:9b** - Google's larger model
- **mistral:7b** - Good general-purpose model

#### Memory Usage Guide
| Model | RAM Required | Speed | Quality |
|-------|-------------|-------|---------|
| qwen2:1.5b | ~2GB | ⚡⚡⚡ | ⭐⭐ |
| llama3.2:3b | ~4GB | ⚡⚡ | ⭐⭐⭐ |
| phi3:mini | ~3GB | ⚡⚡ | ⭐⭐⭐ |
| llama3.2:7b | ~8GB | ⚡ | ⭐⭐⭐⭐ |
| gemma2:9b | ~12GB | ⚡ | ⭐⭐⭐⭐ |

## 🎨 Advanced Configuration

### Custom System Prompts

The system automatically optimizes prompts for VTuber interactions, but you can customize the base message in `config.py`:

```python
BASE_SYSTEM_MESSAGE = """You are Livy, a sophisticated AI VTuber...
- Add your custom personality traits here
- Specify interaction styles
- Set response preferences
"""
```

### Multiple Model Setup

You can install multiple models and switch between them:

```bash
# Install multiple models
docker exec vtuber-ollama ollama pull llama3.2:3b
docker exec vtuber-ollama ollama pull phi3:mini
docker exec vtuber-ollama ollama pull qwen2:1.5b

# Switch models by updating .env
OLLAMA_MODEL=phi3:mini  # Change this line
```

### GPU Optimization

For NVIDIA GPU users:

```bash
# Check GPU support
nvidia-smi

# Run with GPU acceleration
docker run -d \
  --name vtuber-ollama \
  --gpus all \
  -p 11434:11434 \
  -v ./ollama_data:/root/.ollama \
  ollama/ollama:latest
```

## 🔧 Alternative LLM Providers

### Custom Local API

If you have your own LLM API:

```env
LLM_PROVIDER=custom_local
LLM_API_URL=http://127.0.0.1:5050/generate_llama
LLM_STREAM_URL=http://127.0.0.1:5050/generate_stream
USE_STREAMING=true
```

### OpenAI (Fallback)

To use OpenAI as a fallback:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o
```

## 🚨 Troubleshooting

### Common Issues

#### Ollama Not Responding
```bash
# Check if container is running
docker ps | grep ollama

# Check container logs
docker logs vtuber-ollama

# Restart Ollama
docker restart vtuber-ollama
```

#### Model Not Found
```bash
# List installed models
docker exec vtuber-ollama ollama list

# Pull missing model
docker exec vtuber-ollama ollama pull llama3.2:3b
```

#### Out of Memory
- Switch to a smaller model (qwen2:1.5b)
- Reduce system memory usage
- Consider upgrading RAM

#### Slow Responses
- Use GPU acceleration if available
- Switch to a smaller model
- Ensure no other heavy processes are running

### Performance Tuning

#### CPU Optimization
```bash
# Increase CPU cores for Ollama
docker run -d \
  --name vtuber-ollama \
  --cpus="4.0" \
  -p 11434:11434 \
  -v ./ollama_data:/root/.ollama \
  ollama/ollama:latest
```

#### Memory Optimization
```bash
# Set memory limits
docker run -d \
  --name vtuber-ollama \
  --memory="8g" \
  -p 11434:11434 \
  -v ./ollama_data:/root/.ollama \
  ollama/ollama:latest
```

### Monitoring

#### Check Model Performance
```bash
# Monitor resource usage
docker stats vtuber-ollama

# Test response times
python test_ollama.py
```

#### Logs
```bash
# VTuber system logs
tail -f logs/player_log_*.txt

# Ollama logs
docker logs -f vtuber-ollama
```

## 🔄 Switching Between Providers

You can easily switch between different LLM providers by updating your `.env` file:

### To Ollama
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
```

### To OpenAI
```env
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o
```

### To Custom Local
```env
LLM_PROVIDER=custom_local
LLM_API_URL=http://your-api:5000/generate
```

## 📊 Performance Comparison

| Provider | Cost | Speed | Privacy | Offline | Setup |
|----------|------|-------|---------|---------|-------|
| **Ollama** | Free | Fast | 100% | Yes | Medium |
| **OpenAI** | $$ | Very Fast | No | No | Easy |
| **Custom Local** | Free | Variable | 100% | Yes | Hard |

## 🛠️ Development Tips

### Adding New Models

1. Find models on [Ollama Model Library](https://ollama.ai/library)
2. Pull the model: `docker exec vtuber-ollama ollama pull model_name`
3. Update `.env`: `OLLAMA_MODEL=model_name`
4. Test with `python test_ollama.py`

### Custom Model Parameters

Edit `config.py` to adjust model parameters:

```python
# In build_llm_payload function
"options": {
    "temperature": 0.8,    # Creativity (0.0-1.0)
    "top_p": 0.9,         # Focus (0.0-1.0)
    "num_predict": 4000,  # Max tokens
}
```

## 📚 Resources

- [Ollama Documentation](https://ollama.ai/docs)
- [Model Library](https://ollama.ai/library)
- [Docker Documentation](https://docs.docker.com/)
- [VTuber System Documentation](../README.md)

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Run the test script: `python test_ollama.py`
3. Check logs in `logs/` directory
4. Ensure Docker and Ollama are running
5. Verify your `.env` configuration

---

**Happy VTubing with Local LLMs! 🎭🤖** 