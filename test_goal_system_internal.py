#!/usr/bin/env python3
"""
🎯 Test Goal Management System Internally

Test the goal management system by executing Python code directly inside the container.
This tests the actual goal management services and tools we built.
"""

import subprocess
import json

def run_in_container(python_code: str) -> str:
    """Execute Python code inside the AutoGen container"""
    
    # Escape quotes and newlines for shell
    escaped_code = python_code.replace('"', '\\"').replace('\\', '\\\\')
    
    # Execute Python code in the container
    cmd = f'docker exec autogen_cognitive_standalone python3 -c "{escaped_code}"'
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nReturn Code: {result.returncode}"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 30 seconds"
    except Exception as e:
        return f"ERROR: {e}"

def test_goal_management_system():
    """Test the complete goal management system"""
    
    print("🎯 TESTING GOAL MANAGEMENT SYSTEM INTERNALLY")
    print("=" * 70)
    
    # Test 1: Check if goal management services can be imported
    print("\n1. 📦 Testing Goal Management Service Import...")
    test_code = '''
import sys
sys.path.append("/app")

try:
    from autogen_agent.services.goal_management_service import GoalManagementService, get_goal_management_service
    print("✅ [TEST] Goal Management Service imported successfully")
    
    from autogen_agent.services.metrics_integration_service import MetricsIntegrationService, get_metrics_integration_service  
    print("✅ [TEST] Metrics Integration Service imported successfully")
    
    from autogen_agent.tools.goal_management_tools import GOAL_MANAGEMENT_TOOLS, run
    print("✅ [TEST] Goal Management Tools imported successfully")
    print(f"✅ [TEST] Available tools: {list(GOAL_MANAGEMENT_TOOLS.keys())}")
    
except Exception as e:
    print(f"❌ [TEST] Import failed: {e}")
    import traceback
    traceback.print_exc()
'''
    
    result = run_in_container(test_code)
    print(result)
    
    # Test 2: Test basic goal management tool functionality
    print("\n2. 🎯 Testing Goal Management Tool Functionality...")
    test_code = '''
import sys
sys.path.append("/app")
import asyncio
import json

async def test_goal_tools():
    try:
        from autogen_agent.tools.goal_management_tools import run
        
        # Test 1: Overview action (default)
        print("🔍 [TEST] Testing goal tools overview...")
        context = {"action": "overview"}
        result = await run(context)
        print(f"📊 [TEST] Overview result: {json.dumps(result, indent=2, default=str)}")
        
        # Test 2: Define a goal
        print("\\n🎯 [TEST] Testing goal definition...")
        context = {
            "action": "define_goal",
            "goal": "Optimize agent decision speed to under 2 seconds",
            "priority": 8
        }
        result = await run(context)
        print(f"📝 [TEST] Goal definition result: {json.dumps(result, indent=2, default=str)}")
        
        print("✅ [TEST] Goal management tools working successfully!")
        
    except Exception as e:
        print(f"❌ [TEST] Goal tools test failed: {e}")
        import traceback
        traceback.print_exc()

# Run the async test
asyncio.run(test_goal_tools())
'''
    
    result = run_in_container(test_code)
    print(result)
    
    # Test 3: Test Cognee Direct Service Integration
    print("\n3. 🧠 Testing Cognee Direct Service Integration...")
    test_code = '''
import sys
sys.path.append("/app")
import asyncio

async def test_cognee_direct():
    try:
        from autogen_agent.services.cognee_direct_service import get_cognee_direct_service
        
        print("🔍 [TEST] Getting Cognee Direct Service...")
        cognee_service = await get_cognee_direct_service()
        
        if cognee_service:
            print("✅ [TEST] Cognee Direct Service initialized successfully")
            
            # Test status
            status = await cognee_service.get_status()
            print(f"📊 [TEST] Cognee status: {status}")
            
            # Test basic functionality
            print("🧪 [TEST] Testing Cognee add data...")
            test_data = ["Goal management system test: AutoGen performance optimization goal defined"]
            result = await cognee_service.add_data(test_data)
            print(f"💾 [TEST] Add data result: {result}")
            
            # Test search
            print("🔍 [TEST] Testing Cognee search...")
            search_results = await cognee_service.search("goal management optimization")
            print(f"🔍 [TEST] Search results: {len(search_results)} items found")
            
        else:
            print("⚠️ [TEST] Cognee Direct Service not available")
        
    except Exception as e:
        print(f"❌ [TEST] Cognee test failed: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_cognee_direct())
'''
    
    result = run_in_container(test_code)
    print(result)
    
    # Test 4: Test Tool Registry Integration
    print("\n4. 🔧 Testing Tool Registry Integration...")
    test_code = '''
import sys
sys.path.append("/app")

try:
    from autogen_agent.tool_registry import ToolRegistry
    
    print("🔍 [TEST] Testing Tool Registry...")
    registry = ToolRegistry()
    registry.load_tools()
    
    available_tools = registry.get_available_tools()
    disabled_tools = registry.get_disabled_tools()
    tool_status = registry.get_tool_status()
    
    print(f"✅ [TEST] Available tools: {available_tools}")
    print(f"🚫 [TEST] Disabled tools: {disabled_tools}")
    print(f"📊 [TEST] Tool status: {tool_status}")
    
    # Check if goal management tools are loaded
    if "goal_management_tools" in available_tools:
        print("✅ [TEST] Goal management tools successfully loaded in registry!")
    else:
        print("⚠️ [TEST] Goal management tools not found in available tools")
        
except Exception as e:
    print(f"❌ [TEST] Tool registry test failed: {e}")
    import traceback
    traceback.print_exc()
'''
    
    result = run_in_container(test_code)
    print(result)
    
    # Test 5: Test complete goal workflow
    print("\n5. 🚀 Testing Complete Goal Workflow...")
    test_code = '''
import sys
sys.path.append("/app")
import asyncio
import json

async def test_complete_workflow():
    try:
        print("🎯 [TEST] Starting complete goal management workflow...")
        
        # Import required services
        from autogen_agent.services.goal_management_service import get_goal_management_service
        from autogen_agent.services.metrics_integration_service import get_metrics_integration_service
        from autogen_agent.tools.goal_management_tools import define_autonomous_goal, get_active_goals
        
        # Step 1: Define a goal
        print("\\n🎯 Step 1: Define autonomous goal...")
        goal_result = await define_autonomous_goal(
            "Achieve sub-2-second decision times while maintaining 95% success rate",
            priority=9
        )
        print(f"📝 Goal definition: {json.dumps(goal_result, indent=2, default=str)}")
        
        # Step 2: Get active goals
        print("\\n📋 Step 2: Get active goals...")
        goals_result = await get_active_goals()
        print(f"📊 Active goals: {json.dumps(goals_result, indent=2, default=str)}")
        
        # Step 3: Simulate metrics collection
        print("\\n📊 Step 3: Simulate metrics collection...")
        metrics_service = await get_metrics_integration_service()
        if metrics_service:
            performance_data = {
                "iteration": 1,
                "decision_time": 2.5,
                "success_rate": 0.92,
                "error_count": 1,
                "tool_used": "goal_test",
                "memory_usage": 85.0
            }
            
            snapshot = await metrics_service.collect_real_time_metrics(performance_data)
            print(f"📈 Metrics snapshot: {json.dumps(snapshot, indent=2, default=str)}")
        else:
            print("⚠️ Metrics service not available")
        
        print("\\n✅ [TEST] Complete workflow test successful!")
        
    except Exception as e:
        print(f"❌ [TEST] Complete workflow test failed: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_complete_workflow())
'''
    
    result = run_in_container(test_code)
    print(result)
    
    print("\n" + "=" * 70)
    print("🎯 GOAL MANAGEMENT SYSTEM INTERNAL TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    test_goal_management_system() 