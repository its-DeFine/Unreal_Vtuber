#!/usr/bin/env python3
"""
🎯 Container Goal Management Test

Test the goal management system from inside the container.
"""

import sys
import asyncio
import json
import traceback

sys.path.append("/app")

async def test_goal_management_system():
    """Test the complete goal management system"""
    
    print("🎯 TESTING GOAL MANAGEMENT SYSTEM")
    print("=" * 50)
    
    # Test 1: Import Services
    print("\n1. 📦 Testing Imports...")
    try:
        from autogen_agent.services.goal_management_service import get_goal_management_service
        from autogen_agent.services.metrics_integration_service import get_metrics_integration_service
        from autogen_agent.tools.goal_management_tools import GOAL_MANAGEMENT_TOOLS, run
        print("✅ All goal management modules imported successfully")
        print(f"✅ Available tools: {list(GOAL_MANAGEMENT_TOOLS.keys())}")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return
    
    # Test 2: Test Goal Tools
    print("\n2. 🎯 Testing Goal Tools...")
    try:
        # Test overview
        context = {"action": "overview"}
        result = await run(context)
        print(f"📊 Overview result: {result.get('success', False)}")
        
        # Test goal definition
        context = {
            "action": "define_goal",
            "goal": "Achieve sub-2-second decision speed with 95% accuracy",
            "priority": 9
        }
        result = await run(context)
        print(f"📝 Goal definition: {result.get('success', False)}")
        if result.get('success'):
            print(f"🎯 Goal ID: {result.get('goal_id', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Goal tools test failed: {e}")
        traceback.print_exc()
    
    # Test 3: Test Services
    print("\n3. 🔧 Testing Services...")
    try:
        goal_service = await get_goal_management_service()
        metrics_service = await get_metrics_integration_service()
        
        print(f"✅ Goal service available: {goal_service is not None}")
        print(f"✅ Metrics service available: {metrics_service is not None}")
        
        if goal_service:
            goals = await goal_service.get_current_goals()
            print(f"📊 Current goals count: {len(goals)}")
            
        if metrics_service:
            # Test metrics collection
            performance_data = {
                "iteration": 1,
                "decision_time": 1.8,
                "success_rate": 0.96,
                "error_count": 0,
                "tool_used": "test_tool",
                "memory_usage": 75.0
            }
            
            snapshot = await metrics_service.collect_real_time_metrics(performance_data)
            print(f"📈 Metrics collection: {snapshot.get('success', False)}")
            
    except Exception as e:
        print(f"❌ Services test failed: {e}")
        traceback.print_exc()
    
    # Test 4: Test Cognee Integration
    print("\n4. 🧠 Testing Cognee Integration...")
    try:
        from autogen_agent.services.cognee_direct_service import get_cognee_direct_service
        
        cognee_service = await get_cognee_direct_service()
        print(f"✅ Cognee service available: {cognee_service is not None}")
        
        if cognee_service:
            status = await cognee_service.get_status()
            print(f"📊 Cognee status: {status}")
            
            # Test adding goal data to memory
            test_data = ["Goal system test: Performance optimization goal with 95% accuracy target"]
            result = await cognee_service.add_data(test_data)
            print(f"💾 Data storage: {result.get('success', False)}")
            
    except Exception as e:
        print(f"❌ Cognee test failed: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🎯 GOAL MANAGEMENT SYSTEM TEST COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_goal_management_system()) 