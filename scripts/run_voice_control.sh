#!/bin/bash
# Run Voice Control from WSL
# This script helps WSL users run the Windows voice control
# Created: 2025-07-14

echo "🎤 Voice Control for VTuber Orchestrator (WSL)"
echo "============================================="
echo
echo "⚠️  WSL does not support microphone access natively."
echo
echo "To use voice control, please run on Windows:"
echo
echo "1. Open Command Prompt or PowerShell on Windows (not WSL)"
echo "2. Navigate to the scripts folder:"
echo "   cd /path/to/autonomy/scripts"
echo
echo "3. Run the setup (first time only):"
echo "   setup_windows_voice.bat"
echo
echo "4. Run the voice control:"
echo "   python windows_voice_sender.py"
echo
echo "Make sure the orchestrator is running in WSL:"
echo "   docker-compose -f docker-compose.all.yml up orchestrator"
echo
echo "For detailed instructions, see:"
echo "   docs/WINDOWS_VOICE_CONTROL_SETUP.md"