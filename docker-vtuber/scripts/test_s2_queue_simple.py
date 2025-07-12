#!/usr/bin/env python3
"""Simple test to verify S2 queue processing"""

import requests
import json
import time
import subprocess

def send_s2_stimuli(content, character_id="dr._house_doctor_template"):
    """Send stimuli to S2"""
    url = "http://localhost:8000/api/v1/stimuli/submit"
    payload = {
        "content": content,
        "source": "test_s2_queue",
        "priority": "high",
        "metadata": {
            "character_id": character_id
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Sent stimuli: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error sending stimuli: {e}")
        return None

def check_queue():
    """Check queue file contents"""
    try:
        result = subprocess.run(['docker', 'exec', 'autogen_agent', 'cat', '/tmp/s2_processing_queue.json'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print(f"\nQueue has {len(data)} items")
            return data
        else:
            print("Queue file not found")
            return []
    except Exception as e:
        print(f"Error checking queue: {e}")
        return []

def check_processed():
    """Check processed file"""
    try:
        result = subprocess.run(['docker', 'exec', 'autogen_agent', 'cat', '/tmp/s2_processed_stimuli.json'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print(f"\nProcessed has {len(data)} items")
            if data:
                latest = data[-1]
                print(f"Latest processed: {latest.get('timestamp')} - Status: {latest.get('status')}")
            return data
        else:
            print("Processed file not found")
            return []
    except Exception as e:
        print(f"Error checking processed: {e}")
        return []

def main():
    print("=== S2 Queue Processing Test ===\n")
    
    # Check initial queue state
    print("Initial queue state:")
    initial_queue = check_queue()
    initial_processed = check_processed()
    initial_processed_count = len(initial_processed)
    
    # Send test stimuli
    print("\nSending test stimuli...")
    response = send_s2_stimuli("Analyze Bitcoin price movements and market sentiment")
    
    if response:
        # Wait a moment for queue to be written
        time.sleep(2)
        
        # Check queue again
        print("\nQueue after sending:")
        queue_after = check_queue()
        
        # Wait for processing
        print("\nWaiting 10 seconds for processing...")
        time.sleep(10)
        
        # Check queue and processed
        print("\nFinal state:")
        final_queue = check_queue()
        final_processed = check_processed()
        
        # Check if item was processed
        if len(final_processed) > initial_processed_count:
            print("\n✅ Item was processed!")
        else:
            print("\n❌ Item was NOT processed")
            
        if len(final_queue) < len(queue_after):
            print("✅ Queue was cleared")
        else:
            print("❌ Queue was NOT cleared")

if __name__ == "__main__":
    main()