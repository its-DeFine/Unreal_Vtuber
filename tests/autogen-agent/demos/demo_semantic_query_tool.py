#!/usr/bin/env python3
"""
Demo: Semantic Graph Query Tool
Shows how agents can query the semantic knowledge graph
"""

import asyncio
import json
from datetime import datetime

# Import the tool
from autogen_agent.tools.semantic_graph_query_tool import get_semantic_query_tool


async def demo_query_tool():
    """Demonstrate various query capabilities"""
    
    print("🔍 SEMANTIC GRAPH QUERY TOOL DEMO")
    print("=" * 60)
    
    # Get the query tool
    tool = get_semantic_query_tool()
    
    # Display tool specification
    print("\n📋 Tool Specification:")
    spec = tool.get_tool_spec()
    print(json.dumps(spec, indent=2))
    
    print("\n" + "=" * 60)
    print("📊 EXAMPLE QUERIES FOR AGENTS:")
    print("=" * 60)
    
    # Example 1: Full-text search
    print("\n1️⃣ FULL-TEXT SEARCH")
    print("   Query: 'Bitcoin' in trading context")
    example1 = {
        "query_type": "search",
        "query": "Bitcoin",
        "context": "trading_finance",
        "limit": 5
    }
    print(f"   Parameters: {json.dumps(example1, indent=6)}")
    
    # Example 2: Pattern matching
    print("\n2️⃣ PATTERN MATCHING")
    print("   Query: Find tools that produced communications")
    example2 = {
        "query_type": "pattern",
        "query": "tool:* -> communication",
        "limit": 5
    }
    print(f"   Parameters: {json.dumps(example2, indent=6)}")
    
    # Example 3: Temporal query
    print("\n3️⃣ TEMPORAL QUERY")
    print("   Query: Recent trading activity in last 24 hours")
    example3 = {
        "query_type": "temporal",
        "query": "trade",
        "time_range": {"hours": 24},
        "context": "trading_finance",
        "limit": 10
    }
    print(f"   Parameters: {json.dumps(example3, indent=6)}")
    
    # Example 4: Context analysis
    print("\n4️⃣ CONTEXT ANALYSIS")
    print("   Query: Analyze S2→S1 communication patterns")
    example4 = {
        "query_type": "context",
        "context": "s2_to_s1_messages",
        "limit": 10
    }
    print(f"   Parameters: {json.dumps(example4, indent=6)}")
    
    # Example 5: Relationship exploration
    print("\n5️⃣ RELATIONSHIP QUERY")
    print("   Query: Explore relationships for a specific node")
    example5 = {
        "query_type": "relationships",
        "query": "s2_market_analysis",  # node ID
        "limit": 10
    }
    print(f"   Parameters: {json.dumps(example5, indent=6)}")
    
    print("\n" + "=" * 60)
    print("🤖 HOW AGENTS USE THIS TOOL:")
    print("=" * 60)
    
    print("""
1. S2 Analyst Agent:
   - Query: "What trading signals were generated in the last hour?"
   - Use: Temporal query with context="trading_finance"
   
2. S2 Trader Agent:
   - Query: "Show me all error patterns that led to failed trades"
   - Use: Pattern match "error -> trade" 
   
3. S1 Avatar Agent:
   - Query: "What messages did I receive from S2 recently?"
   - Use: Search in context="s2_to_s1_messages"
   
4. S2 Programmer Agent:
   - Query: "Which tools have been executing successfully?"
   - Use: Search "success" in context="tool_executions"
   
5. Team Coordinator:
   - Query: "Analyze agent collaboration patterns"
   - Use: Context analysis of "agent_state"
""")
    
    print("\n" + "=" * 60)
    print("💡 ADVANCED PATTERNS:")
    print("=" * 60)
    
    print("""
Pattern Syntax for Agents:
- "tool:* -> *" : All tool executions and their results
- "s2:* -> s1:*" : All S2 to S1 communications
- "error -> *" : What errors led to
- "* -> trade" : What triggered trades
- "stimuli:* -> agent:*" : How stimuli are routed to agents

Query Chaining:
1. Search for a concept → Get node IDs
2. Query relationships for those nodes
3. Analyze patterns in the results
4. Make decisions based on historical data
""")
    
    print("\n" + "=" * 60)
    print("🔗 INTEGRATION WITH AUTOGEN:")
    print("=" * 60)
    
    print("""
# In your AutoGen agent configuration:

from autogen_agent.tools import query_semantic_graph

# Register the tool
tools = [
    {
        "name": "query_semantic_graph",
        "description": "Query the semantic knowledge graph",
        "function": query_semantic_graph
    }
]

# Agent can now use it:
result = await query_semantic_graph(
    query_type="search",
    query="trading opportunity",
    context="s2_to_s1_messages",
    limit=5
)
""")
    
    print("\n✅ The semantic query tool is ready for agent integration!")
    print("   Agents can now query the knowledge graph for intelligent decision-making.")


async def demo_mock_queries():
    """Demonstrate mock query results"""
    
    print("\n\n" + "=" * 60)
    print("📝 MOCK QUERY RESULTS:")
    print("=" * 60)
    
    # Mock search result
    mock_search = {
        "success": True,
        "query": "Bitcoin",
        "query_type": "full_text_search",
        "results": [
            {
                "id": "node_123",
                "content": "S2: Bitcoin market analysis shows bullish trend",
                "context": "trading_finance",
                "type": "analysis",
                "timestamp": datetime.now().isoformat(),
                "metadata": {"confidence": 0.85}
            },
            {
                "id": "node_124",
                "content": "Trade executed: BUY 0.5 Bitcoin @ $48,200",
                "context": "trading_finance",
                "type": "trade",
                "timestamp": datetime.now().isoformat(),
                "metadata": {"amount": 0.5, "price": 48200}
            }
        ],
        "relationships": [
            {"source": "node_123", "type": "TRIGGERS", "target": "node_124"}
        ],
        "count": 2
    }
    
    print("\n🔍 Search Result Example:")
    print(json.dumps(mock_search, indent=2))
    
    # Mock pattern result
    mock_pattern = {
        "success": True,
        "query": "tool:* -> communication",
        "query_type": "pattern_match",
        "patterns": [
            {
                "source": {
                    "id": "tool_001",
                    "content": "Tool 'crypto_scanner' executed successfully",
                    "type": "tool_execution"
                },
                "relationship": {
                    "type": "PRODUCED",
                    "properties": {"confidence": 0.9}
                },
                "target": {
                    "id": "comm_001",
                    "content": "S2→S1: Bitcoin buying opportunity detected",
                    "type": "communication"
                },
                "timestamp": datetime.now().isoformat()
            }
        ],
        "count": 1
    }
    
    print("\n🔗 Pattern Match Example:")
    print(json.dumps(mock_pattern, indent=2))


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_query_tool())
    asyncio.run(demo_mock_queries())