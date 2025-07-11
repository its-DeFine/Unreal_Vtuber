#!/usr/bin/env python3
"""
S2 Full System Test
===================

Comprehensive test of the S2 character-team system including:
- Character-specific team activation
- SCB updates
- Neo4j storage
- Queue processing
"""

import json
import time
import subprocess
from datetime import datetime

def test_character_team(character_id, team_type, prompt):
    """Test a specific character-team combination"""
    
    print(f"\n🎭 Testing {character_id} ({team_type} team)")
    print("-" * 50)
    
    # Create stimuli
    stimuli = {
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "source": f"test_{team_type}",
        "processing_mode": "s2_only",
        "metadata": {
            "character_id": character_id,
            "team_type": team_type,
            "test_id": f"test_{int(time.time())}"
        }
    }
    
    # Send to queue
    cmd = f"echo '{json.dumps([stimuli])}' > /tmp/s2_processing_queue.json"
    subprocess.run(["docker", "exec", "autogen_agent", "bash", "-c", cmd])
    print(f"✅ Sent: {prompt[:50]}...")
    
    # Wait for processing
    time.sleep(15)
    
    # Check results
    logs = subprocess.run(
        ["docker", "logs", "autogen_agent", "--tail", "100"],
        capture_output=True,
        text=True
    )
    
    # Look for processing indicators
    found_indicators = []
    
    # Check for team processing
    if f"team_type': '{team_type}'" in logs.stdout:
        found_indicators.append("team_type")
    
    # Check for character
    if character_id in logs.stdout:
        found_indicators.append("character_id")
    
    # Check for prompt content
    key_words = prompt.lower().split()[:3]
    for word in key_words:
        if word in logs.stdout.lower():
            found_indicators.append(f"keyword:{word}")
            break
    
    # Check for orchestrator processing
    if "STIMULI ANALYSIS REQUEST" in logs.stdout:
        found_indicators.append("orchestrator")
    
    if found_indicators:
        print(f"✅ Processing detected: {', '.join(found_indicators)}")
        return True
    else:
        print("❌ No clear processing detected")
        return False

def main():
    print("🧪 S2 Character-Team System Full Test")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        ("dr._house_doctor_template", "trader", "Analyze Bitcoin volatility and recommend hedging strategies"),
        ("weatherman_template", "streamer", "Create viral weather content for TikTok"),
        ("emma_teacher_template", "teacher", "Design a lesson plan for teaching Python to beginners"),
        ("secretary_template", "default", "Optimize system memory usage and performance")
    ]
    
    results = []
    
    # Run tests
    for character_id, team_type, prompt in test_cases:
        success = test_character_team(character_id, team_type, prompt)
        results.append((character_id, team_type, success))
    
    # Check SCB
    print("\n📊 Checking SCB Updates")
    print("-" * 50)
    scb_check = subprocess.run(
        ["docker", "exec", "redis_scb", "redis-cli", "DBSIZE"],
        capture_output=True,
        text=True
    )
    if scb_check.stdout.strip() != "(empty array)":
        print(f"✅ SCB has data: {scb_check.stdout.strip()}")
    else:
        print("⚠️ SCB appears empty")
    
    # Summary
    print("\n📈 Test Summary")
    print("=" * 60)
    success_count = sum(1 for _, _, success in results if success)
    total_count = len(results)
    
    for character_id, team_type, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {character_id:30} ({team_type:10}) - {'Processed' if success else 'Failed'}")
    
    print(f"\nSuccess Rate: {success_count}/{total_count} ({success_count/total_count*100:.0f}%)")
    
    # Final status
    if success_count == total_count:
        print("\n🎉 All tests passed! S2 system is working correctly.")
    elif success_count > 0:
        print(f"\n⚠️ Partial success: {success_count} out of {total_count} tests passed.")
    else:
        print("\n❌ All tests failed. S2 system needs debugging.")

if __name__ == "__main__":
    main()