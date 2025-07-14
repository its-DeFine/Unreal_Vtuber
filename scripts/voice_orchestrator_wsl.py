#!/usr/bin/env python3
"""
Voice Orchestrator for WSL
Uses Windows host audio through WSL2 audio passthrough or network streaming
Created: 2025-07-14
"""
import os
import sys
import json
import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# HTTP client
import httpx

# For WSL audio, we have multiple options
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    print("Warning: SpeechRecognition not available")

# Check if we can use Windows PowerShell for audio
import subprocess
import platform


@dataclass
class VoiceCommand:
    """Parsed voice command"""
    persona: Optional[str]
    action: str
    content: str
    raw_text: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class WSLVoiceOrchestrator:
    """Voice control for WSL environments"""
    
    def __init__(self, orchestrator_url="http://localhost:8082"):
        self.orchestrator_url = orchestrator_url
        self.is_wsl = self._detect_wsl()
        
        print("🎤 WSL Voice Orchestrator")
        print(f"📡 Orchestrator: {self.orchestrator_url}")
        print(f"🖥️  WSL Detected: {self.is_wsl}")
        print("=" * 60)
        
        # Persona detection
        self.persona_keywords = {
            'trader': ['trader', 'trading', 'market', 'bitcoin', 'crypto'],
            'educator': ['educator', 'teacher', 'teach', 'explain', 'learn'],
            'streamer': ['streamer', 'stream', 'joke', 'fun', 'game']
        }
    
    def _detect_wsl(self) -> bool:
        """Detect if running in WSL"""
        return 'microsoft' in platform.uname().release.lower()
    
    def parse_command(self, text: str) -> Optional[VoiceCommand]:
        """Parse text into command"""
        text_lower = text.lower().strip()
        
        # Detect persona
        persona = None
        for p, keywords in self.persona_keywords.items():
            if any(kw in text_lower for kw in keywords):
                persona = p
                break
        
        # Detect action
        action = 'general'
        if any(w in text_lower for w in ['teach', 'explain', 'what is']):
            action = 'teach'
        elif any(w in text_lower for w in ['analyze', 'check', 'look']):
            action = 'analyze'
        elif any(w in text_lower for w in ['joke', 'fun', 'play']):
            action = 'entertain'
        
        return VoiceCommand(
            persona=persona,
            action=action,
            content=text,
            raw_text=text
        )
    
    async def route_command(self, command: VoiceCommand) -> Dict[str, Any]:
        """Route command to orchestrator"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            stimulus = {
                "stimulus_id": f"voice_{int(time.time()*1000)}",
                "text": command.content,
                "context": {"source": "voice_wsl"}
            }
            
            if command.persona:
                stimulus["context"]["persona"] = command.persona
            
            try:
                # Route through orchestrator
                route_resp = await client.post(f"{self.orchestrator_url}/route", json=stimulus)
                if route_resp.status_code != 200:
                    return {"error": f"Routing failed: {route_resp.status_code}"}
                
                routing = route_resp.json()
                
                # Execute
                exec_resp = await client.post(f"{self.orchestrator_url}/execute", json=routing)
                
                return {
                    "success": exec_resp.status_code == 200,
                    "routing": routing,
                    "persona": routing.get("config", {}).get("persona")
                }
                
            except Exception as e:
                return {"error": str(e)}
    
    def use_windows_speech_api(self):
        """Use Windows Speech Recognition through PowerShell"""
        print("\n🎙️ Using Windows Speech Recognition (via PowerShell)")
        print("This will open a PowerShell window on your Windows host")
        print("=" * 60)
        
        # PowerShell script for speech recognition
        ps_script = """
Add-Type -AssemblyName System.Speech
$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
$recognizer.SetInputToDefaultAudioDevice()

$grammar = New-Object System.Speech.Recognition.GrammarBuilder
$grammar.Append("trader analyze bitcoin")
$grammar.Append("educator teach me about")
$grammar.Append("streamer tell me a joke")
$recognizer.LoadGrammar((New-Object System.Speech.Recognition.Grammar $grammar))

