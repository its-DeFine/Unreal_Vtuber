# Voice Control for VTuber Orchestrator

Control your VTuber system with natural voice commands!

## Features
- 🎤 Real-time voice recognition
- 🤖 Natural language command parsing
- 🎭 Automatic persona detection (trader/educator/streamer)
- 🚀 Direct orchestrator integration
- 🔌 Two implementations: Online (Google) and Offline (Vosk)

## Quick Start

### 1. Run Setup
```bash
cd scripts
./setup_voice_control.sh
```

Choose between:
- **Option 1**: Google Speech Recognition (easier, needs internet)
- **Option 2**: Vosk (offline, better performance, 40MB download)

### 2. Start Voice Control

For Google version:
```bash
python3 voice_orchestrator_gateway.py
```

For Vosk version:
```bash
python3 voice_orchestrator_vosk.py
```

## Usage Examples

Simply speak these commands:

### Educator Commands
- "Educator, teach me about blockchain"
- "Explain how smart contracts work"
- "What is cryptocurrency?"
- "Teach me about DeFi"

### Trader Commands
- "Trader, analyze bitcoin price"
- "Check the crypto market"
- "Analyze ethereum trends"
- "What's the market doing?"

### Streamer Commands
- "Streamer, tell me a joke"
- "Tell me a funny story"
- "Let's have some fun"
- "Play a game"

## How It Works

1. **Voice Input** → Microphone captures your speech
2. **Recognition** → Converts speech to text
3. **Parsing** → Extracts persona and intent
4. **Routing** → Sends to orchestrator
5. **Execution** → Appropriate character responds

## Architecture

```
Voice → Speech Recognition → Command Parser → Orchestrator API → VTuber Response
```

## Command Structure

Commands are parsed to detect:
- **Persona**: Which character should respond (trader/educator/streamer)
- **Action**: What type of response (teach/analyze/entertain)
- **Content**: The actual query or topic

## Tips

1. **Speak clearly** - Enunciate your words
2. **Use keywords** - Include persona names for better routing
3. **Natural language** - No need for rigid syntax
4. **Continuous listening** - Vosk version listens continuously

## Environment Variables

- `ORCHESTRATOR_URL`: Orchestrator endpoint (default: http://localhost:8082)
- `VOSK_MODEL_PATH`: Path to Vosk model (default: vosk-model-small-en-us-0.15)

## Troubleshooting

### "No module named 'pyaudio'"
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev
pip3 install pyaudio

# macOS
brew install portaudio
pip3 install pyaudio
```

### "Model not found"
Run the setup script to download the Vosk model:
```bash
./setup_voice_control.sh
```

### "Connection refused"
Make sure the orchestrator is running:
```bash
docker-compose -f docker-compose.all.yml up orchestrator
```

## Performance

- **Google version**: 
  - ~1-2 second latency
  - Requires internet
  - Very accurate

- **Vosk version**:
  - ~300-600ms latency
  - Completely offline
  - Good accuracy with small model

## Advanced Usage

### Custom Wake Word
Modify the code to add wake word detection:
```python
if "hey vtuber" in text.lower():
    # Process the rest of the command
```

### Custom Personas
Add new persona keywords in the script:
```python
self.persona_keywords = {
    'trader': [...],
    'educator': [...],
    'streamer': [...],
    'scientist': ['research', 'experiment', 'hypothesis']  # New!
}
```

---

Created: 2025-07-14