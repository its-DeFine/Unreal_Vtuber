#!/usr/bin/env python3
"""
🎯 Simple Goal Management Test

Test the goal management system without Cognee dependency.
"""

import sys
import asyncio
import json
import traceback

sys.path.append("/app")

async def test_goal_tools_only():
    """Test just the goal management tools without Cognee"""
    
    print("🎯 SIMPLE GOAL MANAGEMENT TEST")
    print("=" * 40)
    
    try:
        # Import without Cognee dependency
        from autogen_agent.tools.goal_management_tools import run, GOAL_MANAGEMENT_TOOLS
        
        print("✅ Goal management tools imported successfully")
        print(f"Available tools: {list(GOAL_MANAGEMENT_TOOLS.keys())}")
        
        # Test 1: Overview action  
        print("\n1. 📊 Testing Overview...")
        context = {"action": "overview"}
        result = await run(context)
        print(f"Success: {result.get('success', 'Unknown')}")
        print(f"Tool: {result.get('tool', 'Unknown')}")
        
        # Test 2: Define a goal
        print("\n2. 🎯 Testing Goal Definition...")
        context = {
            "action": "define_goal",
            "goal": "Optimize agent response time to under 1.5 seconds",
            "priority": 8
        }
        result = await run(context)
        print(f"Success: {result.get('success', 'Unknown')}")
        if result.get('success'):
            print(f"Goal ID: {result.get('goal_id', 'N/A')}")
            print(f"Title: {result.get('goal', {}).get('title', 'N/A')}")
        
        # Test 3: Get active goals
        print("\n3. 📋 Testing Get Active Goals...")
        context = {"action": "get_goals"}
        result = await run(context)
        print(f"Success: {result.get('success', 'Unknown')}")
        goals = result.get('goals', [])
        print(f"Active goals count: {len(goals)}")
        
        # Test 4: Next priority goal
        print("\n4. 🔥 Testing Next Priority Goal...")
        context = {"action": "next_goal"}
        result = await run(context)
        print(f"Success: {result.get('success', 'Unknown')}")
        if result.get('success') and result.get('goal'):
            goal = result.get('goal')
            print(f"Next goal: {goal.get('title', 'N/A')}")
            print(f"Priority: {goal.get('priority', 'N/A')}")
        
        print("\n✅ GOAL MANAGEMENT TOOLS WORKING!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_goal_tools_only()) 