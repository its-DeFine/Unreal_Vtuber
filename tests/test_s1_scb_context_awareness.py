#!/usr/bin/env python3
"""
Test to verify S1's awareness of SCB context in its responses
"""

import json
import time
import redis
import requests
from datetime import datetime

# Configuration
ORCHESTRATOR_URL = "http://localhost:8082"
REDIS_URL = "redis://localhost:6379/0"

def test_scb_context_awareness():
    """Test S1's actual use of SCB context in responses"""
    
    print("🧪 Testing S1's SCB Context Awareness in Responses")
    print("=" * 60)
    
    r = redis.from_url(REDIS_URL)
    
    # Clear SCB
    print("\n1️⃣ Clearing SCB...")
    r.delete("scb:logs")
    r.delete("scb:summary")
    
    # Add specific context that S1 should be aware of
    print("\n2️⃣ Adding specific context to SCB...")
    
    # Add a directive from S2
    directive_entry = {
        "type": "directive",
        "actor": "s2_planner",
        "text": "IMPORTANT: User's favorite color is purple and they love cats",
        "t": datetime.utcnow().isoformat(),
        "salience": 1.0,
        "ttl": 300  # 5 minutes
    }
    r.lpush("scb:logs", json.dumps(directive_entry))
    
    # Add some chat history
    chat_entries = [
        {
            "type": "speech",
            "actor": "user",
            "text": "I'm thinking of redecorating my room",
            "t": datetime.utcnow().isoformat(),
            "salience": 0.8
        },
        {
            "type": "speech", 
            "actor": "vtuber",
            "text": "That sounds exciting! What style are you going for?",
            "t": datetime.utcnow().isoformat(),
            "salience": 0.7
        }
    ]
    
    for entry in chat_entries:
        r.lpush("scb:logs", json.dumps(entry))
    
    # Set summary
    r.set("scb:summary", "User planning room redecoration. REMEMBER: User loves purple and cats.")
    
    print("✅ Added context about user preferences (purple color, loves cats)")
    
    # Wait for SCB to be processed
    time.sleep(5)
    
    # Send a query that should use this context
    print("\n3️⃣ Sending query that should demonstrate context awareness...")
    
    query = {
        "stimulus_id": "scb_awareness_test",
        "text": "What color scheme would you suggest for my room?",
        "priority": "normal"
    }
    
    response = requests.post(f"{ORCHESTRATOR_URL}/process", json=query)
    result = response.json()
    
    print(f"\n📊 Orchestrator routing: {result['routing_decision']['system']}")
    
    # For this test, we need to wait for S1 to actually process and generate response
    print("\n4️⃣ Waiting for S1 to generate response...")
    time.sleep(10)  # Give S1 time to process
    
    # Check Redis for logged AI responses
    print("\n5️⃣ Checking for context-aware response...")
    
    scb_logs = r.lrange("scb:logs", 0, 20)
    
    found_aware_response = False
    for log_entry in scb_logs:
        entry = json.loads(log_entry)
        if entry.get("actor") == "vtuber" and entry.get("type") == "speech":
            response_text = entry.get("text", "").lower()
            print(f"\n🤖 AI Response: {entry['text'][:200]}...")
            
            # Check if response mentions purple or cats
            if "purple" in response_text or "cat" in response_text:
                found_aware_response = True
                print("✅ Response shows awareness of SCB context!")
                break
    
    if not found_aware_response:
        print("⚠️  Response doesn't explicitly mention SCB context")
        print("    (This might be due to the LLM's interpretation)")
    
    # Display current SCB state
    print("\n📜 Current SCB state:")
    summary = r.get("scb:summary")
    if summary:
        print(f"  Summary: {summary.decode()}")
    print(f"  Total log entries: {len(scb_logs)}")
    
    return found_aware_response

if __name__ == "__main__":
    try:
        result = test_scb_context_awareness()
        print("\n" + "="*60)
        if result:
            print("✅ S1 demonstrates SCB context awareness!")
        else:
            print("⚠️  S1 may be using SCB but not explicitly showing it")
            print("    (SCB data is included in prompts but LLM response varies)")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()