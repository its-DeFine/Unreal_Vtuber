"""
Test file for ExecutionCoordinatorNode.

This test verifies the basic functionality of the executor node including:
- Initialization
- Different execution options (A, B, C)
- Retry logic
- Emergency override handling
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from src.gateway.nodes.executor_node import ExecutionCoordinatorNode
from src.models.stimuli import RoutingDecision, AnalyzedStimuli, StimuliCategory, Priority
from src.models.decisions import (
    ProcessingDecision, ExecutionPlan, ExecutionPriority,
    RetryPolicy, ExecutionResult
)
from src.config.settings import ExecutorConfig, System1Config, System2Config
from src.utils.metrics import MetricsCollector


@pytest.fixture
def executor_config():
    """Create test executor configuration."""
    return ExecutorConfig(
        parallel_execution=True,
        max_parallel_tasks=5,
        execution_timeout=30.0,
        retry_failed_executions=True,
        max_retry_attempts=3,
        retry_delay=1.0,
        emergency_override_path="config/emergency_override.py"
    )


@pytest.fixture
def system1_config():
    """Create test System1 configuration."""
    return System1Config(
        vtuber_endpoint="http://test-vtuber:5001",
        tts_endpoint="http://test-vtuber:5001/tts"
    )


@pytest.fixture
def system2_config():
    """Create test System2 configuration."""
    return System2Config(
        autogen_endpoint="http://test-autogen:3100",
        cognee_endpoint="http://test-cognee:8000"
    )


@pytest.fixture
def mock_metrics():
    """Create mock metrics collector."""
    metrics = MagicMock(spec=MetricsCollector)
    metrics.increment_decision = MagicMock()
    metrics.increment_processing_errors = MagicMock()
    metrics.record_node_processing_time = MagicMock()
    metrics.set_execution_success_rate = MagicMock()
    return metrics


@pytest.fixture
async def executor_node(executor_config, system1_config, system2_config, mock_metrics):
    """Create executor node instance."""
    node = ExecutionCoordinatorNode(
        config=executor_config,
        system1_config=system1_config,
        system2_config=system2_config,
        metrics_collector=mock_metrics
    )
    
    # Initialize the node
    await node.initialize()
    
    # Mock system interfaces
    node.system1_interface = AsyncMock()
    node.system1_interface.trigger_avatar_response = AsyncMock(return_value=True)
    
    node.system2_interface = AsyncMock()
    node.system2_interface.submit_for_analysis = AsyncMock(return_value="test-task-id")
    
    yield node
    
    # Shutdown
    await node.shutdown()


def create_test_routing_decision(
    decision_type: ProcessingDecision = ProcessingDecision.AVATAR_AND_ANALYSIS
):
    """Create a test routing decision."""
    stimuli_id = str(uuid.uuid4())
    
    # Create analyzed stimuli
    analyzed_stimuli = AnalyzedStimuli(
        id=stimuli_id,
        content="Test stimuli content",
        source="test_source",
        category=StimuliCategory.USER_INTERACTION,
        confidence=0.9
    )
    
    # Create execution plan
    execution_plan = ExecutionPlan(
        id=str(uuid.uuid4()),
        stimuli_id=stimuli_id,
        decision=decision_type,
        target_systems=["system1", "system2"] if decision_type == ProcessingDecision.AVATAR_AND_ANALYSIS else ["system2"],
        execution_order=["parallel"],
        timeout_settings={"system1": 10.0, "system2": 20.0},
        retry_policies=[
            RetryPolicy(system="system1", max_attempts=2),
            RetryPolicy(system="system2", max_attempts=3)
        ],
        priority=ExecutionPriority.HIGH,
        parallel_execution=True,
        execution_params={
            "stimuli_content": analyzed_stimuli.content,
            "category": analyzed_stimuli.category.name,
            "confidence": analyzed_stimuli.confidence
        }
    )
    
    # Create routing decision
    routing_decision = RoutingDecision(
        stimuli_id=stimuli_id,
        decision=decision_type,
        execution_plan=execution_plan,
        confidence_score=0.85,
        reasoning="Test routing decision"
    )
    
    # Attach analyzed stimuli for easier access
    routing_decision.analyzed_stimuli = analyzed_stimuli
    
    return routing_decision


@pytest.mark.asyncio
async def test_executor_initialization(executor_node):
    """Test executor node initialization."""
    assert executor_node.is_initialized
    assert executor_node.system1_interface is not None
    assert executor_node.system2_interface is not None


@pytest.mark.asyncio
async def test_option_a_execution(executor_node, mock_metrics):
    """Test Option A: Avatar + Analysis concurrent execution."""
    # Create routing decision for Option A
    routing_decision = create_test_routing_decision(
        ProcessingDecision.AVATAR_AND_ANALYSIS
    )
    
    # Execute
    result = await executor_node.process(routing_decision)
    
    # Verify execution
    assert result.success
    assert "system1" in result.affected_systems
    assert "system2" in result.affected_systems
    
    # Verify both systems were called
    executor_node.system1_interface.trigger_avatar_response.assert_called_once()
    executor_node.system2_interface.submit_for_analysis.assert_called_once()
    
    # Verify metrics
    mock_metrics.increment_decision.assert_called_with("option_a")
    mock_metrics.set_execution_success_rate.assert_called()


@pytest.mark.asyncio
async def test_option_b_execution(executor_node, mock_metrics):
    """Test Option B: Analysis only execution."""
    # Create routing decision for Option B
    routing_decision = create_test_routing_decision(
        ProcessingDecision.ANALYSIS_ONLY
    )
    routing_decision.execution_plan.target_systems = ["system2"]
    
    # Execute
    result = await executor_node.process(routing_decision)
    
    # Verify execution
    assert result.success
    assert "system2" in result.affected_systems
    
    # Verify only System2 was called
    executor_node.system1_interface.trigger_avatar_response.assert_not_called()
    executor_node.system2_interface.submit_for_analysis.assert_called_once()
    
    # Verify metrics
    mock_metrics.increment_decision.assert_called_with("option_b")


@pytest.mark.asyncio
async def test_option_c_execution(executor_node, mock_metrics):
    """Test Option C: Log only execution."""
    # Create routing decision for Option C
    routing_decision = create_test_routing_decision(
        ProcessingDecision.LOG_ONLY
    )
    routing_decision.execution_plan.target_systems = ["log"]
    
    # Execute
    result = await executor_node.process(routing_decision)
    
    # Verify execution
    assert result.success
    assert "logging" in result.affected_systems
    
    # Verify no systems were called
    executor_node.system1_interface.trigger_avatar_response.assert_not_called()
    executor_node.system2_interface.submit_for_analysis.assert_not_called()
    
    # Verify metrics
    mock_metrics.increment_decision.assert_called_with("option_c")


@pytest.mark.asyncio
async def test_retry_logic(executor_node, mock_metrics):
    """Test retry logic with exponential backoff."""
    # Create routing decision
    routing_decision = create_test_routing_decision(
        ProcessingDecision.ANALYSIS_ONLY
    )
    
    # Make System2 fail twice, then succeed
    call_count = 0
    async def failing_submit(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Test connection error")
        return "test-task-id"
    
    executor_node.system2_interface.submit_for_analysis = AsyncMock(
        side_effect=failing_submit
    )
    
    # Execute
    result = await executor_node.process(routing_decision)
    
    # Verify execution succeeded after retries
    assert result.success
    assert result.retry_count == 2  # Two retries before success
    
    # Verify System2 was called 3 times
    assert call_count == 3


@pytest.mark.asyncio
async def test_emergency_override(executor_node, mock_metrics):
    """Test emergency override handling."""
    # Create routing decision for emergency
    routing_decision = create_test_routing_decision(
        ProcessingDecision.EMERGENCY_OVERRIDE
    )
    routing_decision.execution_plan.execution_params["emergency_type"] = "system_critical"
    
    # Mock emergency override file
    with patch('importlib.util.spec_from_file_location') as mock_spec:
        mock_module = MagicMock()
        mock_module.handle_emergency = AsyncMock(return_value=True)
        
        mock_spec.return_value = MagicMock()
        mock_spec.return_value.loader = MagicMock()
        
        with patch('importlib.util.module_from_spec', return_value=mock_module):
            # Execute
            result = await executor_node.process(routing_decision)
    
    # Verify execution
    assert result.success
    assert result.results.get("override") == "emergency"


@pytest.mark.asyncio
async def test_timeout_handling(executor_node, mock_metrics):
    """Test timeout handling."""
    # Create routing decision
    routing_decision = create_test_routing_decision(
        ProcessingDecision.AVATAR_AND_ANALYSIS
    )
    
    # Make System1 timeout
    async def slow_response(*args, **kwargs):
        await asyncio.sleep(15)  # Longer than timeout
        return True
    
    executor_node.system1_interface.trigger_avatar_response = AsyncMock(
        side_effect=slow_response
    )
    
    # Set short timeout
    routing_decision.execution_plan.timeout_settings["system1"] = 0.1
    
    # Execute
    result = await executor_node.process(routing_decision)
    
    # Should have partial success (System2 succeeded, System1 timed out)
    assert result.partial_success or not result.success
    
    # Verify error metrics
    mock_metrics.increment_processing_errors.assert_called()


@pytest.mark.asyncio
async def test_parallel_execution(executor_node):
    """Test parallel execution of multiple systems."""
    # Create routing decision
    routing_decision = create_test_routing_decision(
        ProcessingDecision.AVATAR_AND_ANALYSIS
    )
    
    # Track execution order
    execution_order = []
    
    async def track_system1(*args, **kwargs):
        execution_order.append("system1_start")
        await asyncio.sleep(0.1)
        execution_order.append("system1_end")
        return True
    
    async def track_system2(*args, **kwargs):
        execution_order.append("system2_start")
        await asyncio.sleep(0.05)
        execution_order.append("system2_end")
        return "test-task-id"
    
    executor_node.system1_interface.trigger_avatar_response = AsyncMock(
        side_effect=track_system1
    )
    executor_node.system2_interface.submit_for_analysis = AsyncMock(
        side_effect=track_system2
    )
    
    # Execute
    result = await executor_node.process(routing_decision)
    
    # Verify parallel execution (both start before either ends)
    assert execution_order.index("system1_start") < execution_order.index("system2_end")
    assert execution_order.index("system2_start") < execution_order.index("system1_end")
    assert result.success


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])