#!/usr/bin/env python3
"""
S2 Memory and Conversation Test
===============================

Test S2 teams' ability to:
1. Remember past conversations
2. Use Neo4j and SCB for info recovery
3. Maintain context across multiple interactions
4. Demonstrate team memory capabilities

Usage:
    python s2_memory_conversation_test.py
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, List

async def test_s2_memory_capabilities():
    """Test S2 team memory and conversation continuity"""
    
    print("🧠 Testing S2 Memory and Conversation Capabilities")
    
    # Test scenario: Multi-conversation memory
    trader_conversation = [
        {
            "step": 1,
            "content": "Remember this about me: My name is Alice, I'm 35 years old, conservative investor, prefer low-risk investments like bonds and blue-chip stocks. I have $50k to invest.",
            "expected_memory": ["Alice", "35", "conservative", "low-risk", "50k"]
        },
        {
            "step": 2, 
            "content": "What investment strategy would you recommend based on my profile?",
            "expected_memory": ["Alice", "conservative", "low-risk", "previous", "profile"]
        },
        {
            "step": 3,
            "content": "How should I diversify my $50k portfolio given my risk tolerance?",
            "expected_memory": ["50k", "risk tolerance", "diversify", "conservative"]
        }
    ]
    
    educator_conversation = [
        {
            "step": 1,
            "content": "Remember: I'm learning Python programming. I'm a beginner who struggles with loops and functions. I learn best with visual examples.",
            "expected_memory": ["Python", "beginner", "loops", "functions", "visual"]
        },
        {
            "step": 2,
            "content": "Can you help me understand for loops better, considering my learning style?",
            "expected_memory": ["for loops", "learning style", "visual", "beginner"]
        },
        {
            "step": 3,
            "content": "Based on my progress with loops, what should I learn next in Python?",
            "expected_memory": ["progress", "loops", "next", "Python"]
        }
    ]
    
    streamer_conversation = [
        {
            "step": 1,
            "content": "Remember this: I'm a new streamer with 100 followers, I stream gaming content 3 times a week, my audience is mostly 18-25 years old gamers.",
            "expected_memory": ["100 followers", "gaming", "3 times", "18-25", "audience"]
        },
        {
            "step": 2,
            "content": "How can I grow my follower count based on my current setup?",
            "expected_memory": ["grow", "follower", "current", "setup", "gaming"]
        },
        {
            "step": 3,
            "content": "What content would work best for my 18-25 gaming audience?",
            "expected_memory": ["18-25", "gaming", "audience", "content"]
        }
    ]
    
    # Test each team's memory capabilities
    results = []
    
    for team_name, conversation in [
        ("trader", trader_conversation),
        ("educator", educator_conversation), 
        ("streamer", streamer_conversation)
    ]:
        print(f"\n🎯 Testing {team_name.upper()} team memory...")
        team_results = await test_team_memory(team_name, conversation)
        results.append({
            "team": team_name,
            "results": team_results
        })
    
    # Test cross-team memory sharing
    print(f"\n🔗 Testing cross-team memory sharing...")
    cross_team_results = await test_cross_team_memory()
    results.append({
        "team": "cross_team",
        "results": cross_team_results
    })
    
    # Generate report
    generate_memory_report(results)
    
    return results

async def test_team_memory(team_name: str, conversation: List[Dict]) -> List[Dict]:
    """Test memory capabilities of a specific team"""
    
    team_results = []
    
    async with aiohttp.ClientSession() as session:
        for step_data in conversation:
            step = step_data["step"]
            content = step_data["content"]
            expected_memory = step_data["expected_memory"]
            
            print(f"  Step {step}: {content[:50]}...")
            
            try:
                start_time = time.time()
                async with session.post(
                    "http://localhost:8200/api/test/process",
                    json={
                        "team_type": team_name,
                        "content": content,
                        "metadata": {
                            "memory_test": True,
                            "step": step,
                            "session_id": f"{team_name}_memory_test",
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    timeout=60
                ) as response:
                    processing_time = time.time() - start_time
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Analyze response for memory indicators
                        response_content = str(result.get("result", {}))
                        memory_analysis = analyze_memory_indicators(
                            response_content, 
                            expected_memory,
                            step > 1  # Expect memory after first step
                        )
                        
                        step_result = {
                            "step": step,
                            "content": content,
                            "success": result.get("status") == "success",
                            "processing_time": processing_time,
                            "memory_analysis": memory_analysis,
                            "response": result.get("result", {}),
                            "insights_generated": bool(result.get("result", {}).get("insights")),
                            "total_messages": result.get("result", {}).get("total_messages", 0)
                        }
                        
                        memory_found = memory_analysis["memory_score"] > 0
                        print(f"    ✅ Step {step}: {processing_time:.2f}s, Memory: {memory_found}")
                        
                    else:
                        step_result = {
                            "step": step,
                            "content": content,
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "processing_time": processing_time
                        }
                        print(f"    ❌ Step {step}: Failed with HTTP {response.status}")
                    
                    team_results.append(step_result)
                    
                    # Wait between steps to allow memory processing
                    await asyncio.sleep(2)
            
            except Exception as e:
                error_result = {
                    "step": step,
                    "content": content,
                    "success": False,
                    "error": str(e),
                    "processing_time": 0
                }
                team_results.append(error_result)
                print(f"    ❌ Step {step}: Error - {e}")
    
    return team_results

def analyze_memory_indicators(response_content: str, expected_memory: List[str], expect_memory: bool) -> Dict[str, Any]:
    """Analyze response for memory indicators"""
    
    response_lower = response_content.lower()
    
    # Memory keywords
    memory_keywords = [
        "remember", "recall", "mentioned", "previous", "earlier", "before",
        "discussed", "conversation", "you said", "last time", "profile",
        "context", "based on what", "considering", "given that"
    ]
    
    # Check for memory keywords
    memory_indicators_found = [kw for kw in memory_keywords if kw in response_lower]
    
    # Check for expected memory content
    expected_found = [item for item in expected_memory if item.lower() in response_lower]
    
    # Calculate memory score
    memory_score = len(memory_indicators_found) + (len(expected_found) * 2)
    
    return {
        "expects_memory": expect_memory,
        "memory_indicators": memory_indicators_found,
        "expected_content_found": expected_found,
        "memory_score": memory_score,
        "has_memory_reference": len(memory_indicators_found) > 0,
        "response_length": len(response_content)
    }

async def test_cross_team_memory() -> List[Dict]:
    """Test memory sharing between different teams"""
    
    cross_team_results = []
    
    # Scenario: Information shared with trader team, then accessed by educator team
    async with aiohttp.ClientSession() as session:
        
        # Step 1: Share information with trader team
        print("  Step 1: Sharing info with trader team...")
        try:
            async with session.post(
                "http://localhost:8200/api/test/process",
                json={
                    "team_type": "trader",
                    "content": "Please remember: I'm interested in learning about cryptocurrency trading while maintaining a conservative investment approach.",
                    "metadata": {
                        "cross_team_test": True,
                        "step": 1,
                        "session_id": "cross_team_test"
                    }
                },
                timeout=60
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    cross_team_results.append({
                        "step": 1,
                        "team": "trader", 
                        "action": "store_info",
                        "success": result.get("status") == "success",
                        "result": result.get("result", {})
                    })
                    print("    ✅ Info stored with trader team")
                else:
                    print("    ❌ Failed to store info with trader team")
        
        except Exception as e:
            print(f"    ❌ Error storing info: {e}")
        
        # Wait for potential cross-team propagation
        await asyncio.sleep(3)
        
        # Step 2: Try to access information from educator team
        print("  Step 2: Accessing info from educator team...")
        try:
            async with session.post(
                "http://localhost:8200/api/test/process",
                json={
                    "team_type": "educator",
                    "content": "I want to learn about cryptocurrency. Can you help me based on any previous context about my interests?",
                    "metadata": {
                        "cross_team_test": True,
                        "step": 2,
                        "session_id": "cross_team_test"
                    }
                },
                timeout=60
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    response_content = str(result.get("result", {}))
                    
                    # Check if educator team shows awareness of trader context
                    context_indicators = ["conservative", "trading", "cryptocurrency", "investment"]
                    context_found = [term for term in context_indicators if term.lower() in response_content.lower()]
                    
                    cross_team_results.append({
                        "step": 2,
                        "team": "educator",
                        "action": "retrieve_info", 
                        "success": result.get("status") == "success",
                        "context_awareness": len(context_found) > 0,
                        "context_found": context_found,
                        "result": result.get("result", {})
                    })
                    
                    context_aware = len(context_found) > 0
                    print(f"    {'✅' if context_aware else '⚠️'} Educator team context awareness: {context_aware}")
                else:
                    print("    ❌ Failed to get response from educator team")
        
        except Exception as e:
            print(f"    ❌ Error retrieving info: {e}")
    
    return cross_team_results

def generate_memory_report(results: List[Dict]):
    """Generate comprehensive memory test report"""
    
    print(f"\n{'='*80}")
    print(f"🧠 S2 MEMORY TEST REPORT")
    print(f"{'='*80}")
    
    total_steps = 0
    successful_steps = 0
    memory_detected_steps = 0
    
    for team_result in results:
        team_name = team_result["team"]
        team_tests = team_result["results"]
        
        if team_name != "cross_team":
            print(f"\n📊 {team_name.upper()} TEAM RESULTS:")
            
            team_steps = len(team_tests)
            team_success = len([t for t in team_tests if t.get("success", False)])
            team_memory = len([t for t in team_tests if t.get("memory_analysis", {}).get("has_memory_reference", False)])
            
            print(f"  Total Steps: {team_steps}")
            print(f"  Successful: {team_success}/{team_steps} ({team_success/team_steps*100:.1f}%)")
            print(f"  Memory Detected: {team_memory}/{team_steps} ({team_memory/team_steps*100:.1f}%)")
            
            # Show memory progression
            for test in team_tests:
                step = test.get("step", 0)
                memory_score = test.get("memory_analysis", {}).get("memory_score", 0)
                expected_content = len(test.get("memory_analysis", {}).get("expected_content_found", []))
                print(f"    Step {step}: Memory Score {memory_score}, Expected Content Found: {expected_content}")
            
            total_steps += team_steps
            successful_steps += team_success
            memory_detected_steps += team_memory
    
    # Cross-team results
    cross_team_data = [r for r in results if r["team"] == "cross_team"]
    if cross_team_data:
        cross_results = cross_team_data[0]["results"]
        print(f"\n🔗 CROSS-TEAM MEMORY RESULTS:")
        
        for test in cross_results:
            step = test.get("step", 0)
            team = test.get("team", "")
            action = test.get("action", "")
            success = test.get("success", False)
            context_aware = test.get("context_awareness", False)
            
            if action == "store_info":
                print(f"  Step {step} ({team}): Store Info - {'✅' if success else '❌'}")
            elif action == "retrieve_info":
                print(f"  Step {step} ({team}): Retrieve Info - {'✅' if success else '❌'}, Context Aware: {'✅' if context_aware else '❌'}")
    
    # Overall summary
    print(f"\n📈 OVERALL SUMMARY:")
    print(f"Total Test Steps: {total_steps}")
    print(f"Successful Steps: {successful_steps}/{total_steps} ({successful_steps/total_steps*100:.1f}%)")
    print(f"Memory Detection: {memory_detected_steps}/{total_steps} ({memory_detected_steps/total_steps*100:.1f}%)")
    
    # Save detailed report
    report_file = f"/tmp/s2_memory_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "memory_detected_steps": memory_detected_steps,
            "success_rate": f"{successful_steps/total_steps*100:.1f}%",
            "memory_detection_rate": f"{memory_detected_steps/total_steps*100:.1f}%",
            "detailed_results": results
        }, f, indent=2)
    
    print(f"\n📁 Detailed report saved to: {report_file}")
    print(f"{'='*80}")

async def main():
    """Main test execution"""
    print("🧠 Starting S2 Memory and Conversation Test")
    
    try:
        results = await test_s2_memory_capabilities()
        print("✅ S2 memory test completed successfully")
        return results
    except Exception as e:
        print(f"❌ S2 memory test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())