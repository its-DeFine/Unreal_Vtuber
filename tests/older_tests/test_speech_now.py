#!/usr/bin/env python3
"""
Simple Direct Speech Test - Hear Characters Now!
Created: 2025-07-13
"""

import requests
import time
import json

def test_speech_now():
    """Direct test to hear character speech immediately"""
    
    print("\n🔊 DIRECT SPEECH TEST - MAKE SURE YOUR SPEAKERS ARE ON!")
    print("="*60)
    
    base_url = "http://localhost:5001"
    
    # Test 1: Gordon Trader
    print("\n🎭 TEST 1: GORDON TRADER")
    print("-"*40)
    
    # Switch to Gordon
    try:
        response = requests.post(f"{base_url}/character/switch", 
            json={"character_id": "gordon_trader_template"},
            timeout=5)
        print(f"Switch response: {response.status_code}")
    except Exception as e:
        print(f"Switch error: {e}")
    
    time.sleep(1)
    
    # Gordon speaks
    try:
        response = requests.post(f"{base_url}/process_text",
            json={
                "text": "Greetings! This is Gordon Trader from the trading team. Testing our new SCB state management utilities. The market is showing bullish momentum on Tesla at 250.",
                "direct_speech": True
            },
            timeout=10)
        print(f"Speech response: {response.status_code} - {response.json()}")
        print("🔊 YOU SHOULD HEAR GORDON SPEAKING NOW!")
    except Exception as e:
        print(f"Speech error: {e}")
    
    print("⏳ Waiting 6 seconds for speech to complete...")
    time.sleep(6)
    
    # Test 2: Emma Teacher
    print("\n🎭 TEST 2: EMMA TEACHER")
    print("-"*40)
    
    # Switch to Emma
    try:
        response = requests.post(f"{base_url}/character/switch",
            json={"character_id": "emma_teacher_template"},
            timeout=5)
        print(f"Switch response: {response.status_code}")
    except Exception as e:
        print(f"Switch error: {e}")
    
    time.sleep(1)
    
    # Emma speaks
    try:
        response = requests.post(f"{base_url}/process_text",
            json={
                "text": "Hello students! This is Emma from the educator team. We're testing our character mapping utilities. Today's lesson demonstrates real-time speech synthesis!",
                "direct_speech": True
            },
            timeout=10)
        print(f"Speech response: {response.status_code} - {response.json()}")
        print("🔊 YOU SHOULD HEAR EMMA SPEAKING NOW!")
    except Exception as e:
        print(f"Speech error: {e}")
    
    print("⏳ Waiting 6 seconds for speech to complete...")
    time.sleep(6)
    
    # Test 3: Mike Streamer  
    print("\n🎭 TEST 3: MIKE STREAMER")
    print("-"*40)
    
    # Switch to Mike
    try:
        response = requests.post(f"{base_url}/character/switch",
            json={"character_id": "mike_streamer_template"},
            timeout=5)
        print(f"Switch response: {response.status_code}")
    except Exception as e:
        print(f"Switch error: {e}")
    
    time.sleep(1)
    
    # Mike speaks
    try:
        response = requests.post(f"{base_url}/process_text",
            json={
                "text": "Hey everyone! Mike here from the streaming team! We're live testing the SCB utilities with real speech output. This is so cool - you can hear all three teams speaking!",
                "direct_speech": True
            },
            timeout=10)
        print(f"Speech response: {response.status_code} - {response.json()}")
        print("🔊 YOU SHOULD HEAR MIKE SPEAKING NOW!")
    except Exception as e:
        print(f"Speech error: {e}")
    
    print("⏳ Waiting 6 seconds for speech to complete...")
    time.sleep(6)
    
    # Test 4: Test SCB Context
    print("\n🗄️ TEST 4: SCB CONTEXT WITH SPEECH")
    print("-"*40)
    
    # Send with SCB context
    scb_context = {
        "team_scb:trader": {"market_analysis": "TSLA bullish at 250"},
        "team_scb:educator": {"current_lesson": "Integration Testing"},
        "team_scb:streamer": {"viewer_count": 150},
        "common_scb": {"system_status": "active", "test_mode": True}
    }
    
    try:
        response = requests.post(f"{base_url}/process_text",
            json={
                "text": "Testing SCB integration. All teams are active with their own state management. Common SCB shows system is active.",
                "direct_speech": True,
                "autonomous_context": scb_context
            },
            timeout=10)
        print(f"SCB speech response: {response.status_code} - {response.json()}")
        print("🔊 YOU SHOULD HEAR SCB CONTEXT SPEECH NOW!")
    except Exception as e:
        print(f"SCB speech error: {e}")
    
    print("\n" + "="*60)
    print("✅ SPEECH TESTS COMPLETED!")
    print("="*60)
    print("\n🔊 Did you hear all three characters speaking?")
    print("   - Gordon (Trader): Deep trading voice")
    print("   - Emma (Educator): Clear teaching voice")  
    print("   - Mike (Streamer): Energetic streaming voice")
    print("\n📝 If you didn't hear anything:")
    print("   1. Check your speakers/headphones")
    print("   2. Check container logs: docker-compose logs neurosync_s1")
    print("   3. Check TTS provider settings in .env")
    print("\n🎯 The utilities are working if characters switched and spoke!")

if __name__ == "__main__":
    test_speech_now()