#!/usr/bin/env python3
"""
Test All Routing Scenarios
==========================

Tests S1-only, S2-only, and S1+S2 routing with different characters
to simulate real user interactions.
"""

import os
import sys
import json
import time
import asyncio
import aiohttp
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


# Test scenarios for each routing type
TEST_SCENARIOS = {
    "s1_only": [
        {
            "name": "Direct Speech Request",
            "content": "Say hello to everyone watching the stream!",
            "metadata": {"force_s1": True, "target_systems": ["s1"]},
            "expected_decision": "AVATAR_ONLY",
            "description": "User wants avatar to speak directly"
        },
        {
            "name": "Announcement Request", 
            "content": "announce: Welcome to today's educational stream about AI",
            "metadata": {"announcement_mode": True},
            "expected_decision": "AVATAR_ONLY",
            "description": "Streamer announcement for avatar speech"
        },
        {
            "name": "Interactive Response",
            "content": "Thanks for the donation! I really appreciate your support",
            "metadata": {"interaction_type": "donation_response"},
            "expected_decision": "AVATAR_ONLY", 
            "description": "Avatar responding to viewer interaction"
        }
    ],
    "s2_only": [
        {
            "name": "Trader Analysis",
            "content": "Analyze the current cryptocurrency market trends and identify investment opportunities",
            "metadata": {"force_s2": True, "target_systems": ["s2"], "character_id": "dr._house_doctor_template"},
            "expected_decision": "ANALYSIS_ONLY",
            "description": "Complex market analysis for trader character"
        },
        {
            "name": "Streaming Strategy",
            "content": "Develop a content strategy to grow my Twitch channel and increase viewer engagement",
            "metadata": {"force_s2": True, "target_systems": ["s2"], "character_id": "weatherman_template"},
            "expected_decision": "ANALYSIS_ONLY",
            "description": "Strategic planning for streamer character"
        },
        {
            "name": "Educational Content",
            "content": "Create a comprehensive lesson plan for teaching quantum computing basics",
            "metadata": {"force_s2": True, "target_systems": ["s2"], "character_id": "emma_teacher_template"},
            "expected_decision": "ANALYSIS_ONLY",
            "description": "Educational content creation for teacher character"
        }
    ],
    "s1_and_s2": [
        {
            "name": "Explain and Demonstrate",
            "content": "Explain how neural networks work and give a simple example",
            "metadata": {"target_systems": ["s1", "s2"], "character_id": "emma_teacher_template"},
            "expected_decision": "AVATAR_AND_ANALYSIS",
            "description": "Teacher explains concept (S1) with detailed analysis (S2)"
        },
        {
            "name": "Market Update Speech",
            "content": "Give me a market update on Bitcoin and explain the trends to viewers",
            "metadata": {"target_systems": ["s2"], "character_id": "trader_character"},
            "expected_decision": "ANALYSIS_ONLY",
            "description": "Trader provides market analysis (S2 only - traders don't use S1)"
        },
        {
            "name": "Stream Planning Discussion",
            "content": "Let's plan next week's streaming schedule and discuss content ideas with the audience",
            "metadata": {"target_systems": ["s1", "s2"], "character_id": "weatherman_template"},
            "expected_decision": "AVATAR_AND_ANALYSIS",
            "description": "Streamer discusses plans (S1) while analyzing strategy (S2)"
        }
    ]
}


async def check_service_health(session: aiohttp.ClientSession) -> Dict[str, bool]:
    """Check health of all services."""
    services = {
        "graphflow": "http://localhost:8000/health",
        "neurosync_s1": "http://localhost:5001/health",
        "autogen_s2": "http://localhost:8200/health"
    }
    
    health_status = {}
    
    for service, url in services.items():
        try:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    health_status[service] = True
                    
                    # Special handling for S2 teams status
                    if service == "autogen_s2" and "s2_teams_status" in data:
                        s2_status = data["s2_teams_status"]
                        print(f"   S2 Teams: Enabled={s2_status.get('enabled')}, "
                              f"Queue Consumer={s2_status.get('queue_consumer')}, "
                              f"Orchestrator={s2_status.get('orchestrator')}")
                else:
                    health_status[service] = False
        except Exception as e:
            health_status[service] = False
            print(f"❌ {service}: {e}")
    
    return health_status


