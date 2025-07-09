#!/usr/bin/env python3
"""
Test S1/S2 interaction with SCB and Semantic Map visualization

This test verifies:
1. S1 and S2 can write to SCB
2. SCB data is transformed to semantic entries
3. Data flows into Cognee knowledge graph
4. Graph can be exported and visualized
"""

import asyncio
import logging
import json
import time
import aiohttp
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class S1S2SemanticTester:
    """Test S1/S2 communication through semantic maps"""
    
    def __init__(self):
        self.s1_endpoint = "http://neurosync:5001"
        self.s2_endpoint = "http://localhost:8000"
        self.test_results = []
    
    async def run_all_tests(self):
        """Run all S1/S2 semantic tests"""
        logger.info("🚀 Starting S1/S2 Semantic Map Integration Tests")
        
        tests = [
            ("Test S1 Direct Speech", self.test_s1_direct_speech),
            ("Test S2 Tool Execution", self.test_s2_tool_execution),
            ("Test S2 to S1 Communication", self.test_s2_to_s1_communication),
            ("Test Complex Trading Scenario", self.test_trading_scenario),
            ("Test Stimuli Processing Flow", self.test_stimuli_flow),
            ("Test Graph Export", self.test_graph_export),
            ("Test Visualization", self.test_visualization)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n🔧 Running: {test_name}")
            try:
                result = await test_func()
                self.test_results.append({
                    "name": test_name,
                    "success": result.get("success", False),
                    "details": result
                })
                
                if result.get("success"):
                    logger.info(f"✅ {test_name} - PASSED")
                else:
                    logger.error(f"❌ {test_name} - FAILED: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"❌ {test_name} - ERROR: {e}")
                self.test_results.append({
                    "name": test_name,
                    "success": False,
                    "error": str(e)
                })
        
        self.print_summary()
    
    async def test_s1_direct_speech(self):
        """Test S1 Avatar direct speech processing"""
        try:
            async with aiohttp.ClientSession() as session:
                # Send direct speech to S1
                payload = {
                    "text": "Hello! This is S1 Avatar speaking directly to test the semantic map.",
                    "direct_speech": True,
                    "autonomous_context": {
                        "source": "semantic_test",
                        "test": True
                    }
                }
                
                async with session.post(
                    f"{self.s1_endpoint}/process_text",
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Wait for SCB state to be published
                        await asyncio.sleep(2)
                        
                        # Check if the message appears in semantic search
                        search_result = await self.search_semantic_map("S1 Avatar speaking")
                        
                        return {
                            "success": search_result.get("count", 0) > 0,
                            "s1_response": result,
                            "semantic_search": search_result
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"S1 failed: HTTP {response.status}"
                        }
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_s2_tool_execution(self):
        """Test S2 AutoGen tool execution tracking"""
        try:
            # First, trigger a tool execution through S2
            # This simulates AutoGen executing a tool
            scb_state = {
                "tool_used": "market_analysis_tool",
                "success": True,
                "tool_result": {
                    "analysis": "BTC showing strong support at $48,000",
                    "recommendation": "Consider buying opportunity"
                },
                "timestamp": time.time(),
                "agent_responses": {
                    "s2_analyst": {
                        "message": "Market analysis completed successfully"
                    }
                }
            }
            
            # Send to SCB transformation
            await self.send_to_scb_transform(scb_state)
            
            # Wait for processing
            await asyncio.sleep(2)
            
            # Search for tool execution in semantic map
            search_result = await self.search_semantic_map(
                "market_analysis_tool",
                context="tool_executions"
            )
            
            return {
                "success": search_result.get("count", 0) > 0,
                "tool_execution": scb_state,
                "semantic_search": search_result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_s2_to_s1_communication(self):
        """Test S2 to S1 communication flow"""
        try:
            # S2 sends a message to S1
            s2_message = {
                "agent_responses": {
                    "s2_trader": {
                        "message": "Trade executed: Bought 0.5 BTC at $48,500"
                    },
                    "s2_to_s1": {
                        "message": "Please inform the user about the successful Bitcoin purchase"
                    }
                },
                "context": "trading_communication",
                "timestamp": time.time()
            }
            
            await self.send_to_scb_transform(s2_message)
            
            # S1 responds
            s1_response = {
                "agent_responses": {
                    "s1_avatar": {
                        "message": "Great news! Your Bitcoin purchase of 0.5 BTC has been completed successfully!"
                    }
                },
                "context": "s1_to_s2_feedback",
                "timestamp": time.time()
            }
            
            await self.send_to_scb_transform(s1_response)
            
            # Wait for processing
            await asyncio.sleep(3)
            
            # Search for communication flow
            s2_to_s1_search = await self.search_semantic_map(
                "inform user Bitcoin",
                context="s2_to_s1_messages"
            )
            
            s1_to_s2_search = await self.search_semantic_map(
                "purchase completed",
                context="s1_to_s2_feedback"
            )
            
            return {
                "success": (s2_to_s1_search.get("count", 0) > 0 and 
                           s1_to_s2_search.get("count", 0) > 0),
                "s2_to_s1_found": s2_to_s1_search.get("count", 0),
                "s1_to_s2_found": s1_to_s2_search.get("count", 0)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_trading_scenario(self):
        """Test complete trading scenario with semantic tracking"""
        try:
            scenario_states = []
            
            # 1. Market analysis
            scenario_states.append({
                "tool_used": "crypto_market_scanner",
                "success": True,
                "tool_result": {
                    "signals": ["BTC bullish divergence", "ETH support test"],
                    "confidence": 0.85
                },
                "agent_responses": {
                    "s2_analyst": {"message": "Identified trading opportunity in BTC"}
                },
                "timestamp": time.time()
            })
            
            # 2. Risk assessment
            scenario_states.append({
                "tool_used": "risk_calculator",
                "success": True,
                "tool_result": {
                    "position_size": 0.3,
                    "stop_loss": "$47,000",
                    "take_profit": "$52,000"
                },
                "timestamp": time.time()
            })
            
            # 3. Trade execution
            scenario_states.append({
                "tool_used": "exchange_api",
                "success": True,
                "trade": "BUY 0.3 BTC @ $48,000",
                "portfolio": {"BTC": 1.3, "ETH": 5.0, "USD": 25000},
                "agent_responses": {
                    "s2_trader": {"message": "Buy order filled successfully"}
                },
                "timestamp": time.time()
            })
            
            # 4. Notify S1
            scenario_states.append({
                "agent_responses": {
                    "s2_to_s1": {"message": "Trading update: Successfully purchased 0.3 BTC. Portfolio now contains 1.3 BTC total."}
                },
                "timestamp": time.time()
            })
            
            # Send all states
            for state in scenario_states:
                await self.send_to_scb_transform(state)
                await asyncio.sleep(0.5)
            
            # Wait for processing
            await asyncio.sleep(3)
            
            # Verify the flow in semantic map
            tool_search = await self.search_semantic_map("crypto_market_scanner", context="tool_executions")
            trade_search = await self.search_semantic_map("BTC", context="trading_finance")
            comm_search = await self.search_semantic_map("portfolio", context="s2_to_s1_messages")
            
            return {
                "success": all([
                    tool_search.get("count", 0) > 0,
                    trade_search.get("count", 0) > 0,
                    comm_search.get("count", 0) > 0
                ]),
                "tools_found": tool_search.get("count", 0),
                "trades_found": trade_search.get("count", 0),
                "communications_found": comm_search.get("count", 0)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_stimuli_flow(self):
        """Test stimuli processing through the system"""
        try:
            async with aiohttp.ClientSession() as session:
                # Send a stimuli to S2
                stimuli_payload = {
                    "stimuli_id": f"test_semantic_{int(time.time())}",
                    "content": "What's the current Bitcoin price and should I buy?",
                    "source": "semantic_test",
                    "priority": "high",
                    "category": "trading_query",
                    "metadata": {"test": True}
                }
                
                async with session.post(
                    f"{self.s2_endpoint}/api/stimuli/receive",
                    json=stimuli_payload
                ) as response:
                    if response.status == 200:
                        stimuli_response = await response.json()
                        
                        # Wait for processing
                        await asyncio.sleep(3)
                        
                        # Search for stimuli in semantic map
                        stimuli_search = await self.search_semantic_map(
                            stimuli_payload["stimuli_id"],
                            context="stimuli_context"
                        )
                        
                        return {
                            "success": stimuli_search.get("count", 0) > 0,
                            "stimuli_response": stimuli_response,
                            "semantic_search": stimuli_search
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Stimuli failed: HTTP {response.status}"
                        }
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_graph_export(self):
        """Test exporting the semantic graph"""
        try:
            async with aiohttp.ClientSession() as session:
                # Export in different formats
                formats = ["d3js", "cytoscape", "json_ld"]
                results = []
                
                for format in formats:
                    async with session.get(
                        f"{self.s2_endpoint}/api/semantic-map/export?format={format}"
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Check data structure
                            has_data = False
                            node_count = 0
                            
                            if format == "d3js" and "data" in data:
                                has_data = "nodes" in data["data"] and "links" in data["data"]
                                node_count = len(data["data"].get("nodes", []))
                            elif format == "cytoscape" and "data" in data:
                                has_data = "elements" in data["data"]
                                elements = data["data"].get("elements", [])
                                node_count = sum(1 for e in elements if "source" not in e.get("data", {}))
                            elif format == "json_ld" and "data" in data:
                                has_data = "@graph" in data["data"]
                                node_count = len([n for n in data["data"].get("@graph", []) if "@type" in n])
                            
                            results.append({
                                "format": format,
                                "success": has_data and node_count > 0,
                                "node_count": node_count
                            })
                        else:
                            results.append({
                                "format": format,
                                "success": False,
                                "error": f"HTTP {response.status}"
                            })
                
                all_success = all(r["success"] for r in results)
                total_nodes = sum(r.get("node_count", 0) for r in results) / len(results)
                
                return {
                    "success": all_success and total_nodes > 5,  # Should have at least 5 nodes
                    "formats_tested": len(formats),
                    "average_nodes": total_nodes,
                    "results": results
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_visualization(self):
        """Test graph visualization generation"""
        try:
            async with aiohttp.ClientSession() as session:
                # Generate visualization
                async with session.get(
                    f"{self.s2_endpoint}/api/semantic-map/visualize"
                ) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        
                        # Check HTML structure
                        has_pyvis = "pyvis" in html_content.lower()
                        has_vis_network = "vis.Network" in html_content or "vis-network" in html_content
                        has_nodes = "nodes" in html_content
                        has_edges = "edges" in html_content
                        
                        return {
                            "success": all([has_pyvis, has_nodes, has_edges]),
                            "html_size": len(html_content),
                            "has_pyvis": has_pyvis,
                            "has_vis_network": has_vis_network,
                            "has_graph_elements": has_nodes and has_edges
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Visualization failed: HTTP {response.status}"
                        }
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_to_scb_transform(self, scb_state):
        """Helper to send SCB state for transformation"""
        # In real implementation, this would go through the SCB client
        # For testing, we'll call the transformation directly
        from autogen_agent.services.scb_cognee_bridge import transform_and_store_scb_state
        await transform_and_store_scb_state(scb_state)
    
    async def search_semantic_map(self, query, context=None):
        """Helper to search semantic map"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "query": query,
                "context": context,
                "limit": 10
            }
            
            async with session.post(
                f"{self.s2_endpoint}/api/semantic-map/search",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"count": 0, "error": f"Search failed: HTTP {response.status}"}
    
    def print_summary(self):
        """Print test summary"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed
        
        logger.info("\n" + "="*50)
        logger.info("📊 S1/S2 Semantic Map Test Summary")
        logger.info("="*50)
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            logger.info("\nFailed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    logger.info(f"  - {result['name']}: {result.get('error', 'Unknown error')}")
        
        # Key insights
        logger.info("\n🔍 Key Insights:")
        
        # Check if basic communication works
        s1_test = next((r for r in self.test_results if "S1 Direct" in r["name"]), None)
        if s1_test and s1_test["success"]:
            logger.info("  ✅ S1 Avatar can publish to semantic map")
        
        s2_test = next((r for r in self.test_results if "S2 Tool" in r["name"]), None)
        if s2_test and s2_test["success"]:
            logger.info("  ✅ S2 AutoGen tool executions are tracked")
        
        comm_test = next((r for r in self.test_results if "Communication" in r["name"]), None)
        if comm_test and comm_test["success"]:
            logger.info("  ✅ S2→S1 and S1→S2 communication flows work")
        
        export_test = next((r for r in self.test_results if "Export" in r["name"]), None)
        if export_test and export_test["success"]:
            avg_nodes = export_test["details"].get("average_nodes", 0)
            logger.info(f"  ✅ Graph export works with ~{int(avg_nodes)} nodes")
        
        viz_test = next((r for r in self.test_results if "Visualization" in r["name"]), None)
        if viz_test and viz_test["success"]:
            logger.info("  ✅ Interactive visualization can be generated")


async def main():
    """Main test runner"""
    logger.info("🌐 S1/S2 Semantic Map Integration Test Suite")
    logger.info("Testing complete flow: S1/S2 → SCB → Cognee → Visualization")
    
    tester = S1S2SemanticTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())