#!/usr/bin/env python3
"""Test script to verify orchestrator fixes for interruption and content control"""

import requests
import time
import json

BASE_URL = "http://localhost:5001"

def test_orchestrator_status():
    """Check if orchestrator is running"""
    print("🔍 Checking orchestrator status...")
    try:
        response = requests.get(f"{BASE_URL}/orchestrator/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Orchestrator status: {json.dumps(status, indent=2)}")
            return True
        else:
            print(f"❌ Orchestrator not available: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking orchestrator: {e}")
        return False

def test_direct_speech():
    """Test that orchestrator-generated content speaks exactly what we send"""
    print("\n🗣️ Testing direct speech content control...")
    
    # First, ask it to talk about ancient Rome
    payload = {
        "text": "Tell me about ancient Rome",
        "autonomous_context": "user_request"
    }
    
    print(f"📤 Sending: {payload['text']}")
    response = requests.post(f"{BASE_URL}/process_text", json=payload)
    print(f"📥 Response: {response.json()}")
    
    # Wait for orchestrator to process
    time.sleep(3)
    
    # Check status to see what's queued
    status = requests.get(f"{BASE_URL}/orchestrator/status").json()
    if 'pending_actions' in status:
        print(f"📋 Pending actions: {status['pending_actions']}")

def test_interruption():
    """Test interruption capability"""
    print("\n⚡ Testing interruption...")
    
    # Start a long speech
    payload = {
        "text": "Tell me a very long story about the history of computers, starting from the very beginning with Charles Babbage",
        "autonomous_context": "user_request"
    }
    
    print(f"📤 Starting long speech: {payload['text'][:50]}...")
    response = requests.post(f"{BASE_URL}/process_text", json=payload)
    
    # Wait a bit for it to start
    time.sleep(2)
    
    # Now interrupt with high priority
    print("⚡ Sending interruption...")
    interrupt_payload = {
        "action": "interrupt"
    }
    response = requests.post(f"{BASE_URL}/orchestrator/control", json=interrupt_payload)
    print(f"📥 Interrupt response: {response.json()}")
    
    # Send new high priority content
    time.sleep(0.5)
    new_payload = {
        "text": "STOP! Tell me about space exploration instead",
        "autonomous_context": "urgent_request"
    }
    
    print(f"📤 Sending new high priority request: {new_payload['text']}")
    response = requests.post(f"{BASE_URL}/process_text", json=new_payload)
    print(f"📥 Response: {response.json()}")

def test_manual_queue_control():
    """Test manual queue control for direct speech"""
    print("\n🎮 Testing manual queue control...")
    
    # Queue direct speech
    payload = {
        "action": "queue_speech",
        "text": "This is exactly what I want you to say about ancient Rome: The Roman Empire was one of the most powerful civilizations in history.",
        "priority": "high",
        "interrupt": False
    }
    
    print(f"📤 Queueing direct speech: {payload['text'][:50]}...")
    response = requests.post(f"{BASE_URL}/orchestrator/control", json=payload)
    print(f"📥 Response: {response.json()}")

def main():
    """Run all tests"""
    print("🧪 Testing Orchestrator Fixes")
    print("=" * 60)
    
    # Check if orchestrator is available
    if not test_orchestrator_status():
        print("⚠️ Orchestrator not available. Make sure container is running with AUTONOMOUS_ORCHESTRATION_ENABLED=true")
        return
    
    # Run tests
    test_direct_speech()
    test_interruption()
    test_manual_queue_control()
    
    print("\n✅ Tests completed!")

if __name__ == "__main__":
    main() 