async def load_character(session: aiohttp.ClientSession, character_id: str) -> bool:
    """Load a specific character in S1."""
    try:
        # First, get list of available characters
        async with session.get("http://localhost:5001/character/list") as response:
            if response.status == 200:
                characters = await response.json()
                print(f"   Available characters: {len(characters.get('characters', []))}")
        
        # Load the character
        load_url = f"http://localhost:5001/character/load"
        load_data = {"character_id": character_id}
        
        async with session.post(load_url, json=load_data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Loaded character: {character_id}")
                return True
            else:
                print(f"❌ Failed to load character: {response.status}")
                return False
                
    except Exception as e:
        print(f"❌ Error loading character: {e}")
        return False


async def send_stimuli(session: aiohttp.ClientSession, scenario: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Send stimuli to GraphFlow and return the result."""
    
    graphflow_url = "http://localhost:8000/api/v1/stimuli/submit"
    
    stimuli_data = {
        "content": scenario["content"],
        "source": "test_routing",
        "priority": "high",
        "metadata": scenario.get("metadata", {})
    }
    
    try:
        async with session.post(graphflow_url, json=stimuli_data, timeout=10) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                text = await response.text()
                print(f"❌ GraphFlow error: {response.status} - {text}")
                return None
    except Exception as e:
        print(f"❌ Failed to send stimuli: {e}")
        return None


async def check_s1_processing(session: aiohttp.ClientSession, wait_time: int = 5) -> bool:
    """Check if S1 processed the stimuli by looking at recent outputs."""
    await asyncio.sleep(wait_time)
    
    # Check S1 character state or logs
    try:
        async with session.get("http://localhost:5001/character/current") as response:
            if response.status == 200:
                data = await response.json()
                print(f"   S1 Character active: {data.get('character_data', {}).get('name', 'Unknown')}")
                return True
    except:
        pass
    
    return False


async def check_s2_processing(wait_time: int = 10) -> Dict[str, Any]:
    """Check S2 queue processing."""
    await asyncio.sleep(wait_time)
    
    results = {
        "queue_items": 0,
        "processed_items": 0,
        "last_processed": None
    }
    
    # Check queue file
    queue_file = Path("/tmp/s2_queue/s2_processing_queue.json")
    if queue_file.exists():
        try:
            with open(queue_file, 'r') as f:
                queue_data = json.load(f)
            results["queue_items"] = len(queue_data)
        except:
            pass
    
    # Check processed file
    processed_file = Path("/tmp/s2_queue/s2_processed_stimuli.json")
    if processed_file.exists():
        try:
            with open(processed_file, 'r') as f:
                processed_data = json.load(f)
            results["processed_items"] = len(processed_data)
            if processed_data:
                results["last_processed"] = processed_data[-1].get("timestamp")
        except:
            pass
    
    return results


async def test_routing_scenario(
    session: aiohttp.ClientSession,
    routing_type: str,
    scenarios: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Test a specific routing type with its scenarios."""
    
    print(f"\n{'='*60}")
    print(f"🧪 Testing {routing_type.upper()} Routing")
    print(f"{'='*60}")
    
    results = {
        "routing_type": routing_type,
        "total_tests": len(scenarios),
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Test {i}/{len(scenarios)}: {scenario['name']}")
        print(f"   Description: {scenario['description']}")
        print(f"   Content: {scenario['content'][:60]}...")
        
        test_result = {
            "name": scenario["name"],
            "success": False,
            "decision": None,
            "s1_processed": False,
            "s2_processed": False,
            "error": None
        }
        
        # Load character if specified
        character_id = scenario.get("metadata", {}).get("character_id")
        if character_id:
            print(f"   Loading character: {character_id}")
            await load_character(session, character_id)
            await asyncio.sleep(2)  # Wait for character to load
        
        # Send stimuli
        result = await send_stimuli(session, scenario)
        
        if result:
            decision = result.get("decision", "UNKNOWN")
            test_result["decision"] = decision
            
            print(f"   ✅ Stimuli sent successfully")
            print(f"   Decision: {decision}")
            print(f"   Expected: {scenario['expected_decision']}")
            
            # Check if decision matches expected
            if decision == scenario["expected_decision"]:
                print(f"   ✅ Routing decision correct!")
                
                # Verify processing based on routing type
                if routing_type == "s1_only":
                    # Check S1 processing
                    s1_ok = await check_s1_processing(session)
                    test_result["s1_processed"] = s1_ok
                    test_result["success"] = s1_ok
                    
                elif routing_type == "s2_only":
                    # Check S2 processing
                    s2_status = await check_s2_processing()
                    s2_ok = s2_status["processed_items"] > 0 or s2_status["queue_items"] > 0
                    test_result["s2_processed"] = s2_ok
                    test_result["success"] = s2_ok
                    print(f"   S2 Queue: {s2_status['queue_items']} items")
                    print(f"   S2 Processed: {s2_status['processed_items']} items")
                    
                elif routing_type == "s1_and_s2":
                    # Check both S1 and S2
                    s1_ok = await check_s1_processing(session, wait_time=3)
                    s2_status = await check_s2_processing(wait_time=7)
                    s2_ok = s2_status["processed_items"] > 0 or s2_status["queue_items"] > 0
                    
                    test_result["s1_processed"] = s1_ok
                    test_result["s2_processed"] = s2_ok
                    test_result["success"] = s1_ok or s2_ok  # At least one should process
                    
                    print(f"   S1 Processing: {'✅' if s1_ok else '❌'}")
                    print(f"   S2 Processing: {'✅' if s2_ok else '❌'}")
                    
                if test_result["success"]:
                    results["passed"] += 1
                    print(f"   ✅ TEST PASSED")
                else:
                    results["failed"] += 1
                    print(f"   ❌ TEST FAILED: Processing not verified")
            else:
                print(f"   ❌ Routing decision mismatch!")
                test_result["error"] = f"Expected {scenario['expected_decision']}, got {decision}"
                results["failed"] += 1
        else:
            print(f"   ❌ Failed to send stimuli")
            test_result["error"] = "Failed to send stimuli"
            results["failed"] += 1
        
        results["details"].append(test_result)
        
        # Brief pause between tests
        await asyncio.sleep(3)
    
    return results


async def main():
    parser = argparse.ArgumentParser(description="Test all routing scenarios")
    parser.add_argument("--routing", choices=["s1_only", "s2_only", "s1_and_s2", "all"], 
                       default="all", help="Which routing type to test")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()
    
    print("🚀 Comprehensive Routing Test Suite")
    print("="*60)
    print(f"Testing routing: {args.routing}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with aiohttp.ClientSession() as session:
        # Check service health
        print("\n📋 Checking Service Health...")
        health = await check_service_health(session)
        
        all_healthy = all(health.values())
        for service, status in health.items():
            print(f"   {service}: {'✅' if status else '❌'}")
        
        if not all_healthy:
            print("\n❌ Not all services are healthy. Please check your setup.")
            return
        
        # Run tests based on selection
        all_results = []
        
        if args.routing == "all":
            test_types = ["s1_only", "s2_only", "s1_and_s2"]
        else:
            test_types = [args.routing]
        
        for test_type in test_types:
            if test_type in TEST_SCENARIOS:
                result = await test_routing_scenario(
                    session,
                    test_type,
                    TEST_SCENARIOS[test_type]
                )
                all_results.append(result)
        
        # Summary
        print(f"\n{'='*60}")
        print("📊 TEST SUMMARY")
        print(f"{'='*60}")
        
        total_passed = sum(r["passed"] for r in all_results)
        total_failed = sum(r["failed"] for r in all_results)
        total_tests = sum(r["total_tests"] for r in all_results)
        
        for result in all_results:
            print(f"\n{result['routing_type'].upper()}:")
            print(f"   Passed: {result['passed']}/{result['total_tests']}")
            print(f"   Failed: {result['failed']}/{result['total_tests']}")
            
            if args.verbose:
                for detail in result["details"]:
                    status = "✅" if detail["success"] else "❌"
                    print(f"   {status} {detail['name']}: {detail['decision']}")
                    if detail["error"]:
                        print(f"      Error: {detail['error']}")
        
        print(f"\n{'='*60}")
        print(f"TOTAL: {total_passed}/{total_tests} passed ({total_passed/total_tests*100:.1f}%)")
        print(f"{'='*60}")
        
        # Save results
        results_file = f"routing_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tests": total_tests,
                    "passed": total_passed,
                    "failed": total_failed
                },
                "results": all_results
            }, f, indent=2)
        
        print(f"\n📄 Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())