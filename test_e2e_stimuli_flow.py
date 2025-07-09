#!/usr/bin/env python3
"""
End-to-End Stimuli Flow Test
Tests the complete flow: External Stimuli -> GraphFlow -> S1/S2 -> Character Responses
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any

# Service endpoints
GRAPHFLOW_URL = "http://localhost:8081"
NEUROSYNC_S1_URL = "http://localhost:5001"
AUTOGEN_S2_URL = "http://localhost:8200"

# Test API key from GraphFlow config
API_KEY = "test-key-12345"

def test_service_health():
    """Test health of all services"""
    print("🔍 Testing service health...")
    
    services = {
        "NeuroSync S1": f"{NEUROSYNC_S1_URL}/health",
        "GraphFlow Gateway": f"{GRAPHFLOW_URL}/api/v1/health",
        "AutoGen S2": f"{AUTOGEN_S2_URL}/health"
    }
    
    results = {}
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                results[name] = {
                    "status": "healthy" if data.get("status") == "healthy" else "unhealthy",
                    "details": data
                }
                print(f"✅ {name}: {results[name]['status']}")
            else:
                results[name] = {"status": "unhealthy", "code": response.status_code}
                print(f"❌ {name}: HTTP {response.status_code}")
        except Exception as e:
            results[name] = {"status": "error", "error": str(e)}
            print(f"❌ {name}: {str(e)}")
    
    return results

def test_character_switching():
    """Test character switching functionality"""
    print("\n🎭 Testing character switching...")
    
    # List available characters
    try:
        response = requests.get(f"{NEUROSYNC_S1_URL}/character/list", timeout=10)
        if response.status_code == 200:
            characters = response.json().get("characters", [])
            print(f"📋 Available characters: {len(characters)}")
            for char in characters[:3]:  # Show first 3
                print(f"   - {char.get('name', 'Unknown')} ({char.get('id', 'no-id')})")
            
            # Test switching to first character
            if characters:
                char_id = characters[0].get("id")
                switch_response = requests.post(
                    f"{NEUROSYNC_S1_URL}/character/switch",
                    json={"character_id": char_id},
                    timeout=10
                )
                if switch_response.status_code == 200:
                    print(f"✅ Successfully switched to character: {char_id}")
                    return True
                else:
                    print(f"❌ Character switch failed: {switch_response.status_code}")
            else:
                print("⚠️ No characters available for switching")
        else:
            print(f"❌ Failed to get character list: {response.status_code}")
    except Exception as e:
        print(f"❌ Character switching error: {str(e)}")
    
    return False

def test_stimuli_submission():
    """Test stimuli submission through GraphFlow"""
    print("\n🚀 Testing stimuli submission...")
    
    # Test stimuli
    test_stimuli = [
        {
            "content": "Hello, can you introduce yourself?",
            "source": "e2e_test",
            "priority": "medium",
            "metadata": {"test": "character_introduction"}
        },
        {
            "content": "What's the weather like today?",
            "source": "e2e_test",
            "priority": "medium", 
            "metadata": {"test": "weather_query"}
        },
        {
            "content": "Tell me a joke",
            "source": "e2e_test",
            "priority": "low",
            "metadata": {"test": "humor_request"}
        }
    ]
    
    results = []
    
    for i, stimulus in enumerate(test_stimuli, 1):
        print(f"\n📨 Test {i}: {stimulus['content'][:50]}...")
        
        try:
            # Submit stimuli to GraphFlow
            response = requests.post(
                f"{GRAPHFLOW_URL}/api/v1/stimuli/submit",
                json=stimulus,
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Stimuli accepted: {result.get('stimuli_id', 'unknown')}")
                print(f"   Decision: {result.get('decision', 'unknown')}")
                print(f"   Target: {result.get('target_system', 'unknown')}")
                print(f"   Processing time: {result.get('processing_time', 0):.2f}s")
                
                results.append({
                    "stimulus": stimulus,
                    "result": result,
                    "success": True
                })
            else:
                print(f"❌ Stimuli rejected: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                results.append({
                    "stimulus": stimulus,
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })
        
        except Exception as e:
            print(f"❌ Stimuli submission error: {str(e)}")
            results.append({
                "stimulus": stimulus,
                "success": False,
                "error": str(e)
            })
        
        # Wait between tests
        time.sleep(2)
    
    return results

def test_direct_s1_processing():
    """Test direct S1 processing"""
    print("\n🎯 Testing direct S1 processing...")
    
    try:
        test_text = "Hi, I'm testing the direct S1 processing endpoint."
        response = requests.post(
            f"{NEUROSYNC_S1_URL}/process_text",
            json={"text": test_text},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ S1 processing successful")
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Provider: {result.get('llm_provider', 'unknown')}")
            return True
        else:
            print(f"❌ S1 processing failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ S1 processing error: {str(e)}")
        return False

def test_graphflow_analytics():
    """Test GraphFlow analytics and metrics"""
    print("\n📊 Testing GraphFlow analytics...")
    
    try:
        # Get system status instead of analytics
        response = requests.get(
            f"{GRAPHFLOW_URL}/api/v1/status",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10
        )
        
        if response.status_code == 200:
            analytics = response.json()
            print(f"✅ Analytics retrieved")
            print(f"   Total processed: {analytics.get('total_processed', 0)}")
            print(f"   Success rate: {analytics.get('success_rate', 0):.1%}")
            print(f"   Average processing time: {analytics.get('avg_processing_time', 0):.2f}s")
            
            # Show recent decisions
            decisions = analytics.get('recent_decisions', [])
            if decisions:
                print(f"   Recent decisions: {len(decisions)}")
                for decision in decisions[-3:]:  # Last 3
                    print(f"     - {decision.get('decision', 'unknown')} -> {decision.get('target', 'unknown')}")
            
            return True
        else:
            print(f"❌ Analytics failed: HTTP {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Analytics error: {str(e)}")
        return False

def main():
    """Run comprehensive end-to-end tests"""
    print("🧪 Starting End-to-End Stimuli Flow Tests")
    print("=" * 60)
    
    # Test service health
    health_results = test_service_health()
    
    # Test character switching
    char_success = test_character_switching()
    
    # Test stimuli submission
    stimuli_results = test_stimuli_submission()
    
    # Test direct S1 processing
    s1_success = test_direct_s1_processing()
    
    # Test GraphFlow analytics
    analytics_success = test_graphflow_analytics()
    
    # Summary
    print("\n📋 TEST SUMMARY")
    print("=" * 30)
    
    total_tests = 5
    passed_tests = 0
    
    services_healthy = sum(1 for result in health_results.values() if result.get("status") == "healthy")
    print(f"Service Health: {services_healthy}/{len(health_results)} services healthy")
    if services_healthy == len(health_results):
        passed_tests += 1
    
    print(f"Character Switching: {'✅ PASS' if char_success else '❌ FAIL'}")
    if char_success:
        passed_tests += 1
    
    successful_stimuli = sum(1 for result in stimuli_results if result.get("success", False))
    print(f"Stimuli Submission: {successful_stimuli}/{len(stimuli_results)} stimuli processed")
    if successful_stimuli > 0:
        passed_tests += 1
    
    print(f"Direct S1 Processing: {'✅ PASS' if s1_success else '❌ FAIL'}")
    if s1_success:
        passed_tests += 1
    
    print(f"GraphFlow Analytics: {'✅ PASS' if analytics_success else '❌ FAIL'}")
    if analytics_success:
        passed_tests += 1
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())