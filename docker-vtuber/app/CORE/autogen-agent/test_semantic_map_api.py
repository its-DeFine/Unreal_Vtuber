#!/usr/bin/env python3
"""
Simple test for semantic map API functionality
"""

import asyncio
import aiohttp
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_semantic_map_api():
    """Test semantic map through API endpoints"""
    base_url = "http://localhost:8200"
    
    logger.info("🧪 Testing Semantic Map API")
    
    async with aiohttp.ClientSession() as session:
        # 1. Check status
        logger.info("1. Checking semantic map status...")
        async with session.get(f"{base_url}/api/semantic-map/status") as resp:
            status = await resp.json()
            logger.info(f"✅ Status: {json.dumps(status, indent=2)}")
        
        # 2. Add some test entries
        logger.info("\n2. Adding test entries...")
        test_entries = [
            {
                "content": "S2 executed market analysis tool",
                "type": "tool_execution",
                "context": "tool_executions",
                "metadata": {"tool": "market_analysis", "result": "bullish"}
            },
            {
                "content": "S2 to S1: Please inform user about BTC purchase",
                "type": "communication",
                "context": "s2_to_s1_messages",
                "metadata": {"from": "s2_trader", "to": "s1_avatar"}
            },
            {
                "content": "S1 response: Bitcoin purchase completed successfully",
                "type": "feedback",
                "context": "s1_to_s2_feedback",
                "metadata": {"from": "s1_avatar", "to": "s2_trader"}
            },
            {
                "content": "Trade executed: BUY 0.5 BTC @ $48,000",
                "type": "trade",
                "context": "trading_finance",
                "metadata": {"amount": 0.5, "price": 48000, "asset": "BTC"}
            }
        ]
        
        for entry in test_entries:
            async with session.post(
                f"{base_url}/api/semantic-map/add",
                json=entry
            ) as resp:
                result = await resp.json()
                logger.info(f"✅ Added: {entry['content'][:50]}...")
        
        # 3. Search semantic map
        logger.info("\n3. Searching semantic map...")
        searches = [
            {"query": "BTC", "context": None},
            {"query": "market analysis", "context": "tool_executions"},
            {"query": "inform user", "context": "s2_to_s1_messages"}
        ]
        
        for search in searches:
            async with session.post(
                f"{base_url}/api/semantic-map/search",
                json=search
            ) as resp:
                results = await resp.json()
                logger.info(f"🔍 Search '{search['query']}' (context: {search['context']}): Found {results.get('count', 0)} results")
        
        # 4. Export graph
        logger.info("\n4. Exporting graph...")
        formats = ["d3js", "graphml", "cytoscape"]
        
        for fmt in formats:
            async with session.get(
                f"{base_url}/api/semantic-map/export?format={fmt}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if fmt == "d3js":
                        nodes = len(data.get("data", {}).get("nodes", []))
                        edges = len(data.get("data", {}).get("links", []))
                        logger.info(f"✅ Export {fmt}: {nodes} nodes, {edges} edges")
                    else:
                        logger.info(f"✅ Export {fmt}: Success")
                else:
                    logger.error(f"❌ Export {fmt}: Failed with status {resp.status}")
        
        # 5. Get metrics
        logger.info("\n5. Getting graph metrics...")
        async with session.get(f"{base_url}/api/semantic-map/metrics") as resp:
            if resp.status == 200:
                metrics = await resp.json()
                logger.info(f"📊 Metrics: {json.dumps(metrics, indent=2)}")
            else:
                logger.error(f"❌ Metrics failed: {resp.status}")
        
        # 6. Check visualization
        logger.info("\n6. Checking visualization...")
        async with session.get(f"{base_url}/api/semantic-map/visualize") as resp:
            if resp.status == 200:
                html = await resp.text()
                logger.info(f"✅ Visualization HTML generated: {len(html)} bytes")
            else:
                logger.error(f"❌ Visualization failed: {resp.status}")
        
        # 7. Access static viewer
        logger.info("\n7. Checking static viewer...")
        async with session.get(f"{base_url}/semantic-viewer") as resp:
            if resp.status == 200:
                html = await resp.text()
                logger.info(f"✅ Static viewer accessible: {len(html)} bytes")
                logger.info(f"🌐 Visit http://localhost:8200/semantic-viewer to see the interactive graph!")
            else:
                logger.error(f"❌ Static viewer failed: {resp.status}")

if __name__ == "__main__":
    asyncio.run(test_semantic_map_api())