#!/usr/bin/env python3
"""
Windows Voice Sender
Runs on Windows host and sends voice commands to WSL orchestrator
Created: 2025-07-14
"""
import speech_recognition as sr
import requests
import json
import time
import sys

# Configuration - update with your WSL2 IP
WSL_IP = "localhost"  # or your WSL2 IP address
ORCHESTRATOR_PORT = 8082
ORCHESTRATOR_URL = f"http://{WSL_IP}:{ORCHESTRATOR_PORT}"

def parse_command(text):
    """Simple command parsing"""
    text_lower = text.lower()
    
    # Detect persona
    persona = None
    if any(word in text_lower for word in ['trader', 'trading', 'market', 'bitcoin']):
        persona = 'trader'
    elif any(word in text_lower for word in ['educator', 'teacher', 'teach', 'explain']):
        persona = 'educator'
    elif any(word in text_lower for word in ['streamer', 'stream', 'joke', 'fun']):
        persona = 'streamer'
    
    return {
        'text': text,
        'persona': persona
    }

def send_to_orchestrator(command):
    """Send command to WSL orchestrator"""
    stimulus = {
        "stimulus_id": f"voice_win_{int(time.time()*1000)}",
        "text": command['text'],
        "context": {"source": "voice_windows"}
    }
    
    if command['persona']:
        stimulus["context"]["persona"] = command['persona']
    
    try:
        # Route through orchestrator
        route_response = requests.post(f"{ORCHESTRATOR_URL}/route", json=stimulus, timeout=10)
        if route_response.status_code != 200:
            print(f"❌ Routing failed: {route_response.status_code}")
            return False
        
        routing = route_response.json()
        print(f"   → Routed to: {routing.get('system')}")
        
        # Execute
        exec_response = requests.post(f"{ORCHESTRATOR_URL}/execute", json=routing, timeout=10)
        if exec_response.status_code == 200:
            print(f"   ✅ Sent to {routing.get('config', {}).get('persona', 'assistant')}")
            return True
        else:
            print(f"   ❌ Execution failed: {exec_response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to WSL orchestrator at {ORCHESTRATOR_URL}")
        print("Make sure:")
        print("1. The orchestrator is running in WSL")
        print("2. WSL2 networking is properly configured")
        print("3. Try using WSL2 IP instead of localhost")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main voice control loop on Windows"""
    print("🎤 Windows Voice Control for WSL Orchestrator")
    print("=" * 60)
    print(f"📡 Orchestrator URL: {ORCHESTRATOR_URL}")
    print("\nChecking connection to WSL...")
    
    # Test connection
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Connected to orchestrator!")
        else:
            print("⚠️  Orchestrator responded but may not be healthy")
    except:
        print("❌ Cannot connect to orchestrator")
        print("\nTroubleshooting:")
        print("1. Make sure orchestrator is running in WSL: docker-compose up orchestrator")
        print("2. Check WSL2 IP: wsl hostname -I")
        print("3. Update WSL_IP in this script")
        return
    
    print("\n🎙️ Voice Control Active!")
    print("=" * 60)
    print("Say commands like:")
    print("  • 'Educator, teach me about blockchain'")
    print("  • 'Trader, analyze bitcoin'")
    print("  • 'Streamer, tell me a joke'")
    print("\nSay 'stop listening' to quit")
    print("=" * 60)
    
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    # Calibrate for ambient noise
    print("\n🔧 Calibrating for ambient noise...")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    print("✅ Ready!\n")
    
    while True:
        try:
            with microphone as source:
                print("🎤 Listening...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
            print("🔄 Processing...")
            try:
                text = recognizer.recognize_google(audio)
                print(f"💬 Heard: '{text}'")
                
                # Check for exit
                if 'stop listening' in text.lower():
                    print("\n👋 Goodbye!")
                    break
                
                # Parse and send command
                command = parse_command(text)
                send_to_orchestrator(command)
                
            except sr.UnknownValueError:
                print("❓ Could not understand audio")
            except sr.RequestError as e:
                print(f"❌ Recognition error: {e}")
                
        except sr.WaitTimeoutError:
            pass  # Just timeout, continue listening
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Check if we have required packages
    try:
        import speech_recognition
        import requests
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("\nInstall with:")
        print("pip install SpeechRecognition requests pyaudio")
        sys.exit(1)
    
    main()