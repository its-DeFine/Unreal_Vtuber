#!/bin/bash
# Run Voice Control with Virtual Environment
# Created: 2025-07-14

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/voice_control_env"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found. Creating it..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install pyaudio SpeechRecognition httpx pyttsx3 vosk
    deactivate
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

echo "🎤 Voice Control for VTuber Orchestrator"
echo "========================================"
echo
echo "Choose voice recognition mode:"
echo "1) Google Speech Recognition (online)"
echo "2) Vosk (offline, low latency)"
echo
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo
    echo "🌐 Starting Google Speech Recognition mode..."
    python3 "$SCRIPT_DIR/voice_orchestrator_gateway.py"
elif [ "$choice" = "2" ]; then
    # Check if Vosk model exists
    MODEL_PATH="$SCRIPT_DIR/vosk-model-small-en-us-0.15"
    if [ ! -d "$MODEL_PATH" ]; then
        echo
        echo "📥 Downloading Vosk model (40MB)..."
        cd "$SCRIPT_DIR"
        wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
        unzip -q vosk-model-small-en-us-0.15.zip
        rm vosk-model-small-en-us-0.15.zip
        echo "✅ Model downloaded"
    fi
    
    echo
    echo "🔌 Starting Vosk offline mode..."
    cd "$SCRIPT_DIR"
    python3 voice_orchestrator_vosk.py
else
    echo "❌ Invalid choice"
    deactivate
    exit 1
fi

# Deactivate virtual environment when done
deactivate