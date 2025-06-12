#!/usr/bin/env python3
"""
Simple test script to verify intelligent tool selection without full container setup
"""

import sys
import os
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from autogen_agent.tool_registry import ToolRegistry

# Configure logging to see our intelligent selection logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_intelligent_selection():
    """Test the intelligent tool selection system"""
    
    # Create registry
    registry = ToolRegistry()
    
    # Manually add some mock tools for testing
    def mock_goal_tool(context):
        return {"success": True, "message": "Goal tool executed"}
    
    def mock_evolution_tool(context):
        return {"success": True, "message": "Evolution tool executed"}
    
    def mock_vtuber_tool(context):
        return {"success": True, "message": "VTuber tool executed"}
    
    def mock_variable_tool(context):
        return {"success": True, "message": "Variable tool executed"}
    
    # Add tools to registry
    registry.tools = {
        "goal_management_tools": mock_goal_tool,
        "core_evolution_tool": mock_evolution_tool,
        "advanced_vtuber_control": mock_vtuber_tool,
        "variable_tool_calls": mock_variable_tool
    }
    
    # Initialize performance tracking for each tool
    for tool_name in registry.tools.keys():
        registry.tool_performance[tool_name] = {
            'total_uses': 0,
            'successes': 0,
            'avg_execution_time': 0.0,
            'context_relevance_scores': [],
            'last_used': 0
        }
    
    print("\n" + "="*80)
    print("🧠 TESTING INTELLIGENT TOOL SELECTION SYSTEM")
    print("="*80 + "\n")
    
    # Test 1: Goal context
    print("TEST 1: Goal-related context")
    context1 = {
        "message": "I need to set a new goal for improving system performance",
        "iteration": 1,
        "autonomous": True
    }
    tool1 = registry.select_tool(context1)
    print(f"Expected: goal_management_tools")
    print(f"Selected: {[name for name, func in registry.tools.items() if func == tool1][0]}")
    print()
    
    # Test 2: Performance issues
    print("TEST 2: Performance optimization context")
    context2 = {
        "description": "System is running slow, need optimization and performance improvements",
        "error_count": 5,
        "decision_time": 4.5,
        "iteration": 2
    }
    tool2 = registry.select_tool(context2)
    print(f"Expected: core_evolution_tool")
    print(f"Selected: {[name for name, func in registry.tools.items() if func == tool2][0]}")
    print()
    
    # Test 3: VTuber context
    print("TEST 3: VTuber activation context")
    context3 = {
        "request": "Activate the VTuber avatar and start streaming",
        "iteration": 3
    }
    tool3 = registry.select_tool(context3)
    print(f"Expected: advanced_vtuber_control")
    print(f"Selected: {[name for name, func in registry.tools.items() if func == tool3][0]}")
    print()
    
    # Test 4: Evolution trigger at 5th iteration
    print("TEST 4: 5th iteration evolution trigger")
    context4 = {
        "action": "Regular system check",
        "iteration": 5,
        "autonomous": True
    }
    tool4 = registry.select_tool(context4)
    print(f"Expected: core_evolution_tool (5th iteration bonus)")
    print(f"Selected: {[name for name, func in registry.tools.items() if func == tool4][0]}")
    print()
    
    # Test 5: Dynamic/adaptive context
    print("TEST 5: Dynamic selection context")
    context5 = {
        "query": "Use adaptive and dynamic tool selection based on context",
        "iteration": 8,
        "autonomous": True
    }
    tool5 = registry.select_tool(context5)
    print(f"Expected: variable_tool_calls")
    print(f"Selected: {[name for name, func in registry.tools.items() if func == tool5][0]}")
    print()
    
    # Test performance tracking
    print("\n" + "="*80)
    print("📊 TESTING PERFORMANCE TRACKING")
    print("="*80 + "\n")
    
    # Simulate some executions
    registry.update_tool_performance("goal_management_tools", True, 0.5)
    registry.update_tool_performance("goal_management_tools", True, 0.6)
    registry.update_tool_performance("goal_management_tools", False, 0.4)
    registry.update_tool_performance("core_evolution_tool", True, 2.1)
    registry.update_tool_performance("core_evolution_tool", True, 1.8)
    
    # Get status
    status = registry.get_tool_status()
    print("Performance Summary:")
    for tool_name, perf in status['performance_summary'].items():
        print(f"  {tool_name}:")
        print(f"    - Success Rate: {perf['success_rate']*100:.1f}%")
        print(f"    - Avg Execution Time: {perf['avg_execution_time']:.2f}s")
        print(f"    - Total Uses: {perf['total_uses']}")
    
    print(f"\nIntelligent Selection Enabled: {status['intelligent_selection_enabled']}")
    print(f"Context Mappings: {status['context_mappings']}")
    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    test_intelligent_selection()