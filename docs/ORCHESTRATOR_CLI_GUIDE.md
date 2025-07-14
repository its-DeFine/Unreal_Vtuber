# Orchestrator CLI Guide
*Created: 2025-07-14*

## Overview

The Orchestrator CLI provides a text-based interface to control the VTuber orchestrator system. This solution works perfectly in WSL, Linux, and Windows environments without requiring any audio hardware or complex setup.

## Features

- 🌐 **Cross-platform**: Works in WSL, Linux, and Windows
- 🎯 **Auto-routing**: Automatically detects personas from natural language
- 🎨 **Color-coded**: Visual feedback with persona-specific colors
- 📜 **History tracking**: Review previous commands
- ⚡ **Real-time**: Instant routing to appropriate systems

## Quick Start

### 1. Start the Orchestrator

In one terminal:
```bash
cd /home/geo/directories/autonomy
docker-compose -f docker-compose.all.yml up orchestrator
```

### 2. Run the CLI

In another terminal:
```bash
cd scripts
./run_orchestrator_cli.sh
```

Or directly with Python:
```bash
python3 orchestrator_cli.py
```

## Usage

### Natural Language Commands

Just type naturally, and the system will detect the appropriate persona:

```
💬 > teach me about blockchain
🔄 Processing...
✅ 📚 Educator (system_2)

💬 > analyze bitcoin price trends
🔄 Processing...
✅ 📈 Trader (system_2)

💬 > tell me a joke
🔄 Processing...
✅ 🎮 Streamer (system_1)
```

### Explicit Persona Selection

Include the persona name for explicit routing:

```
💬 > educator, explain quantum computing
💬 > trader, what's happening with ethereum
💬 > streamer, let's have some fun
```

### Special Commands

- `help` - Show command examples and tips
- `history` - View last 10 commands
- `status` - Check orchestrator connection
- `clear` - Clear the screen
- `exit` or `quit` - Exit the CLI

## Persona Detection

The CLI automatically detects personas based on keywords:

### 📈 Trader
Keywords: trade, trading, market, bitcoin, crypto, stock
- "What's the market doing?"
- "Analyze crypto trends"
- "Trading opportunities today"

### 📚 Educator
Keywords: teach, explain, learn, what is, how does, education
- "Teach me about AI"
- "What is machine learning?"
- "Explain blockchain technology"

### 🎮 Streamer
Keywords: stream, joke, fun, play, game, entertain
- "Tell me something funny"
- "Let's play a game"
- "Entertain me"

## Architecture

```
┌─────────────────┐      HTTP API      ┌──────────────────┐
│                 │ ─────────────────→ │   Orchestrator   │
│  CLI Interface  │                    │   (Port 8082)    │
│                 │ ←───────────────── │                  │
└─────────────────┘      Response      └──────────────────┘
         │                                      │
         │                                      ↓
    User Input                          Route to S1/S2
         │                                      │
         ↓                                      ↓
  Natural Language                    Character Response
     Processing                         with Persona
```

## Configuration

### Custom Orchestrator URL

```bash
# Default: http://localhost:8082
python3 orchestrator_cli.py http://192.168.1.100:8082
```

Or set environment variable:
```bash
export ORCHESTRATOR_URL=http://custom-host:8082
./run_orchestrator_cli.sh
```

## Integration

The CLI integrates with the full VTuber system:
- Routes commands to appropriate S1/S2 systems
- Triggers character switching
- Updates visual identity in Unreal Engine
- Generates appropriate voice responses

## Troubleshooting

### "Cannot connect to orchestrator"

1. Ensure orchestrator is running:
   ```bash
   docker ps | grep orchestrator
   ```

2. Check the port is accessible:
   ```bash
   curl http://localhost:8082/health
   ```

3. Verify no firewall blocking

### "Command not recognized"

- Use natural language
- Include more context
- Check spelling of keywords

## Advanced Usage

### Batch Commands

You can pipe commands for automation:
```bash
echo "teach me about AI" | python3 orchestrator_cli.py
```

### Command History

History is stored in memory during the session. Use the `history` command to review recent interactions.

### Custom Personas

To add custom personas or keywords, edit the `personas` dictionary in `orchestrator_cli.py`.

## Benefits Over Voice Control

- **No audio hardware required**
- **Works everywhere** (WSL, SSH, containers)
- **Perfect accuracy** (no speech recognition errors)
- **Faster input** for complex queries
- **Copy/paste support**
- **Scriptable and automatable**

---

*This CLI provides reliable, cross-platform control of your VTuber orchestrator system without the complexity of audio handling.*