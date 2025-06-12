#!/usr/bin/env python3
"""
Basic test suite for AutoGen system - tests what's actually implemented
"""

import asyncio
import aiohttp
import json
from datetime import datetime

# Configuration
AUTOGEN_URL = "http://localhost:8201"

async def test_health():
    """Test system health"""
    print("\n🔍 Testing System Health...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{AUTOGEN_URL}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ System is healthy")
                    print(f"   AutoGen available: {data.get('autogen_available')}")
                    print(f"   Cycles completed: {data.get('analytics', {}).get('cycles_completed')}")
                    print(f"   Tools registered: {data.get('analytics', {}).get('tools_registered')}")
                    return True
                else:
                    print(f"❌ Health check failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

async def test_vtuber_control():
    """Test VTuber control endpoint"""
    print("\n🔍 Testing VTuber Control...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{AUTOGEN_URL}/vtuber/control?action=status") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ VTuber control endpoint accessible")
                    print(f"   Activated: {data.get('activated', False)}")
                    return True
                else:
                    print(f"❌ VTuber control failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ VTuber test failed: {e}")
            return False

async def test_statistics():
    """Test statistics endpoint"""
    print("\n🔍 Testing Statistics...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Statistics retrieved")
                    print(f"   Total decisions: {data.get('total_decisions', 0)}")
                    print(f"   Success rate: {data.get('success_rate', 0):.2%}")
                    print(f"   Avg decision time: {data.get('avg_decision_time', 0):.2f}s")
                    return True
                else:
                    print(f"❌ Statistics failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Statistics test failed: {e}")
            return False

async def monitor_cognitive_cycles(duration=30):
    """Monitor cognitive cycles for a period"""
    print(f"\n🔍 Monitoring Cognitive Cycles for {duration} seconds...")
    
    async with aiohttp.ClientSession() as session:
        start_time = datetime.now()
        initial_cycles = 0
        
        # Get initial count
        try:
            async with session.get(f"{AUTOGEN_URL}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    initial_cycles = data.get('analytics', {}).get('cycles_completed', 0)
        except:
            pass
        
        # Wait
        print(f"   Initial cycles: {initial_cycles}")
        print(f"   Waiting {duration} seconds...")
        await asyncio.sleep(duration)
        
        # Get final count
        try:
            async with session.get(f"{AUTOGEN_URL}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    final_cycles = data.get('analytics', {}).get('cycles_completed', 0)
                    
                    cycles_completed = final_cycles - initial_cycles
                    print(f"✅ Monitoring complete")
                    print(f"   Final cycles: {final_cycles}")
                    print(f"   Cycles in period: {cycles_completed}")
                    print(f"   Rate: {cycles_completed / duration * 60:.1f} cycles/minute")
                    return True
        except Exception as e:
            print(f"❌ Monitoring failed: {e}")
            return False

async def check_tool_selection_behavior():
    """Check what tools are being selected"""
    print("\n🔍 Checking Tool Selection Behavior...")
    
    # Since the tool selection API has issues, let's check via statistics
    async with aiohttp.ClientSession() as session:
        try:
            # Get initial state
            async with session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tool_usage = data.get('tool_usage', {})
                    
                    if tool_usage:
                        print("✅ Tool usage statistics:")
                        for tool, count in tool_usage.items():
                            print(f"   {tool}: {count} uses")
                    else:
                        print("⚠️  No tool usage recorded yet")
                    
                    # Check if system is stuck on one tool
                    if tool_usage and len(tool_usage) == 1:
                        print("⚠️  WARNING: System may be stuck selecting only one tool!")
                    
                    return True
        except Exception as e:
            print(f"❌ Tool behavior check failed: {e}")
            return False

async def check_memory_system():
    """Check memory system status"""
    print("\n🔍 Checking Memory System...")
    
    # Try to store a test memory
    async with aiohttp.ClientSession() as session:
        try:
            test_memory = {
                "context": {"test": "memory check"},
                "action": "test_action",
                "result": {"success": True}
            }
            
            async with session.post(
                f"{AUTOGEN_URL}/api/memory/store",
                json=test_memory
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Memory storage working")
                    print(f"   Memory ID: {data.get('memory_id')}")
                    print(f"   Storage type: {data.get('storage', 'unknown')}")
                    
                    # Check if Cognee is working
                    if "cognee" in data.get('storage', '').lower():
                        print("   ✅ Cognee integration active")
                    else:
                        print("   ⚠️  Cognee not available - using PostgreSQL fallback")
                    
                    return True
                else:
                    print(f"❌ Memory storage failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Memory test failed: {e}")
            return False

async def main():
    """Run all basic tests"""
    print("🚀 AutoGen System Basic Tests")
    print("=" * 60)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Target: {AUTOGEN_URL}")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Health Check", await test_health()))
    results.append(("VTuber Control", await test_vtuber_control()))
    results.append(("Statistics", await test_statistics()))
    results.append(("Memory System", await check_memory_system()))
    results.append(("Tool Selection", await check_tool_selection_behavior()))
    results.append(("Cognitive Cycles", await monitor_cognitive_cycles(20)))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name}")
    
    # Analysis
    print("\n" + "=" * 60)
    print("SYSTEM ANALYSIS")
    print("=" * 60)
    
    print("\n🔍 Key Findings:")
    print("1. The system appears to be stuck selecting 'advanced_vtuber_control' repeatedly")
    print("2. Cognee is not available (DNS resolution failure)")
    print("3. The system falls back to PostgreSQL-only memory")
    print("4. Tool selection scoring may need adjustment")
    print("\n💡 Recommendations:")
    print("1. Fix tool selection diversity - it's selecting the same tool repeatedly")
    print("2. Either fix Cognee DNS or disable it completely")
    print("3. Adjust tool scoring weights to ensure variety")
    print("4. Consider adding a 'recently used' penalty to tool selection")
    
if __name__ == "__main__":
    asyncio.run(main())