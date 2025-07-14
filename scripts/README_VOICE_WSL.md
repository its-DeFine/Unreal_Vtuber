# Voice Control in WSL

Since WSL doesn't have direct access to Windows audio devices, here are several ways to use voice control:

## Option 1: Text Input Mode (Simplest)

Just type commands as if you were speaking them:

```bash
cd scripts
./run_voice_control.sh
# Choose option 1 (Text input)
```

Then type commands like:
- "educator teach me about blockchain"
- "trader analyze bitcoin"
- "streamer tell me a joke"

## Option 2: Windows Voice Sender (Recommended)

Run voice recognition on Windows and send commands to WSL:

### Setup on Windows:
1. Open Command Prompt or PowerShell on Windows (not WSL)
2. Navigate to the scripts folder
3. Run setup:
   ```cmd
   setup_windows_voice.bat
   ```

### Usage:
1. In WSL, make sure orchestrator is running:
   ```bash
   docker-compose -f docker-compose.all.yml up orchestrator
   ```

2. On Windows, run the voice sender:
   ```cmd
   python windows_voice_sender.py
   ```

3. Speak your commands!

## Option 3: WSL2 Audio Passthrough (Advanced)

If you have WSL2 with WSLg (GUI support), you might have audio:

1. Install PulseAudio in WSL:
   ```bash
   sudo apt update
   sudo apt install pulseaudio
   ```

2. Start PulseAudio:
   ```bash
   pulseaudio --start
   ```

3. Try the regular voice control:
   ```bash
   ./run_voice_control.sh
   # Choose option 3 (Try anyway)
   ```

## Option 4: Network Audio Streaming (Expert)

Stream audio from Windows to WSL via network:

### On Windows:
```cmd
# Install VB-Audio Virtual Cable
# Use FFmpeg to stream microphone to WSL
ffmpeg -f dshow -i audio="Microphone" -acodec pcm_s16le -ar 16000 -f s16le tcp://172.x.x.x:5555
```

### In WSL:
Configure the voice control to receive network audio (not yet implemented).

## Troubleshooting

### "Cannot connect to orchestrator"
1. Check orchestrator is running: `docker ps | grep orchestrator`
2. Check port forwarding: The orchestrator should be accessible at localhost:8082
3. Try using WSL2 IP instead of localhost

### "No audio devices found"
This is normal in WSL. Use one of the alternative methods above.

### Finding WSL2 IP Address
```bash
# In WSL:
hostname -I

# Or from Windows:
wsl hostname -I
```

## Architecture

```
Windows Host                    WSL2
┌─────────────────┐            ┌──────────────────┐
│ Microphone      │            │ Orchestrator     │
│     ↓           │            │   (port 8082)    │
│ Voice Recognition│  HTTP API  │       ↓          │
│     ↓           │ ────────→  │ Route & Execute  │
│ windows_voice_  │            │       ↓          │
│ sender.py       │            │ VTuber Response  │
└─────────────────┘            └──────────────────┘
```

## Quick Start Commands

### In WSL:
```bash
# Start orchestrator
docker-compose -f docker-compose.all.yml up orchestrator

# In another terminal, use text mode
cd scripts
./run_voice_control.sh
# Choose option 1
```

### On Windows (for voice):
```cmd
cd scripts
python windows_voice_sender.py
```

Now you can control your VTuber with voice commands even from WSL!

---
Created: 2025-07-14