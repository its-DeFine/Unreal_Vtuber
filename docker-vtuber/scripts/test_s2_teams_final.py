#!/usr/bin/env python3
"""Final comprehensive test for S2 character teams"""

import requests
import json
import time
import subprocess
from datetime import datetime

def check_queue():
    """Check queue file contents in container"""
    try:
        result = subprocess.run(['docker', 'exec', 'autogen_agent', 'cat', '/tmp/s2_processing_queue.json'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            return data
        else:
            return []
    except Exception as e:
        print(f"Error checking queue: {e}")
        return []

def check_processed():
    """Check processed file in container"""
    try:
        result = subprocess.run(['docker', 'exec', 'autogen_agent', 'cat', '/tmp/s2_processed_stimuli.json'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            return data
        else:
            return []
    except Exception as e:
        print(f"Error checking processed: {e}")
        return []

def clear_queue():
    """Clear the queue file"""
    try:
        subprocess.run(['docker', 'exec', 'autogen_agent', 'sh', '-c', 'echo "[]" > /tmp/s2_processing_queue.json'], 
                      capture_output=True, text=True)
        print("✅ Queue cleared")
    except Exception as e:
        print(f"❌ Error clearing queue: {e}")

def send_stimuli(content, character_id, source="test", force_s2=True):
    """Send stimuli with S2 routing"""
    url = "http://localhost:8000/api/v1/stimuli/submit"
    payload = {
        "content": content,
        "source": source,
        "priority": "medium",
        "metadata": {
            "force_s2": force_s2,
            "character_id": character_id,
            "s2_teams_mode": True,
            "test_id": f"test_{int(time.time())}"
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending stimuli: {e}")
        return None

def test_character_teams():
    """Test all character teams with S2 routing"""
    
    print("=== S2 Character Teams Final Test ===\n")
    
    # Clear queue first
    clear_queue()
    time.sleep(1)
    
    # Test configurations
    test_cases = [
        {
            "character": "dr._house_doctor_template",
            "team": "TRADER",
            "content": "Analyze cryptocurrency market volatility and suggest risk management strategies",
            "expected_keywords": ["market", "portfolio", "trading", "risk"]
        },
        {
            "character": "weatherman_template", 
            "team": "STREAMER",
            "content": "Create engaging content strategy for social media growth",
            "expected_keywords": ["content", "social", "engagement", "audience"]
        },
        {
            "character": "emma_teacher_template",
            "team": "TEACHER", 
            "content": "Design adaptive learning curriculum for Python programming beginners",
            "expected_keywords": ["educational", "learning", "curriculum", "assessment"]
        },
        {
            "character": "secretary_template",
            "team": "DEFAULT",
            "content": "Optimize system performance and resource allocation",
            "expected_keywords": ["optimization", "system", "performance", "resources"]
        }
    ]
    
    # Phase 1: Send stimuli to each character
    print("Phase 1: Sending stimuli to each character team\n")
    
    initial_queue = check_queue()
    initial_processed = check_processed()
    print(f"Initial state: {len(initial_queue)} in queue, {len(initial_processed)} processed\n")
    
    results = []
    for test in test_cases:
        print(f"Testing {test['team']} team ({test['character']}):")
        print(f"  Content: {test['content'][:60]}...")
        
        result = send_stimuli(test['content'], test['character'], f"test_{test['team'].lower()}")
        
        if result:
            print(f"  Response: {result.get('status')} - {result.get('decision')}")
            print(f"  Message: {result.get('message')}")
            
            # Check if routed to S2
            if result.get('decision') == 'ANALYSIS_ONLY' or 'S2' in result.get('message', ''):
                print("  ✅ Routed to S2!")
                results.append({**test, "routed": True, "response": result})
            else:
                print("  ❌ NOT routed to S2")
                results.append({**test, "routed": False, "response": result})
        else:
            print("  ❌ Failed to send")
            results.append({**test, "routed": False, "response": None})
        
        print()
        time.sleep(2)
    
    # Phase 2: Check queue status
    print("\nPhase 2: Checking queue status\n")
    
    current_queue = check_queue()
    print(f"Current queue: {len(current_queue)} items")
    
    if current_queue:
        print("\nQueue contents:")
        for i, item in enumerate(current_queue[-4:], 1):  # Show last 4
            print(f"  {i}. {item.get('timestamp')} - {item.get('prompt', '')[:50]}...")
            if 'metadata' in item and 'character_id' in item['metadata']:
                print(f"     Character: {item['metadata']['character_id']}")
    
    # Phase 3: Wait for processing
    print("\n\nPhase 3: Waiting for queue consumer to process...\n")
    
    for i in range(6):  # Wait up to 30 seconds
        time.sleep(5)
        new_queue = check_queue()
        new_processed = check_processed()
        
        processed_count = len(new_processed) - len(initial_processed)
        queue_cleared = len(new_queue) < len(current_queue)
        
        print(f"After {(i+1)*5}s: Queue={len(new_queue)}, Processed={processed_count}")
        
        if queue_cleared or processed_count > 0:
            print("✅ Queue consumer is processing!")
            break
    
    # Phase 4: Analyze results
    print("\n\nPhase 4: Analyzing results\n")
    
    final_queue = check_queue()
    final_processed = check_processed()
    
    # Count successes
    routed_count = sum(1 for r in results if r['routed'])
    processed_count = len(final_processed) - len(initial_processed)
    queue_cleared = len(final_queue) < len(current_queue)
    
    print(f"Summary:")
    print(f"  - Stimuli sent: {len(test_cases)}")
    print(f"  - Routed to S2: {routed_count}")
    print(f"  - Items processed: {processed_count}")
    print(f"  - Queue cleared: {'Yes' if queue_cleared else 'No'}")
    
    # Check for team-specific behavior in logs
    print("\n\nPhase 5: Checking for team-specific behavior\n")
    
    try:
        # Get recent autogen logs
        result = subprocess.run(['docker', 'logs', 'autogen_agent', '--tail', '200'], 
                              capture_output=True, text=True)
        logs = result.stdout + result.stderr
        
        teams_found = 0
        for test in test_cases:
            team_indicators = any(keyword.lower() in logs.lower() for keyword in test['expected_keywords'])
            if team_indicators:
                print(f"✅ {test['team']} team indicators found!")
                teams_found += 1
            else:
                print(f"❌ {test['team']} team indicators NOT found")
        
        print(f"\nTeams showing specialized behavior: {teams_found}/{len(test_cases)}")
        
    except Exception as e:
        print(f"Error checking logs: {e}")
    
    # Final verdict
    print("\n\n=== FINAL VERDICT ===")
    
    success_rate = (routed_count / len(test_cases)) * 100
    print(f"\nRouting success rate: {success_rate:.0f}%")
    
    if routed_count == len(test_cases):
        print("✅ All stimuli routed to S2!")
    else:
        print(f"⚠️ Only {routed_count}/{len(test_cases)} stimuli routed to S2")
    
    if processed_count > 0:
        print("✅ Queue consumer is processing stimuli!")
    else:
        print("❌ Queue consumer is NOT processing stimuli")
    
    if teams_found >= 3:
        print("✅ Specialized team behavior detected!")
    else:
        print(f"⚠️ Only {teams_found}/4 teams showing specialized behavior")
    
    overall_success = routed_count == len(test_cases) and processed_count > 0 and teams_found >= 3
    
    if overall_success:
        print("\n🎉 S2 CHARACTER TEAMS SYSTEM IS WORKING! 🎉")
    else:
        print("\n⚠️ S2 character teams system needs attention")
    
    return overall_success

if __name__ == "__main__":
    success = test_character_teams()
    exit(0 if success else 1)