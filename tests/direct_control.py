#!/usr/bin/env python3
"""
Direct control script that sends specific commands to stop speech and clear queues
"""

import requests
import json
import time

BASE_URL = "http://localhost:5001"

def force_stop_and_clear():
    """Force stop all speech and clear queues"""
    print("🛑 Forcing complete stop and queue clear...")
    
    # 1. Send multiple interrupt commands
    print("⚡ Sending interrupt commands...")
    for i in range(3):
        try:
            response = requests.post(
                f"{BASE_URL}/orchestrator/control",
                json={"action": "interrupt"},
                timeout=1
            )
            print(f"   Interrupt {i+1}: {response.status_code}")
        except:
            pass
        time.sleep(0.1)
    
    # 2. Send empty direct speech to flush
    print("🔄 Flushing with empty speech...")
    try:
        response = requests.post(
            f"{BASE_URL}/orchestrator/control",
            json={
                "action": "queue_speech",
                "text": " ",  # Single space
                "priority": "urgent",
                "interrupt": True
            },
            timeout=2
        )
        print(f"   Flush speech: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    time.sleep(0.5)
    
    # 3. Send a test message with high priority
    print("📢 Sending test message...")
    try:
        response = requests.post(
            f"{BASE_URL}/orchestrator/control",
            json={
                "action": "queue_speech",
                "text": "System reset complete. I am now ready for your commands.",
                "priority": "urgent",
                "interrupt": True
            },
            timeout=2
        )
        print(f"   Test message: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 4. Check final status
    time.sleep(1)
    print("\n📊 Final status check...")
    try:
        response = requests.get(f"{BASE_URL}/orchestrator/status", timeout=2)
        if response.status_code == 200:
            status = response.json()
            print(f"   Is speaking: {status['current_action']['is_speaking']}")
            print(f"   Pending actions: {status.get('pending_actions', 0)}")
    except:
        pass

def send_direct_speech_bypassing_llm():
    """Send direct speech that bypasses LLM processing"""
    print("\n🎯 Sending direct speech (bypassing LLM)...")
    
    # This uses the direct_speech flag to bypass LLM
    payload = {
        "text": "Hello! This is a direct message bypassing the language model. The system is now under manual control.",
        "autonomous_context": {
            "source": "orchestrator_speech",
            "direct_speech": True,
            "is_directive": True
        },
        "direct_speech": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/process_text", json=payload, timeout=5)
        print(f"Direct speech response: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

def check_actual_state():
    """Try to understand the actual state"""
    print("\n🔍 Checking actual system state...")
    
    # Get orchestrator status
    try:
        response = requests.get(f"{BASE_URL}/orchestrator/status", timeout=2)
        if response.status_code == 200:
            status = response.json()
            print("\n📊 Orchestrator Status:")
            print(f"   Enabled: {status['enabled']}")
            print(f"   Running: {status['running']}")
            print(f"   Is speaking: {status['current_action']['is_speaking']}")
            print(f"   TTS queue: {status['current_action']['tts_queue_size']}")
            print(f"   Pending actions: {status.get('pending_actions', 0)}")
            
            # Check if there's a mismatch
            if not status['current_action']['is_speaking'] and status.get('pending_actions', 0) == 0:
                print("\n⚠️ WARNING: System shows no activity but you hear speech!")
                print("   This indicates a state tracking issue.")
    except Exception as e:
        print(f"Error checking status: {e}")

def main():
    print("🔧 Direct VTuber Control Tool")
    print("==============================")
    
    # First check the state
    check_actual_state()
    
    print("\n" + "="*50)
    print("Options:")
    print("1. Force stop all speech and clear queues")
    print("2. Send direct speech (bypass LLM)")
    print("3. Both (stop then send direct message)")
    print("="*50)
    
    choice = input("Select option (1-3): ").strip()
    
    if choice == "1":
        force_stop_and_clear()
    elif choice == "2":
        send_direct_speech_bypassing_llm()
    elif choice == "3":
        force_stop_and_clear()
        time.sleep(2)
        send_direct_speech_bypassing_llm()
    else:
        print("Invalid choice")
    
    # Final status check
    time.sleep(2)
    print("\n" + "="*50)
    check_actual_state()

if __name__ == "__main__":
    main() 