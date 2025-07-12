#!/usr/bin/env python3
"""Test script to send stimuli specifically to S2"""

import requests
import json
import time

def test_s2_routing():
    """Test different ways to route to S2"""
    
    test_cases = [
        {
            "name": "S2 target_systems",
            "payload": {
                "content": "Analyze market trends for cryptocurrency",
                "source": "test_s2_routing",
                "priority": "high",
                "metadata": {
                    "target_systems": ["s2", "system2"],
                    "character_id": "dr._house_doctor_template"
                }
            }
        },
        {
            "name": "Analysis only category",
            "payload": {
                "content": "Analyze market trends for cryptocurrency",
                "source": "test_s2_routing",
                "priority": "medium",
                "category": "SYSTEM_NOTIFICATION",
                "metadata": {
                    "character_id": "dr._house_doctor_template"
                }
            }
        },
        {
            "name": "Request type analysis",
            "payload": {
                "content": "Analyze market trends for cryptocurrency",
                "source": "test_s2_routing", 
                "priority": "medium",
                "metadata": {
                    "request_type": "analysis",
                    "character_id": "dr._house_doctor_template"
                }
            }
        },
        {
            "name": "S2 force flag",
            "payload": {
                "content": "Analyze market trends for cryptocurrency",
                "source": "test_s2_routing",
                "priority": "medium",
                "metadata": {
                    "force_s2": True,
                    "character_id": "dr._house_doctor_template"
                }
            }
        }
    ]
    
    url = "http://localhost:8000/api/v1/stimuli/submit"
    
    for test in test_cases:
        print(f"\n=== Testing: {test['name']} ===")
        print(f"Payload: {json.dumps(test['payload'], indent=2)}")
        
        try:
            response = requests.post(url, json=test['payload'])
            result = response.json()
            print(f"Response: {response.status_code}")
            print(f"Decision: {result.get('decision')}")
            print(f"Message: {result.get('message')}")
            
            # Check if it went to S2
            if "S2" in result.get('message', '') or result.get('decision') == 'ANALYSIS_ONLY':
                print("✅ Routed to S2")
            else:
                print("❌ NOT routed to S2")
                
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(2)

if __name__ == "__main__":
    test_s2_routing()