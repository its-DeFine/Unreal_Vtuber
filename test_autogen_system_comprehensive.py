#!/usr/bin/env python3
"""
Comprehensive test suite for AutoGen autonomous agent system

Tests:
1. System connectivity and health
2. Tool selection intelligence
3. SMART goal functionality
4. Auto-improvement capabilities
5. Statistics extraction
6. Memory system (PostgreSQL + Cognee fallback)
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Configuration
AUTOGEN_URL = "http://localhost:8201"
POSTGRES_URL = "postgresql://postgres:postgres@localhost:5435/autonomous_agent"

class AutoGenSystemTester:
    def __init__(self):
        self.results = []
        self.session = None
        
    async def setup(self):
        """Initialize test session"""
        self.session = aiohttp.ClientSession()
        
    async def teardown(self):
        """Cleanup test session"""
        if self.session:
            await self.session.close()
            
    async def test_system_health(self):
        """Test 1: Check system health and connectivity"""
        print("\n🔍 Test 1: System Health Check")
        print("-" * 50)
        
        try:
            # Check API health
            async with self.session.get(f"{AUTOGEN_URL}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ API Health: {data}")
                    self.results.append(("API Health", True, data))
                else:
                    print(f"❌ API Health failed: {resp.status}")
                    self.results.append(("API Health", False, f"Status: {resp.status}"))
                    
            # Check database connectivity via API
            async with self.session.get(f"{AUTOGEN_URL}/api/test-db") as resp:
                if resp.status == 200:
                    print("✅ Database connectivity: OK")
                    self.results.append(("Database", True, "Connected"))
                else:
                    print("❌ Database connectivity: Failed")
                    self.results.append(("Database", False, "Not connected"))
                    
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            self.results.append(("System Health", False, str(e)))
            
    async def test_tool_selection(self):
        """Test 2: Verify intelligent tool selection"""
        print("\n🔍 Test 2: Tool Selection Intelligence")
        print("-" * 50)
        
        test_contexts = [
            {
                "context": "I need to create a goal for improving system performance",
                "expected_tool": "goal_management_tools"
            },
            {
                "context": "Show me the VTuber avatar",
                "expected_tool": "advanced_vtuber_control"
            },
            {
                "context": "Analyze and improve the code performance",
                "expected_tool": "core_evolution_tool"
            }
        ]
        
        for test in test_contexts:
            try:
                # Get tool selection via API
                async with self.session.post(
                    f"{AUTOGEN_URL}/api/select-tool",
                    json={"context": test["context"]}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        selected = data.get("tool", "")
                        score = data.get("score", 0)
                        
                        if test["expected_tool"] in selected:
                            print(f"✅ Context: '{test['context'][:50]}...'")
                            print(f"   Selected: {selected} (score: {score})")
                            self.results.append((f"Tool Selection - {test['expected_tool']}", True, f"Score: {score}"))
                        else:
                            print(f"❌ Context: '{test['context'][:50]}...'")
                            print(f"   Expected: {test['expected_tool']}, Got: {selected}")
                            self.results.append((f"Tool Selection - {test['expected_tool']}", False, f"Got: {selected}"))
                    else:
                        print(f"❌ Tool selection API failed: {resp.status}")
                        self.results.append(("Tool Selection", False, f"API error: {resp.status}"))
                        
            except Exception as e:
                print(f"❌ Tool selection test failed: {e}")
                self.results.append(("Tool Selection", False, str(e)))
                
    async def test_smart_goals(self):
        """Test 3: Test SMART goal creation and tracking"""
        print("\n🔍 Test 3: SMART Goal Management")
        print("-" * 50)
        
        try:
            # Create a SMART goal
            goal_request = {
                "description": "Improve tool selection accuracy by 20% in the next 7 days",
                "category": "performance"
            }
            
            async with self.session.post(
                f"{AUTOGEN_URL}/api/goals/create",
                json=goal_request
            ) as resp:
                if resp.status == 200:
                    goal_data = await resp.json()
                    goal_id = goal_data.get("id")
                    print(f"✅ Created SMART goal: {goal_id}")
                    print(f"   Specific: {goal_data.get('specific')}")
                    print(f"   Measurable: {goal_data.get('measurable')}")
                    print(f"   Achievable: {goal_data.get('achievable')}")
                    print(f"   Relevant: {goal_data.get('relevant')}")
                    print(f"   Time-bound: {goal_data.get('time_bound')}")
                    self.results.append(("SMART Goal Creation", True, f"Goal ID: {goal_id}"))
                    
                    # Test goal progress tracking
                    await asyncio.sleep(1)
                    
                    # Update progress
                    progress_update = {
                        "goal_id": goal_id,
                        "metric_updates": {
                            "tool_selection_accuracy": 0.75
                        }
                    }
                    
                    async with self.session.post(
                        f"{AUTOGEN_URL}/api/goals/progress",
                        json=progress_update
                    ) as prog_resp:
                        if prog_resp.status == 200:
                            progress_data = await prog_resp.json()
                            print(f"✅ Goal progress updated: {progress_data.get('progress', 0)}%")
                            self.results.append(("Goal Progress Tracking", True, f"Progress: {progress_data.get('progress')}%"))
                        else:
                            print("❌ Goal progress update failed")
                            self.results.append(("Goal Progress Tracking", False, f"Status: {prog_resp.status}"))
                else:
                    print(f"❌ SMART goal creation failed: {resp.status}")
                    self.results.append(("SMART Goal Creation", False, f"Status: {resp.status}"))
                    
        except Exception as e:
            print(f"❌ SMART goal test failed: {e}")
            self.results.append(("SMART Goals", False, str(e)))
            
    async def test_auto_improvement(self):
        """Test 4: Test Darwin-Gödel auto-improvement capabilities"""
        print("\n🔍 Test 4: Auto-Improvement (Darwin-Gödel)")
        print("-" * 50)
        
        try:
            # Request code analysis
            analysis_request = {
                "target_module": "tool_registry",
                "improvement_type": "performance"
            }
            
            async with self.session.post(
                f"{AUTOGEN_URL}/api/evolution/analyze",
                json=analysis_request
            ) as resp:
                if resp.status == 200:
                    analysis = await resp.json()
                    print(f"✅ Code analysis completed")
                    print(f"   Bottlenecks found: {len(analysis.get('bottlenecks', []))}")
                    print(f"   Improvements suggested: {len(analysis.get('improvements', []))}")
                    self.results.append(("Code Analysis", True, f"Found {len(analysis.get('bottlenecks', []))} issues"))
                    
                    # Test improvement generation (simulation mode)
                    if analysis.get('improvements'):
                        improvement_req = {
                            "improvement_id": analysis['improvements'][0].get('id'),
                            "simulation_mode": True
                        }
                        
                        async with self.session.post(
                            f"{AUTOGEN_URL}/api/evolution/apply",
                            json=improvement_req
                        ) as imp_resp:
                            if imp_resp.status == 200:
                                imp_result = await imp_resp.json()
                                print(f"✅ Improvement simulation: {imp_result.get('status')}")
                                self.results.append(("Auto-Improvement", True, "Simulation successful"))
                            else:
                                print("❌ Improvement simulation failed")
                                self.results.append(("Auto-Improvement", False, f"Status: {imp_resp.status}"))
                else:
                    print(f"❌ Code analysis failed: {resp.status}")
                    self.results.append(("Code Analysis", False, f"Status: {resp.status}"))
                    
        except Exception as e:
            print(f"❌ Auto-improvement test failed: {e}")
            self.results.append(("Auto-Improvement", False, str(e)))
            
    async def test_statistics_extraction(self):
        """Test 5: Test statistics and metrics extraction"""
        print("\n🔍 Test 5: Statistics Extraction")
        print("-" * 50)
        
        try:
            # Get system statistics
            async with self.session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    print(f"✅ System statistics retrieved:")
                    print(f"   Total decisions: {stats.get('total_decisions', 0)}")
                    print(f"   Tool usage: {stats.get('tool_usage', {})}")
                    print(f"   Success rate: {stats.get('success_rate', 0):.2%}")
                    print(f"   Average decision time: {stats.get('avg_decision_time', 0):.2f}s")
                    self.results.append(("Statistics Extraction", True, f"Total decisions: {stats.get('total_decisions', 0)}"))
                    
                    # Get detailed analytics
                    async with self.session.get(f"{AUTOGEN_URL}/api/analytics/performance") as perf_resp:
                        if perf_resp.status == 200:
                            perf_data = await perf_resp.json()
                            print(f"✅ Performance analytics:")
                            print(f"   Decision patterns: {len(perf_data.get('patterns', []))}")
                            print(f"   Performance trends: {perf_data.get('trend', 'stable')}")
                            self.results.append(("Performance Analytics", True, f"Patterns: {len(perf_data.get('patterns', []))}"))
                        else:
                            print("❌ Performance analytics failed")
                            self.results.append(("Performance Analytics", False, f"Status: {perf_resp.status}"))
                else:
                    print(f"❌ Statistics retrieval failed: {resp.status}")
                    self.results.append(("Statistics Extraction", False, f"Status: {resp.status}"))
                    
        except Exception as e:
            print(f"❌ Statistics test failed: {e}")
            self.results.append(("Statistics", False, str(e)))
            
    async def test_memory_system(self):
        """Test 6: Test memory system with Cognee fallback"""
        print("\n🔍 Test 6: Memory System (PostgreSQL + Cognee)")
        print("-" * 50)
        
        try:
            # Test memory storage
            memory_data = {
                "context": {"test": "memory storage"},
                "action": "test_action",
                "result": {"success": True, "data": "test data"}
            }
            
            async with self.session.post(
                f"{AUTOGEN_URL}/api/memory/store",
                json=memory_data
            ) as resp:
                if resp.status == 200:
                    mem_result = await resp.json()
                    memory_id = mem_result.get("memory_id")
                    print(f"✅ Memory stored: {memory_id}")
                    print(f"   Storage: {mem_result.get('storage', 'unknown')}")
                    self.results.append(("Memory Storage", True, f"ID: {memory_id}"))
                    
                    # Test memory retrieval
                    await asyncio.sleep(1)
                    
                    retrieval_req = {
                        "query": "test memory storage",
                        "limit": 5
                    }
                    
                    async with self.session.post(
                        f"{AUTOGEN_URL}/api/memory/search",
                        json=retrieval_req
                    ) as search_resp:
                        if search_resp.status == 200:
                            memories = await search_resp.json()
                            print(f"✅ Retrieved {len(memories)} memories")
                            if memories:
                                print(f"   Most relevant: {memories[0].get('id', 'unknown')}")
                                print(f"   Relevance: {memories[0].get('relevance', 0):.2f}")
                            self.results.append(("Memory Retrieval", True, f"Found {len(memories)} memories"))
                        else:
                            print("❌ Memory retrieval failed")
                            self.results.append(("Memory Retrieval", False, f"Status: {search_resp.status}"))
                else:
                    print(f"❌ Memory storage failed: {resp.status}")
                    self.results.append(("Memory Storage", False, f"Status: {resp.status}"))
                    
        except Exception as e:
            print(f"❌ Memory system test failed: {e}")
            self.results.append(("Memory System", False, str(e)))
            
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        print("\nDetailed Results:")
        print("-" * 60)
        for test_name, success, details in self.results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} | {test_name:<30} | {details}")
            
        print("\n" + "=" * 60)
        
        # Return overall success
        return passed == total
        
async def main():
    """Run all tests"""
    print("🚀 AutoGen System Comprehensive Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Target: {AUTOGEN_URL}")
    print("=" * 60)
    
    tester = AutoGenSystemTester()
    
    try:
        await tester.setup()
        
        # Run all tests
        await tester.test_system_health()
        await tester.test_tool_selection()
        await tester.test_smart_goals()
        await tester.test_auto_improvement()
        await tester.test_statistics_extraction()
        await tester.test_memory_system()
        
        # Print summary
        success = tester.print_summary()
        
        if success:
            print("\n🎉 All tests passed! System is functioning as intended.")
        else:
            print("\n⚠️  Some tests failed. Please check the system configuration.")
            
    finally:
        await tester.teardown()
        
if __name__ == "__main__":
    asyncio.run(main())