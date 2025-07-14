"""
Full Orchestrator Execution Tests
Tests the complete flow: routing -> execution -> response
"""
import pytest
import httpx
import asyncio
import time
import json
from typing import Dict, Any

# Test configuration
ORCHESTRATOR_URL = "http://localhost:8082"
TIMEOUT = httpx.Timeout(30.0, connect=5.0)


@pytest.fixture
async def async_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


class TestFullExecution:
    """Test complete orchestrator execution flow"""
    
    @pytest.mark.asyncio
    async def test_s1_full_execution(self, async_client):
        """Test full execution flow to S1"""
        test_stimulus = {
            "stimulus_id": f"test_s1_exec_{int(time.time())}",
            "text": "Hello, tell me a quick joke!",
            "priority": "normal"
        }
        
        # Use the /process endpoint for full execution
        response = await async_client.post(
            f"{ORCHESTRATOR_URL}/process",
            json=test_stimulus
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify response structure
        assert result["success"] is True
        assert "routing_decision" in result
        assert "execution_results" in result
        
        # Verify routing to S1
        routing = result["routing_decision"]
        assert routing["system"] == "s1"
        assert routing["confidence"] >= 0.7
        
        # Verify execution results
        assert "s1" in result["execution_results"]
        s1_result = result["execution_results"]["s1"]
        assert s1_result["status"] == "processing"
        assert s1_result["s1_system"] is True
        
        print(f"S1 Execution successful: {result}")
    
    @pytest.mark.asyncio
    async def test_s2_full_execution(self, async_client):
        """Test full execution flow to S2"""
        test_stimulus = {
            "stimulus_id": f"test_s2_exec_{int(time.time())}",
            "text": "Analyze the cryptocurrency market trends and provide a detailed trading strategy",
            "priority": "normal"
        }
        
        response = await async_client.post(
            f"{ORCHESTRATOR_URL}/process",
            json=test_stimulus
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify response structure
        assert result["success"] is True
        assert "routing_decision" in result
        assert "execution_results" in result
        
        # Verify routing to S2
        routing = result["routing_decision"]
        assert routing["system"] == "s2"
        assert routing["config"]["team"] == "trader"
        
        # Verify execution results
        assert "s2" in result["execution_results"]
        s2_result = result["execution_results"]["s2"]
        
        # S2 should have response indicating it received the stimulus
        assert "stimuli_id" in s2_result or "stimulus_id" in s2_result
        assert s2_result.get("success", False) is True or "agent_decision" in s2_result
        
        # Check that S2 queued or processed the stimulus
        if "agent_decision" in s2_result:
            assert "queued" in s2_result["agent_decision"] or "processing" in s2_result["agent_decision"]
        
        print(f"S2 Execution successful: {result}")
    
    @pytest.mark.asyncio
    async def test_hybrid_execution(self, async_client):
        """Test execution that routes to both systems"""
        test_stimulus = {
            "stimulus_id": f"test_hybrid_exec_{int(time.time())}",
            "text": "What's the current BTC price and analyze why it's at that level?",
            "priority": "normal"
        }
        
        response = await async_client.post(
            f"{ORCHESTRATOR_URL}/process",
            json=test_stimulus
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify routing decision
        routing = result["routing_decision"]
        assert routing["system"] == "both"
        
        # When routed to both, we should have results from both systems
        exec_results = result["execution_results"]
        assert "s1" in exec_results or "s2" in exec_results
        
        print(f"Hybrid Execution result: {result}")
    
    @pytest.mark.asyncio
    async def test_concurrent_executions(self, async_client):
        """Test multiple concurrent executions"""
        num_requests = 5
        
        async def make_request(i: int):
            stimulus = {
                "stimulus_id": f"concurrent_exec_{i}_{int(time.time())}",
                "text": f"Test request {i}: Hello!",
                "priority": "normal"
            }
            
            response = await async_client.post(
                f"{ORCHESTRATOR_URL}/process",
                json=stimulus
            )
            return response.status_code == 200, response.json()
        
        # Execute concurrent requests
        results = await asyncio.gather(*[make_request(i) for i in range(num_requests)])
        
        # Verify all succeeded
        success_count = sum(1 for success, _ in results if success)
        assert success_count == num_requests
        
        # Verify each has proper response
        for success, result in results:
            assert success
            assert result["success"] is True
            assert "execution_results" in result
    
    @pytest.mark.asyncio
    async def test_system_health_before_execution(self, async_client):
        """Verify systems are healthy before executing"""
        # Check orchestrator health
        health_response = await async_client.get(f"{ORCHESTRATOR_URL}/health")
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert health_data["apis"]["system1"] == "healthy"
        assert health_data["apis"]["system2"] == "healthy"
        
        print("All systems healthy and ready for execution")
    
    @pytest.mark.asyncio
    async def test_execution_latency(self, async_client):
        """Test that executions complete within reasonable time"""
        latencies = []
        
        for i in range(3):
            stimulus = {
                "stimulus_id": f"latency_test_{i}",
                "text": "Quick response test",
                "priority": "normal"
            }
            
            start_time = time.time()
            response = await async_client.post(
                f"{ORCHESTRATOR_URL}/process",
                json=stimulus
            )
            end_time = time.time()
            
            assert response.status_code == 200
            result = response.json()
            
            # Record latencies
            actual_latency_ms = (end_time - start_time) * 1000
            reported_latency_ms = result.get("total_latency_ms", 0)
            
            latencies.append(reported_latency_ms)
            
            # Should complete within 5 seconds for S1
            if result["routing_decision"]["system"] == "s1":
                assert reported_latency_ms < 5000, f"S1 execution too slow: {reported_latency_ms}ms"
        
        avg_latency = sum(latencies) / len(latencies)
        print(f"Average execution latency: {avg_latency:.2f}ms")


class TestErrorRecovery:
    """Test error handling during execution"""
    
    @pytest.mark.asyncio
    async def test_empty_text_execution(self, async_client):
        """Test handling of empty text in execution"""
        stimulus = {
            "stimulus_id": "empty_text_exec",
            "text": "",
            "priority": "normal"
        }
        
        response = await async_client.post(
            f"{ORCHESTRATOR_URL}/process",
            json=stimulus
        )
        
        # Should handle gracefully
        assert response.status_code == 200
        result = response.json()
        
        # Even with empty text, should route somewhere
        assert "routing_decision" in result
        assert result["routing_decision"]["confidence"] <= 0.5  # Low confidence expected
    
    @pytest.mark.asyncio
    async def test_malformed_request(self, async_client):
        """Test handling of malformed requests"""
        # Missing required fields
        bad_stimulus = {
            "text": "Test without stimulus_id"
        }
        
        response = await async_client.post(
            f"{ORCHESTRATOR_URL}/process",
            json=bad_stimulus
        )
        
        # Should return error
        assert response.status_code in [422, 400, 500]


class TestSystemSpecificRouting:
    """Test routing to specific systems based on content"""
    
    @pytest.mark.asyncio
    async def test_trader_persona_routing(self, async_client):
        """Test that trading queries route correctly"""
        trading_queries = [
            "What's the current BTC price?",
            "Show me ETH market data",
            "Quick crypto market update"
        ]
        
        for query in trading_queries:
            stimulus = {
                "stimulus_id": f"trader_test_{int(time.time())}",
                "text": query,
                "priority": "normal"
            }
            
            response = await async_client.post(
                f"{ORCHESTRATOR_URL}/process",
                json=stimulus
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Should route to S1 with trader persona
            routing = result["routing_decision"]
            assert routing["system"] in ["s1", "both"]
            if routing["system"] == "s1":
                assert routing["config"]["persona"] == "trader"
    
    @pytest.mark.asyncio
    async def test_complex_analysis_routing(self, async_client):
        """Test that complex queries route to S2"""
        complex_queries = [
            "Create a comprehensive cryptocurrency portfolio optimization strategy",
            "Analyze market trends and provide backtesting results",
            "Research blockchain technology and its implications"
        ]
        
        for query in complex_queries:
            stimulus = {
                "stimulus_id": f"complex_test_{int(time.time())}",
                "text": query,
                "priority": "normal"
            }
            
            response = await async_client.post(
                f"{ORCHESTRATOR_URL}/process",
                json=stimulus
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Should route to S2
            routing = result["routing_decision"]
            assert routing["system"] in ["s2", "both"]
            if routing["system"] == "s2":
                assert routing["config"]["team"] in ["trader", "educator"]


if __name__ == "__main__":
    # Run tests with proper asyncio handling
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-s"])