Write-Host "Listening... Say 'exit' to stop"
while ($true) {
    $result = $recognizer.Recognize()
    if ($result.Text -eq "exit") { break }
    if ($result.Text) { Write-Output $result.Text }
}
"""
        
        # Save script temporarily
        script_path = "/tmp/voice_recognition.ps1"
        with open(script_path, 'w') as f:
            f.write(ps_script)
        
        # Run PowerShell on Windows host
        try:
            # Use PowerShell.exe from Windows
            cmd = f"powershell.exe -ExecutionPolicy Bypass -File {script_path}"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            print("\n🎤 PowerShell voice recognition started!")
            print("Speak into your Windows microphone...")
            
            # Read output from PowerShell
            for line in process.stdout:
                text = line.strip()
                if text:
                    print(f"\n💬 Heard: '{text}'")
                    command = self.parse_command(text)
                    if command:
                        asyncio.run(self._process_single_command(command))
                        
        except Exception as e:
            print(f"❌ PowerShell error: {e}")
    
    def use_network_audio_stream(self):
        """Use network audio streaming from Windows"""
        print("\n🌐 Network Audio Streaming Mode")
        print("=" * 60)
        print("\nTo use this mode:")
        print("1. On Windows, install VB-Audio Virtual Cable")
        print("2. Run a streaming server (e.g., VLC or FFmpeg)")
        print("3. Stream audio to WSL2 IP address")
        print("\nExample Windows command:")
        print('ffmpeg -f dshow -i audio="Microphone" -acodec pcm_s16le -ar 16000 -f s16le tcp://172.x.x.x:5555')
        print("\nThen this script will receive the audio stream")
        
        # Implementation would receive TCP audio stream
        # This is a placeholder for the concept
        print("\n❌ Network streaming not yet implemented")
        print("For now, use text input mode instead")
    
    def use_text_input_mode(self):
        """Simple text input mode for testing"""
        print("\n📝 Text Input Mode (WSL Compatible)")
        print("=" * 60)
        print("Type your commands as if speaking them:")
        print("Examples:")
        print("  • educator teach me about blockchain")
        print("  • trader analyze bitcoin")
        print("  • streamer tell me a joke")
        print("\nType 'exit' to quit")
        print("=" * 60)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while True:
            try:
                text = input("\n🎤 > ").strip()
                
                if text.lower() in ['exit', 'quit']:
                    print("👋 Goodbye!")
                    break
                
                if text:
                    command = self.parse_command(text)
                    if command:
                        loop.run_until_complete(self._process_single_command(command))
                        
            except KeyboardInterrupt:
                print("\n👋 Interrupted")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def _process_single_command(self, command: VoiceCommand):
        """Process a single command"""
        print(f"\n🚀 Processing: {command.content}")
        if command.persona:
            print(f"   Persona: {command.persona}")
        
        result = await self.route_command(command)
        
        if result.get("success"):
            persona = result.get("persona", "assistant")
            print(f"   ✅ Sent to {persona}")
        else:
            print(f"   ❌ Error: {result.get('error')}")
    
    def run(self):
        """Main entry point"""
        print("\n🎯 Choose input method:")
        print("1. Text input (works everywhere)")
        print("2. Windows Speech API (via PowerShell)")
        print("3. Network audio streaming (advanced)")
        
        if SR_AVAILABLE:
            print("4. Try direct microphone (may not work in WSL)")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "1":
            self.use_text_input_mode()
        elif choice == "2":
            self.use_windows_speech_api()
        elif choice == "3":
            self.use_network_audio_stream()
        elif choice == "4" and SR_AVAILABLE:
            self.try_direct_microphone()
        else:
            print("Using text input mode by default")
            self.use_text_input_mode()
    
    def try_direct_microphone(self):
        """Try to use microphone directly (may fail in WSL)"""
        print("\n🎤 Attempting direct microphone access...")
        
        try:
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                print("✅ Microphone initialized!")
                print("Adjusting for ambient noise...")
                recognizer.adjust_for_ambient_noise(source)
                
                print("\n🎤 Listening... Say 'exit' to stop")
                
                while True:
                    try:
                        audio = recognizer.listen(source, timeout=5)
                        text = recognizer.recognize_google(audio)
                        print(f"\n💬 Heard: '{text}'")
                        
                        if text.lower() == 'exit':
                            break
                            
                        command = self.parse_command(text)
                        if command:
                            asyncio.run(self._process_single_command(command))
                            
                    except sr.WaitTimeoutError:
                        pass
                    except sr.UnknownValueError:
                        print("❓ Could not understand")
                    except Exception as e:
                        print(f"❌ Error: {e}")
                        
        except Exception as e:
            print(f"❌ Microphone initialization failed: {e}")
            print("\nFalling back to text input mode...")
            self.use_text_input_mode()


def main():
    """Entry point"""
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8082")
    
    gateway = WSLVoiceOrchestrator(orchestrator_url)
    gateway.run()


if __name__ == "__main__":
    main()