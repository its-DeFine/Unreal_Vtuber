#!/usr/bin/env python3
"""
Verify the 5th iteration bonus for core_evolution_tool
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(__file__))
from autogen_agent.tool_registry import ToolRegistry

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

# Create registry and add mock tools
registry = ToolRegistry()
registry.tools = {
    "goal_management_tools": lambda c: {"success": True},
    "core_evolution_tool": lambda c: {"success": True},
    "advanced_vtuber_control": lambda c: {"success": True},
    "variable_tool_calls": lambda c: {"success": True}
}

# Initialize performance tracking
for tool_name in registry.tools.keys():
    registry.tool_performance[tool_name] = {
        'total_uses': 0,
        'successes': 0,
        'avg_execution_time': 0.0,
        'context_relevance_scores': [],
        'last_used': 0
    }

print("\n🔍 Testing 5th Iteration Bonus for core_evolution_tool\n")

# Test iterations 4, 5, 6, 10, 15
for iteration in [4, 5, 6, 10, 15]:
    context = {
        "action": "Regular system check",
        "iteration": iteration,
        "autonomous": True
    }
    
    # Calculate scores manually for core_evolution_tool
    context_text = registry._extract_context_text(context)
    relevance = registry._calculate_context_relevance("core_evolution_tool", context, context_text)
    
    print(f"Iteration {iteration}:")
    print(f"  Context relevance for core_evolution_tool: {relevance:.3f}")
    
    # Select tool
    tool = registry.select_tool(context)
    selected_name = [name for name, func in registry.tools.items() if func == tool][0]
    print(f"  Selected tool: {selected_name}")
    print()