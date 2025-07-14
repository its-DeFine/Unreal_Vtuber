#!/usr/bin/env python3
"""
Voice Orchestrator Gateway
A compact voice control interface for the VTuber orchestrator system
Supports commands like "educator teach me about blockchain" or "trader analyze bitcoin"
Created: 2025-07-14
"""
import os
import sys
import json
import time
import asyncio
import threading
import queue
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# HTTP client for orchestrator API
import httpx

# Speech recognition - using SpeechRecognition for simplicity
# For production, consider Vosk for offline, real-time recognition
try:
    import speech_recognition as sr
except ImportError:
    print("Please install speech recognition: pip install SpeechRecognition")
    sys.exit(1)

# Try to import pyttsx3 for text-to-speech feedback
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    print("Warning: pyttsx3 not available. Install with: pip install pyttsx3")
    TTS_AVAILABLE = False


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


class VoiceOrchestrator:
    """Voice control gateway for orchestrator"""
    
    def __init__(self, orchestrator_url="http://localhost:8082"):
        self.orchestrator_url = orchestrator_url
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Command queue for async processing
        self.command_queue = queue.Queue()
        
        # TTS engine for feedback
        self.tts = None
        if TTS_AVAILABLE:
            self.tts = pyttsx3.init()
            self.tts.setProperty('rate', 180)  # Slightly faster speech
        
        # Persona keywords
        self.persona_keywords = {
            'trader': ['trader', 'trading', 'market', 'bitcoin', 'crypto', 'analyze'],
            'educator': ['educator', 'teacher', 'teach', 'explain', 'learn', 'education'],
            'streamer': ['streamer', 'stream', 'entertainment', 'fun', 'joke', 'story']
        }
        
        # Action keywords
        self.action_keywords = {
            'teach': ['teach', 'explain', 'tell me about', 'what is', 'how does'],
            'analyze': ['analyze', 'analysis', 'check', 'look at', 'evaluate'],
            'entertain': ['joke', 'story', 'fun', 'play', 'game']
        }
        
        print("🎤 Voice Orchestrator Gateway Initialized")
        print(f"📡 Orchestrator URL: {self.orchestrator_url}")
        print("=" * 60)
    
    def speak(self, text: str):
        """Provide audio feedback"""
        if self.tts:
            self.tts.say(text)
            self.tts.runAndWait()
        else:
            print(f"🔊 {text}")
    
    def parse_command(self, text: str) -> Optional[VoiceCommand]:
        """Parse voice input into structured command"""
        text_lower = text.lower()
        
        # Detect persona
        persona = None
        for p, keywords in self.persona_keywords.items():
            if any(kw in text_lower for kw in keywords):
                persona = p
                break
        
        # Detect action type
        action = 'general'
        for act, keywords in self.action_keywords.items():
            if any(kw in text_lower for kw in keywords):
                action = act
                break
        
        # Extract content - remove persona keywords to get cleaner content
        content = text
        if persona:
            for kw in self.persona_keywords[persona]:
                content = content.replace(kw, '').replace(kw.capitalize(), '')
        
        # Clean up common command words
        for phrase in ['please', 'can you', 'could you', 'i want', 'i need']:
            content = content.replace(phrase, '')
        
        content = ' '.join(content.split())  # Clean extra spaces
        
        return VoiceCommand(
            persona=persona,
            action=action,
            content=content.strip() or text,
            raw_text=text
        )
    
    async def route_to_orchestrator(self, command: VoiceCommand) -> Dict[str, Any]:
        """Send command to orchestrator"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare stimulus
            stimulus = {
                "stimulus_id": f"voice_{int(time.time()*1000)}",
                "text": command.content,
                "context": {
                    "source": "voice",
                    "action": command.action
                }
            }
            
            # Add persona hint if detected
            if command.persona:
                stimulus["context"]["persona"] = command.persona
            
            try:
                # Route through orchestrator
                print(f"\n📤 Routing: {command.content}")
                if command.persona:
                    print(f"   Persona: {command.persona}")
                
                # First, get routing decision
                route_response = await client.post(
                    f"{self.orchestrator_url}/route",
                    json=stimulus
                )
                
                if route_response.status_code != 200:
                    return {"error": f"Routing failed: {route_response.status_code}"}
                
                routing = route_response.json()
                print(f"   → Routed to: {routing.get('system')}")
                
                # Execute the routing
                exec_response = await client.post(
                    f"{self.orchestrator_url}/execute",
                    json=routing
                )
                
                if exec_response.status_code == 200:
                    return {"success": True, "routing": routing}
                else:
                    return {"error": f"Execution failed: {exec_response.status_code}"}
                    
            except Exception as e:
                return {"error": str(e)}
    
    def listen_once(self) -> Optional[str]:
        """Listen for a single voice command"""
        with self.microphone as source:
            # Adjust for ambient noise
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            print("\n🎤 Listening...")
            try:
                # Listen with timeout
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                # Recognize speech
                print("🔄 Processing...")
                text = self.recognizer.recognize_google(audio)
                print(f"📝 Heard: \"{text}\"")
                return text
                
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                print("❓ Could not understand audio")
                return None
            except sr.RequestError as e:
                print(f"❌ Recognition error: {e}")
                return None
    
    async def process_commands(self):
        """Process commands from queue"""
        while True:
            try:
                if not self.command_queue.empty():
                    command = self.command_queue.get()
                    
                    # Route to orchestrator
                    result = await self.route_to_orchestrator(command)
                    
                    if result.get("success"):
                        routing = result.get("routing", {})
                        persona = routing.get("config", {}).get("persona", "assistant")
                        self.speak(f"Sending to {persona}")
                    else:
                        self.speak("Sorry, there was an error")
                        print(f"❌ Error: {result.get('error')}")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Processing error: {e}")
    
    def run(self):
        """Main voice control loop"""
        print("\n🎙️ Voice Control Active!")
        print("=" * 60)
        print("Example commands:")
        print("  • 'Educator, teach me about blockchain'")
        print("  • 'Trader, analyze bitcoin price'")
        print("  • 'Streamer, tell me a joke'")
        print("  • 'Explain how smart contracts work'")
        print("\nSay 'stop' or 'exit' to quit")
        print("=" * 60)
        
        # Start async command processor
        loop = asyncio.new_event_loop()
        processor_thread = threading.Thread(
            target=lambda: loop.run_until_complete(self.process_commands()),
            daemon=True
        )
        processor_thread.start()
        
        # Calibrate microphone
        print("\n🔧 Calibrating for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print("✅ Ready!")
        self.speak("Voice control ready")
        
        # Main listening loop
        try:
            while True:
                text = self.listen_once()
                
                if text:
                    # Check for exit commands
                    if any(word in text.lower() for word in ['stop', 'exit', 'quit']):
                        self.speak("Goodbye")
                        break
                    
                    # Parse and queue command
                    command = self.parse_command(text)
                    if command:
                        self.command_queue.put(command)
                        self.speak("Processing")
                
        except KeyboardInterrupt:
            print("\n\n👋 Voice control stopped")
        finally:
            # Cleanup
            if self.tts:
                self.tts.stop()


def main():
    """Entry point"""
    # Get orchestrator URL from environment or use default
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8082")
    
    # Create and run voice gateway
    gateway = VoiceOrchestrator(orchestrator_url)
    gateway.run()


if __name__ == "__main__":
    main()