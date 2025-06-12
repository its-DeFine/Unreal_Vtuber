#!/usr/bin/env python3
"""
Test script for verifying intelligent tool selection in ToolRegistry
"""

import sys
import os
import logging
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'CORE', 'autogen-agent'))

from autogen_agent.tool_registry import ToolRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_context_scenarios():
    """Test various context scenarios to verify intelligent selection"""
    
    # Initialize tool registry
    registry = ToolRegistry()
    registry.load_tools()
    
    print("\n🧪 Testing Intelligent Tool Selection System\n")
    print("=" * 80)
    
    # Test scenarios
    test_cases = [
        # Goal-related contexts
        {
            "name": "Goal Setting Context",
            "context": {
                "message": "I need to set a new goal for improving system performance",
                "iteration": 1,
                "autonomous": True
            },
            "expected": "goal_management_tools"
        },
        {
            "name": "Progress Tracking",
            "context": {
                "task": "Check progress on current objectives and update metrics",
                "iteration": 2,
                "autonomous": True
            },
            "expected": "goal_management_tools"
        },
        # Performance/Evolution contexts
        {
            "name": "Performance Issues",
            "context": {
                "description": "System is running slow, need optimization",
                "error_count": 5,
                "decision_time": 4.5,
                "iteration": 3
            },
            "expected": "core_evolution_tool"
        },
        {
            "name": "Evolution Trigger (5th iteration)",
            "context": {
                "action": "Regular system check",
                "iteration": 5,
                "autonomous": True
            },
            "expected": "core_evolution_tool"
        },
        # VTuber contexts
        {
            "name": "VTuber Activation",
            "context": {
                "request": "Activate the VTuber avatar and start streaming",
                "iteration": 6
            },
            "expected": "advanced_vtuber_control"
        },
        {
            "name": "Avatar Control",
            "context": {
                "message": "Control the character voice and avatar appearance",
                "iteration": 7
            },
            "expected": "advanced_vtuber_control"
        },
        # Variable/Dynamic contexts
        {
            "name": "Dynamic Selection",
            "context": {
                "query": "Use adaptive and dynamic tool selection based on context",
                "iteration": 8,
                "autonomous": True
            },
            "expected": "variable_tool_calls"
        },
        # Mixed contexts
        {
            "name": "Mixed Goal and Performance",
            "context": {
                "input": "Set a goal to improve system performance and optimization",
                "iteration": 9,
                "autonomous": True
            },
            "expected": ["goal_management_tools", "core_evolution_tool"]  # Either could win
        }
    ]
    
    # Run tests
    correct_selections = 0
    total_tests = len(test_cases)
    
    for test in test_cases:
        print(f"\n📋 Test: {test['name']}")
        print(f"Context: {test['context']}")
        
        # Select tool
        tool = registry.select_tool(test['context'])
        
        # Find selected tool name
        selected_name = None
        for name, func in registry.tools.items():
            if func == tool:
                selected_name = name
                break
        
        # Check if selection matches expected
        expected = test['expected']
        if isinstance(expected, list):
            is_correct = selected_name in expected
            expected_str = " or ".join(expected)
        else:
            is_correct = selected_name == expected
            expected_str = expected
        
        if is_correct:
            print(f"✅ CORRECT: Selected {selected_name}")
            correct_selections += 1
        else:
            print(f"❌ INCORRECT: Selected {selected_name}, expected {expected_str}")
        
        # Show all scores for debugging
        print("Scores breakdown available in logs")
    
    print("\n" + "=" * 80)
    print(f"\n📊 Results: {correct_selections}/{total_tests} correct selections ({correct_selections/total_tests*100:.1f}%)")
    
    # Test performance tracking
    print("\n\n🔄 Testing Performance Tracking\n")
    print("=" * 80)
    
    # Simulate some tool executions
    contexts_with_results = [
        ("goal_management_tools", {"success": True}, 0.5),
        ("goal_management_tools", {"success": True}, 0.6),
        ("goal_management_tools", {"success": False}, 0.4),
        ("core_evolution_tool", {"success": True}, 2.1),
        ("core_evolution_tool", {"success": True}, 1.8),
        ("advanced_vtuber_control", {"success": True}, 0.3),
        ("advanced_vtuber_control", {"success": False}, 0.2),
    ]
    
    for tool_name, result, exec_time in contexts_with_results:
        success = result.get('success', True)
        registry.update_tool_performance(tool_name, success, exec_time)
    
    # Get status
    status = registry.get_tool_status()
    
    print("\n📈 Performance Summary:")
    for tool_name, perf in status['performance_summary'].items():
        print(f"\n{tool_name}:")
        print(f"  - Success Rate: {perf['success_rate']*100:.1f}%")
        print(f"  - Avg Execution Time: {perf['avg_execution_time']:.2f}s")
        print(f"  - Total Uses: {perf['total_uses']}")
    
    print(f"\n🧠 Intelligent Selection Status:")
    print(f"  - Enabled: {status['intelligent_selection_enabled']}")
    print(f"  - Context Mappings: {status['context_mappings']}")
    print(f"  - Usage History Length: {status['usage_history_length']}")
    
    # Test diversity bonus
    print("\n\n🔀 Testing Diversity Bonus\n")
    print("=" * 80)
    
    # Use same tool multiple times
    for i in range(5):
        context = {"message": "Set another goal", "iteration": 10 + i}
        tool = registry.select_tool(context)
        print(f"Iteration {i+1}: Tool selected (check logs for diversity impact)")
    
    print("\n✅ Intelligent Tool Selection System Test Complete!")

if __name__ == "__main__":
    test_context_scenarios()