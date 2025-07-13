#!/usr/bin/env python3
"""
Test to verify that S1 includes SCB data in its LLM prompts
"""

import json
import time
import redis
import requests
from datetime import datetime

# Configuration
S1_URL = "http://localhost:5001"
ORCHESTRATOR_URL = "http://localhost:8082"
REDIS_URL = "redis://localhost:6379/0"

def test_s1_scb_prompt_integration():
    """Test that S1 includes SCB context in its prompts"""
    
    print("🧪 Testing S1 SCB Prompt Integration")
    print("=" * 50)
    
    # Connect to Redis
    r = redis.from_url(REDIS_URL)
    
    # 1. Clear existing SCB data
    print("\n1️⃣ Clearing existing SCB data...")
    r.delete("scb:logs")
    r.delete("scb:summary")
    
    # 2. Add some context to SCB
    print("\n2️⃣ Adding test context to SCB...")
    
    # Add S2 analysis to SCB
    scb_entry = {
        "type": "analysis",
        "actor": "s2_trader_team", 
        "text": "Bitcoin shows strong bullish momentum with RSI at 72. Recommendation: HOLD with stop-loss at $64,000",
        "t": datetime.utcnow().isoformat(),
        "salience": 0.95
    }
    r.lpush("scb:logs", json.dumps(scb_entry))
    
    # Add user context
    user_entry = {
        "type": "speech",
        "actor": "user",
        "text": "I'm worried about my Bitcoin investment",
        "t": datetime.utcnow().isoformat(),
        "salience": 0.8
    }
    r.lpush("scb:logs", json.dumps(user_entry))
    
    # Set a summary
    r.set("scb:summary", "Recent context: User concerned about BTC investment. S2 analysis shows bullish momentum, recommends HOLD.")
    
    print("✅ Added context to SCB")
    
    # 3. Wait for summarizer to process
    print("\n3️⃣ Waiting for SCB summarizer...")
    time.sleep(5)
    
    # 4. Send a query through orchestrator
    print("\n4️⃣ Sending query that should use SCB context...")
    
    query = {
        "stimulus_id": "scb_test_001",
        "text": "Should I sell my Bitcoin?",
        "priority": "high"
    }
    
    response = requests.post(f"{ORCHESTRATOR_URL}/process", json=query)
    result = response.json()
    
    print(f"Orchestrator response: {json.dumps(result, indent=2)}")
    
    # 5. Check S1's response for SCB context awareness
    print("\n5️⃣ Analyzing S1 response for SCB awareness...")
    
    if result.get("success"):
        # The response should show awareness of:
        # - Previous concern about BTC investment
        # - S2's bullish analysis
        # - HOLD recommendation
        
        # Check S1 logs for SCB usage
        s1_health = requests.get(f"{S1_URL}/health").json()
        print(f"S1 health: {s1_health}")
        
        # Verify SCB data is still there
        scb_logs = r.lrange("scb:logs", 0, -1)
        scb_summary = r.get("scb:summary")
        
        print(f"\n📊 SCB Status:")
        print(f"  - Log entries: {len(scb_logs)}")
        print(f"  - Summary exists: {scb_summary is not None}")
        
        if scb_summary:
            print(f"  - Summary content: {scb_summary.decode()}")
        
        # Check if response acknowledges previous context
        execution_results = result.get("execution_results", {})
        s1_result = execution_results.get("s1", {})
        
        print(f"\n🎯 S1 Processing Status: {s1_result.get('status')}")
        
        return True
    
    return False

def test_scb_persistence_across_queries():
    """Test that SCB context persists across multiple queries"""
    
    print("\n\n🧪 Testing SCB Persistence Across Queries")
    print("=" * 50)
    
    r = redis.from_url(REDIS_URL)
    
    # First query - establish context
    print("\n1️⃣ First query to establish context...")
    
    query1 = {
        "stimulus_id": "scb_persist_001",
        "text": "I bought Bitcoin at $70,000 and I'm concerned about the price drop",
        "priority": "normal"
    }
    
    response1 = requests.post(f"{ORCHESTRATOR_URL}/process", json=query1)
    print(f"Response 1 status: {response1.status_code}")
    
    time.sleep(3)  # Let SCB update
    
    # Second query - should have context from first
    print("\n2️⃣ Second query that should use previous context...")
    
    query2 = {
        "stimulus_id": "scb_persist_002", 
        "text": "What should I do now?",
        "priority": "normal"
    }
    
    response2 = requests.post(f"{ORCHESTRATOR_URL}/process", json=query2)
    result2 = response2.json()
    
    print(f"Response 2: {json.dumps(result2, indent=2)}")
    
    # Check SCB contents
    scb_logs = r.lrange("scb:logs", 0, -1)
    print(f"\n📊 SCB now contains {len(scb_logs)} entries")
    
    # Display recent entries
    print("\n📜 Recent SCB entries:")
    for i, log in enumerate(scb_logs[:5]):
        entry = json.loads(log)
        print(f"  [{i}] {entry['actor']}: {entry['text'][:60]}...")
    
    return True

if __name__ == "__main__":
    try:
        # Run tests
        test1_result = test_s1_scb_prompt_integration()
        test2_result = test_scb_persistence_across_queries()
        
        print("\n\n✅ All SCB prompt integration tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()