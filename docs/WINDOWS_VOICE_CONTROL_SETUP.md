# Windows Voice Control Setup Guide
*Created: 2025-07-14*

## Overview

This guide provides complete instructions for setting up voice control for the VTuber orchestrator from a Windows environment. The voice control system allows you to speak commands that are automatically routed to the appropriate VTuber persona (trader, educator, or streamer).

## Architecture

```
Windows Environment                          WSL2/Docker Environment
┌─────────────────────────┐                 ┌──────────────────────────┐
│  Microphone Input       │                 │  Orchestrator Service    │
│          ↓              │                 │  (Port 8082)             │
│  Speech Recognition     │                 │          ↑               │
│  (Google Speech API)    │                 │          │               │
│          ↓              │     HTTP        │          │               │
│  windows_voice_sender.py│ ─────────────→ │  Route & Execute         │
│          ↓              │     API         │          ↓               │
│  Command Parsing        │                 │  VTuber Response         │
│  & Persona Detection    │                 │  (S1/S2 Systems)         │
└─────────────────────────┘                 └──────────────────────────┘
```

## Prerequisites

### Windows Requirements
- Windows 10/11
- Python 3.8 or higher
- Working microphone
- Internet connection (for Google Speech Recognition)

### WSL Requirements
- Docker environment running
- Orchestrator service active
- Port 8082 accessible from Windows

## Step-by-Step Setup

### 1. Verify Python Installation

Open Command Prompt or PowerShell on Windows (not WSL) and run:

```cmd
python --version
```

If Python is not installed, download from [python.org](https://python.org).

### 2. Navigate to Scripts Directory

```cmd
cd C:\path\to\autonomy\scripts
```

Replace with your actual path to the project.

### 3. Run Setup Script

Execute the one-time setup:

```cmd
setup_windows_voice.bat
```

This will:
- Check Python availability
- Install required packages:
  - `SpeechRecognition` - For voice input
  - `requests` - For HTTP communication
  - `pyaudio` - For microphone access

### 4. Start the Orchestrator (in WSL)

In your WSL terminal:

```bash
cd /home/geo/directories/autonomy
docker-compose -f docker-compose.all.yml up orchestrator
```

Wait for the service to start. You should see:
```
orchestrator-service | INFO: Application startup complete
```

### 5. Run Voice Control (on Windows)

Back in Windows Command Prompt/PowerShell:

```cmd
python windows_voice_sender.py
```

You should see:
```
🎤 Windows Voice Control for WSL Orchestrator
============================================================
📡 Orchestrator URL: http://localhost:8082
✅ Connected to orchestrator!
🎙️ Voice Control Active!
```

## Using Voice Control

### Supported Commands

The system recognizes natural language commands and automatically routes them to the appropriate persona:

#### Trader Commands
- "Trader, analyze bitcoin"
- "What's the market doing?"
- "Trading analysis for ethereum"

#### Educator Commands
- "Educator, teach me about blockchain"
- "Explain machine learning"
- "Teacher, what is quantum computing?"

#### Streamer Commands
- "Streamer, tell me a joke"
- "Let's have some fun"
- "Stream something entertaining"

### Command Structure

Commands are parsed for:
1. **Persona Detection**: Keywords identify which character to use
2. **Content Extraction**: The actual query or request
3. **Automatic Routing**: Commands go to S1 (simple) or S2 (complex) based on content

### Exit Commands

Say "stop listening" to quit the voice control.

## Configuration

### Changing WSL IP Address

If your WSL uses a different IP than localhost, edit `windows_voice_sender.py`:

```python
# Line 14
WSL_IP = "localhost"  # Change to your WSL2 IP
```

To find your WSL2 IP:
```cmd
wsl hostname -I
```

### Adjusting Microphone Sensitivity

The script auto-calibrates for ambient noise. If you experience issues:
- Speak clearly and at normal volume
- Ensure your microphone is selected as default in Windows
- Close other applications using the microphone

## Troubleshooting

### "Cannot connect to orchestrator"

1. Verify orchestrator is running:
   ```bash
   # In WSL
   docker ps | grep orchestrator
   ```

2. Check port accessibility:
   ```cmd
   # In Windows
   curl http://localhost:8082/health
   ```

3. Try WSL2 IP instead of localhost

### "No microphone found"

1. Check Windows sound settings
2. Ensure microphone permissions are granted
3. Test microphone in Windows Voice Recorder

### "Recognition errors"

1. Check internet connection (required for Google Speech)
2. Speak more clearly
3. Reduce background noise

### "Import errors"

Re-run the setup script:
```cmd
setup_windows_voice.bat
```

Or manually install:
```cmd
pip install SpeechRecognition requests pyaudio
```

## Advanced Features

### Custom Persona Keywords

Edit the `persona_keywords` dictionary in `windows_voice_sender.py`:

```python
self.persona_keywords = {
    'trader': ['trader', 'trading', 'market', 'bitcoin', 'crypto'],
    'educator': ['educator', 'teacher', 'teach', 'explain', 'learn'],
    'streamer': ['streamer', 'stream', 'joke', 'fun', 'game']
}
```

### Logging Commands

All commands are logged with timestamps and routing information:
```
💬 Heard: 'educator teach me about AI'
   → Routed to: system_2
   ✅ Sent to educator
```

### Network Configuration

For advanced network setups, you can modify the orchestrator URL:
```python
ORCHESTRATOR_URL = f"http://{WSL_IP}:{ORCHESTRATOR_PORT}"
```

## Best Practices

1. **Clear Commands**: Speak naturally but clearly
2. **Persona First**: Start with the persona name for better routing
3. **Concise Queries**: Keep commands focused and specific
4. **Wait for Processing**: Allow the system to process before next command

## Security Notes

- Voice commands are processed locally before sending
- Only text (not audio) is sent to the orchestrator
- No voice data is stored or logged
- Commands are routed through local network only

## Integration with VTuber System

The voice control integrates seamlessly with:
- Character switching based on persona
- Visual identity changes in Unreal Engine
- Speech generation with appropriate character voice
- Context-aware responses from S1/S2 systems

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all services are running
3. Review logs in both Windows and WSL terminals
4. Ensure network connectivity between Windows and WSL

---

*This system provides hands-free control of your VTuber orchestrator, enabling natural interaction with multiple AI personas through voice commands.*