#!/usr/bin/env python3
"""Test S2 routing with proper metadata after fixing decision matrix"""

import requests
import json
import time
import subprocess

def check_queue():
    """Check queue file contents"""
    try:
        result = subprocess.run(['docker', 'exec', 'autogen_agent', 'cat', '/tmp/s2_processing_queue.json'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print(f"Queue has {len(data)} items")
            if data:
                latest = data[-1]
                print(f"Latest: {latest.get('timestamp')} - {latest.get('prompt')[:50]}...")
            return len(data)
        else:
            print("Queue file not found or empty")
            return 0
    except Exception as e:
        print(f"Error checking queue: {e}")
        return 0

def clear_queue():
    """Clear the queue file"""
    try:
        subprocess.run(['docker', 'exec', 'autogen_agent', 'sh', '-c', 'echo "[]" > /tmp/s2_processing_queue.json'], 
                      capture_output=True, text=True)
        print("Queue cleared")
    except Exception as e:
        print(f"Error clearing queue: {e}")

def test_s2_routing():
    """Test S2 routing with different metadata approaches"""
    
    # Clear queue first
    clear_queue()
    time.sleep(1)
    
    print("=== Testing S2 Routing (Fixed) ===\n")
    
    url = "http://localhost:8000/api/v1/stimuli/submit"
    
    test_cases = [
        {
            "name": "force_s2 flag",
            "payload": {
                "content": "Analyze Bitcoin market trends and suggest trading strategies",
                "source": "test_s2_fixed",
                "priority": "high",
                "metadata": {
                    "force_s2": True,
                    "character_id": "dr._house_doctor_template"
                }
            }
        },
        {
            "name": "target_systems s2",
            "payload": {
                "content": "Create educational content about machine learning basics",
                "source": "test_s2_fixed",
                "priority": "medium",
                "metadata": {
                    "target_systems": ["s2"],
                    "character_id": "emma_teacher_template"
                }
            }
        },
        {
            "name": "s2_teams_mode flag",
            "payload": {
                "content": "Analyze social media engagement metrics and trends",
                "source": "test_s2_fixed",
                "priority": "medium",
                "metadata": {
                    "s2_teams_mode": True,
                    "character_id": "weatherman_template"
                }
            }
        },
        {
            "name": "processing_mode s2_only",
            "payload": {
                "content": "Optimize system performance and resource allocation",
                "source": "test_s2_fixed",
                "priority": "medium",
                "metadata": {
                    "processing_mode": "s2_only",
                    "character_id": "secretary_template"
                }
            }
        }
    ]
    
    initial_count = check_queue()
    print(f"Initial queue count: {initial_count}\n")
    
    for i, test in enumerate(test_cases):
        print(f"{i+1}. Testing: {test['name']}")
        print(f"   Content: {test['payload']['content'][:50]}...")
        print(f"   Character: {test['payload']['metadata'].get('character_id')}")
        
        try:
            response = requests.post(url, json=test['payload'])
            result = response.json()
            print(f"   Response: {response.status_code}")
            print(f"   Decision: {result.get('decision')}")
            print(f"   Message: {result.get('message')}")
            
            # Check if routed correctly
            if result.get('decision') == 'ANALYSIS_ONLY' or 'S2' in result.get('message', ''):
                print("   ✅ Routed to S2!")
            else:
                print("   ❌ NOT routed to S2")
                
        except Exception as e:
            print(f"   Error: {e}")
        
        print()
        time.sleep(2)
    
    # Check final queue state
    print("\nChecking final queue state...")
    final_count = check_queue()
    
    if final_count > initial_count:
        print(f"✅ {final_count - initial_count} items added to S2 queue!")
    else:
        print("❌ No items added to S2 queue")
    
    # Wait for processing
    print("\nWaiting 15 seconds for queue consumer to process...")
    time.sleep(15)
    
    # Check if queue was processed
    processed_count = check_queue()
    if processed_count < final_count:
        print(f"✅ Queue consumer processed {final_count - processed_count} items!")
    else:
        print("❌ Queue consumer did not process any items")
    
    # Check character teams in logs
    print("\nChecking for character team activations...")
    try:
        result = subprocess.run(['docker', 'logs', 'autogen_agent', '--tail', '100'], 
                              capture_output=True, text=True)
        logs = result.stdout + result.stderr
        
        team_indicators = {
            "TRADER": ["market", "portfolio", "trading", "risk"],
            "STREAMER": ["content", "social", "engagement", "audience"],
            "TEACHER": ["educational", "learning", "curriculum", "assessment"],
            "DEFAULT": ["optimization", "system", "performance"]
        }
        
        for team, keywords in team_indicators.items():
            if any(keyword in logs for keyword in keywords):
                print(f"✅ {team} team indicators found!")
        
    except Exception as e:
        print(f"Error checking logs: {e}")

if __name__ == "__main__":
    test_s2_routing()