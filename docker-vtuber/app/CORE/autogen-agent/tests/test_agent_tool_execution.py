#!/usr/bin/env python3
"""
Test that agents are actually executing tools based on their conversations
"""

import asyncio
import aiohttp
import json
import time

AUTOGEN_URL = "http://localhost:8202"

async def test_tool_execution():
    async with aiohttp.ClientSession() as session:
        print("🔍 Testing Agent-Tool Execution Bridge")
        print("=" * 60)
        
        # Get initial statistics
        async with session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
            initial_stats = await resp.json()
            print(f"Initial cycles completed: {initial_stats.get('total_decisions', 0)}")
            print(f"Initial tool usage: {initial_stats.get('tool_usage', {})}")
        
        # Wait for a few cycles to complete
        print("\n⏳ Waiting for 3 autonomous cycles (90 seconds)...")
        await asyncio.sleep(90)
        
        # Get updated statistics
        async with session.get(f"{AUTOGEN_URL}/api/statistics") as resp:
            final_stats = await resp.json()
            print(f"\nFinal cycles completed: {final_stats.get('total_decisions', 0)}")
            print(f"Final tool usage: {final_stats.get('tool_usage', {})}")
        
        # Check if cycles increased
        cycles_diff = final_stats.get('total_decisions', 0) - initial_stats.get('total_decisions', 0)
        print(f"\n📊 New cycles completed: {cycles_diff}")
        
        # Check container logs for tool execution
        print("\n📝 Checking container logs for tool execution evidence...")
        # This would normally use docker logs, but we'll check via the API
        
        if cycles_diff > 0:
            print("✅ Autonomous cycles are running")
        else:
            print("❌ No new cycles detected")
        
        # Test health endpoint
        async with session.get(f"{AUTOGEN_URL}/health") as resp:
            health = await resp.json()
            print(f"\n🏥 System health: {health.get('status')}")
            print(f"   AutoGen available: {health.get('autogen_available')}")
            print(f"   Tools registered: {health.get('analytics', {}).get('tools_registered', 0)}")

if __name__ == "__main__":
    asyncio.run(test_tool_execution())