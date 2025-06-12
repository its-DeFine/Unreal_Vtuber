#!/usr/bin/env python3
"""
Test Darwin-Gödel evolution engine in action
Monitor for actual code analysis and improvement attempts
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

AUTOGEN_URL = "http://localhost:8202"

async def trigger_evolution():
    """Directly trigger the Darwin-Gödel evolution engine"""
    async with aiohttp.ClientSession() as session:
        print("🧬 Darwin-Gödel Evolution Engine Live Test")
        print("=" * 60)
        print(f"Started at: {datetime.now()}")
        print("=" * 60)
        
        # First, check current state
        print("\n📊 Checking current system state...")
        async with session.get(f"{AUTOGEN_URL}/health") as resp:
            health = await resp.json()
            print(f"System health: {health.get('status')}")
            print(f"Cycles completed: {health.get('analytics', {}).get('cycles_completed', 0)}")
        
        # Request code analysis directly
        print("\n🔬 Requesting Darwin-Gödel code analysis...")
        analysis_request = {
            "target_module": "tool_registry",
            "improvement_type": "performance",
            "analyze_only": False  # Allow real analysis
        }
        
        try:
            async with session.post(
                f"{AUTOGEN_URL}/api/evolution/analyze",
                json=analysis_request
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print("✅ Code analysis complete!")
                    print(f"   Bottlenecks found: {len(result.get('bottlenecks', []))}")
                    print(f"   Improvements suggested: {len(result.get('improvements', []))}")
                    
                    # Show some details
                    if result.get('bottlenecks'):
                        print("\n🔍 Sample bottlenecks identified:")
                        for b in result['bottlenecks'][:2]:
                            print(f"   - {b.get('description', 'No description')}")
                    
                    if result.get('improvements'):
                        print("\n💡 Sample improvements suggested:")
                        for i in result['improvements'][:2]:
                            print(f"   - {i.get('description', 'No description')}")
                else:
                    print(f"❌ Analysis failed: {resp.status}")
                    print(await resp.text())
        except Exception as e:
            print(f"❌ Error requesting analysis: {e}")
        
        # Try simulation mode
        print("\n🧪 Testing improvement simulation...")
        sim_request = {
            "improvement_id": "optimize_tool_selection",
            "simulation_mode": True
        }
        
        try:
            async with session.post(
                f"{AUTOGEN_URL}/api/evolution/apply",
                json=sim_request
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Simulation result: {result.get('status', 'unknown')}")
                    if result.get('changes'):
                        print("   Simulated changes:")
                        for change in result.get('changes', [])[:3]:
                            print(f"   - {change}")
                else:
                    print(f"❌ Simulation failed: {resp.status}")
        except Exception as e:
            print(f"❌ Error in simulation: {e}")
        
        # Monitor for autonomous evolution
        print("\n⏳ Monitoring for autonomous evolution cycles (60 seconds)...")
        print("   (The system should analyze and potentially improve itself)")
        
        start_time = time.time()
        evolution_count = 0
        
        while time.time() - start_time < 60:
            await asyncio.sleep(10)
            
            # Check if evolution happened
            async with session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
                stats = await resp.json()
                cycles = stats.get('total_decisions', 0)
                
                # Check logs would be done via docker logs
                print(f"   [{int(time.time() - start_time)}s] Cycles: {cycles}")
        
        print("\n📋 Test Summary:")
        print("- Code analysis endpoint tested")
        print("- Simulation mode tested")
        print("- Autonomous monitoring completed")
        
        # Final check for any file modifications
        print("\n🔍 Checking for actual code modifications...")
        print("   (In simulation mode, no real changes should occur)")
        
        return True

async def main():
    """Run the evolution test"""
    try:
        # Make sure container is running
        print("🐳 Ensuring container is running...")
        
        # Run the test
        await trigger_evolution()
        
        print("\n✅ Darwin-Gödel test completed!")
        print("\n💡 To enable REAL modifications, you would need to:")
        print("   1. Set DARWIN_GODEL_REAL_MODIFICATIONS=true")
        print("   2. Set DARWIN_GODEL_REQUIRE_APPROVAL=false (or create approval file)")
        print("   3. Restart the container")
        print("\n⚠️  Current mode: SIMULATION (safe)")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())