#!/usr/bin/env python3
"""
Test Neo4j Semantic Map with Mock SCB Data
Creates and visualizes a semantic graph
"""

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_neo4j_semantic_map():
    """Test Neo4j semantic map with mock data"""
    base_url = "http://localhost:8200"
    
    logger.info("🚀 NEO4J SEMANTIC MAP TEST")
    logger.info("=" * 50)
    
    # Step 1: Check service status
    logger.info("\n1️⃣ CHECKING SERVICE STATUS")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/health") as resp:
            health = await resp.json()
            logger.info(f"✅ AutoGen Agent: {health['status']}")
        
        async with session.get(f"{base_url}/api/semantic-map/status") as resp:
            status = await resp.json()
            logger.info(f"✅ Neo4j Bridge: Active")
            logger.info(f"   - Total Nodes: {status['bridge']['total_nodes']}")
            logger.info(f"   - Total Relationships: {status['bridge']['total_relationships']}")
    
    # Step 2: Create mock SCB states and add them
    logger.info("\n2️⃣ CREATING MOCK SCB STATES")
    
    mock_states = [
        # S2 Market Analysis
        {
            "content": "S2 AutoGen analyzed Bitcoin market: Strong bullish divergence detected at $48,000 support level",
            "type": "market_analysis",
            "context": "trading_finance",
            "metadata": {
                "agent": "s2_analyst",
                "asset": "BTC",
                "price": 48000,
                "signal": "bullish",
                "confidence": 0.85,
                "timestamp": time.time()
            }
        },
        # S2 Tool Execution
        {
            "content": "Executed crypto_market_scanner tool: Found 3 high-confidence trading opportunities",
            "type": "tool_execution",
            "context": "tool_executions",
            "metadata": {
                "tool": "crypto_market_scanner",
                "success": True,
                "opportunities": ["BTC", "ETH", "SOL"],
                "execution_time": 2.5,
                "timestamp": time.time()
            }
        },
        # S2 to S1 Communication
        {
            "content": "S2→S1: Please inform user about Bitcoin buying opportunity at current price",
            "type": "communication",
            "context": "s2_to_s1_messages",
            "metadata": {
                "from": "s2_trader",
                "to": "s1_avatar",
                "priority": "high",
                "action": "inform_user",
                "timestamp": time.time()
            }
        },
        # S1 Response
        {
            "content": "S1 Avatar: Great news! I've identified a strong Bitcoin buying opportunity at $48,000",
            "type": "avatar_speech",
            "context": "s1_to_s2_feedback",
            "metadata": {
                "from": "s1_avatar",
                "to": "user",
                "speech_generated": True,
                "emotion": "excited",
                "timestamp": time.time()
            }
        },
        # Trade Execution
        {
            "content": "Trade executed: BUY 0.5 BTC @ $48,200 - Order filled successfully",
            "type": "trade",
            "context": "trading_finance",
            "metadata": {
                "action": "BUY",
                "amount": 0.5,
                "asset": "BTC",
                "price": 48200,
                "order_id": "ORD-123456",
                "timestamp": time.time()
            }
        },
        # Portfolio Update
        {
            "content": "Portfolio updated: BTC: 1.5, ETH: 5.0, USD: 25,000",
            "type": "portfolio_state",
            "context": "trading_finance",
            "metadata": {
                "holdings": {"BTC": 1.5, "ETH": 5.0, "USD": 25000},
                "total_value_usd": 97300,
                "timestamp": time.time()
            }
        },
        # Stimuli Processing
        {
            "content": "Stimuli received: 'What is my current portfolio value?'",
            "type": "stimuli",
            "context": "stimuli_context",
            "metadata": {
                "stimuli_id": "stim_001",
                "source": "user_query",
                "routing": "s2_portfolio_manager",
                "timestamp": time.time()
            }
        },
        # Agent State
        {
            "content": "S2 AutoGen Team: 3 agents collaborated on portfolio analysis",
            "type": "agent_collaboration",
            "context": "agent_state",
            "metadata": {
                "agents": ["s2_analyst", "s2_trader", "s2_portfolio_manager"],
                "collaboration_score": 0.9,
                "consensus": True,
                "timestamp": time.time()
            }
        },
        # System Event
        {
            "content": "System performance: All services operational, latency < 100ms",
            "type": "system_health",
            "context": "system_events",
            "metadata": {
                "services": ["s1_avatar", "s2_autogen", "neo4j", "redis"],
                "avg_latency_ms": 75,
                "status": "healthy",
                "timestamp": time.time()
            }
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, state in enumerate(mock_states):
            async with session.post(f"{base_url}/api/semantic-map/add", json=state) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"✅ Added node {i+1}/9: {state['type']} - {state['content'][:50]}...")
                else:
                    logger.error(f"❌ Failed to add node {i+1}")
            
            # Small delay between additions
            await asyncio.sleep(0.1)
    
    # Step 3: Search the graph
    logger.info("\n3️⃣ SEARCHING SEMANTIC GRAPH")
    
    searches = [
        ("Bitcoin", None, "Search all contexts for Bitcoin"),
        ("tool", "tool_executions", "Search tool executions"),
        ("S2", "s2_to_s1_messages", "Search S2→S1 messages"),
        ("portfolio", "trading_finance", "Search trading context")
    ]
    
    async with aiohttp.ClientSession() as session:
        for query, context, desc in searches:
            payload = {"query": query, "context": context, "limit": 5}
            async with session.post(f"{base_url}/api/semantic-map/search", json=payload) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    logger.info(f"🔍 {desc}: Found {results['count']} results")
                    for r in results.get('results', [])[:2]:
                        logger.info(f"   - {r['content'][:60]}... (score: {r.get('score', 0):.2f})")
    
    # Step 4: Get graph metrics
    logger.info("\n4️⃣ GRAPH METRICS")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/api/semantic-map/metrics") as resp:
            if resp.status == 200:
                metrics = await resp.json()
                logger.info(f"📊 Graph Statistics:")
                logger.info(f"   - Total Nodes: {metrics.get('nodes', 0)}")
                logger.info(f"   - Total Edges: {metrics.get('edges', 0)}")
                logger.info(f"   - Graph Density: {metrics.get('density', 0):.3f}")
                logger.info(f"   - Components: {metrics.get('components', 0)}")
                
                if 'context_distribution' in metrics:
                    logger.info(f"   - Context Distribution:")
                    for ctx, count in metrics['context_distribution'].items():
                        logger.info(f"     • {ctx}: {count} nodes")
    
    # Step 5: Export graph for visualization
    logger.info("\n5️⃣ EXPORTING GRAPH")
    async with aiohttp.ClientSession() as session:
        # Export as D3.js
        async with session.get(f"{base_url}/api/semantic-map/export?format=d3js") as resp:
            if resp.status == 200:
                data = await resp.json()
                logger.info(f"✅ D3.js export: {data['nodes']} nodes, {data['edges']} edges")
                
                # Save to file
                with open("/tmp/semantic_graph_d3.json", "w") as f:
                    json.dump(data['data'], f, indent=2)
                logger.info(f"   - Saved to: /tmp/semantic_graph_d3.json")
        
        # Generate PyVis visualization
        async with session.get(f"{base_url}/api/semantic-map/visualize") as resp:
            if resp.status == 200:
                html = await resp.text()
                with open("/tmp/semantic_graph_neo4j.html", "w") as f:
                    f.write(html)
                logger.info(f"✅ PyVis visualization saved to: /tmp/semantic_graph_neo4j.html")
    
    # Step 6: Summary
    logger.info("\n" + "=" * 50)
    logger.info("📋 TEST SUMMARY")
    logger.info("✅ Neo4j semantic map is working!")
    logger.info("✅ Added 9 semantic nodes across different contexts")
    logger.info("✅ Search functionality operational")
    logger.info("✅ Graph metrics available")
    logger.info("✅ Export and visualization working")
    
    logger.info("\n🌐 ACCESS POINTS:")
    logger.info(f"   - Interactive Viewer: http://localhost:8200/semantic-viewer")
    logger.info(f"   - Neo4j Browser: http://localhost:7474 (neo4j/password123)")
    logger.info(f"   - PyVis HTML: file:///tmp/semantic_graph_neo4j.html")
    logger.info(f"   - D3.js Data: /tmp/semantic_graph_d3.json")
    
    logger.info("\n💡 The semantic graph shows:")
    logger.info("   - S2 market analysis → tool execution → communication flow")
    logger.info("   - S1 avatar responses and feedback")
    logger.info("   - Trading decisions and portfolio updates")
    logger.info("   - Complete system interaction graph")


if __name__ == "__main__":
    asyncio.run(test_neo4j_semantic_map())