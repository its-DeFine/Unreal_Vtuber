#!/usr/bin/env python3
"""
Detailed test of Darwin-Gödel evolution showing actual code improvements
"""

import asyncio
import aiohttp
import json

AUTOGEN_URL = "http://localhost:8202"

async def test_evolution_details():
    async with aiohttp.ClientSession() as session:
        print("🧬 Darwin-Gödel Detailed Evolution Test")
        print("=" * 60)
        
        # 1. Analyze specific module
        print("\n1️⃣ Requesting detailed code analysis...")
        analysis_request = {
            "target_module": "tool_registry",
            "improvement_type": "performance",
            "detailed": True
        }
        
        async with session.post(f"{AUTOGEN_URL}/api/evolution/analyze", json=analysis_request) as resp:
            if resp.status == 200:
                result = await resp.json()
                print("✅ Analysis complete!")
                print(f"\n📊 Bottlenecks found: {len(result.get('bottlenecks', []))}")
                for i, bottleneck in enumerate(result.get('bottlenecks', [])[:3]):
                    print(f"   {i+1}. {bottleneck}")
                
                print(f"\n💡 Improvements suggested: {len(result.get('improvements', []))}")
                for imp in result.get('improvements', [])[:3]:
                    print(f"   - ID: {imp.get('id')}")
                    print(f"     Description: {imp.get('description')}")
                    print(f"     Type: {imp.get('type', 'optimization')}")
                    print()
        
        # 2. Check evolution metrics
        print("\n2️⃣ Checking evolution metrics...")
        async with session.get(f"{AUTOGEN_URL}/api/evolution/metrics") as resp:
            if resp.status == 200:
                metrics = await resp.json()
                print("📈 Evolution Metrics:")
                print(f"   Total analyses: {metrics.get('total_analyses', 0)}")
                print(f"   Improvements identified: {metrics.get('improvements_identified', 0)}")
                print(f"   Simulations run: {metrics.get('simulations_run', 0)}")
                print(f"   Real modifications: {metrics.get('real_modifications', 0)}")
                print(f"   Mode: {metrics.get('mode', 'SIMULATION')}")
        
        # 3. Trigger autonomous cycle with evolution
        print("\n3️⃣ Triggering autonomous cycle with evolution focus...")
        
        # Wait for a cycle
        print("⏳ Waiting 30 seconds for autonomous evolution cycle...")
        await asyncio.sleep(30)
        
        # 4. Check if evolution was triggered
        print("\n4️⃣ Checking if evolution was triggered...")
        async with session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
            stats = await resp.json()
            print(f"   Cycles completed: {stats.get('total_decisions', 0)}")
            print(f"   Tool usage: {stats.get('tool_usage', {})}")
        
        print("\n📝 Summary:")
        print("- Darwin-Gödel engine is analyzing code for improvements")
        print("- Running in SIMULATION mode (no real changes)")
        print("- Identifies bottlenecks and suggests optimizations")
        print("- Would make real changes if DARWIN_GODEL_REAL_MODIFICATIONS=true")

if __name__ == "__main__":
    asyncio.run(test_evolution_details())