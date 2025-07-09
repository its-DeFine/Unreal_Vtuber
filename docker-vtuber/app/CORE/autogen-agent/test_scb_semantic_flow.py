#!/usr/bin/env python3
"""
Test SCB to Semantic Map flow
"""

import asyncio
import json
import time
import redis
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scb_semantic_flow():
    """Test publishing SCB states and viewing them in semantic map"""
    
    # Connect to Redis SCB
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    logger.info("🚀 Testing SCB → Semantic Map Flow")
    
    # 1. Publish S2 tool execution state
    logger.info("\n1. Publishing S2 tool execution...")
    scb_state = {
        "timestamp": time.time(),
        "iteration": 1,
        "tool_used": "crypto_market_scanner",
        "success": True,
        "tool_result": {
            "analysis": "BTC showing bullish divergence on 4H chart",
            "signals": ["RSI oversold", "MACD crossover", "Support at $47,500"],
            "confidence": 0.85
        },
        "agent_responses": {
            "s2_analyst": {
                "message": "Strong buy signal detected for Bitcoin",
                "reasoning": "Multiple technical indicators align"
            }
        }
    }
    redis_client.publish("scb_updates", json.dumps(scb_state))
    logger.info("✅ Published tool execution state")
    
    # 2. Publish S2 to S1 communication
    await asyncio.sleep(1)
    logger.info("\n2. Publishing S2 → S1 communication...")
    scb_state = {
        "timestamp": time.time(),
        "iteration": 2,
        "agent_responses": {
            "s2_to_s1": {
                "message": "Please inform the user: Strong BTC buy signal detected. Recommend purchasing 0.5 BTC at current price.",
                "priority": "high",
                "context": "trading_opportunity"
            }
        }
    }
    redis_client.publish("scb_updates", json.dumps(scb_state))
    logger.info("✅ Published S2 → S1 message")
    
    # 3. Publish S1 response
    await asyncio.sleep(1)
    logger.info("\n3. Publishing S1 response...")
    scb_state = {
        "timestamp": time.time(),
        "iteration": 3,
        "agent_responses": {
            "s1_avatar": {
                "message": "Great news! I've detected a strong buying opportunity for Bitcoin. Technical analysis shows bullish signals.",
                "speech_generated": True
            },
            "s1_to_s2": {
                "message": "User informed about BTC opportunity. Awaiting trading decision.",
                "status": "message_delivered"
            }
        }
    }
    redis_client.publish("scb_updates", json.dumps(scb_state))
    logger.info("✅ Published S1 feedback")
    
    # 4. Publish trading execution
    await asyncio.sleep(1)
    logger.info("\n4. Publishing trading execution...")
    scb_state = {
        "timestamp": time.time(),
        "iteration": 4,
        "tool_used": "exchange_api",
        "success": True,
        "trade": "BUY 0.5 BTC @ $48,200",
        "portfolio": {
            "BTC": 1.5,
            "ETH": 5.0,
            "USD": 25000
        },
        "agent_responses": {
            "s2_trader": {
                "message": "Buy order executed successfully",
                "order_id": "ORD-123456"
            }
        }
    }
    redis_client.publish("scb_updates", json.dumps(scb_state))
    logger.info("✅ Published trade execution")
    
    # 5. Publish stimuli processing
    await asyncio.sleep(1)
    logger.info("\n5. Publishing stimuli processing...")
    scb_state = {
        "timestamp": time.time(),
        "iteration": 5,
        "stimuli_id": "stim_001",
        "stimuli_content": "What's my current portfolio value?",
        "decision": "Route to S2 for portfolio calculation",
        "routing": {
            "target": "s2_portfolio_manager",
            "reasoning": "User requesting financial information"
        }
    }
    redis_client.publish("scb_updates", json.dumps(scb_state))
    logger.info("✅ Published stimuli processing")
    
    # 6. Wait for processing
    logger.info("\n⏳ Waiting for semantic map processing...")
    await asyncio.sleep(5)
    
    # 7. Check results
    logger.info("\n📊 Results:")
    logger.info("1. Check SCB Redis for published states:")
    logger.info(f"   - Redis ping: {redis_client.ping()}")
    
    logger.info("\n2. View semantic map visualization:")
    logger.info("   - Open http://localhost:8200/semantic-viewer")
    logger.info("   - The graph should show:")
    logger.info("     • Tool execution nodes (red)")
    logger.info("     • S2→S1 communication (orange)")
    logger.info("     • S1→S2 feedback (green)")
    logger.info("     • Trading nodes (pink)")
    logger.info("     • Stimuli nodes (purple)")
    
    logger.info("\n3. API endpoints to explore:")
    logger.info("   - Status: http://localhost:8200/api/semantic-map/status")
    logger.info("   - Search: POST http://localhost:8200/api/semantic-map/search")
    logger.info("   - Export: http://localhost:8200/api/semantic-map/export?format=d3js")
    logger.info("   - Metrics: http://localhost:8200/api/semantic-map/metrics")

if __name__ == "__main__":
    asyncio.run(test_scb_semantic_flow())