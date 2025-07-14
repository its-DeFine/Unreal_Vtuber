#!/bin/bash
# Setup script for Voice Orchestrator Gateway
# Created: 2025-07-14

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/voice_control_env"

echo "🎤 Voice Orchestrator Setup"
echo "=========================="
echo

# Check Python version
python3 --version >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip >/dev/null 2>&1

echo "Choose your voice recognition engine:"
echo "1) Google Speech Recognition (easier, requires internet)"
echo "2) Vosk (offline, better performance)"
echo
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo
    echo "📦 Installing Google Speech Recognition dependencies..."
    pip install SpeechRecognition pyaudio pyttsx3 httpx
    
    echo
    echo "✅ Setup complete!"
    echo
    echo "To run the voice control:"
    echo "  ./run_voice_control.sh"
    echo
    echo "Note: This requires internet connection for speech recognition"
    
elif [ "$choice" = "2" ]; then
    echo
    echo "📦 Installing Vosk dependencies..."
    pip install vosk pyaudio httpx
    
    echo
    echo "📥 Downloading Vosk model (40MB)..."
    if [ ! -d "vosk-model-small-en-us-0.15" ]; then
        wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
        unzip -q vosk-model-small-en-us-0.15.zip
        rm vosk-model-small-en-us-0.15.zip
        echo "✅ Model downloaded"
    else
        echo "✅ Model already exists"
    fi
    
    echo
    echo "✅ Setup complete!"
    echo
    echo "To run the voice control:"
    echo "  ./run_voice_control.sh"
    echo
    echo "This works completely offline with low latency"
    
else
    echo "❌ Invalid choice"
    exit 1
fi

echo
echo "🎯 Make sure the orchestrator is running at http://localhost:8082"
echo "   or set ORCHESTRATOR_URL environment variable"
echo
echo "Example commands you can say:"
echo "  • 'Educator, teach me about blockchain'"
echo "  • 'Trader, analyze bitcoin price'"
echo "  • 'Streamer, tell me a joke'"
echo

# Deactivate virtual environment
deactivate