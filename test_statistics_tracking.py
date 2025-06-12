#!/usr/bin/env python3
"""
Test statistics tracking and improvement measurement
"""

import asyncio
import aiohttp
import json
import time

AUTOGEN_URL = "http://localhost:8202"

async def test_statistics():
    async with aiohttp.ClientSession() as session:
        print("📊 Testing Statistics and Improvement Tracking")
        print("=" * 60)
        
        # 1. Get initial statistics
        print("\n1️⃣ Initial Statistics:")
        async with session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
            stats = await resp.json()
            print(f"   Total decisions: {stats.get('total_decisions', 0)}")
            print(f"   Tool usage: {stats.get('tool_usage', {})}")
            print(f"   Success rate: {stats.get('success_rate', 0):.2f}%")
            print(f"   Avg decision time: {stats.get('avg_decision_time', 0):.3f}s")
            initial_decisions = stats.get('total_decisions', 0)
        
        # 2. Check health for more analytics
        print("\n2️⃣ Health Check Analytics:")
        async with session.get(f"{AUTOGEN_URL}/health") as resp:
            health = await resp.json()
            analytics = health.get('analytics', {})
            print(f"   Cycles completed: {analytics.get('cycles_completed', 0)}")
            print(f"   Tools registered: {analytics.get('tools_registered', 0)}")
        
        # 3. Check performance analytics
        print("\n3️⃣ Performance Analytics:")
        async with session.get(f"{AUTOGEN_URL}/api/analytics/performance") as resp:
            perf = await resp.json()
            print(f"   Decision patterns: {len(perf.get('patterns', []))}")
            print(f"   Performance trend: {perf.get('trend', 'unknown')}")
            print(f"   Insights: {len(perf.get('insights', []))}")
        
        # 4. Wait for some cycles and check improvement
        print("\n4️⃣ Monitoring for 60 seconds to see statistics evolution...")
        print("   Checking every 20 seconds:")
        
        for i in range(3):
            await asyncio.sleep(20)
            async with session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
                stats = await resp.json()
                decisions = stats.get('total_decisions', 0)
                print(f"   [{(i+1)*20}s] Decisions: {decisions} (+{decisions - initial_decisions})")
                
                # Check if tool usage is being tracked
                tool_usage = stats.get('tool_usage', {})
                if tool_usage:
                    print(f"        Tool usage: {tool_usage}")
        
        # 5. Check if there's a tool registry status endpoint
        print("\n5️⃣ Checking Tool Registry Status:")
        try:
            async with session.get(f"{AUTOGEN_URL}/api/tools/status") as resp:
                if resp.status == 200:
                    tool_status = await resp.json()
                    print(f"   Total tools: {tool_status.get('total_tools', 0)}")
                    if 'performance_summary' in tool_status:
                        print("   Performance summary available!")
        except:
            print("   Tool status endpoint not available")
        
        # 6. Direct evolution metrics check
        print("\n6️⃣ Evolution Metrics:")
        print("   (Would show real modifications, improvements applied, etc.)")
        print("   Currently in SIMULATION mode - no real changes tracked")
        
        print("\n📝 Summary:")
        print("- Basic statistics are tracked (decisions, cycles)")
        print("- Tool usage tracking exists but may not be persisted")
        print("- Performance analytics infrastructure exists")
        print("- Improvement measurement requires persistent storage")
        print("- System has the capability but needs activation")

if __name__ == "__main__":
    asyncio.run(test_statistics())