#!/usr/bin/env python3
"""
Final S2-S1 Forwarding Test
Created: 2025-07-13 19:30

Tests the complete forwarding flow with detailed logging.
"""

import requests
import json
import time
from datetime import datetime


def test_final_forwarding():
    """Final comprehensive forwarding test"""
    
    print("\n🚀 FINAL S2->S1 FORWARDING TEST")
    print("="*60)
    print(f"Time: {datetime.now().isoformat()}")
    
    # Send test with s1_and_s2 mode
    test_data = {
        "stimuli_id": f"final_test_{int(time.time())}",
        "content": "The cryptocurrency market is showing strong bullish signals. Bitcoin's momentum indicates a potential breakout above resistance levels.",
        "source": "final_test",
        "priority": "high",
        "processing_mode": "s1_and_s2",  # Put it at root level too
        "metadata": {
            "processing_mode": "s1_and_s2",
            "character_type": "gordon_trader_template",
            "team_preference": "trader",
            "test_type": "forwarding_verification"
        }
    }
    
    print("\n📤 Sending stimuli with s1_and_s2 mode:")
    print(json.dumps(test_data, indent=2))
    
    try:
        resp = requests.post(
            "http://localhost:8200/api/stimuli/receive",
            json=test_data,
            timeout=10
        )
        
        if resp.status_code == 200:
            result = resp.json()
            print("\n✅ Stimuli accepted!")
            print(json.dumps(result, indent=2))
        else:
            print(f"\n❌ Failed: {resp.status_code}")
            print(resp.text)
            return
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return
    
    print("\n⏳ Waiting 20 seconds for processing...")
    for i in range(20, 0, -1):
        print(f"\r   {i} seconds remaining...", end="", flush=True)
        time.sleep(1)
    
    print("\n\n📊 TEST COMPLETE!")
    print("\n🔍 VERIFICATION STEPS:")
    print("\n1. Check S2 queue processing:")
    print("   docker logs autogen_agent --tail 100 | grep -i 'queue.*process'")
    print("\n2. Check for S1 forwarding:")
    print("   docker logs autogen_agent --tail 100 | grep -i 'forward.*s1'")
    print("\n3. Check S1 for incoming requests:")
    print("   docker logs neurosync_s1 --tail 100 | grep -E 'POST.*process_text|character.*activate'")
    print("\n4. Check processed items:")
    print("   docker exec autogen_agent cat /tmp/s2_queue/s2_processed_history.json | python3 -m json.tool | tail -50")


if __name__ == "__main__":
    test_final_forwarding()