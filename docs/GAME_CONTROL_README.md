# 🎮 NeuroSync Game Control System

**AI-powered natural language interface for controlling Unreal Engine avatar/VTuber applications via TCP commands.**

---

## 🎯 Overview

The Game Control System allows external applications (like orchestrator agents) to send natural language prompts to NeuroSync, which then converts them into Unreal Engine TCP commands for real-time avatar and environment control.

### ✨ Key Features

- **Natural Language Processing**: Convert prompts like "yellow hair, medieval scene" into precise TCP commands
- **Comprehensive Command Support**: Hair color, outfits, environments, animations, morphs, and more
- **Non-blocking Architecture**: Game control runs independently of speech processing
- **Error Resilience**: Graceful handling of TCP connection failures and malformed prompts
- **Health Monitoring**: Built-in endpoints for system health checks and feature discovery

---

## 🏗️ Architecture

```
External Orchestrator
        ↓ POST /game_control
NeuroSync Game Control Endpoint
        ↓ Natural Language Prompt
Game Control LLM Processor
        ↓ JSON Array of Commands  
TCP Controller
        ↓ Individual Commands
Unreal Engine (127.0.0.1:7777)
        ↓ Visual Changes
Avatar/Environment Updates
```

---

## 🚀 Quick Start

### Prerequisites
- NeuroSync Player running on port 5001
- Unreal Engine application with TCP Listener enabled on port 7777
- LLM provider configured (OpenAI or Ollama)

### Basic Usage

```bash
# Test the system
curl -X POST http://localhost:5001/game_control \
  -H "Content-Type: application/json" \
  -d '{"prompt": "yellow hair, medieval scene"}'

# Check health
curl http://localhost:5001/game_control/health

# Get available features
curl http://localhost:5001/game_control/features
```

---

## 📡 API Endpoints

### 1. Game Control Processing
**`POST /game_control`**

Process a natural language prompt and apply changes to the Unreal Engine application.

**Request:**
```json
{
  "prompt": "yellow hair, medieval scene"
}
```

**Response:**
```json
{
  "status": "completed",
  "prompt": "yellow hair, medieval scene",
  "commands_generated": 4,
  "commands_successful": 4,
  "commands_failed": 0,
  "tcp_host": "127.0.0.1",
  "tcp_port": 7777,
  "command_details": [
    {"command": "HCR.0.9", "status": "success"},
    {"command": "HCG.0.9", "status": "success"},
    {"command": "HCB.0.2", "status": "success"},
    {"command": "LVL.Medieval", "status": "success"}
  ]
}
```

### 2. Health Check
**`GET /game_control/health`**

Check the status of the game control system and TCP connection.

**Response:**
```json
{
  "status": "healthy",
  "tcp_connection": {
    "overall": "healthy",
    "connection": "healthy",
    "commands": "healthy",
    "config": {
      "host": "127.0.0.1",
      "port": 7777,
      "timeout": 2.0
    }
  },
  "processor_available": true,
  "controller_available": true
}
```

### 3. Features Discovery
**`GET /game_control/features`**

Get information about supported features and example commands.

**Response:**
```json
{
  "status": "available",
  "features": {
    "levels": ["Home", "Medieval", "DJ", "Lofi"],
    "presets": ["Masc", "Fem", "Masc1", "Fem1"],
    "outfits": ["Default", "Maid Dress", "Pop Star", "Kimono"],
    "animations": ["Dance"]
  },
  "example_commands": {
    "hair_color_red": ["HCR.0.9", "HCG.0.1", "HCB.0.1"],
    "medieval_scene": ["LVL.Medieval"]
  },
  "usage": {
    "endpoint": "/game_control",
    "method": "POST",
    "example_prompts": [
      "yellow hair, medieval scene",
      "blue hair, bigger eyes, DJ scene"
    ]
  }
}
```

---

## 🎨 Supported Commands

### 🏰 Environments
- **`LVL.Home`** - Cloud environment
- **`LVL.Medieval`** - Castle/fantasy scene  
- **`LVL.DJ`** - Music/party environment
- **`LVL.Lofi`** - Cozy ambient setting

### 👤 Character Presets
- **`PRS.Fem`** - Feminine build
- **`PRS.Masc`** - Masculine build
- **`PRS.Fem1`** - Feminine variant
- **`PRS.Masc1`** - Masculine variant

### 👗 Outfits
- **`OF.Default`** - Default outfit
- **`OF.Maid Dress`** - Maid costume
- **`OF.Pop Star`** - Colorful pop outfit
- **`OF.Kimono`** - Traditional Japanese kimono
- **`OF.Black Dress`** - Elegant black dress

### 💇 Hair Colors (RGB 0.0-1.0)
- **Red**: `HCR.0.9`, `HCG.0.1`, `HCB.0.1`
- **Blue**: `HCR.0.1`, `HCG.0.3`, `HCB.0.9`  
- **Yellow**: `HCR.0.9`, `HCG.0.9`, `HCB.0.2`
- **Blonde**: `HCR.0.9`, `HCG.0.8`, `HCB.0.3`

### 🎭 Facial Features
- **`MTEYW.0.8`** - Eye width
- **`MTNW.0.6`** - Nose width
- **`MTCW.0.7`** - Chin width

