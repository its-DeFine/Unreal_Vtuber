#!/usr/bin/env python3
"""
Test Enhanced Autonomous Team Capabilities

Tests:
1. SCB operations tool functionality
2. Dynamic tool registration
3. Graduated autonomy configuration
4. Tool management capabilities
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any

# Test configuration
os.environ["AUTONOMY_LEVEL"] = "MODIFIER"  # Allow file modifications for testing
os.environ["DARWIN_GODEL_REQUIRE_APPROVAL"] = "false"  # Disable approval for testing


async def test_scb_operations():
    """Test SCB operations tool"""
    print("\n🔄 Testing SCB Operations Tool")
    print("="*60)
    
    from autogen_agent.tools.scb_operations_tool import run as scb_tool
    from autogen_agent.clients.scb_client import SCBClient
    
    # Create mock SCB client
    scb_client = SCBClient(None)  # Standalone mode
    
    # Test 1: Read state (should fail in standalone)
    context = {
        "action": "read",
        "agent": "test_agent",
        "scb_client": scb_client
    }
    
    result = await scb_tool(context)
    print(f"Read state result: {result}")
    assert result['success'] == False
    assert "standalone mode" in result['error']
    print("✅ Correctly detected standalone mode")
    
    # Test 2: List available actions
    context = {
        "action": "unknown_action_test",
        "scb_client": scb_client
    }
    
    result = await scb_tool(context)
    print(f"\nUnknown action result: {result}")
    assert result['success'] == False
    if 'available_actions' in result:
        print(f"Available actions: {result.get('available_actions', [])}")
        print("✅ Listed available actions")
    else:
        print("✅ Handled unknown action")
    
    return True


async def test_dynamic_tool_registration():
    """Test dynamic tool registration"""
    print("\n🔧 Testing Dynamic Tool Registration")
    print("="*60)
    
    from autogen_agent.tool_registry import ToolRegistry
    
    registry = ToolRegistry()
    
    # Test 1: Create a simple tool
    def simple_tool(context: Dict[str, Any]) -> Dict[str, Any]:
        """A simple test tool"""
        return {
            "success": True,
            "message": f"Hello from simple tool! Input: {context.get('input', 'none')}"
        }
    
    # Register the tool
    result = registry.register_runtime_tool(
        tool_name="test_simple_tool",
        tool_func=simple_tool,
        metadata={
            "description": "A simple test tool",
            "context_keywords": ["test", "simple"]
        },
        require_approval=False  # For testing
    )
    
    print(f"Registration result: {result}")
    assert result['success'] == True
    print("✅ Successfully registered runtime tool")
    
    # Test 2: Execute the tool
    test_result = registry.execute_tool_sync("test_simple_tool", {"input": "test data"})
    print(f"Execution result: {test_result}")
    assert test_result['success'] == True
    print("✅ Successfully executed runtime tool")
    
    # Test 3: List runtime tools
    runtime_tools = registry.list_runtime_tools()
    print(f"Runtime tools: {[t['name'] for t in runtime_tools]}")
    assert any(t['name'] == 'test_simple_tool' for t in runtime_tools)
    print("✅ Runtime tool appears in list")
    
    # Test 4: Unregister the tool
    unregister_result = registry.unregister_tool("test_simple_tool")
    print(f"Unregister result: {unregister_result}")
    assert unregister_result['success'] == True
    print("✅ Successfully unregistered tool")
    
    return True


async def test_autonomy_configuration():
    """Test graduated autonomy configuration"""
    print("\n🎯 Testing Autonomy Configuration")
    print("="*60)
    
    from autogen_agent.autonomy_config import get_autonomy_manager, AutonomyLevel
    
    manager = get_autonomy_manager()
    
    # Test 1: Check current status
    status = manager.get_status()
    print(f"Current autonomy level: {status['level']}")
    print(f"Can modify files: {status['can_modify_files']}")
    print(f"Can create tools: {status['can_create_tools']}")
    
    # Test 2: Check operation permissions
    operations = ["file_modify", "tool_create", "external_call"]
    
    for op in operations:
        result = manager.can_perform_operation(op)
        print(f"\nCan perform '{op}': {result['allowed']}")
        print(f"Reason: {result['reason']}")
    
    # Test 3: Record some operations
    for i in range(5):
        manager.record_operation("test_operation", success=True)
    
    manager.record_operation("test_operation", success=False)
    
    # Test 4: Evaluate upgrade eligibility
    evaluation = manager.evaluate_autonomy_upgrade()
    print(f"\nUpgrade evaluation:")
    print(f"Eligible: {evaluation['eligible']}")
    print(f"Current level: {evaluation['current_level']}")
    print(f"Next level: {evaluation['next_level']}")
    print(f"Reasons: {evaluation['reasons']}")
    
    return True


async def test_tool_management():
    """Test tool management capabilities"""
    print("\n🔨 Testing Tool Management")
    print("="*60)
    
    from autogen_agent.tools.tool_management import run as tool_mgmt
    from autogen_agent.tool_registry import ToolRegistry
    
    registry = ToolRegistry()
    
    # Test 1: List all tools
    context = {
        "action": "list",
        "tool_registry": registry
    }
    
    result = await tool_mgmt(context)
    print(f"Total tools: {result.get('total_tools', 0)}")
    print(f"Core tools: {len(result.get('categories', {}).get('core', []))}")
    print(f"Runtime tools: {len(result.get('categories', {}).get('runtime', []))}")
    assert result['success'] == True
    print("✅ Successfully listed tools")
    
    # Test 2: Inspect a specific tool
    context = {
        "action": "inspect",
        "tool_name": "goal_management_tools",
        "tool_registry": registry
    }
    
    result = await tool_mgmt(context)
    if result['success']:
        print(f"\nInspected tool: {result['tool_info']['name']}")
        print(f"Is async: {result['tool_info']['is_async']}")
        print("✅ Successfully inspected tool")
    
    # Test 3: Check autonomy status
    context = {
        "action": "autonomy_status",
        "tool_registry": registry
    }
    
    result = await tool_mgmt(context)
    if result['success']:
        status = result['autonomy_status']
        print(f"\nAutonomy capabilities:")
        for cap in status.get('capabilities_summary', []):
            print(f"  - {cap}")
        print("✅ Successfully checked autonomy status")
    
    # Test 4: Get performance metrics
    context = {
        "action": "performance",
        "tool_registry": registry
    }
    
    result = await tool_mgmt(context)
    if result['success']:
        print(f"\nPerformance data for {result.get('total_tools', 0)} tools")
        print("✅ Successfully retrieved performance metrics")
    
    return True


async def test_integrated_scenario():
    """Test integrated scenario with all components"""
    print("\n🌟 Testing Integrated Scenario")
    print("="*60)
    
    from autogen_agent.tool_registry import ToolRegistry
    from autogen_agent.autonomy_config import get_autonomy_manager
    
    registry = ToolRegistry()
    autonomy = get_autonomy_manager()
    
    print("Scenario: Autonomous team wants to create a custom analysis tool")
    
    # Step 1: Check if they can create tools
    can_create = autonomy.can_perform_operation("tool_create")
    print(f"\n1. Can create tools: {can_create['allowed']}")
    
    if not can_create['allowed']:
        print(f"   Reason: {can_create['reason']}")
        print("   (In production, team would create objective to request capability)")
    
    # Step 2: Define a custom tool
    custom_tool_code = '''
async def run(context):
    """Custom analysis tool created by autonomous team"""
    data = context.get("data", [])
    
    if not data:
        return {"success": False, "error": "No data provided"}
    
    # Perform analysis
    analysis = {
        "count": len(data),
        "summary": f"Analyzed {len(data)} items",
        "timestamp": datetime.now().isoformat()
    }
    
    return {
        "success": True,
        "analysis": analysis
    }
'''
    
    # Step 3: Register the tool (would require approval in production)
    from autogen_agent.tools.tool_management import _create_tool
    
    # Mock context with tool creation
    result = {
        "success": True,
        "message": "Tool creation simulated (would require approval in production)"
    }
    
    print(f"\n2. Tool creation result: {result}")
    
    # Step 4: Record the operation
    autonomy.record_operation("tool_create", success=True)
    
    # Step 5: Check updated metrics
    status = autonomy.get_status()
    print(f"\n3. Operations today: {status['operations_today']}")
    print(f"   Operations remaining: {status['operations_remaining']}")
    
    print("\n✅ Integrated scenario completed successfully")
    
    return True


async def main():
    """Run all tests"""
    print("🚀 Testing Enhanced Autonomous Team Capabilities")
    print("="*80)
    print(f"Started at: {datetime.now()}")
    print("="*80)
    
    tests = [
        ("SCB Operations", test_scb_operations),
        ("Dynamic Tool Registration", test_dynamic_tool_registration),
        ("Autonomy Configuration", test_autonomy_configuration),
        ("Tool Management", test_tool_management),
        ("Integrated Scenario", test_integrated_scenario)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, "PASS" if success else "FAIL"))
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, "ERROR"))
    
    # Print summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)
    
    for test_name, status in results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"{icon} {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.0f}%)")
    
    # Save test results
    test_report = {
        "timestamp": datetime.now().isoformat(),
        "results": dict(results),
        "summary": {
            "total": total,
            "passed": passed,
            "success_rate": passed/total
        }
    }
    
    with open("enhanced_capabilities_test_report.json", "w") as f:
        json.dump(test_report, f, indent=2)
    
    print("\n✅ Test report saved to enhanced_capabilities_test_report.json")


if __name__ == "__main__":
    asyncio.run(main())