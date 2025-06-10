#!/usr/bin/env python3
"""
Test script for AutoGen Cognitive Enhancement System
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime

# Add the autogen_agent module to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from autogen_agent.cognitive_memory import CognitiveMemoryManager
from autogen_agent.cognitive_decision_engine import CognitiveDecisionEngine
from autogen_agent.tool_registry import ToolRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

async def test_cognitive_memory():
    """Test the cognitive memory system"""
    print("🧠 Testing Cognitive Memory Manager...")
    
    # Initialize memory manager (without Cognee for testing)
    db_url = "postgresql://postgres:postgres@localhost:5434/autonomous_agent"
    memory = CognitiveMemoryManager(db_url)
    
    try:
        await memory.initialize()
        print("✅ Memory manager initialized successfully")
        
        # Test storing an interaction
        context = {"test": "context", "iteration": 1}
        action = "test_action"
        result = {"success": True, "message": "Test successful"}
        
        memory_id = await memory.store_interaction(context, action, result)
        print(f"✅ Stored interaction with ID: {memory_id}")
        
        # Test retrieving relevant context
        memories = await memory.retrieve_relevant_context("test")
        print(f"✅ Retrieved {len(memories)} relevant memories")
        
        return True
        
    except Exception as e:
        print(f"❌ Cognitive memory test failed: {e}")
        return False

async def test_decision_engine():
    """Test the cognitive decision engine"""
    print("🧠 Testing Cognitive Decision Engine...")
    
    try:
        # Initialize components
        db_url = "postgresql://postgres:postgres@localhost:5434/autonomous_agent"
        memory = CognitiveMemoryManager(db_url)
        await memory.initialize()
        
        registry = ToolRegistry()
        registry.load_tools()
        
        decision_engine = CognitiveDecisionEngine(memory, registry)
        print("✅ Decision engine initialized successfully")
        
        # Test making a decision
        context = {
            "test": "decision_context",
            "iteration": 1,
            "autonomous": True,
            "message": "Test decision making"
        }
        
        result = await decision_engine.make_intelligent_decision(context)
        print(f"✅ Decision made: {result.get('tool_used', 'unknown')} - Success: {result.get('success', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Decision engine test failed: {e}")
        return False

def test_tool_registry():
    """Test the tool registry"""
    print("🧠 Testing Tool Registry...")
    
    try:
        registry = ToolRegistry()
        registry.load_tools()
        
        print(f"✅ Loaded {len(registry.tools)} tools:")
        for tool_name in registry.tools.keys():
            print(f"  - {tool_name}")
        
        # Test tool selection
        context = {"test": "tool_context"}
        tool = registry.select_tool(context)
        
        if tool:
            result = tool(context)
            print(f"✅ Tool executed successfully: {result}")
        else:
            print("⚠️ No tool selected")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool registry test failed: {e}")
        return False

async def test_full_system():
    """Test the full cognitive system integration"""
    print("🚀 Testing Full Cognitive System Integration...")
    
    try:
        # Initialize all components
        db_url = "postgresql://postgres:postgres@localhost:5434/autonomous_agent"
        memory = CognitiveMemoryManager(db_url)
        await memory.initialize()
        
        registry = ToolRegistry()
        registry.load_tools()
        
        decision_engine = CognitiveDecisionEngine(memory, registry)
        
        # Run multiple decision cycles
        for i in range(3):
            context = {
                "iteration": i + 1,
                "autonomous": True,
                "message": f"Full system test iteration {i + 1}",
                "timestamp": time.time()
            }
            
            print(f"\n🔄 Running decision cycle #{i + 1}...")
            result = await decision_engine.make_intelligent_decision(context)
            
            print(f"✅ Cycle {i + 1} completed:")
            print(f"  - Tool: {result.get('tool_used', 'unknown')}")
            print(f"  - Success: {result.get('success', False)}")
            print(f"  - Memory Enhanced: {result.get('memory_enhanced', False)}")
            print(f"  - Execution Time: {result.get('execution_time', 0):.3f}s")
            
            # Small delay between cycles
            await asyncio.sleep(1)
        
        return True
        
    except Exception as e:
        print(f"❌ Full system test failed: {e}")
        return False

async def main():
    """Main test runner"""
    print("🧪 AutoGen Cognitive Enhancement System Tests")
    print("=" * 50)
    
    tests = [
        ("Tool Registry", test_tool_registry),
        ("Cognitive Memory", test_cognitive_memory),
        ("Decision Engine", test_decision_engine),
        ("Full System Integration", test_full_system)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test...")
        print("-" * 30)
        
        start_time = time.time()
        
        if asyncio.iscoroutinefunction(test_func):
            success = await test_func()
        else:
            success = test_func()
        
        duration = time.time() - start_time
        
        results.append((test_name, success, duration))
        
        if success:
            print(f"✅ {test_name} test passed ({duration:.2f}s)")
        else:
            print(f"❌ {test_name} test failed ({duration:.2f}s)")
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, duration in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status} ({duration:.2f}s)")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Cognitive enhancement system is ready.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the logs for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main()) 