#!/usr/bin/env python3
"""
Voice Orchestrator Gateway (Vosk Version)
High-performance offline voice control for the VTuber orchestrator
Real-time streaming recognition with low latency
Created: 2025-07-14
"""
import os
import sys
import json
import time
import queue
import asyncio
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# HTTP client
import httpx

# Audio handling
try:
    import pyaudio
except ImportError:
    print("Please install PyAudio: pip install pyaudio")
    sys.exit(1)

# Vosk speech recognition
try:
    import vosk
except ImportError:
    print("Please install Vosk: pip install vosk")
    print("Also download a model from https://alphacephei.com/vosk/models")
    sys.exit(1)


@dataclass
class VoiceCommand:
    """Parsed voice command"""
    persona: Optional[str]
    action: str
    content: str
    raw_text: str
    confidence: float = 1.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class VoskVoiceOrchestrator:
    """High-performance voice control using Vosk"""
    
    def __init__(self, orchestrator_url="http://localhost:8082", model_path="vosk-model-small-en-us-0.15"):
        self.orchestrator_url = orchestrator_url
        self.model_path = model_path
        
        # Initialize Vosk
        if not os.path.exists(model_path):
            print(f"❌ Model not found at {model_path}")
            print("Download from: https://alphacephei.com/vosk/models")
            print("Recommended: vosk-model-small-en-us-0.15 (40MB)")
            sys.exit(1)
        
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        
        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Command processing
        self.command_queue = queue.Queue()
        self.is_running = False
        
        # Keywords for real-time detection
        self.keywords = {
            'personas': ['trader', 'educator', 'streamer', 'teacher'],
            'actions': ['teach', 'explain', 'analyze', 'tell', 'show'],
            'topics': ['blockchain', 'bitcoin', 'crypto', 'market', 'price']
        }
        
        # Build grammar for better recognition
        self._build_grammar()
        
        print("🎤 Vosk Voice Orchestrator Initialized")
        print(f"📡 Orchestrator: {self.orchestrator_url}")
        print(f"🧠 Model: {os.path.basename(model_path)}")
        print("=" * 60)
    
    def _build_grammar(self):
        """Build recognition grammar for better accuracy"""
        # Grammar helps Vosk focus on expected commands
        grammar = {
            "phrases": [
                "trader analyze bitcoin",
                "trader check the market",
                "educator teach me about blockchain",
                "educator explain smart contracts",
                "streamer tell me a joke",
                "streamer play a game",
                "what is cryptocurrency",
                "how does blockchain work",
                "analyze the price",
                "teach me about trading"
            ]
        }
        
        # Set grammar if recognizer supports it
        try:
            self.recognizer.SetGrammar(json.dumps(grammar))
        except:
            pass  # Not all models support grammar
    
    def parse_command(self, text: str, confidence: float = 1.0) -> Optional[VoiceCommand]:
        """Parse recognized text into command"""
        text_lower = text.lower().strip()
        
        # Skip empty or noise
        if not text_lower or len(text_lower) < 3:
            return None
        
        # Detect persona from keywords
        persona = None
        for p in ['trader', 'educator', 'streamer']:
            if p in text_lower:
                persona = p
                break
        
        # Alternative persona detection
        if not persona:
            if any(w in text_lower for w in ['teach', 'explain', 'learn']):
                persona = 'educator'
            elif any(w in text_lower for w in ['analyze', 'market', 'price', 'bitcoin']):
                persona = 'trader'
            elif any(w in text_lower for w in ['joke', 'fun', 'play', 'game']):
                persona = 'streamer'
        
        # Determine action
        action = 'general'
        if any(w in text_lower for w in ['teach', 'explain', 'what is', 'how']):
            action = 'teach'
        elif any(w in text_lower for w in ['analyze', 'check', 'look']):
            action = 'analyze'
        elif any(w in text_lower for w in ['joke', 'story', 'fun']):
            action = 'entertain'
        
        return VoiceCommand(
            persona=persona,
            action=action,
            content=text,
            raw_text=text,
            confidence=confidence
        )
    
    async def route_command(self, command: VoiceCommand) -> Dict[str, Any]:
        """Route command to orchestrator"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            stimulus = {
                "stimulus_id": f"voice_{int(time.time()*1000)}",
                "text": command.content,
                "context": {
                    "source": "voice",
                    "confidence": command.confidence
                }
            }
            
            if command.persona:
                stimulus["context"]["persona"] = command.persona
            
            try:
                # Get routing decision
                route_resp = await client.post(f"{self.orchestrator_url}/route", json=stimulus)
                if route_resp.status_code != 200:
                    return {"error": f"Routing failed: {route_resp.status_code}"}
                
                routing = route_resp.json()
                
                # Execute routing
                exec_resp = await client.post(f"{self.orchestrator_url}/execute", json=routing)
                
                return {
                    "success": exec_resp.status_code == 200,
                    "routing": routing,
                    "persona": routing.get("config", {}).get("persona")
                }
                
            except Exception as e:
                return {"error": str(e)}
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Audio stream callback for continuous recognition"""
        if self.recognizer.AcceptWaveform(in_data):
            result = json.loads(self.recognizer.Result())
            text = result.get('text', '').strip()
            
            if text:
                print(f"\n💬 Recognized: \"{text}\"")
                command = self.parse_command(text)
                if command:
                    self.command_queue.put(command)
        else:
            # Partial result for real-time feedback
            partial = json.loads(self.recognizer.PartialResult())
            partial_text = partial.get('partial', '').strip()
            if partial_text:
                print(f"\r🎤 Listening: {partial_text}...", end='', flush=True)
        
        return (in_data, pyaudio.paContinue)
    
    async def process_commands(self):
        """Process commands asynchronously"""
        while self.is_running:
            try:
                # Non-blocking check
                try:
                    command = self.command_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.1)
                    continue
                
                print(f"\n🚀 Processing: {command.content}")
                if command.persona:
                    print(f"   Persona: {command.persona}")
                
                result = await self.route_command(command)
                
                if result.get("success"):
                    persona = result.get("persona", "assistant")
                    print(f"   ✅ Sent to {persona}")
                else:
                    print(f"   ❌ Error: {result.get('error')}")
                
            except Exception as e:
                print(f"❌ Processing error: {e}")
    
    def run(self):
        """Main voice control loop"""
        print("\n🎙️ Vosk Voice Control Active!")
        print("=" * 60)
        print("Commands:")
        print("  • 'trader analyze bitcoin'")
        print("  • 'educator teach me about blockchain'")
        print("  • 'streamer tell me a joke'")
        print("  • Say 'stop listening' to quit")
        print("=" * 60)
        print("\n🎤 Listening continuously...\n")
        
        self.is_running = True
        
        # Start command processor
        loop = asyncio.new_event_loop()
        processor = threading.Thread(
            target=lambda: loop.run_until_complete(self.process_commands()),
            daemon=True
        )
        processor.start()
        
        # Open audio stream
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8192,
            stream_callback=self.audio_callback
        )
        
        self.stream.start_stream()
        
        try:
            # Keep running until interrupted
            while self.is_running and self.stream.is_active():
                time.sleep(0.1)
                
                # Check for stop command in queue
                if not self.command_queue.empty():
                    # Peek at commands for stop
                    items = []
                    while not self.command_queue.empty():
                        cmd = self.command_queue.get()
                        items.append(cmd)
                        if 'stop' in cmd.content.lower() and 'listening' in cmd.content.lower():
                            print("\n\n🛑 Stop command received")
                            self.is_running = False
                            break
                    
                    # Put back non-stop commands
                    for item in items:
                        if self.is_running:
                            self.command_queue.put(item)
                            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted")
        finally:
            # Cleanup
            self.is_running = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.audio.terminate()
            print("✅ Voice control stopped")


def main():
    """Entry point"""
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8082")
    model_path = os.getenv("VOSK_MODEL_PATH", "vosk-model-small-en-us-0.15")
    
    print("🚀 Starting Vosk Voice Orchestrator")
    print(f"📁 Model path: {model_path}")
    
    gateway = VoskVoiceOrchestrator(orchestrator_url, model_path)
    gateway.run()


if __name__ == "__main__":
    main()