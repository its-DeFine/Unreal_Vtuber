#!/usr/bin/env python3
"""
Demo: Semantic Graph Query Tool (Simplified)
Shows the query tool specification and example usage
"""

import json
from datetime import datetime

def demo_query_tool():
    """Demonstrate the semantic query tool capabilities"""
    
    print("🔍 SEMANTIC GRAPH QUERY TOOL DEMO")
    print("=" * 60)
    
    # Tool specification
    tool_spec = {
        "name": "semantic_graph_query",
        "description": (
            "Query the semantic knowledge graph for historical patterns, relationships, "
            "and insights. Supports full-text search, pattern matching, and temporal queries."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["search", "pattern", "temporal", "context", "relationships"],
                    "description": "Type of query to perform"
                },
                "query": {
                    "type": "string",
                    "description": "The search query or pattern to match"
                },
                "context": {
                    "type": "string",
                    "enum": ["general", "s2_to_s1_messages", "s1_to_s2_feedback", 
                             "tool_executions", "stimuli_context", "agent_state", 
                             "trading_finance", "system_events"],
                    "description": "Semantic context to search within (optional)"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "hours": {"type": "integer", "description": "Hours to look back"},
                        "days": {"type": "integer", "description": "Days to look back"}
                    },
                    "description": "Time range for temporal queries"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of results to return"
                }
            },
            "required": ["query_type", "query"]
        }
    }
    
    print("\n📋 Tool Specification:")
    print(json.dumps(tool_spec, indent=2))
    
    print("\n" + "=" * 60)
    print("📊 EXAMPLE QUERIES FOR AGENTS:")
    print("=" * 60)
    
    # Example queries
    examples = [
        {
            "title": "1️⃣ FULL-TEXT SEARCH",
            "description": "Query: 'Bitcoin' in trading context",
            "request": {
                "query_type": "search",
                "query": "Bitcoin",
                "context": "trading_finance",
                "limit": 5
            },
            "expected_result": {
                "success": True,
                "query": "Bitcoin",
                "query_type": "full_text_search",
                "results": [
                    {
                        "id": "node_123",
                        "content": "S2: Bitcoin market analysis shows bullish trend",
                        "context": "trading_finance",
                        "type": "analysis",
                        "timestamp": datetime.now().isoformat()
                    }
                ],
                "count": 1
            }
        },
        {
            "title": "2️⃣ PATTERN MATCHING",
            "description": "Query: Find tools that produced communications",
            "request": {
                "query_type": "pattern",
                "query": "tool:* -> communication",
                "limit": 5
            },
            "expected_result": {
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
                            "content": "S2→S1: Bitcoin buying opportunity",
                            "type": "communication"
                        }
                    }
                ],
                "count": 1
            }
        },
        {
            "title": "3️⃣ TEMPORAL QUERY",
            "description": "Query: Recent trading activity in last 24 hours",
            "request": {
                "query_type": "temporal",
                "query": "trade",
                "time_range": {"hours": 24},
                "context": "trading_finance",
                "limit": 10
            }
        },
        {
            "title": "4️⃣ CONTEXT ANALYSIS",
            "description": "Query: Analyze S2→S1 communication patterns",
            "request": {
                "query_type": "context",
                "context": "s2_to_s1_messages",
                "limit": 10
            }
        },
        {
            "title": "5️⃣ RELATIONSHIP QUERY",
            "description": "Query: Explore relationships for a specific node",
            "request": {
                "query_type": "relationships",
                "query": "s2_market_analysis",
                "limit": 10
            }
        }
    ]
    
    for example in examples:
        print(f"\n{example['title']}")
        print(f"   {example['description']}")
        print(f"   Request: {json.dumps(example['request'], indent=6)}")
        if "expected_result" in example:
            print(f"   Expected Result Preview:")
            print(f"   {json.dumps(example['expected_result'], indent=6)[:200]}...")
    
    print("\n" + "=" * 60)
    print("🤖 HOW AGENTS USE THIS TOOL:")
    print("=" * 60)
    
    agent_examples = [
        {
            "agent": "S2 Analyst Agent",
            "query": "What trading signals were generated in the last hour?",
            "usage": "Temporal query with context='trading_finance'"
        },
        {
            "agent": "S2 Trader Agent",
            "query": "Show me all error patterns that led to failed trades",
            "usage": "Pattern match 'error -> trade'"
        },
        {
            "agent": "S1 Avatar Agent",
            "query": "What messages did I receive from S2 recently?",
            "usage": "Search in context='s2_to_s1_messages'"
        },
        {
            "agent": "S2 Programmer Agent",
            "query": "Which tools have been executing successfully?",
            "usage": "Search 'success' in context='tool_executions'"
        },
        {
            "agent": "Team Coordinator",
            "query": "Analyze agent collaboration patterns",
            "usage": "Context analysis of 'agent_state'"
        }
    ]
    
    for example in agent_examples:
        print(f"\n{example['agent']}:")
        print(f"   - Query: \"{example['query']}\"")
        print(f"   - Use: {example['usage']}")
    
    print("\n" + "=" * 60)
    print("💡 PATTERN SYNTAX:")
    print("=" * 60)
    
    patterns = {
        "tool:*": "Any tool execution",
        "s2:*": "Any S2 agent node",
        "s1:*": "Any S1 agent node",
        "error": "Error nodes",
        "*": "Any node",
        "->": "Relationship direction",
        "tool:* -> *": "All tool executions and their results",
        "s2:* -> s1:*": "All S2 to S1 communications",
        "error -> *": "What errors led to",
        "* -> trade": "What triggered trades",
        "stimuli:* -> agent:*": "How stimuli are routed to agents"
    }
    
    for pattern, description in patterns.items():
        print(f"   '{pattern}' : {description}")
    
    print("\n" + "=" * 60)
    print("🔗 API ENDPOINTS:")
    print("=" * 60)
    
    print("""
POST /api/semantic-map/query
   - Execute a semantic graph query
   - Request body contains query parameters
   
GET /api/semantic-map/query/examples
   - Get example queries and documentation
   - Returns pattern syntax and use cases
""")
    
    print("\n" + "=" * 60)
    print("📝 QUERY CHAINING STRATEGY:")
    print("=" * 60)
    
    print("""
1. Discovery Phase: Search for relevant concepts
   → query_type: "search", query: "error"
   
2. Exploration Phase: Query relationships for discovered nodes
   → query_type: "relationships", query: "node_123"
   
3. Analysis Phase: Identify patterns in the results
   → query_type: "pattern", query: "* -> error"
   
4. Decision Phase: Make informed decisions based on data
   → Use insights to avoid similar errors
""")
    
    print("\n✅ The semantic query tool enables intelligent agent decision-making!")
    print("   Agents can now query historical patterns to improve their responses.")
    
    print("\n" + "=" * 60)
    print("🏗️ ARCHITECTURE SUMMARY:")
    print("=" * 60)
    
    print("""
1. SCB States (Redis) → Flat state storage
   - Current system state
   - Real-time updates
   
2. Neo4j Graph → Semantic knowledge
   - Historical patterns
   - Relationships
   - Context-aware storage
   
3. Query Tool → Agent intelligence
   - Pattern recognition
   - Temporal analysis
   - Context understanding
   
4. Agent Decisions → Improved behavior
   - Learn from history
   - Avoid past errors
   - Optimize strategies
""")

if __name__ == "__main__":
    demo_query_tool()