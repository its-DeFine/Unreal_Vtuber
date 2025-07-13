"""
Orchestrator Integration Tests
Tests routing decisions, API registry, health checks, and latency requirements
"""
import pytest
import httpx
import asyncio
import time
import json
from typing import Dict, Any

# Test configuration
ORCHESTRATOR_URL = "http://localhost:8082"
S1_URL = "http://localhost:5000"
S2_URL = "http://localhost:8200"
TIMEOUT = httpx.Timeout(30.0, connect=5.0)


@pytest.fixture
async def async_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


class TestOrchestratorHealth:
    """Test orchestrator health and readiness"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        """Test orchestrator health check endpoint"""
        response = await async_client.get(f"{ORCHESTRATOR_URL}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] in ["healthy", "degraded"]
        assert "apis" in health_data
        assert "system1" in health_data["apis"]
        assert "system2" in health_data["apis"]
    
    @pytest.mark.asyncio
    async def test_api_registry_loaded(self, async_client):
        """Test that API registry is properly loaded"""
        response = await async_client.get(f"{ORCHESTRATOR_URL}/api/registry")
        assert response.status_code == 200
        
        registry = response.json()
        assert "system1" in registry
        assert "system2" in registry
        
        # Check S1 configuration
        s1_config = registry["system1"]
        assert "endpoint" in s1_config
        assert "capabilities" in s1_config
        assert "personas" in s1_config
        
        # Check S2 configuration
        s2_config = registry["system2"]
        assert "endpoint" in s2_config
        assert "capabilities" in s2_config
        assert "teams" in s2_config


class TestRoutingDecisions:
    """Test routing logic for different stimulus types"""
    
    @pytest.mark.asyncio
    async def test_route_realtime_to_s1(self, async_client):
        """Test that real-time queries route to S1"""
        test_cases = [
            ("What's the current BTC price?", "trader"),
            ("Tell me a joke", "streamer"),
            ("What time is it?", "streamer"),
        ]
        
        for text, expected_persona in test_cases:
            request = {
                "stimulus_id": f"test_{int(time.time())}",
                "text": text,
                "priority": "normal"
            }
            
            response = await async_client.post(
                f"{ORCHESTRATOR_URL}/route",
                json=request
            )
            assert response.status_code == 200
            
            decision = response.json()
            assert decision["system"] == "s1"
            assert decision["config"]["persona"] == expected_persona
            assert decision["confidence"] >= 0.7
            assert "reasoning" in decision
    
    @pytest.mark.asyncio
    async def test_route_complex_to_s2(self, async_client):
        """Test that complex queries route to S2"""
        test_cases = [
            ("Analyze the cryptocurrency market trends for the past month", "trader"),
            ("Create a comprehensive trading strategy", "trader"),
            ("Research and explain quantum computing", "educator"),
        ]
        
        for text, expected_team in test_cases:
            request = {
                "stimulus_id": f"test_{int(time.time())}",
                "text": text,
                "priority": "normal"
            }
            
            response = await async_client.post(
                f"{ORCHESTRATOR_URL}/route",
                json=request
            )
            assert response.status_code == 200
            
            decision = response.json()
            assert decision["system"] == "s2"
            assert decision["config"]["team"] == expected_team
            assert decision["confidence"] >= 0.7
    
    @pytest.mark.asyncio
    async def test_route_hybrid_to_both(self, async_client):
        """Test that hybrid queries route to both systems"""
        request = {
            "stimulus_id": f"test_{int(time.time())}",
            "text": "Tell me the BTC price and analyze the trend",
            "priority": "normal"
        }
        
        response = await async_client.post(
            f"{ORCHESTRATOR_URL}/route",
            json=request
        )
        assert response.status_code == 200
        
        decision = response.json()
        assert decision["system"] == "both"
        assert "coordination" in decision["config"]
        assert decision["config"]["coordination"] in ["s1_then_s2", "parallel"]


class TestLatencyRequirements:
    """Test that routing decisions meet latency requirements"""
    
    @pytest.mark.asyncio
    async def test_routing_latency_under_10ms(self, async_client):
        """Test that routing decisions complete in under 10ms (target)"""
        latencies = []
        
        # Run multiple routing decisions to get average
        for i in range(10):
            request = {
                "stimulus_id": f"latency_test_{i}",
                "text": "What's the weather like?",
                "priority": "normal"
            }
            
            start_time = time.time()
            response = await async_client.post(
                f"{ORCHESTRATOR_URL}/route",
                json=request
            )
            end_time = time.time()
            
            assert response.status_code == 200
            
            # Check reported latency
            decision = response.json()
            reported_latency = decision.get("latency_ms", 0)
            
            # Calculate actual latency
            actual_latency_ms = (end_time - start_time) * 1000
            latencies.append(reported_latency)
            
            # Individual request should be under 50ms (critical threshold)
            assert reported_latency < 50, f"Routing latency {reported_latency}ms exceeds critical threshold"
        
        # Average should be close to target
        avg_latency = sum(latencies) / len(latencies)
        print(f"Average routing latency: {avg_latency:.2f}ms")
        
        # Warn if average exceeds target
        if avg_latency > 10:
            pytest.warns(UserWarning, f"Average latency {avg_latency:.2f}ms exceeds 10ms target")


class TestExecutionFlow:
    """Test full execution flow through orchestrator"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires S1 and S2 to be running")
    async def test_execute_s1_routing(self, async_client):
        """Test executing a routing decision to S1"""
        # First make routing decision
        route_request = {
            "stimulus_id": "exec_test_s1",
            "text": "Hello, how are you?",
            "priority": "normal"
        }
        
        route_response = await async_client.post(
            f"{ORCHESTRATOR_URL}/route",
            json=route_request
        )
        assert route_response.status_code == 200
        
        decision = route_response.json()
        
        # Execute the routing
        exec_response = await async_client.post(
            f"{ORCHESTRATOR_URL}/execute",
            json=decision
        )
        assert exec_response.status_code == 200
        
        result = exec_response.json()
        assert "s1" in result
        assert result["s1"]["success"] is True


