#!/usr/bin/env python3
"""
Interactive script to control the VTuber container
- Check status
- Interrupt current speech
- Send environment change commands
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:5001"

def check_status():
    """Check orchestrator status"""
    print("\n📊 Checking Orchestrator Status...")
    try:
        response = requests.get(f"{BASE_URL}/orchestrator/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Orchestrator is {'running' if status.get('running', False) else 'stopped'}")
            print(f"   - Is speaking: {status['current_action']['is_speaking']}")
            print(f"   - TTS queue size: {status['current_action']['tts_queue_size']}")
            print(f"   - Current environment: {status['current_action']['current_environment']}")
            print(f"   - Pending actions: {status.get('pending_actions', 0)}")
            return status
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to container. Is it running on port 5001?")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def interrupt_speech():
    """Interrupt current speech"""
    print("\n⚡ Interrupting current activity...")
    try:
        response = requests.post(
            f"{BASE_URL}/orchestrator/control",
            json={"action": "interrupt"},
            timeout=5
        )
        if response.status_code == 200:
            print("✅ Interrupt sent successfully")
            return True
        else:
            print(f"❌ Failed to interrupt: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error interrupting: {e}")
        return False

def send_environment_change(prompt):
    """Send environment change command"""
    print(f"\n🎮 Sending environment change: {prompt}")
    try:
        # First interrupt if speaking
        status = check_status()
        if status and status['current_action']['is_speaking']:
            interrupt_speech()
            time.sleep(0.5)
        
        # Send environment change with high priority
        response = requests.post(
            f"{BASE_URL}/process_text",
            json={
                "text": prompt,
                "autonomous_context": {
                    "source": "orchestrator_environment",
                    "priority": "urgent"
                }
            },
            timeout=5
        )
        if response.status_code == 200:
            print("✅ Environment change command sent")
            return True
        else:
            print(f"❌ Failed to send command: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def queue_direct_speech(text, priority="high"):
    """Queue direct speech"""
    print(f"\n🗣️ Queueing direct speech: {text[:50]}...")
    try:
        response = requests.post(
            f"{BASE_URL}/orchestrator/control",
            json={
                "action": "queue_speech",
                "text": text,
                "priority": priority,
                "interrupt": True
            },
            timeout=5
        )
        if response.status_code == 200:
            print("✅ Speech queued successfully")
            return True
        else:
            print(f"❌ Failed to queue speech: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def send_custom_text(text):
    """Send custom text for processing"""
    print(f"\n💬 Sending text: {text}")
    try:
        response = requests.post(
            f"{BASE_URL}/process_text",
            json={
                "text": text,
                "autonomous_context": "user_request"
            },
            timeout=5
        )
        if response.status_code == 200:
            print("✅ Text sent successfully")
            return True
        else:
            print(f"❌ Failed to send text: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def interactive_menu():
    """Interactive menu for controlling the VTuber"""
    while True:
        print("\n" + "="*60)
        print("🎭 VTuber Control Menu")
        print("="*60)
        print("1. Check status")
        print("2. Interrupt current speech")
        print("3. Change environment (scene/appearance)")
        print("4. Queue direct speech")
        print("5. Send custom text")
        print("6. Quick environment presets")
        print("0. Exit")
        print("-"*60)
        
        choice = input("Select option: ").strip()
        
        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "1":
            check_status()
        elif choice == "2":
            interrupt_speech()
        elif choice == "3":
            prompt = input("Enter environment change (e.g., 'change hair to blue', 'set medieval scene'): ").strip()
            if prompt:
                send_environment_change(prompt)
        elif choice == "4":
            text = input("Enter exact text to speak: ").strip()
            if text:
                queue_direct_speech(text)
        elif choice == "5":
            text = input("Enter text to process: ").strip()
            if text:
                send_custom_text(text)
        elif choice == "6":
            print("\n🎨 Environment Presets:")
            print("a. Medieval fantasy scene")
            print("b. Futuristic cyberpunk")
            print("c. Beach sunset")
            print("d. Space station")
            print("e. Change hair color")
            print("f. Change lighting")
            
            preset = input("Select preset: ").strip().lower()
            presets = {
                'a': "Set a medieval fantasy scene with castle walls and torches",
                'b': "Change to a futuristic cyberpunk environment with neon lights",
                'c': "Set a peaceful beach scene at sunset",
                'd': "Change environment to a space station with stars visible",
                'e': "Change my hair color to " + input("Enter color: ").strip(),
                'f': "Change the lighting to " + input("Enter lighting type (warm/cool/dramatic): ").strip()
            }
            
            if preset in presets:
                send_environment_change(presets[preset])
        
        time.sleep(1)  # Brief pause before showing menu again

def main():
    """Main function"""
    print("🎭 VTuber Container Interaction Tool")
    print("=====================================")
    
    # First check if we can connect
    status = check_status()
    if not status:
        print("\n⚠️ Cannot connect to VTuber container.")
        print("Make sure:")
        print("  1. Container is running")
        print("  2. Port 5001 is accessible")
        print("  3. AUTONOMOUS_ORCHESTRATION_ENABLED=true")
        return
    
    # If it's speaking and repeating, offer to interrupt
    if status['current_action']['is_speaking']:
        print("\n⚠️ The VTuber appears to be speaking.")
        if input("Would you like to interrupt? (y/n): ").lower() == 'y':
            interrupt_speech()
            time.sleep(1)
    
    # Start interactive menu
    interactive_menu()

if __name__ == "__main__":
    main() 