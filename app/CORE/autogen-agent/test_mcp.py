#!/usr/bin/env python3
"""
Test script to demonstrate AutoGen MCP integration
"""
import asyncio
import json
import sys
import os

# Add the autogen_agent module to path
sys.path.append('/app')

from autogen_agent.mcp_server import AutoGenMcpServer

async def test_mcp_server():
    """Test the MCP server functionality"""
    
    print("🔗 Testing AutoGen MCP Server Integration")
    
    # Create a mock cognitive system
    cognitive_system_mock = type('CognitiveSystem', (), {
        'openai_api_key': os.getenv('OPENAI_API_KEY', 'test_key'),
        'cognee_available': True,
        'autonomous_mode': True,
        'iteration_count': 5
    })()
    
    # Initialize MCP server
    mcp_server = AutoGenMcpServer(cognitive_system_mock)
    success = await mcp_server.initialize()
    
    if success:
        print("✅ MCP Server initialized successfully!")
        print(f"📊 Available tools: {len(mcp_server.mcp_tools)}")
        
        # List available tools
        print("\n🔧 Available MCP Tools:")
        for tool in mcp_server.mcp_tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Test get_cognitive_status
        print("\n🧠 Testing get_cognitive_status:")
        status_result = await mcp_server.handle_mcp_call("get_cognitive_status", {})
        print(json.dumps(status_result, indent=2))
        
        # Test get_system_metrics
        print("\n📊 Testing get_system_metrics:")
        metrics_result = await mcp_server.handle_mcp_call("get_system_metrics", {"timeframe": "1h"})
        print(json.dumps(metrics_result, indent=2))
        
        # Test trigger_cognitive_decision
        print("\n🎯 Testing trigger_cognitive_decision:")
        decision_result = await mcp_server.handle_mcp_call("trigger_cognitive_decision", {
            "context": "Test decision from MCP tool",
            "autonomous": False
        })
        print(json.dumps(decision_result, indent=2))
        
        print("\n🎉 All MCP tests completed successfully!")
        
    else:
        print("❌ MCP Server initialization failed")

if __name__ == "__main__":
    asyncio.run(test_mcp_server()) 