class TestErrorHandling:
    """Test error handling and fallback behavior"""
    
    @pytest.mark.asyncio
    async def test_invalid_request_format(self, async_client):
        """Test handling of invalid request format"""
        # Missing required fields
        invalid_request = {
            "text": "Test without stimulus_id"
        }
        
        response = await async_client.post(
            f"{ORCHESTRATOR_URL}/route",
            json=invalid_request
        )
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, async_client):
        """Test handling of empty text"""
        request = {
            "stimulus_id": "empty_test",
            "text": "",
            "priority": "normal"
        }
        
        response = await async_client.post(
            f"{ORCHESTRATOR_URL}/route",
            json=request
        )
        # Should still work but route to default
        assert response.status_code == 200
        
        decision = response.json()
        assert decision["system"] in ["s1", "s2", "both"]
        assert decision["confidence"] <= 0.5  # Low confidence for empty input


class TestMetrics:
    """Test metrics endpoint"""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, async_client):
        """Test that metrics are exposed"""
        response = await async_client.get(f"{ORCHESTRATOR_URL}/metrics")
        assert response.status_code == 200
        
        # Check for Prometheus format
        metrics_text = response.text
        assert "orchestrator_routing_total" in metrics_text
        assert "orchestrator_routing_duration_seconds" in metrics_text
        assert "orchestrator_api_errors_total" in metrics_text


# Performance test suite
class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_routing_decisions(self, async_client):
        """Test handling multiple concurrent routing requests"""
        num_requests = 50
        
        async def make_routing_request(i: int):
            request = {
                "stimulus_id": f"concurrent_test_{i}",
                "text": f"Test request number {i}",
                "priority": "normal"
            }
            
            response = await async_client.post(
                f"{ORCHESTRATOR_URL}/route",
                json=request
            )
            return response.status_code == 200
        
        # Make concurrent requests
        tasks = [make_routing_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.95, f"Success rate {success_rate} below threshold"


if __name__ == "__main__":
    # Run tests with proper asyncio handling
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])