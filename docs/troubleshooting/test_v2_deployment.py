#!/usr/bin/env python3
"""
Test V2 Autonomous Orchestrator Deployment
Verifies that the V2 system is working correctly
"""

import time
import requests
import json

def test_v2_deployment():
    """Test the V2 deployment"""
    
    base_url = "http://localhost:5001"
    
    print("🧪 Testing V2 Autonomous Orchestrator Deployment")
    print("=" * 50)
    
    # 1. Check orchestrator status
    print("\n1. Checking orchestrator status...")
    try:
        response = requests.get(f"{base_url}/orchestrator/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Orchestrator status: {json.dumps(status, indent=2)}")
            
            # Check for V2 specific fields
            if 'min_idle_time' in str(status):
                print("✅ V2 configuration detected!")
            else:
                print("⚠️ V2 configuration may not be active")
        else:
            print(f"❌ Status check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking status: {e}")
    
    # 2. Test direct speech (should bypass orchestrator)
    print("\n2. Testing direct speech...")
    try:
        response = requests.post(
            f"{base_url}/process_text",
            json={
                "text": "V2 test: Direct speech works",
                "direct_speech": True
            }
        )
        if response.status_code == 200:
            print("✅ Direct speech accepted")
        else:
            print(f"❌ Direct speech failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error with direct speech: {e}")
    
    # 3. Monitor autonomous behavior timing
    print("\n3. Monitoring autonomous behavior (30 seconds)...")
    print("Expected behavior:")
    print("- Should wait 10-15 seconds before first autonomous speech")
    print("- Speeches should be short (under 100 chars)")
    print("- 3-5 second gaps between speeches")
    print("\nStarting monitor...")
    
    start_time = time.time()
    last_check = start_time
    
    while time.time() - start_time < 30:
        current_time = time.time()
        
        # Check every 2 seconds
        if current_time - last_check >= 2:
            elapsed = current_time - start_time
            print(f"\r⏱️ {elapsed:.1f}s - Monitoring...", end="", flush=True)
            
            # Check orchestrator status
            try:
                response = requests.get(f"{base_url}/orchestrator/status", timeout=1)
                if response.status_code == 200:
                    status = response.json()
                    if status.get('current_action', {}).get('is_speaking'):
                        print(f"\n🗣️ Speaking detected at {elapsed:.1f}s!")
            except:
                pass
                
            last_check = current_time
            
        time.sleep(0.1)
    
    print("\n\n✅ Monitoring complete")
    
    # 4. Test interruption
    print("\n4. Testing interruption...")
    try:
        # Trigger autonomous speech
        response = requests.post(
            f"{base_url}/process_text",
            json={
                "text": "Start talking about the weather",
                "autonomous_context": {"source": "test"}
            }
        )
        
        time.sleep(0.5)  # Let it start
        
        # Send interrupt
        response = requests.post(
            f"{base_url}/process_text",
            json={
                "text": "Stop! Tell me about cats instead",
                "priority": "urgent"
            }
        )
        
        if response.status_code == 200:
            print("✅ Interruption sent successfully")
        else:
            print(f"❌ Interruption failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing interruption: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 V2 deployment test complete!")
    print("\nNext steps:")
    print("1. Check docker logs: docker-compose logs -f neurosync")
    print("2. Look for [DECISION], [SPEECH], [STATE] log patterns")
    print("3. Verify natural timing behavior")


if __name__ == "__main__":
    test_v2_deployment() 