#!/usr/bin/env python3
"""Quick test of S2 system functionality."""
import requests
import json
import time

def test_s2_routing():
    """Test that trader stimuli routes to S2 only."""
    print("🧪 Testing S2 Routing...")
    
    # Test trader stimuli (should go to S2 only)
    trader_stimuli = {
        "content": "Analyze Bitcoin market trends and provide trading recommendations",
        "character_id": "trader_character",
        "metadata": {
            "character_type": "trader",
            "processing_mode": "analysis"
        }
    }
    
    # Send to GraphFlow
    response = requests.post(
        "http://localhost:8000/api/v1/stimuli/submit",
        json=trader_stimuli
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Stimuli sent successfully")
        print(f"   Full response: {json.dumps(result, indent=2)}")
        
        # Extract decision from response
        decision = result.get("decision", "")
        if not decision:
            decision = result.get("decision_matrix", {}).get("final_decision", "")
        
        print(f"   Decision: {decision}")
        print(f"   Expected: ANALYSIS_ONLY")
        
        if decision == "ANALYSIS_ONLY":
            print("✅ Routing correct - trader goes to S2 only!")
        else:
            print("❌ Routing incorrect - trader should NEVER go to S1!")
            
    else:
        print(f"❌ Failed to send stimuli: {response.status_code}")
        
    # Check S2 status
    print("\n🔍 Checking S2 Status...")
    try:
        s2_response = requests.get("http://localhost:8200/api/status")
        if s2_response.status_code == 200:
            status = s2_response.json()
            print(f"✅ S2 Status:")
            print(f"   Teams Enabled: {status.get('teams_enabled')}")
            print(f"   Queue Size: {status.get('queue_stats', {}).get('queue_size', 0)}")
            print(f"   Processed: {status.get('queue_stats', {}).get('batches_processed', 0)}")
        else:
            print(f"❌ S2 not responding: {s2_response.status_code}")
    except:
        print("❌ S2 container not accessible")

if __name__ == "__main__":
    test_s2_routing()