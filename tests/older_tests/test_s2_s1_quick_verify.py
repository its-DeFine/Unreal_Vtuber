#!/usr/bin/env python3
"""
Quick S2-S1 Forwarding Verification
Created: 2025-07-13 19:15

A quick test to verify S2->S1 forwarding is working.
"""

import requests
import json
import time
from datetime import datetime


def test_forwarding():
    """Quick test of S2->S1 forwarding"""
    
    print("\n🧪 QUICK S2->S1 FORWARDING TEST")
    print("="*50)
    
    # Check S2 health
    try:
        resp = requests.get("http://localhost:8200/health", timeout=5)
        if resp.status_code == 200:
            print("✅ S2 is healthy")
            health = resp.json()
            print(f"   Queue consumer: {health.get('s2_teams_status', {}).get('queue_consumer', False)}")
        else:
            print(f"❌ S2 health check failed: {resp.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to S2: {e}")
        return
    
    # Check S1 health
    try:
        resp = requests.get("http://localhost:5001/health", timeout=5)
        if resp.status_code == 200:
            print("✅ S1 is healthy")
        else:
            print(f"❌ S1 health check failed: {resp.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to S1: {e}")
        return
    
    # Send test stimuli with s1_and_s2 mode
    print("\n📤 Sending test stimuli with s1_and_s2 mode...")
    
    test_stimuli = {
        "stimuli_id": f"quick_test_{int(time.time())}",
        "content": "Bitcoin just hit a new all-time high! This is incredible news for crypto investors.",
        "source": "quick_test",
        "priority": "high",
        "metadata": {
            "processing_mode": "s1_and_s2",  # This should trigger forwarding
            "character_type": "gordon_trader_template",
            "team_preference": "trader"
        }
    }
    
    try:
        resp = requests.post(
            "http://localhost:8200/api/stimuli/receive",
            json=test_stimuli,
            timeout=10
        )
        
        if resp.status_code == 200:
            result = resp.json()
            print("✅ Stimuli accepted by S2")
            print(f"   Status: {result.get('status')}")
            print(f"   Processing mode: {result.get('processing_mode')}")
            print(f"   Queued: {result.get('queued')}")
        else:
            print(f"❌ Failed to submit stimuli: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return
    except Exception as e:
        print(f"❌ Error submitting stimuli: {e}")
        return
    
    print("\n⏳ Waiting 15 seconds for processing and forwarding...")
    time.sleep(15)
    
    print("\n📊 TEST COMPLETE")
    print("="*50)
    print("\n🔍 Now check the logs to verify forwarding:")
    print("\n1. Check S2 logs for forwarding message:")
    print("   docker logs autogen_agent --tail 50 | grep -i 'forwarding\\|s1'")
    print("\n2. Check S1 logs for incoming requests:")
    print("   docker logs neurosync_s1 --tail 50 | grep -i 'process_text\\|POST'")
    print("\n3. Check S2 queue processing:")
    print("   docker logs autogen_agent --tail 100 | grep -i 'queue'")


if __name__ == "__main__":
    test_forwarding()