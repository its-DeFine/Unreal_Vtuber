"""
Unit tests for the ExecutionCoordinatorNode.

Tests all execution options (A, B, C, Emergency), concurrent execution,
retry logic, and error aggregation.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import time

from src.models.stimuli import Priority
from src.models.decisions import (
    ProcessingDecision,
    ExecutionPlan,
    RoutingDecision,
    RetryPolicy,
    ExecutionResult
)
from src.gateway.nodes.executor_node import (
    ExecutionCoordinatorNode,
    ExecutorConfig
)
from src.integrations.system1_interface import System1Interface
from src.integrations.system2_interface import System2Interface


class TestExecutionCoordinatorNode:
    """Test suite for ExecutionCoordinatorNode."""
    
    @pytest.fixture
    def mock_system1_interface(self):
        """Create mock System1 interface."""
        interface = Mock(spec=System1Interface)
        interface.trigger_avatar_response = AsyncMock(return_value=True)
        interface.check_system_availability = AsyncMock(return_value={"available": True})
        interface.estimate_processing_time = AsyncMock(return_value=2.0)
        interface.load_character = AsyncMock(return_value=True)
        interface.set_mode = AsyncMock(return_value=True)
        return interface
    
    @pytest.fixture
    def mock_system2_interface(self):
        """Create mock System2 interface."""
        interface = Mock(spec=System2Interface)
        interface.submit_for_analysis = AsyncMock(return_value="task-123")
        interface.get_agent_status = AsyncMock(return_value={"agents": {"all": "ready"}})
        interface.trigger_evolution_analysis = AsyncMock(return_value=True)
        interface.query_cognee_memory = AsyncMock(return_value=[])
        return interface
    
    @pytest.fixture
    def executor_config(self):
        """Create executor configuration."""
        return ExecutorConfig(
            max_concurrent_executions=10,
            default_timeout=30.0,
            retry_enabled=True,
            max_retry_attempts=3,
            retry_backoff_factor=2.0,
            emergency_override_enabled=True,
            log_execution_details=True
        )
    
    @pytest.fixture
    def executor_node(self, mock_system1_interface, mock_system2_interface, executor_config):
        """Create executor node for testing."""
        return ExecutionCoordinatorNode(
            mock_system1_interface,
            mock_system2_interface,
            executor_config
        )
    
    @pytest.fixture
    def sample_routing_decision(self):
        """Create sample routing decision."""
        return RoutingDecision(
            stimuli_id="test-123",
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            execution_plan=ExecutionPlan(
                decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
                target_systems=["system1", "system2"],
                execution_order="parallel",
                timeout_settings={"system1": 10.0, "system2": 20.0},
                retry_policies={
                    "system1": RetryPolicy(max_attempts=2, backoff_factor=1.5),
                    "system2": RetryPolicy(max_attempts=3, backoff_factor=2.0)
                },
                success_criteria={"min_systems_success": 1}
            ),
            confidence_score=0.9,
            reasoning="User interaction with idle system"
        )
    
    # Test Execution Options
    
    @pytest.mark.asyncio
    async def test_execute_option_a_success(self, executor_node, sample_routing_decision):
        """Test Option A: Avatar tools + agent analysis (concurrent)."""
        result = await executor_node.process(sample_routing_decision)
        
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.stimuli_id == "test-123"
        assert "system1" in result.results
        assert "system2" in result.results
        assert result.results["system1"]["success"] is True
        assert result.results["system2"]["success"] is True
        assert result.results["system2"]["task_id"] == "task-123"
        
        # Verify both systems were called
        executor_node.system1_interface.trigger_avatar_response.assert_called_once()
        executor_node.system2_interface.submit_for_analysis.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_option_b_analysis_only(self, executor_node):
        """Test Option B: Agent analysis only."""
        routing_decision = RoutingDecision(
            stimuli_id="test-456",
            decision=ProcessingDecision.ANALYSIS_ONLY,
            execution_plan=ExecutionPlan(
                decision=ProcessingDecision.ANALYSIS_ONLY,
                target_systems=["system2"],
                execution_order="sequential",
                timeout_settings={"system2": 30.0},
                retry_policies={
                    "system2": RetryPolicy(max_attempts=3, backoff_factor=2.0)
                },
                success_criteria={"min_systems_success": 1}
            ),
            confidence_score=0.8,
            reasoning="System1 is busy"
        )
        
        result = await executor_node.process(routing_decision)
        
        assert result.success is True
        assert "system2" in result.results
        assert "system1" not in result.results
        assert result.results["system2"]["success"] is True
        
        # Verify only System2 was called
        executor_node.system1_interface.trigger_avatar_response.assert_not_called()
        executor_node.system2_interface.submit_for_analysis.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_option_c_log_only(self, executor_node):
        """Test Option C: Log and store only."""
        routing_decision = RoutingDecision(
            stimuli_id="test-789",
            decision=ProcessingDecision.LOG_ONLY,
            execution_plan=ExecutionPlan(
                decision=ProcessingDecision.LOG_ONLY,
                target_systems=[],
                execution_order="none",
                timeout_settings={},
                retry_policies={},
                success_criteria={}
            ),
            confidence_score=0.5,
            reasoning="Low priority contextual update"
        )
        
        result = await executor_node.process(routing_decision)
        
        assert result.success is True
        assert result.results.get("action") == "logged"
        assert "log_timestamp" in result.results
        
        # Verify no systems were called
        executor_node.system1_interface.trigger_avatar_response.assert_not_called()
        executor_node.system2_interface.submit_for_analysis.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_emergency_override(self, executor_node):
        """Test Emergency: Override with immediate processing."""
        routing_decision = RoutingDecision(
            stimuli_id="emergency-123",
            decision=ProcessingDecision.EMERGENCY_OVERRIDE,
            execution_plan=ExecutionPlan(
                decision=ProcessingDecision.EMERGENCY_OVERRIDE,
                target_systems=["emergency"],
                execution_order="immediate",
                timeout_settings={"global": 5.0},
                retry_policies={},
                success_criteria={"must_complete": True},
                metadata={"emergency_type": "system_critical"}
            ),
            confidence_score=1.0,
            reasoning="Critical system failure detected"
        )
        
        # Mock the emergency override module
        with patch('src.gateway.nodes.executor_node.load_emergency_override') as mock_load:
            mock_emergency_handler = AsyncMock(return_value=True)
            mock_load.return_value = mock_emergency_handler
            
            result = await executor_node.process(routing_decision)
            
            assert result.success is True
            assert result.results.get("override") is True
            assert result.execution_time < 5.0  # Within emergency timeout
            mock_emergency_handler.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_emergency_override_missing_file(self, executor_node):
        """Test emergency override when file is missing."""
        routing_decision = RoutingDecision(
            stimuli_id="emergency-456",
            decision=ProcessingDecision.EMERGENCY_OVERRIDE,
            execution_plan=ExecutionPlan(
                decision=ProcessingDecision.EMERGENCY_OVERRIDE,
                target_systems=["emergency"],
                execution_order="immediate",
                timeout_settings={"global": 5.0},
                retry_policies={},
                success_criteria={"must_complete": True}
            ),
            confidence_score=1.0,
            reasoning="Emergency override required"
        )
        
        # Mock ImportError for missing file
        with patch('src.gateway.nodes.executor_node.load_emergency_override') as mock_load:
            mock_load.side_effect = ImportError("Emergency override file not found")
            
            result = await executor_node.process(routing_decision)
            
            assert result.success is False
            assert "error" in result.results
            assert "Emergency override file not found" in result.error_details
    
    # Test Concurrent Execution
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_timing(self, executor_node, sample_routing_decision):
        """Test that systems execute concurrently for Option A."""
        execution_times = {"system1": 0, "system2": 0}
        
        async def slow_avatar_response(*args, **kwargs):
            start = time.time()
            await asyncio.sleep(0.2)  # 200ms
            execution_times["system1"] = time.time() - start
            return True
        
        async def slow_analysis(*args, **kwargs):
            start = time.time()
            await asyncio.sleep(0.3)  # 300ms
            execution_times["system2"] = time.time() - start
            return "task-id"
        
        executor_node.system1_interface.trigger_avatar_response = AsyncMock(
            side_effect=slow_avatar_response
        )
        executor_node.system2_interface.submit_for_analysis = AsyncMock(
            side_effect=slow_analysis
        )
        
        start_time = time.time()
        result = await executor_node.process(sample_routing_decision)
        total_time = time.time() - start_time
        
        assert result.success is True
        # Total time should be close to max(200ms, 300ms) = 300ms, not sum (500ms)
        assert total_time < 0.4  # Allow some overhead
        assert execution_times["system1"] >= 0.2
        assert execution_times["system2"] >= 0.3
    
    @pytest.mark.asyncio
    async def test_partial_success_handling(self, executor_node, sample_routing_decision):
        """Test handling when one system succeeds and another fails."""
        # Make System1 fail
        executor_node.system1_interface.trigger_avatar_response = AsyncMock(
            side_effect=Exception("Avatar service error")
        )
        
        # Adjust success criteria to allow partial success
        sample_routing_decision.execution_plan.success_criteria = {"min_systems_success": 1}
        
        result = await executor_node.process(sample_routing_decision)
        
        # Should be partial success
        assert result.success is True  # Because min_systems_success = 1
        assert result.results["system1"]["success"] is False
        assert result.results["system2"]["success"] is True
        assert "partial_success" in result.metadata
        assert result.metadata["successful_systems"] == ["system2"]
        assert result.metadata["failed_systems"] == ["system1"]
    
    # Test Retry Logic
    
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, executor_node):
        """Test retry logic with exponential backoff."""
        call_count = 0
        call_times = []
        
        async def failing_analysis(*args, **kwargs):
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Connection failed (attempt {call_count})")
            return "success-task-id"
        
        executor_node.system2_interface.submit_for_analysis = AsyncMock(
            side_effect=failing_analysis
        )
        
        routing_decision = RoutingDecision(
            stimuli_id="retry-test",
            decision=ProcessingDecision.ANALYSIS_ONLY,
            execution_plan=ExecutionPlan(
                decision=ProcessingDecision.ANALYSIS_ONLY,
                target_systems=["system2"],
                execution_order="sequential",
                timeout_settings={"system2": 30.0},
                retry_policies={
                    "system2": RetryPolicy(
                        max_attempts=3,
                        backoff_factor=2.0,
                        initial_delay=0.1
                    )
                },
                success_criteria={"min_systems_success": 1}
            ),
            confidence_score=0.8,
            reasoning="Testing retry"
        )
        
        result = await executor_node.process(routing_decision)
        
        assert result.success is True
        assert call_count == 3
        assert result.results["system2"]["retry_count"] == 2
        
        # Verify exponential backoff timing
        if len(call_times) >= 3:
            first_retry_delay = call_times[1] - call_times[0]
            second_retry_delay = call_times[2] - call_times[1]
            # Second delay should be approximately 2x the first (with some tolerance)
            assert 1.5 <= (second_retry_delay / first_retry_delay) <= 2.5
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, executor_node):
        """Test behavior when all retries are exhausted."""
        async def always_failing(*args, **kwargs):
            raise ConnectionError("Permanent failure")
        
        executor_node.system2_interface.submit_for_analysis = AsyncMock(
            side_effect=always_failing
        )
        
        routing_decision = RoutingDecision(
            stimuli_id="retry-fail",
            decision=ProcessingDecision.ANALYSIS_ONLY,
            execution_plan=ExecutionPlan(
                decision=ProcessingDecision.ANALYSIS_ONLY,
                target_systems=["system2"],
                execution_order="sequential",
                timeout_settings={"system2": 30.0},
                retry_policies={
                    "system2": RetryPolicy(max_attempts=2, backoff_factor=1.0)
                },
                success_criteria={"min_systems_success": 1}
            ),
            confidence_score=0.8,
            reasoning="Testing retry exhaustion"
        )
        
        result = await executor_node.process(routing_decision)
        
        assert result.success is False
        assert result.results["system2"]["success"] is False
        assert result.results["system2"]["retry_count"] == 2
        assert "Permanent failure" in result.error_details
    
    # Test Error Aggregation
    
    @pytest.mark.asyncio
    async def test_error_aggregation_multiple_failures(self, executor_node, sample_routing_decision):
        """Test error aggregation when multiple systems fail."""
        executor_node.system1_interface.trigger_avatar_response = AsyncMock(
            side_effect=ValueError("Invalid avatar state")
        )
        executor_node.system2_interface.submit_for_analysis = AsyncMock(
            side_effect=RuntimeError("Agent pool exhausted")
        )
        
        # Require both systems to succeed
        sample_routing_decision.execution_plan.success_criteria = {"min_systems_success": 2}
        
        result = await executor_node.process(sample_routing_decision)
        
        assert result.success is False
        assert len(result.metadata["errors"]) == 2
        assert any("Invalid avatar state" in str(e) for e in result.metadata["errors"])
        assert any("Agent pool exhausted" in str(e) for e in result.metadata["errors"])
        assert result.error_details is not None
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, executor_node, sample_routing_decision):
        """Test timeout handling for slow operations."""
        async def very_slow_operation(*args, **kwargs):
            await asyncio.sleep(5.0)  # 5 seconds
            return True
        
        executor_node.system1_interface.trigger_avatar_response = AsyncMock(
            side_effect=very_slow_operation
        )
        
        # Set short timeout
        sample_routing_decision.execution_plan.timeout_settings["system1"] = 0.5
        
        result = await executor_node.process(sample_routing_decision)
        
        # Should handle timeout gracefully
        assert result.results["system1"]["success"] is False
        assert "timeout" in result.results["system1"]["error"].lower()
        assert result.results["system2"]["success"] is True  # Other system should still work
    
    # Test Complex Scenarios
    
    @pytest.mark.asyncio
    async def test_mixed_execution_order(self, executor_node):
        """Test mixed sequential and parallel execution."""
        routing_decision = RoutingDecision(
            stimuli_id="mixed-test",
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            execution_plan=ExecutionPlan(
                decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
                target_systems=["system1", "system2", "external"],
                execution_order="mixed",
                timeout_settings={
                    "system1": 10.0,
                    "system2": 20.0,
                    "external": 15.0
                },
                retry_policies={
                    "system1": RetryPolicy(max_attempts=2),
                    "system2": RetryPolicy(max_attempts=3),
                    "external": RetryPolicy(max_attempts=1)
                },
                success_criteria={"min_systems_success": 2},
                metadata={
                    "execution_groups": [
                        {"systems": ["system1", "system2"], "type": "parallel"},
                        {"systems": ["external"], "type": "sequential"}
                    ]
                }
            ),
            confidence_score=0.85,
            reasoning="Complex execution pattern"
        )
        
        # Mock external system
        mock_external = AsyncMock(return_value={"status": "processed"})
        with patch.object(executor_node, '_execute_external_api', mock_external):
            result = await executor_node.process(routing_decision)
            
            assert result.success is True
            assert len(result.results) == 3
            mock_external.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check(self, executor_node):
        """Test executor health check functionality."""
        health = await executor_node.health_check()
        
        assert health["healthy"] is True
        assert health["component"] == "ExecutionCoordinatorNode"
        assert "system1_available" in health
        assert "system2_available" in health
        assert "config" in health
        assert health["config"]["max_concurrent_executions"] == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_limit(self, executor_node):
        """Test enforcement of concurrent execution limits."""
        executor_node.config.max_concurrent_executions = 2
        
        # Create multiple routing decisions
        decisions = []
        for i in range(5):
            decisions.append(RoutingDecision(
                stimuli_id=f"concurrent-{i}",
                decision=ProcessingDecision.ANALYSIS_ONLY,
                execution_plan=ExecutionPlan(
                    decision=ProcessingDecision.ANALYSIS_ONLY,
                    target_systems=["system2"],
                    execution_order="sequential",
                    timeout_settings={"system2": 30.0},
                    retry_policies={},
                    success_criteria={"min_systems_success": 1}
                ),
                confidence_score=0.8,
                reasoning=f"Concurrent test {i}"
            ))
        
        # Track concurrent executions
        max_concurrent = 0
        current_concurrent = 0
        
        async def track_concurrent(*args, **kwargs):
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.1)  # Simulate work
            current_concurrent -= 1
            return "task-id"
        
        executor_node.system2_interface.submit_for_analysis = AsyncMock(
            side_effect=track_concurrent
        )
        
        # Execute all decisions concurrently
        results = await asyncio.gather(*[
            executor_node.process(decision) for decision in decisions
        ])
        
        assert all(r.success for r in results)
        assert max_concurrent <= 2  # Should respect limit
    
    @pytest.mark.asyncio
    async def test_execution_metrics_collection(self, executor_node, sample_routing_decision):
        """Test that execution metrics are properly collected."""
        result = await executor_node.process(sample_routing_decision)
        
        assert result.success is True
        assert result.execution_time > 0
        assert "performance_metrics" in result.metadata
        
        metrics = result.metadata["performance_metrics"]
        assert "system1_latency" in metrics
        assert "system2_latency" in metrics
        assert "total_execution_time" in metrics
        assert metrics["total_execution_time"] == result.execution_time


class TestExecutionPlanValidation:
    """Test execution plan validation and adjustment."""
    
    @pytest.fixture
    def executor_node(self):
        """Create basic executor node."""
        mock_s1 = Mock(spec=System1Interface)
        mock_s2 = Mock(spec=System2Interface)
        config = ExecutorConfig()
        return ExecutionCoordinatorNode(mock_s1, mock_s2, config)
    
    def test_validate_execution_plan_valid(self, executor_node):
        """Test validation of valid execution plan."""
        plan = ExecutionPlan(
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            target_systems=["system1", "system2"],
            execution_order="parallel",
            timeout_settings={"system1": 10.0, "system2": 20.0},
            retry_policies={
                "system1": RetryPolicy(max_attempts=3),
                "system2": RetryPolicy(max_attempts=3)
            },
            success_criteria={"min_systems_success": 1}
        )
        
        is_valid, errors = executor_node._validate_execution_plan(plan)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_execution_plan_missing_timeouts(self, executor_node):
        """Test validation catches missing timeout settings."""
        plan = ExecutionPlan(
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            target_systems=["system1", "system2"],
            execution_order="parallel",
            timeout_settings={"system1": 10.0},  # Missing system2
            retry_policies={},
            success_criteria={}
        )
        
        is_valid, errors = executor_node._validate_execution_plan(plan)
        
        assert is_valid is False
        assert any("timeout" in e.lower() for e in errors)
    
    def test_adjust_plan_for_unavailable_system(self, executor_node):
        """Test plan adjustment when a system is unavailable."""
        executor_node.system1_interface.check_system_availability = AsyncMock(
            return_value={"available": False}
        )
        
        plan = ExecutionPlan(
            decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
            target_systems=["system1", "system2"],
            execution_order="parallel",
            timeout_settings={"system1": 10.0, "system2": 20.0},
            retry_policies={},
            success_criteria={"min_systems_success": 2}
        )
        
        adjusted_plan = asyncio.run(executor_node._adjust_plan_for_availability(plan))
        
        assert "system1" not in adjusted_plan.target_systems
        assert adjusted_plan.success_criteria["min_systems_success"] == 1
        assert "system1_unavailable" in adjusted_plan.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])