### 🎬 Animations
- **`ANIM.Dance`** - Dance animation

### 🌙 Environment Controls
- **`SNH.0.1`** - Night time (low sun)
- **`STRB.0.9`** - Bright stars

---

## 🗣️ Example Prompts

### Basic Commands
```
"yellow hair"                    → ["HCR.0.9", "HCG.0.9", "HCB.0.2"]
"medieval scene"                 → ["LVL.Medieval"]
"dance animation"                → ["ANIM.Dance"]
"feminine character"             → ["PRS.Fem"]
```

### Complex Combinations
```
"yellow hair, medieval scene"
→ ["HCR.0.9", "HCG.0.9", "HCB.0.2", "LVL.Medieval"]

"blue hair, bigger eyes, DJ scene"  
→ ["HCR.0.1", "HCG.0.3", "HCB.0.9", "MTEYW.0.8", "LVL.DJ"]

"feminine character, maid dress, red hair"
→ ["PRS.Fem", "OF.Maid Dress", "HCR.0.9", "HCG.0.1", "HCB.0.1"]

"night time, bright stars"
→ ["SNH.0.1", "STRB.0.9"]
```

---

## 🧪 Testing

### Using the Test Script

```bash
# Run comprehensive test
python test_game_control.py

# Test specific prompt
python test_game_control.py --prompt "yellow hair, medieval scene"

# Test health only
python test_game_control.py --health

# Test features only  
python test_game_control.py --features

# Test with custom URL
python test_game_control.py --url http://neurosync:5001
```

### Manual Testing with curl

```bash
# Basic test
curl -X POST http://localhost:5001/game_control \
  -H "Content-Type: application/json" \
  -d '{"prompt": "blue hair, DJ scene"}'

# Health check
curl http://localhost:5001/game_control/health

# Features
curl http://localhost:5001/game_control/features
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# TCP Connection (optional - defaults shown)
UNREAL_TCP_HOST=127.0.0.1
UNREAL_TCP_PORT=7777

# LLM Provider (inherits from main NeuroSync config)
LLM_PROVIDER=openai|ollama
OPENAI_API_KEY=your_key_here
OLLAMA_API_ENDPOINT=http://vtuber-ollama:11434

# Game Control Model (optional - uses lighter model for speed)
GAME_CONTROL_MODEL=llama3.2:3b
```

### Docker Integration

The game control system is automatically initialized when NeuroSync starts. It shares the same LLM configuration as the main speech system but uses optimized settings for faster response times.

---

## 🔧 Architecture Details

### Components

1. **Game Control Processor** (`game_control_processor.py`)
   - LLM-powered natural language → TCP command conversion
   - Supports OpenAI and Ollama providers
   - Optimized prompts for consistent JSON output

2. **TCP Controller** (`unreal_tcp_controller.py`)
   - Async TCP client for Unreal Engine communication
   - Batch command processing with retry logic
   - Connection health monitoring

3. **Flask Endpoints** (in `llm_to_face.py`)
   - RESTful API for external integration
   - Health checks and feature discovery
   - Error handling and logging

### Design Principles

- **Non-blocking**: Game control never interferes with speech processing
- **Resilient**: Graceful handling of connection failures and errors
- **Fast**: Optimized for quick command generation and execution
- **Extensible**: Easy to add new commands and features

---

## 🐛 Troubleshooting

### Common Issues

**Game control system unavailable (503)**
- Check NeuroSync logs for initialization errors
- Verify LLM provider configuration
- Ensure required dependencies are installed

**TCP connection failed**
- Verify Unreal Engine is running
- Check TCP Listener is enabled on port 7777
- Test connection: `telnet 127.0.0.1 7777`

**Commands generated but not applied**
- Check Unreal Engine TCP listener logs
- Verify command format in response
- Test individual commands with manual TCP client

**LLM not generating valid JSON**
- Check API key configuration
- Try different model (e.g., switch to OpenAI from Ollama)
- Monitor logs for specific LLM errors

### Debug Commands

```bash
# Check NeuroSync logs
docker logs neurosync_s1 -f

# Test TCP connection manually
echo "MENU." | nc 127.0.0.1 7777

# Comprehensive health check
curl http://localhost:5001/game_control/health | jq

# Test with simple prompt
curl -X POST http://localhost:5001/game_control \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}' | jq
```

---

## 🔮 Future Enhancements

- **Preset Sequences**: Pre-defined command sequences for common setups
- **Voice Integration**: Direct voice commands for game control
- **Visual Feedback**: Real-time preview of changes before applying
- **Advanced Morphing**: More detailed facial feature control
- **Scene Composition**: Complex environment and lighting setups
- **Animation Sequencing**: Custom animation combinations

---

## 📚 Related Documentation

- [Unreal Engine TCP Control System Documentation](./TCP_CONTROL_DOCUMENTATION.md)
- [NeuroSync Player Main Documentation](./README.md)
- [Docker VTuber System Overview](../../../README.md)

---

**Status**: ✅ Implemented and Ready for Testing  
**Last Updated**: December 2024  
**Maintained by**: NeuroSync Development Team 