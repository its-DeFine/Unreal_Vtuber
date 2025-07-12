#!/usr/bin/env python3
"""
Test script for SCB to Cognee semantic map transformation

This script tests the complete pipeline:
1. SCB state transformation to semantic entries
2. Storage in Cognee knowledge graph
3. Graph export and visualization
"""

import asyncio
import logging
import json
import time
from datetime import datetime
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SemanticMapTester:
    """Test harness for semantic map functionality"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
    
    async def run_all_tests(self):
        """Run all semantic map tests"""
        logger.info("🧪 Starting Semantic Map Tests")
        
        tests = [
            ("Test Service Status", self.test_service_status),
            ("Test SCB State Transformation", self.test_scb_transformation),
            ("Test Semantic Search", self.test_semantic_search),
            ("Test Graph Export", self.test_graph_export),
            ("Test Graph Metrics", self.test_graph_metrics),
            ("Test Visualization", self.test_visualization),
            ("Test Complex Scenario", self.test_complex_scenario)
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
    
    async def test_service_status(self):
        """Test if semantic map services are running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/semantic-map/status") as response:
                    if response.status == 200:
                        status = await response.json()
                        
                        # Check bridge status
                        bridge_ok = (status.get("bridge") and 
                                   status["bridge"].get("processing_active"))
                        
                        # Check export service
                        export_ok = (status.get("export") and 
                                   status["export"].get("cognee_connected"))
                        
                        return {
                            "success": bridge_ok and export_ok,
                            "bridge_status": status.get("bridge"),
                            "export_status": status.get("export")
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Status check failed: HTTP {response.status}"
                        }
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_scb_transformation(self):
        """Test transforming SCB states to semantic entries"""
        try:
            # Import the bridge module directly for testing
            import sys
            sys.path.append('/app')
            from autogen_agent.services.scb_cognee_bridge import (
                SCBCogneeBridge, SemanticContext, transform_and_store_scb_state
            )
            
            # Create test SCB states
            test_states = [
                {
                    "tool_used": "test_tool",
                    "success": True,
                    "timestamp": time.time(),
                    "tool_result": "Test completed successfully"
                },
                {
                    "agent_responses": {
                        "s2_agent": {"message": "Analyzing market data..."},
                        "s1_avatar": {"message": "Displaying results to user"}
                    },
                    "iteration": 1
                },
                {
                    "stimuli_id": "test_stimuli_123",
                    "decision": "Route to S1 for immediate response",
                    "priority": "high"
                },
                {
                    "error": "Connection timeout",
                    "success": False,
                    "timestamp": time.time()
                },
                {
                    "portfolio": {"BTC": 0.5, "ETH": 2.0},
                    "trade": "BUY 0.1 BTC @ $50000",
                    "timestamp": time.time()
                }
            ]
            
            # Transform each state
            bridge = SCBCogneeBridge(use_direct_cognee=True)
            results = []
            
            for state in test_states:
                entries = await bridge.transform_scb_state(state)
                results.append({
                    "state": state,
                    "entries": len(entries),
                    "contexts": [e.context.value for e in entries]
                })
            
            return {
                "success": True,
                "transformed_count": len(results),
                "results": results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_semantic_search(self):
        """Test searching the semantic knowledge graph"""
        try:
            # First, ensure some data is in the graph
            await self._add_test_data()
            
            # Wait for processing
            await asyncio.sleep(2)
            
            # Test various searches
            search_tests = [
                {"query": "tool execution", "context": "tool_executions"},
                {"query": "market trading", "context": "trading_finance"},
                {"query": "error", "context": "system_events"},
                {"query": "communication", "context": None}
            ]
            
            results = []
            async with aiohttp.ClientSession() as session:
                for test in search_tests:
                    payload = {
                        "query": test["query"],
                        "context": test["context"],
                        "limit": 5
                    }
                    
                    async with session.post(
                        f"{self.base_url}/api/semantic-map/search",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            search_result = await response.json()
                            results.append({
                                "query": test["query"],
                                "found": search_result.get("count", 0),
                                "success": True
                            })
                        else:
                            results.append({
                                "query": test["query"],
                                "success": False,
                                "error": f"HTTP {response.status}"
                            })
            
            all_success = all(r["success"] for r in results)
            return {
                "success": all_success,
                "search_results": results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_graph_export(self):
        """Test graph export functionality"""
        try:
            formats = ["d3js", "json_ld", "cytoscape"]
            results = []
            
            async with aiohttp.ClientSession() as session:
                for format in formats:
                    async with session.get(
                        f"{self.base_url}/api/semantic-map/export?format={format}"
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            has_data = False
                            if format == "d3js":
                                has_data = ("nodes" in data.get("data", {}) and 
                                          "links" in data.get("data", {}))
                            elif format == "json_ld":
                                has_data = "@graph" in data.get("data", {})
                            elif format == "cytoscape":
                                has_data = "elements" in data.get("data", {})
                            
                            results.append({
                                "format": format,
                                "success": True,
                                "has_data": has_data,
                                "nodes": data.get("nodes", 0),
                                "edges": data.get("edges", 0)
                            })
                        else:
                            results.append({
                                "format": format,
                                "success": False,
                                "error": f"HTTP {response.status}"
                            })
            
            all_success = all(r["success"] for r in results)
            return {
                "success": all_success,
                "export_results": results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_graph_metrics(self):
        """Test graph metrics analysis"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/semantic-map/metrics"
                ) as response:
                    if response.status == 200:
                        metrics = await response.json()
                        
                        # Check for expected metrics
                        has_basic_metrics = all(
                            key in metrics 
                            for key in ["nodes", "edges", "density"]
                        )
                        
                        return {
                            "success": has_basic_metrics,
                            "metrics": metrics
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Metrics failed: HTTP {response.status}"
                        }
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_visualization(self):
        """Test HTML visualization generation"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/semantic-map/visualize"
                ) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        
                        # Check if it's valid HTML with graph elements
                        is_valid_html = (
                            "<html" in html_content and
                            "pyvis" in html_content.lower()
                        )
                        
                        return {
                            "success": is_valid_html,
                            "html_size": len(html_content)
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Visualization failed: HTTP {response.status}"
                        }
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_complex_scenario(self):
        """Test a complex multi-step scenario"""
        try:
            scenario_states = []
            
            # 1. S2 analyzes market data
            scenario_states.append({
                "tool_used": "market_analysis_tool",
                "success": True,
                "agent_responses": {
                    "s2_analyst": {"message": "BTC showing bullish signals"}
                },
                "metadata": {"market": "crypto", "asset": "BTC"}
            })
            
            # 2. S2 makes trading decision
            scenario_states.append({
                "tool_used": "trading_executor",
                "success": True,
                "trade": "BUY 0.5 BTC @ $48000",
                "agent_responses": {
                    "s2_trader": {"message": "Executing buy order"}
                }
            })
            
            # 3. S2 communicates to S1
            scenario_states.append({
                "agent_responses": {
                    "s2_to_s1": {"message": "Please inform user: Buy order executed successfully"}
                },
                "context": "s2_to_s1_messages"
            })
            
            # 4. S1 responds to user
            scenario_states.append({
                "agent_responses": {
                    "s1_avatar": {"message": "Your Bitcoin purchase has been completed!"}
                },
                "context": "s1_to_s2_feedback"
            })
            
            # Transform and store states
            from autogen_agent.services.scb_cognee_bridge import transform_and_store_scb_state
            
            for state in scenario_states:
                await transform_and_store_scb_state(state)
            
            # Wait for processing
            await asyncio.sleep(3)
            
            # Search for the complete flow
            async with aiohttp.ClientSession() as session:
                # Search for trading activity
                payload = {"query": "BTC buy order", "limit": 10}
                async with session.post(
                    f"{self.base_url}/api/semantic-map/search",
                    json=payload
                ) as response:
                    if response.status == 200:
                        results = await response.json()
                        
                        return {
                            "success": results.get("count", 0) > 0,
                            "scenario_states": len(scenario_states),
                            "search_results": results.get("count", 0)
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Search failed: HTTP {response.status}"
                        }
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _add_test_data(self):
        """Helper to add test data to the knowledge graph"""
        test_states = [
            {
                "tool_used": "data_processor",
                "success": True,
                "timestamp": time.time()
            },
            {
                "error": "Test error for search",
                "success": False,
                "timestamp": time.time()
            },
            {
                "market_analysis": "BTC trending upward",
                "trading": True,
                "timestamp": time.time()
            }
        ]
        
        from autogen_agent.services.scb_cognee_bridge import transform_and_store_scb_state
        
        for state in test_states:
            await transform_and_store_scb_state(state)
    
    def print_summary(self):
        """Print test summary"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed
        
        logger.info("\n" + "="*50)
        logger.info("📊 Semantic Map Test Summary")
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
        
        # Save detailed results
        with open(f"/tmp/semantic_map_test_results_{int(time.time())}.json", "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)


async def main():
    """Main test runner"""
    logger.info("🚀 Semantic Map Integration Test Suite")
    logger.info("Testing SCB → Cognee → Visualization pipeline")
    
    tester = SemanticMapTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())