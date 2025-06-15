#!/usr/bin/env python3
"""
Test key system capabilities:
1. SMART goal creation and tracking
2. Auto-improvement (Darwin-Gödel)
3. Statistics extraction
4. Tool diversity after fixes
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

AUTOGEN_URL = "http://localhost:8202"

class SystemCapabilityTester:
    def __init__(self):
        self.session = None
        self.results = {}
        
    async def setup(self):
        self.session = aiohttp.ClientSession()
        
    async def teardown(self):
        if self.session:
            await self.session.close()
            
    async def test_smart_goals(self):
        """Test SMART goal functionality"""
        print("\n🎯 Testing SMART Goal System...")
        print("-" * 50)
        
        # Test creating a goal via direct API (since we fixed the endpoints)
        try:
            # Create a test goal
            goal_data = {
                "description": "Improve system decision speed by 25% within 48 hours",
                "category": "performance"
            }
            
            print("Creating SMART goal...")
            async with self.session.post(
                f"{AUTOGEN_URL}/api/goals/create",
                json=goal_data
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Goal created successfully!")
                    print(f"   ID: {result.get('id')}")
                    print(f"   Specific: {result.get('specific')}")
                    print(f"   Measurable: {result.get('measurable')}")
                    print(f"   Time-bound: {result.get('time_bound')}")
                    
                    self.results['smart_goals'] = True
                    return result.get('id')
                else:
                    text = await resp.text()
                    print(f"❌ Goal creation failed: {resp.status} - {text}")
                    self.results['smart_goals'] = False
                    
        except Exception as e:
            print(f"❌ SMART goal test error: {e}")
            self.results['smart_goals'] = False
            
    async def test_darwin_godel(self):
        """Test Darwin-Gödel auto-improvement"""
        print("\n🧬 Testing Darwin-Gödel Evolution Engine...")
        print("-" * 50)
        
        try:
            # Request code analysis
            analysis_req = {
                "target_module": "tool_registry",
                "improvement_type": "performance"
            }
            
            print("Requesting code analysis...")
            async with self.session.post(
                f"{AUTOGEN_URL}/api/evolution/analyze",
                json=analysis_req
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    bottlenecks = result.get('bottlenecks', [])
                    improvements = result.get('improvements', [])
                    
                    print(f"✅ Code analysis complete!")
                    print(f"   Bottlenecks found: {len(bottlenecks)}")
                    print(f"   Improvements suggested: {len(improvements)}")
                    
                    if bottlenecks:
                        print(f"   Sample bottleneck: {bottlenecks[0][:100]}...")
                    if improvements:
                        print(f"   Sample improvement: {improvements[0].get('description', '')[:100]}...")
                    
                    self.results['darwin_godel_analysis'] = True
                    
                    # Test simulation mode
                    if improvements:
                        print("\nTesting improvement simulation...")
                        sim_req = {
                            "improvement_id": improvements[0].get('id'),
                            "simulation_mode": True
                        }
                        
                        async with self.session.post(
                            f"{AUTOGEN_URL}/api/evolution/apply",
                            json=sim_req
                        ) as sim_resp:
                            if sim_resp.status == 200:
                                sim_result = await sim_resp.json()
                                print(f"✅ Simulation successful: {sim_result.get('status')}")
                                self.results['darwin_godel_simulation'] = True
                            else:
                                print(f"❌ Simulation failed: {sim_resp.status}")
                                self.results['darwin_godel_simulation'] = False
                else:
                    text = await resp.text()
                    print(f"❌ Code analysis failed: {resp.status} - {text}")
                    self.results['darwin_godel_analysis'] = False
                    
        except Exception as e:
            print(f"❌ Darwin-Gödel test error: {e}")
            self.results['darwin_godel_analysis'] = False
            
    async def test_statistics_extraction(self):
        """Test statistics and analytics extraction"""
        print("\n📊 Testing Statistics Extraction...")
        print("-" * 50)
        
        try:
            # Get system statistics
            async with self.session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    print(f"✅ Statistics retrieved successfully!")
                    print(f"   Total decisions: {stats.get('total_decisions', 0)}")
                    print(f"   Tool usage breakdown: {stats.get('tool_usage', {})}")
                    print(f"   Success rate: {stats.get('success_rate', 0):.2%}")
                    print(f"   Average decision time: {stats.get('avg_decision_time', 0):.3f}s")
                    
                    self.results['statistics'] = True
                    
                    # Get performance analytics
                    print("\nGetting performance analytics...")
                    async with self.session.get(f"{AUTOGEN_URL}/api/analytics/performance") as perf_resp:
                        if perf_resp.status == 200:
                            perf = await perf_resp.json()
                            print(f"✅ Performance analytics retrieved!")
                            print(f"   Decision patterns: {len(perf.get('patterns', []))}")
                            print(f"   Performance trend: {perf.get('trend', 'unknown')}")
                            print(f"   Insights available: {len(perf.get('insights', []))}")
                            
                            self.results['analytics'] = True
                        else:
                            print(f"❌ Performance analytics failed: {perf_resp.status}")
                            self.results['analytics'] = False
                else:
                    print(f"❌ Statistics retrieval failed: {resp.status}")
                    self.results['statistics'] = False
                    
        except Exception as e:
            print(f"❌ Statistics test error: {e}")
            self.results['statistics'] = False
            
    async def test_tool_diversity(self):
        """Test if tool selection diversity improved after fixes"""
        print("\n🔄 Testing Tool Selection Diversity...")
        print("-" * 50)
        
        try:
            # Monitor tool selection for a period
            print("Monitoring tool selection for 30 seconds...")
            
            # Get initial state
            async with self.session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
                if resp.status == 200:
                    initial_stats = await resp.json()
                    initial_usage = initial_stats.get('tool_usage', {})
                    print(f"Initial tool usage: {initial_usage}")
            
            # Wait for some cycles
            await asyncio.sleep(30)
            
            # Get final state
            async with self.session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
                if resp.status == 200:
                    final_stats = await resp.json()
                    final_usage = final_stats.get('tool_usage', {})
                    print(f"Final tool usage: {final_usage}")
                    
                    # Calculate diversity
                    tools_used = len([t for t, count in final_usage.items() if count > 0])
                    total_uses = sum(final_usage.values())
                    
                    if total_uses > 0:
                        # Check if stuck on one tool
                        max_usage = max(final_usage.values()) if final_usage else 0
                        diversity_ratio = 1 - (max_usage / total_uses)
                        
                        print(f"\n📊 Diversity Analysis:")
                        print(f"   Tools used: {tools_used}")
                        print(f"   Total tool calls: {total_uses}")
                        print(f"   Diversity ratio: {diversity_ratio:.2f}")
                        
                        if diversity_ratio > 0.3:
                            print("✅ Good tool diversity!")
                            self.results['tool_diversity'] = True
                        else:
                            print("⚠️  Low tool diversity - may be stuck")
                            self.results['tool_diversity'] = False
                    else:
                        print("⚠️  No tool usage recorded")
                        self.results['tool_diversity'] = False
                        
        except Exception as e:
            print(f"❌ Tool diversity test error: {e}")
            self.results['tool_diversity'] = False
            
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("CAPABILITY TEST SUMMARY")
        print("=" * 60)
        
        capabilities = {
            'smart_goals': 'SMART Goal Management',
            'darwin_godel_analysis': 'Darwin-Gödel Code Analysis',
            'darwin_godel_simulation': 'Darwin-Gödel Simulation',
            'statistics': 'Statistics Extraction',
            'analytics': 'Performance Analytics',
            'tool_diversity': 'Tool Selection Diversity'
        }
        
        for key, name in capabilities.items():
            status = self.results.get(key, False)
            icon = "✅" if status else "❌"
            print(f"{icon} {name}: {'Working' if status else 'Not Working'}")
            
        # Overall assessment
        working = sum(1 for v in self.results.values() if v)
        total = len(capabilities)
        percentage = (working / total) * 100
        
        print(f"\nOverall: {working}/{total} capabilities working ({percentage:.0f}%)")
        
        # Key findings
        print("\n🔍 Key Findings:")
        
        if not self.results.get('smart_goals'):
            print("- SMART goal system needs initialization fixes")
        
        if not self.results.get('darwin_godel_analysis'):
            print("- Darwin-Gödel engine needs proper file path handling")
            
        if not self.results.get('tool_diversity'):
            print("- Tool selection still showing low diversity")
            
        if self.results.get('statistics'):
            print("- Statistics extraction is working properly")
            
        return percentage >= 60  # Consider success if 60% or more capabilities work

async def main():
    """Run capability tests"""
    print("🚀 AutoGen System Capability Tests")
    print("=" * 60)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Target: {AUTOGEN_URL}")
    print("=" * 60)
    
    tester = SystemCapabilityTester()
    
    try:
        await tester.setup()
        
        # Run all capability tests
        await tester.test_smart_goals()
        await tester.test_darwin_godel()
        await tester.test_statistics_extraction()
        await tester.test_tool_diversity()
        
        # Print summary
        success = tester.print_summary()
        
        if success:
            print("\n✅ System shows acceptable capability levels")
        else:
            print("\n⚠️  System capabilities need improvement")
            
    finally:
        await tester.teardown()

if __name__ == "__main__":
    asyncio.run(main())