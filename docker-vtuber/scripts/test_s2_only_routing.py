#!/usr/bin/env python3
"""Test forcing S2-only routing by manipulating the request"""

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
                print(f"Latest: {data[-1].get('timestamp')} - {data[-1].get('prompt')[:50]}...")
            return len(data)
        else:
            print("Queue file not found")
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

def test_s2_only():
    """Test different approaches to get S2-only routing"""
    
    # First clear the queue
    clear_queue()
    time.sleep(1)
    
    print("=== Testing S2-Only Routing ===\n")
    
    # Check initial state
    print("Initial queue state:")
    initial_count = check_queue()
    
    # Test 1: Try with SYSTEM_NOTIFICATION category (should be ANALYSIS_ONLY)
    print("\n1. Testing SYSTEM_NOTIFICATION category:")
    url = "http://localhost:8000/api/v1/stimuli/submit"
    payload = {
        "content": "Analyze Bitcoin market trends and volatility",
        "source": "test_s2_only",
        "priority": "medium",
        "category": "SYSTEM_NOTIFICATION",  # This should trigger ANALYSIS_ONLY
        "metadata": {
            "character_id": "dr._house_doctor_template",
            "force_s2": True
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        print(f"Response: {response.status_code}")
        print(f"Decision: {result.get('decision')}")
        print(f"Message: {result.get('message')}")
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(2)
    
    # Check if it went to queue
    print("\nChecking queue after test 1:")
    count1 = check_queue()
    if count1 > initial_count:
        print("✅ Item added to S2 queue!")
    else:
        print("❌ Item NOT added to S2 queue")
    
    # Test 2: Try with low priority (might bypass nuclear override)
    print("\n2. Testing low priority:")
    payload = {
        "content": "Analyze Ethereum smart contract patterns",
        "source": "test_s2_only",
        "priority": "low",  # Low priority might not trigger nuclear override
        "metadata": {
            "character_id": "dr._house_doctor_template",
            "request_type": "analysis"
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        print(f"Response: {response.status_code}")
        print(f"Decision: {result.get('decision')}")
        print(f"Message: {result.get('message')}")
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(2)
    
    # Check if it went to queue
    print("\nChecking queue after test 2:")
    count2 = check_queue()
    if count2 > count1:
        print("✅ Item added to S2 queue!")
    else:
        print("❌ Item NOT added to S2 queue")
    
    # Wait a bit to see if queue consumer processes anything
    print("\nWaiting 10 seconds to see if queue consumer processes items...")
    time.sleep(10)
    
    print("\nFinal queue state:")
    final_count = check_queue()
    if final_count < count2:
        print("✅ Queue consumer is processing items!")
    else:
        print("❌ Queue consumer is NOT processing items")
    
    # Check processed file
    try:
        result = subprocess.run(['docker', 'exec', 'autogen_agent', 'tail', '-5', '/tmp/s2_processed_stimuli.json'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("\nLast processed entries:")
            print(result.stdout)
    except Exception as e:
        print(f"Error checking processed: {e}")

if __name__ == "__main__":
    test_s2_only()