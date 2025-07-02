#!/usr/bin/env python3
"""
Monitor blendshape streaming to determine actual speaking state
and implement proper interruption based on that
"""

import requests
import json
import time
import threading

BASE_URL = "http://localhost:5001"

# Global state tracking
blendshape_streaming_active = False
last_blendshape_update = 0

def monitor_blendshape_state():
    """Monitor orchestrator status and detect real speaking state"""
    global blendshape_streaming_active, last_blendshape_update
    
    print("👁️ Starting blendshape monitoring...")
    previous_state = None
    speaking_detected = False
    
    while True:
        try:
            response = requests.get(f"{BASE_URL}/orchestrator/status", timeout=1)
            if response.status_code == 200:
                status = response.json()
                current_state = status['current_action']
                
                # Check if blendshape state changed
                if current_state['blendshape_active']:
                    if not speaking_detected:
                        print("🎭 Blendshape streaming STARTED - Speech detected!")
                        speaking_detected = True
                        last_blendshape_update = time.time()
                    blendshape_streaming_active = True
                else:
                    if speaking_detected:
                        print("🔇 Blendshape streaming STOPPED - Speech ended!")
                        speaking_detected = False
                    blendshape_streaming_active = False
                
                # Detect state mismatches
                audio_speaking = current_state['is_speaking']
                if audio_speaking != speaking_detected:
                    print(f"⚠️ State mismatch! Audio state: {audio_speaking}, Blendshape state: {speaking_detected}")
                
                # Show periodic status
                if time.time() - last_blendshape_update > 5:
                    print(f"📊 Status - Blendshapes: {current_state['blendshape_active']}, "
                          f"Audio: {audio_speaking}, Queue: {current_state['tts_queue_size']}")
                    last_blendshape_update = time.time()
                
        except Exception as e:
            print(f"❌ Monitor error: {e}")
        
        time.sleep(0.1)  # Check every 100ms

def wait_for_blendshapes_to_stop(timeout=10):
    """Wait for blendshape streaming to stop"""
    print("⏳ Waiting for blendshapes to stop...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if not blendshape_streaming_active:
            print("✅ Blendshapes stopped!")
            return True
        time.sleep(0.1)
    
    print("⏱️ Timeout waiting for blendshapes to stop")
    return False

def smart_interrupt():
    """Interrupt based on actual blendshape state"""
    print("\n🎯 Smart interrupt based on blendshape state")
    
    # 1. Check current state
    try:
        response = requests.get(f"{BASE_URL}/orchestrator/status", timeout=2)
        if response.status_code == 200:
            status = response.json()
            blendshape_active = status['current_action']['blendshape_active']
            audio_active = status['current_action']['is_speaking']
            
            print(f"Current state - Blendshapes: {blendshape_active}, Audio: {audio_active}")
            
            if not blendshape_active and not audio_active:
                print("✅ System is already idle")
                return True
    except:
        pass
    
    # 2. Send interrupt commands
    print("⚡ Sending interrupt commands...")
    for i in range(3):
        try:
            # Regular interrupt
            requests.post(f"{BASE_URL}/orchestrator/control", 
                         json={"action": "interrupt"}, timeout=1)
            
            # Also try to queue an empty speech to flush
            requests.post(f"{BASE_URL}/orchestrator/control",
                         json={
                             "action": "queue_speech",
                             "text": " ",
                             "priority": "urgent",
                             "interrupt": True
                         }, timeout=1)
        except:
            pass
        time.sleep(0.1)
    
    # 3. Wait for blendshapes to actually stop
    if wait_for_blendshapes_to_stop(timeout=5):
        print("✅ Successfully interrupted!")
        return True
    else:
        print("❌ Failed to interrupt within timeout")
        return False

def send_controlled_speech(text):
    """Send speech and monitor blendshape streaming"""
    print(f"\n📢 Sending speech: {text}")
    
    # First ensure system is idle
    if blendshape_streaming_active:
        print("System is busy, interrupting first...")
        if not smart_interrupt():
            print("Failed to interrupt, trying anyway...")
    
    # Send the speech
    try:
        response = requests.post(
            f"{BASE_URL}/process_text",
            json={
                "text": text,
                "direct_speech": True,
                "autonomous_context": {
                    "source": "orchestrator_speech",
                    "direct_speech": True
                }
            },
            timeout=5
        )
        print(f"Speech sent: {response.status_code}")
        
        # Wait a bit for blendshapes to start
        time.sleep(0.5)
        
        # Monitor until completion
        print("📊 Monitoring blendshape streaming...")
        start_time = time.time()
        max_duration = 30  # Max 30 seconds monitoring
        
        while time.time() - start_time < max_duration:
            if blendshape_streaming_active:
                print("🎭 Blendshapes active...")
                time.sleep(1)
            else:
                print("✅ Speech completed!")
                break
                
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🎭 Blendshape-Based VTuber Monitor & Control")
    print("=" * 50)
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_blendshape_state, daemon=True)
    monitor_thread.start()
    
    # Give monitor time to start
    time.sleep(1)
    
    while True:
        print("\n" + "="*50)
        print("Options:")
        print("1. Check current state")
        print("2. Smart interrupt (based on blendshapes)")
        print("3. Send controlled speech")
        print("4. Monitor only (watch state changes)")
        print("0. Exit")
        print("="*50)
        
        choice = input("Select option: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            try:
                response = requests.get(f"{BASE_URL}/orchestrator/status", timeout=2)
                if response.status_code == 200:
                    status = response.json()
                    current = status['current_action']
                    print(f"\n📊 Current State:")
                    print(f"   Blendshapes active: {current['blendshape_active']}")
                    print(f"   Audio speaking: {current['is_speaking']}")
                    print(f"   TTS queue: {current['tts_queue_size']}")
                    print(f"   Pending actions: {status.get('pending_actions', 0)}")
            except Exception as e:
                print(f"Error: {e}")
                
        elif choice == "2":
            smart_interrupt()
            
        elif choice == "3":
            text = input("Enter text to speak: ").strip()
            if text:
                send_controlled_speech(text)
                
        elif choice == "4":
            print("Monitoring blendshape state (press Ctrl+C to stop)...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nMonitoring stopped")

if __name__ == "__main__":
    main() 