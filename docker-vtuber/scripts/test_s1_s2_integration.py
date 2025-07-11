#!/usr/bin/env python3
"""
S1 + S2 Integration Test
========================

Tests the complete integration between S1 (NeuroSync) and S2 (AutoGen) systems
with different character teams.
"""

import json
import time
import requests
import subprocess
from datetime import datetime

def test_s2_only(character_id, team_type, prompt):
    """Test S2 system only (via queue)"""
    print(f"\n🎯 Testing S2 Only - {team_type} team")
    print("-" * 60)
    
    # Send to S2 queue
    stimuli = {
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "source": f"s2_test_{team_type}",
        "processing_mode": "s2_only",
        "metadata": {
            "character_id": character_id,
            "team_type": team_type
        }
    }
    
    cmd = f"echo '{json.dumps([stimuli])}' > /tmp/s2_processing_queue.json"
    subprocess.run(["docker", "exec", "autogen_agent", "bash", "-c", cmd])
    print(f"📤 Sent to S2 queue: {prompt[:50]}...")
    
    # Wait and check
    time.sleep(15)
    
    # Check queue status
    result = subprocess.run(
        ["docker", "exec", "autogen_agent", "cat", "/tmp/s2_processing_queue.json"],
        capture_output=True,
        text=True
    )
    
    queue_cleared = result.stdout.strip() == "[]"
    
    # Check logs
    logs = subprocess.run(
        ["docker", "logs", "autogen_agent", "--tail", "100"],
        capture_output=True,
        text=True
    )
    
    processing_found = any(word in logs.stdout.lower() for word in prompt.lower().split()[:3])
    team_found = f"team_type': '{team_type}'" in logs.stdout
    
    print(f"📋 Queue cleared: {'✅' if queue_cleared else '❌'}")
    print(f"🔄 Processing detected: {'✅' if processing_found else '❌'}")
    print(f"👥 Team activated: {'✅' if team_found else '❌'}")
    
    return queue_cleared and processing_found

def test_s1_only(character_file, prompt):
    """Test S1 system only (NeuroSync)"""
    print(f"\n🎮 Testing S1 Only - {character_file}")
    print("-" * 60)
    
    try:
        # Send to S1 API
        response = requests.post(
            "http://localhost:5001/api/chat",
            json={
                "message": prompt,
                "character": character_file.replace(".json", "")
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ S1 responded: {data.get('response', '')[:100]}...")
            return True
        else:
            print(f"❌ S1 error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ S1 connection error: {e}")
        return False

def test_s1_s2_integration(character_id, team_type, prompt):
    """Test S1+S2 integration via GraphFlow"""
    print(f"\n🔗 Testing S1+S2 Integration - {team_type} team")
    print("-" * 60)
    
    try:
        # Send to GraphFlow gateway
        response = requests.post(
            "http://localhost:8000/api/stimuli/process",
            json={
                "content": prompt,
                "category": "test_integration",
                "metadata": {
                    "character_id": character_id,
                    "team_type": team_type,
                    "source": "integration_test"
                }
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GraphFlow processed successfully")
            print(f"   Decision: {data.get('decision', 'unknown')}")
            print(f"   S1 triggered: {data.get('s1_response', {}).get('triggered', False)}")
            print(f"   S2 triggered: {data.get('s2_response', {}).get('triggered', False)}")
            return True
        else:
            print(f"❌ GraphFlow error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ GraphFlow connection error: {e}")
        return False

def main():
    print("🧪 S1 + S2 Integration Test Suite")
    print("=" * 80)
    
    # Test configurations
    test_configs = [
        {
            "character_id": "dr._house_doctor_template",
            "character_file": "dr._house_doctor_template.json",
            "team_type": "trader",
            "prompt": "Analyze Bitcoin price volatility and recommend trading strategies for risk management"
        },
        {
            "character_id": "weatherman_template",
            "character_file": "weatherman_template.json", 
            "team_type": "streamer",
            "prompt": "Create an engaging weather forecast video script for social media platforms"
        }
    ]
    
    results = {
        "s2_only": [],
        "s1_only": [],
        "s1_s2_integration": []
    }
    
    # Run tests for each configuration
    for config in test_configs:
        print(f"\n{'='*80}")
        print(f"🎭 Character: {config['character_id']} ({config['team_type']} team)")
        print(f"{'='*80}")
        
        # Test S2 Only
        s2_result = test_s2_only(
            config["character_id"],
            config["team_type"],
            config["prompt"]
        )
        results["s2_only"].append((config["team_type"], s2_result))
        
        # Test S1 Only
        s1_result = test_s1_only(
            config["character_file"],
            config["prompt"]
        )
        results["s1_only"].append((config["team_type"], s1_result))
        
        # Test S1+S2 Integration
        integration_result = test_s1_s2_integration(
            config["character_id"],
            config["team_type"],
            config["prompt"]
        )
        results["s1_s2_integration"].append((config["team_type"], integration_result))
        
        # Wait between tests
        time.sleep(5)
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 Test Summary")
    print(f"{'='*80}\n")
    
    # S2 Only Results
    print("🎯 S2 Only (AutoGen Teams):")
    s2_success = sum(1 for _, success in results["s2_only"] if success)
    for team, success in results["s2_only"]:
        print(f"   {team:10} - {'✅ Success' if success else '❌ Failed'}")
    print(f"   Total: {s2_success}/{len(results['s2_only'])} passed")
    
    # S1 Only Results
    print("\n🎮 S1 Only (NeuroSync):")
    s1_success = sum(1 for _, success in results["s1_only"] if success)
    for team, success in results["s1_only"]:
        print(f"   {team:10} - {'✅ Success' if success else '❌ Failed'}")
    print(f"   Total: {s1_success}/{len(results['s1_only'])} passed")
    
    # Integration Results
    print("\n🔗 S1+S2 Integration (GraphFlow):")
    integration_success = sum(1 for _, success in results["s1_s2_integration"] if success)
    for team, success in results["s1_s2_integration"]:
        print(f"   {team:10} - {'✅ Success' if success else '❌ Failed'}")
    print(f"   Total: {integration_success}/{len(results['s1_s2_integration'])} passed")
    
    # Overall Status
    total_tests = len(results["s2_only"]) + len(results["s1_only"]) + len(results["s1_s2_integration"])
    total_passed = s2_success + s1_success + integration_success
    
    print(f"\n{'='*80}")
    print(f"🏁 Overall: {total_passed}/{total_tests} tests passed ({total_passed/total_tests*100:.0f}%)")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! S1+S2 integration is working perfectly!")
    elif total_passed > total_tests * 0.7:
        print("\n✅ Most tests passed. System is functional with minor issues.")
    else:
        print("\n⚠️ Several tests failed. System needs attention.")

if __name__ == "__main__":
    main()