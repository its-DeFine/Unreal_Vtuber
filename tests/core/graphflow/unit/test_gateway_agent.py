"""
Unit tests for the GraphFlowGatewayAgent.

Tests end-to-end processing, concurrent stimuli handling,
graceful degradation, and metrics collection.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid

from src.models.stimuli import (
    ExternalStimuli,
    StimuliCategory,
    Priority,
    ProcessingResult
)
from src.gateway.gateway_agent import (
    GraphFlowGatewayAgent,
    GraphFlowConfig
)
from src.gateway.flows.stimuli_flow import StimuliFlowManager
from src.integrations.system1_interface import System1Interface
from src.integrations.system2_interface import System2Interface
from src.utils.metrics import MetricsCollector
from src.utils.logging import get_structured_logger


class TestGraphFlowGatewayAgent:
    """Test suite for GraphFlowGatewayAgent."""
    
    @pytest.fixture
    def gateway_config(self):
        """Create gateway configuration."""
        return GraphFlowConfig(
            max_concurrent_stimuli=50,
            processing_timeout=30.0,
            retry_attempts=3,
            llm_provider="ollama",
            llm_model="llama3.2:3b",
            llm_temperature=0.3,
            categorization_confidence_threshold=0.8,
            context_analysis_depth="standard",
            metrics_enabled=True,
            detailed_logging=True,
            performance_tracking=True
        )
    
    @pytest.fixture
    def mock_flow_manager(self):
        """Create mock flow manager."""
        manager = Mock(spec=StimuliFlowManager)
        manager.process_stimuli = AsyncMock()
        manager.get_flow_status = AsyncMock(return_value={"active_flows": 0})
        return manager
    
    @pytest.fixture
    def mock_system1_interface(self):
        """Create mock System1 interface."""
        interface = Mock(spec=System1Interface)
        interface.check_system_availability = AsyncMock(
            return_value={"available": True, "status": "idle"}
        )
        interface.get_current_status = AsyncMock(
            return_value={"is_speaking": False, "is_idle": True}
        )
        return interface
    
    @pytest.fixture
    def mock_system2_interface(self):
        """Create mock System2 interface."""
        interface = Mock(spec=System2Interface)
        interface.get_agent_status = AsyncMock(
            return_value={"agent1": "ready", "agent2": "ready"}
        )
        return interface
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """Create mock metrics collector."""
        collector = Mock(spec=MetricsCollector)
        collector.record_processing_time = Mock()
        collector.increment_stimuli_processed = Mock()
        collector.record_categorization_accuracy = Mock()
        collector.update_system_health = Mock()
        return collector
    
    @pytest.fixture
    async def gateway_agent(self, gateway_config, mock_flow_manager, 
                           mock_system1_interface, mock_system2_interface,
                           mock_metrics_collector):
        """Create gateway agent for testing."""
        agent = GraphFlowGatewayAgent(gateway_config)
        
        # Inject mocks
        agent.flow_manager = mock_flow_manager
        agent.system1_interface = mock_system1_interface
        agent.system2_interface = mock_system2_interface
        agent.metrics_collector = mock_metrics_collector
        
        # Initialize
        await agent.initialize()
        
        yield agent
        
        # Cleanup
        await agent.shutdown()
    
    # Test End-to-End Processing
    
    @pytest.mark.asyncio
    async def test_process_stimuli_success(self, gateway_agent, mock_flow_manager):
        """Test successful end-to-end stimuli processing."""
        stimuli = ExternalStimuli(
            content="Hello, how are you today?",
            source="user_chat",
            priority=Priority.MEDIUM,
            metadata={"user_id": "user123"}
        )
        
        # Mock successful processing
        mock_flow_manager.process_stimuli.return_value = ProcessingResult(
            stimuli_id=stimuli.id,
            success=True,
            decision="AVATAR_AND_ANALYSIS",
            execution_results={
                "system1": {"success": True, "response": "Avatar activated"},
                "system2": {"success": True, "task_id": "task-123"}
            },
            processing_time=1.5,
            metadata={"confidence": 0.95}
        )
        
        result = await gateway_agent.process_stimuli(stimuli)
        
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.stimuli_id == stimuli.id
        assert result.decision == "AVATAR_AND_ANALYSIS"
        assert result.processing_time > 0
        
        # Verify flow manager was called
        mock_flow_manager.process_stimuli.assert_called_once_with(stimuli)
        
        # Verify metrics were recorded
        gateway_agent.metrics_collector.record_processing_time.assert_called()
        gateway_agent.metrics_collector.increment_stimuli_processed.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_stimuli_validation_failure(self, gateway_agent):
        """Test stimuli validation failure."""
        # Invalid stimuli with empty content
        stimuli = ExternalStimuli(
            content="",
            source="unknown"
        )
        
        result = await gateway_agent.process_stimuli(stimuli)
        
        assert result.success is False
        assert "validation" in result.error_details.lower()
        assert result.processing_time == 0
    
    @pytest.mark.asyncio
    async def test_process_stimuli_timeout(self, gateway_agent, mock_flow_manager):
        """Test processing timeout handling."""
        stimuli = ExternalStimuli(
            content="Test timeout",
            source="test"
        )
        
        # Mock slow processing
        async def slow_process(*args):
            await asyncio.sleep(35)  # Longer than timeout
            return ProcessingResult(stimuli_id=stimuli.id, success=True)
        
        mock_flow_manager.process_stimuli = AsyncMock(side_effect=slow_process)
        gateway_agent.config.processing_timeout = 1.0  # Short timeout
        
        result = await gateway_agent.process_stimuli(stimuli)
        
        assert result.success is False
        assert "timeout" in result.error_details.lower()
        assert result.processing_time >= 1.0
    
    # Test Concurrent Stimuli Handling
    
    @pytest.mark.asyncio
    async def test_concurrent_stimuli_processing(self, gateway_agent, mock_flow_manager):
        """Test handling multiple concurrent stimuli."""
        num_stimuli = 10
        stimuli_list = []
        
        for i in range(num_stimuli):
            stimuli_list.append(ExternalStimuli(
                content=f"Concurrent message {i}",
                source="bulk_test",
                priority=Priority.MEDIUM
            ))
        
        # Mock successful processing with varying times
        async def process_with_delay(stim):
            await asyncio.sleep(0.1)  # Small delay
            return ProcessingResult(
                stimuli_id=stim.id,
                success=True,
                decision="ANALYSIS_ONLY",
                processing_time=0.1
            )
        
        mock_flow_manager.process_stimuli = AsyncMock(side_effect=process_with_delay)
        
        # Process all stimuli concurrently
        results = await asyncio.gather(*[
            gateway_agent.process_stimuli(s) for s in stimuli_list
        ])
        
        assert len(results) == num_stimuli
        assert all(r.success for r in results)
        assert mock_flow_manager.process_stimuli.call_count == num_stimuli
    
    @pytest.mark.asyncio
    async def test_concurrent_limit_enforcement(self, gateway_agent, mock_flow_manager):
        """Test enforcement of concurrent processing limits."""
        gateway_agent.config.max_concurrent_stimuli = 3
        
        # Track concurrent executions
        max_concurrent = 0
        current_concurrent = 0
        
        async def track_concurrent(stim):
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.2)  # Simulate work
            current_concurrent -= 1
            return ProcessingResult(stimuli_id=stim.id, success=True)
        
        mock_flow_manager.process_stimuli = AsyncMock(side_effect=track_concurrent)
        
        # Create more stimuli than the limit
        stimuli_list = [
            ExternalStimuli(content=f"Test {i}", source="test")
            for i in range(10)
        ]
        
        # Process all stimuli
        results = await asyncio.gather(*[
            gateway_agent.process_stimuli(s) for s in stimuli_list
        ])
        
        assert all(r.success for r in results)
        assert max_concurrent <= 3  # Should respect limit
    
    # Test Graceful Degradation
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_system1_down(self, gateway_agent, 
                                                     mock_system1_interface,
                                                     mock_flow_manager):
        """Test graceful degradation when System1 is unavailable."""
        # Make System1 unavailable
        mock_system1_interface.check_system_availability.return_value = {
            "available": False,
            "status": "error",
            "reason": "Service unreachable"
        }
        
        stimuli = ExternalStimuli(
            content="User greeting message",
            source="user_chat",
            category_hint=StimuliCategory.USER_INTERACTION
        )
        
        # Mock flow manager to handle degraded mode
        mock_flow_manager.process_stimuli.return_value = ProcessingResult(
            stimuli_id=stimuli.id,
            success=True,
            decision="ANALYSIS_ONLY",  # Fallback to analysis only
            execution_results={
                "system2": {"success": True, "task_id": "task-456"}
            },
            processing_time=1.0,
            metadata={"degraded_mode": True, "reason": "system1_unavailable"}
        )
        
        result = await gateway_agent.process_stimuli(stimuli)
        
        assert result.success is True
        assert result.decision == "ANALYSIS_ONLY"
        assert result.metadata.get("degraded_mode") is True
        assert "system1_unavailable" in result.metadata.get("reason", "")
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_high_load(self, gateway_agent, mock_flow_manager):
        """Test graceful degradation under high load."""
        # Simulate high load conditions
        gateway_agent._active_requests = 45  # Near max capacity
        
        stimuli = ExternalStimuli(
            content="Low priority update",
            source="background",
            priority=Priority.LOW
        )
        
        # Mock degraded processing
        mock_flow_manager.process_stimuli.return_value = ProcessingResult(
            stimuli_id=stimuli.id,
            success=True,
            decision="LOG_ONLY",  # Degraded to log only
            processing_time=0.1,
            metadata={"degraded_mode": True, "reason": "high_load"}
        )
        
        result = await gateway_agent.process_stimuli(stimuli)
        
        assert result.success is True
        assert result.decision == "LOG_ONLY"
        assert result.metadata.get("reason") == "high_load"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_llm_failure(self, gateway_agent, mock_flow_manager):
        """Test graceful degradation when LLM is unavailable."""
        stimuli = ExternalStimuli(
            content="Test message",
            source="test"
        )
        
        # Mock LLM failure with fallback
        mock_flow_manager.process_stimuli.return_value = ProcessingResult(
            stimuli_id=stimuli.id,
            success=True,
            decision="ANALYSIS_ONLY",
            processing_time=0.8,
            metadata={
                "degraded_mode": True,
                "reason": "llm_unavailable",
                "fallback_method": "keyword_based"
            }
        )
        
        result = await gateway_agent.process_stimuli(stimuli)
        
        assert result.success is True
        assert result.metadata.get("fallback_method") == "keyword_based"
    
    # Test Metrics Collection
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, gateway_agent, mock_flow_manager, 
                                    mock_metrics_collector):
        """Test comprehensive metrics collection."""
        # Process multiple stimuli with different outcomes
        stimuli_results = [
            (ExternalStimuli(content="Success 1", source="test"), 
             ProcessingResult(stimuli_id="1", success=True, decision="AVATAR_AND_ANALYSIS",
                            processing_time=1.2, metadata={"confidence": 0.9})),
            (ExternalStimuli(content="Success 2", source="test"), 
             ProcessingResult(stimuli_id="2", success=True, decision="ANALYSIS_ONLY",
                            processing_time=0.8, metadata={"confidence": 0.85})),
            (ExternalStimuli(content="Failure", source="test"), 
             ProcessingResult(stimuli_id="3", success=False, error_details="Processing error",
                            processing_time=0.5))
        ]
        
        for stimuli, expected_result in stimuli_results:
            mock_flow_manager.process_stimuli.return_value = expected_result
            await gateway_agent.process_stimuli(stimuli)
        
        # Verify metrics were collected
        assert mock_metrics_collector.record_processing_time.call_count == 3
        assert mock_metrics_collector.increment_stimuli_processed.call_count == 3
        
        # Check recorded values
        processing_times = [
            call[0][0] for call in mock_metrics_collector.record_processing_time.call_args_list
        ]
        assert 1.2 in processing_times
        assert 0.8 in processing_times
        assert 0.5 in processing_times
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, gateway_agent):
        """Test metrics retrieval."""
        metrics = await gateway_agent.get_metrics()
        
        assert isinstance(metrics, dict)
        assert "total_processed" in metrics
        assert "success_rate" in metrics
        assert "average_processing_time" in metrics
        assert "current_active_requests" in metrics
        assert "system_health" in metrics
    
    # Test Health Check
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, gateway_agent, mock_system1_interface, 
                                       mock_system2_interface):
        """Test health check when all systems are healthy."""
        health = await gateway_agent.health_check()
        
        assert health["status"] == "healthy"
        assert health["gateway_agent"]["active"] is True
        assert health["system1"]["available"] is True
        assert health["system2"]["available"] is True
        assert health["flow_manager"]["status"] == "ready"
        assert "uptime" in health
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, gateway_agent, mock_system1_interface):
        """Test health check in degraded state."""
        # Make System1 unhealthy
        mock_system1_interface.check_system_availability.return_value = {
            "available": False,
            "status": "error"
        }
        
        health = await gateway_agent.health_check()
        
        assert health["status"] == "degraded"
        assert health["system1"]["available"] is False
        assert health["degraded_reasons"] is not None
        assert "system1" in health["degraded_reasons"]
    
    # Test Error Handling
    
    @pytest.mark.asyncio
    async def test_handle_processing_exception(self, gateway_agent, mock_flow_manager):
        """Test handling of processing exceptions."""
        stimuli = ExternalStimuli(content="Test", source="test")
        
        # Mock processing exception
        mock_flow_manager.process_stimuli.side_effect = RuntimeError("Flow processing failed")
        
        result = await gateway_agent.process_stimuli(stimuli)
        
        assert result.success is False
        assert "Flow processing failed" in result.error_details
        assert result.metadata.get("error_type") == "RuntimeError"
    
    @pytest.mark.asyncio
    async def test_handle_initialization_failure(self, gateway_config):
        """Test handling of initialization failures."""
        agent = GraphFlowGatewayAgent(gateway_config)
        
        # Mock initialization failure
        with patch.object(agent, '_initialize_flow_manager', 
                         side_effect=Exception("Init failed")):
            with pytest.raises(Exception) as exc_info:
                await agent.initialize()
            
            assert "Init failed" in str(exc_info.value)
    
    # Test Shutdown and Cleanup
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, gateway_agent, mock_flow_manager):
        """Test graceful shutdown with pending requests."""
        # Start some async processing
        pending_tasks = []
        
        async def slow_process(stim):
            await asyncio.sleep(0.5)
            return ProcessingResult(stimuli_id=stim.id, success=True)
        
        mock_flow_manager.process_stimuli = AsyncMock(side_effect=slow_process)
        
        # Start processing without waiting
        for i in range(3):
            stimuli = ExternalStimuli(content=f"Pending {i}", source="test")
            task = asyncio.create_task(gateway_agent.process_stimuli(stimuli))
            pending_tasks.append(task)
        
        # Give tasks time to start
        await asyncio.sleep(0.1)
        
        # Shutdown should wait for pending tasks
        await gateway_agent.shutdown()
        
        # All tasks should complete
        results = await asyncio.gather(*pending_tasks, return_exceptions=True)
        assert all(isinstance(r, ProcessingResult) for r in results)
    
    # Test Configuration Updates
    
    @pytest.mark.asyncio
    async def test_dynamic_config_update(self, gateway_agent):
        """Test dynamic configuration updates."""
        original_timeout = gateway_agent.config.processing_timeout
        original_max_concurrent = gateway_agent.config.max_concurrent_stimuli
        
        # Update configuration
        new_config = {
            "processing_timeout": 60.0,
            "max_concurrent_stimuli": 100,
            "llm_temperature": 0.5
        }
        
        await gateway_agent.update_config(new_config)
        
        assert gateway_agent.config.processing_timeout == 60.0
        assert gateway_agent.config.max_concurrent_stimuli == 100
        assert gateway_agent.config.llm_temperature == 0.5
        
        # Verify notification of config change
        assert gateway_agent._config_version > 1


class TestGatewayAgentIntegration:
    """Integration tests for gateway agent with real components."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self):
        """Test full pipeline with minimal mocking."""
        config = GraphFlowConfig(
            max_concurrent_stimuli=10,
            processing_timeout=5.0,
            llm_provider="mock",  # Use mock LLM
            metrics_enabled=False  # Disable metrics for test
        )
        
        agent = GraphFlowGatewayAgent(config)
        
        # Mock only external dependencies
        agent.system1_interface = Mock(spec=System1Interface)
        agent.system1_interface.check_system_availability = AsyncMock(
            return_value={"available": True}
        )
        agent.system1_interface.trigger_avatar_response = AsyncMock(return_value=True)
        
        agent.system2_interface = Mock(spec=System2Interface)
        agent.system2_interface.get_agent_status = AsyncMock(
            return_value={"agents": "ready"}
        )
        agent.system2_interface.submit_for_analysis = AsyncMock(return_value="task-id")
        
        try:
            await agent.initialize()
            
            # Test various stimuli types
            test_cases = [
                (ExternalStimuli(content="Hello!", source="user_chat"), 
                 StimuliCategory.USER_INTERACTION),
                (ExternalStimuli(content="Set avatar color to red", source="admin_console"), 
                 StimuliCategory.DIRECT_ADMIN),
                (ExternalStimuli(content="System update available", source="system"), 
                 StimuliCategory.CONTEXTUAL_UPDATE),
            ]
            
            for stimuli, expected_category in test_cases:
                result = await agent.process_stimuli(stimuli)
                
                # Basic assertions - full integration test would verify more
                assert result is not None
                assert result.stimuli_id == stimuli.id
                
        finally:
            await agent.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])