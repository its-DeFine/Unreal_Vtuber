"""
Integration tests for the GraphFlow External Stimuli System.

Tests GraphFlow pipeline integration, system boundary interactions,
and performance under load.
"""

import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import random
import statistics

from src.models.stimuli import (
    ExternalStimuli,
    StimuliCategory,
    Priority,
    ProcessingResult
)
from src.gateway.gateway_agent import GraphFlowGatewayAgent, GraphFlowConfig
from src.gateway.flows.stimuli_flow import StimuliFlowManager
from src.config.settings import (
    System1Config,
    System2Config,
    CategorizerConfig,
    AnalyzerConfig,
    RouterConfig,
    ExecutorConfig
)
from src.integrations.system1_interface import System1Interface
from src.integrations.system2_interface import System2Interface
from src.services.context_service import ContextService
from src.utils.llm_client import LLMClient


class TestGraphFlowPipelineIntegration:
    """Test complete GraphFlow pipeline integration."""
    
    @pytest.fixture
    async def integrated_gateway(self):
        """Create gateway with real components (mocked external systems only)."""
        config = GraphFlowConfig(
            max_concurrent_stimuli=50,
            processing_timeout=30.0,
            llm_provider="mock",
            llm_model="test-model",
            categorization_confidence_threshold=0.7,
            context_analysis_depth="standard"
        )
        
        agent = GraphFlowGatewayAgent(config)
        
        # Mock only external system interfaces
        agent.system1_interface = Mock(spec=System1Interface)
        agent.system1_interface.check_system_availability = AsyncMock(
            return_value={"available": True, "status": "idle"}
        )
        agent.system1_interface.trigger_avatar_response = AsyncMock(return_value=True)
        agent.system1_interface.get_current_status = AsyncMock(
            return_value={"is_speaking": False, "is_idle": True}
        )
        agent.system1_interface.estimate_processing_time = AsyncMock(return_value=1.5)
        
        agent.system2_interface = Mock(spec=System2Interface)
        agent.system2_interface.get_agent_status = AsyncMock(
            return_value={"agent1": "ready", "agent2": "ready"}
        )
        agent.system2_interface.submit_for_analysis = AsyncMock(
            return_value="analysis-task-123"
        )
        agent.system2_interface.trigger_evolution_analysis = AsyncMock(return_value=True)
        
        # Initialize with real flow manager
        await agent.initialize()
        
        yield agent
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_full_pipeline_user_interaction(self, integrated_gateway):
        """Test full pipeline with user interaction stimuli."""
        stimuli = ExternalStimuli(
            content="Hello! Can you tell me about artificial intelligence?",
            source="user_chat",
            priority=Priority.MEDIUM,
            metadata={"user_id": "test_user_123", "platform": "web"}
        )
        
        result = await integrated_gateway.process_stimuli(stimuli)
        
        # Verify full pipeline execution
        assert result.success is True
        assert result.stimuli_id == stimuli.id
        assert result.decision in [
            "AVATAR_AND_ANALYSIS",
            "ANALYSIS_ONLY"
        ]
        assert result.processing_time > 0
        assert result.processing_time < 30.0  # Within timeout
        
        # Verify system interfaces were called appropriately
        if result.decision == "AVATAR_AND_ANALYSIS":
            integrated_gateway.system1_interface.trigger_avatar_response.assert_called()
            integrated_gateway.system2_interface.submit_for_analysis.assert_called()
        else:
            integrated_gateway.system2_interface.submit_for_analysis.assert_called()
    
    @pytest.mark.asyncio
    async def test_full_pipeline_admin_command(self, integrated_gateway):
        """Test full pipeline with admin command stimuli."""
        stimuli = ExternalStimuli(
            content="Set avatar hair color to blue and update personality to cheerful",
            source="admin_console",
            priority=Priority.HIGH,
            metadata={"admin_id": "admin_001", "command_type": "avatar_config"}
        )
        
        result = await integrated_gateway.process_stimuli(stimuli)
        
        assert result.success is True
        assert result.decision == "AVATAR_AND_ANALYSIS"  # Admin commands should trigger both
        assert "confidence" in result.metadata
        assert result.metadata["confidence"] >= 0.8  # High confidence for admin commands
    
    @pytest.mark.asyncio
    async def test_full_pipeline_system_notification(self, integrated_gateway):
        """Test full pipeline with system notification stimuli."""
        stimuli = ExternalStimuli(
            content="Avatar state changed to speaking",
            source="system",
            priority=Priority.HIGH,
            metadata={"event_type": "avatar_state_change", "new_state": "speaking"}
        )
        
        result = await integrated_gateway.process_stimuli(stimuli)
        
        assert result.success is True
        # System notifications about avatar state should be analyzed
        assert result.decision in ["ANALYSIS_ONLY", "LOG_ONLY"]
        assert "system_notification" in str(result.metadata).lower()
    
    @pytest.mark.asyncio
    async def test_pipeline_error_propagation(self, integrated_gateway):
        """Test error propagation through the pipeline."""
        # Make System2 fail
        integrated_gateway.system2_interface.submit_for_analysis.side_effect = \
            RuntimeError("Agent pool exhausted")
        
        stimuli = ExternalStimuli(
            content="Test error handling",
            source="test",
            priority=Priority.MEDIUM
        )
        
        result = await integrated_gateway.process_stimuli(stimuli)
        
        # Should handle error gracefully
        assert result.success is False or result.metadata.get("partial_success") is True
        assert "error" in result.error_details.lower() or "error" in str(result.metadata).lower()
    
    @pytest.mark.asyncio
    async def test_pipeline_concurrent_categories(self, integrated_gateway):
        """Test pipeline handling different stimuli categories concurrently."""
        stimuli_list = [
            ExternalStimuli(
                content="How's the weather today?",
                source="user_chat",
                priority=Priority.MEDIUM
            ),
            ExternalStimuli(
                content="Set avatar mood to happy",
                source="admin_console",
                priority=Priority.HIGH
            ),
            ExternalStimuli(
                content="New follower: @testuser",
                source="twitter",
                priority=Priority.LOW
            ),
            ExternalStimuli(
                content="Background context update from news feed",
                source="rss_feed",
                priority=Priority.LOW
            ),
            ExternalStimuli(
                content="URGENT: High CPU usage detected!",
                source="monitoring",
                priority=Priority.CRITICAL
            )
        ]
        
        # Process all concurrently
        results = await asyncio.gather(*[
            integrated_gateway.process_stimuli(s) for s in stimuli_list
        ], return_exceptions=True)
        
        # Verify all processed successfully
        assert len(results) == len(stimuli_list)
        
        # Check appropriate decisions for each type
        for stimuli, result in zip(stimuli_list, results):
            if isinstance(result, Exception):
                pytest.fail(f"Processing failed for {stimuli.source}: {result}")
            
            assert isinstance(result, ProcessingResult)
            
            # Verify decision logic
            if stimuli.source == "monitoring" and stimuli.priority == Priority.CRITICAL:
                assert result.decision in ["EMERGENCY_OVERRIDE", "AVATAR_AND_ANALYSIS"]
            elif stimuli.source == "admin_console":
                assert result.decision in ["AVATAR_AND_ANALYSIS", "ANALYSIS_ONLY"]
            elif stimuli.source in ["rss_feed"]:
                assert result.decision in ["LOG_ONLY", "ANALYSIS_ONLY"]


class TestSystemBoundaryInteractions:
    """Test interactions at system boundaries."""
    
    @pytest.fixture
    def mock_context_service(self):
        """Create mock context service."""
        service = Mock(spec=ContextService)
        service.get_system_state = AsyncMock(return_value={
            "is_speaking": False,
            "is_idle": True,
            "is_busy": False,
            "has_errors": False,
            "queue_size": 0,
            "resource_utilization": {"cpu": 0.3, "memory": 0.4}
        })
        service.get_user_context = AsyncMock(return_value={
            "interaction_frequency": 5.0,
            "engagement_level": "medium",
            "recent_topics": [],
            "user_preference_match": 0.7,
            "historical_response_patterns": {}
        })
        service.get_environmental_context = AsyncMock(return_value={
            "autonomous_mode_active": True,
            "streaming_status": "live",
            "time_of_day_factor": 0.6,
            "recent_activity_level": "moderate",
            "external_event_context": {}
        })
        service.get_resource_availability = AsyncMock(return_value={
            "cpu_availability": 0.7,
            "memory_availability": 0.6,
            "agent_availability": {"all": True},
            "system1_availability": True,
            "system2_availability": True,
            "estimated_processing_capacity": 50
        })
        return service
    
    @pytest.mark.asyncio
    async def test_system1_boundary_avatar_commands(self):
        """Test System1 boundary for avatar commands."""
        interface = System1Interface(System1Config(
            vtuber_endpoint="http://test:5001",
            tts_endpoint="http://test:5001/tts"
        ))
        
        # Mock HTTP client
        interface._client = Mock()
        interface._client.post = AsyncMock(return_value=Mock(
            status_code=200,
            json=lambda: {"success": True, "message": "Avatar activated"}
        ))
        
        # Test avatar response trigger
        success = await interface.trigger_avatar_response(
            "Hello everyone!",
            {"emotion": "happy", "gesture": "wave"}
        )
        
        assert success is True
        interface._client.post.assert_called_with(
            "http://test:5001/speak",
            json={
                "text": "Hello everyone!",
                "metadata": {"emotion": "happy", "gesture": "wave"}
            }
        )
    
    @pytest.mark.asyncio
    async def test_system2_boundary_agent_submission(self):
        """Test System2 boundary for agent submission."""
        interface = System2Interface(System2Config(
            autogen_endpoint="http://test:3100",
            cognee_endpoint="http://test:8000"
        ))
        
        # Mock HTTP client
        interface._client = Mock()
        interface._client.post = AsyncMock(return_value=Mock(
            status_code=200,
            json=lambda: {"task_id": "agent-task-789", "status": "queued"}
        ))
        
        # Create analyzed stimuli
        from src.models.context import AnalyzedStimuli
        stimuli = Mock(spec=AnalyzedStimuli)
        stimuli.to_dict = Mock(return_value={
            "id": "test-123",
            "content": "Test content",
            "category": "USER_INTERACTION"
        })
        
        # Test submission
        task_id = await interface.submit_for_analysis(stimuli)
        
        assert task_id == "agent-task-789"
        interface._client.post.assert_called()
    
    @pytest.mark.asyncio
    async def test_context_service_boundary(self, mock_context_service):
        """Test context service boundary interactions."""
        # Test aggregated context retrieval
        system_state = await mock_context_service.get_system_state()
        assert system_state["is_idle"] is True
        
        user_context = await mock_context_service.get_user_context("user123")
        assert user_context["engagement_level"] == "medium"
        
        env_context = await mock_context_service.get_environmental_context()
        assert env_context["streaming_status"] == "live"
        
        resources = await mock_context_service.get_resource_availability()
        assert resources["cpu_availability"] == 0.7
    
    @pytest.mark.asyncio
    async def test_external_api_boundary(self):
        """Test external API boundary for stimuli submission."""
        from src.integrations.models import ExternalStimuliRequest
        
        # Create API request
        request = ExternalStimuliRequest(
            content="External API test",
            source="api_client",
            priority="high",
            metadata={"api_key": "test_key", "client_version": "1.0"}
        )
        
        # Verify serialization
        data = request.dict()
        assert data["content"] == "External API test"
        assert data["priority"] == "high"
        assert data["metadata"]["client_version"] == "1.0"


class TestPerformanceUnderLoad:
    """Test system performance under various load conditions."""
    
    @pytest.fixture
    async def load_test_gateway(self):
        """Create gateway configured for load testing."""
        config = GraphFlowConfig(
            max_concurrent_stimuli=100,
            processing_timeout=10.0,
            llm_provider="mock",
            metrics_enabled=True,
            performance_tracking=True
        )
        
        agent = GraphFlowGatewayAgent(config)
        
        # Mock external systems for consistent performance
        agent.system1_interface = Mock(spec=System1Interface)
        agent.system1_interface.check_system_availability = AsyncMock(
            return_value={"available": True}
        )
        agent.system1_interface.trigger_avatar_response = AsyncMock(
            side_effect=lambda *args: asyncio.sleep(0.1)  # 100ms latency
        )
        
        agent.system2_interface = Mock(spec=System2Interface)
        agent.system2_interface.submit_for_analysis = AsyncMock(
            side_effect=lambda *args: asyncio.sleep(0.2)  # 200ms latency
        )
        agent.system2_interface.get_agent_status = AsyncMock(
            return_value={"agents": "ready"}
        )
        
        await agent.initialize()
        yield agent
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_sustained_load(self, load_test_gateway):
        """Test sustained load over time."""
        num_stimuli = 100
        duration = 5.0  # 5 seconds
        
        stimuli_list = []
        for i in range(num_stimuli):
            stimuli_list.append(ExternalStimuli(
                content=f"Load test message {i}",
                source="load_test",
                priority=random.choice([Priority.LOW, Priority.MEDIUM, Priority.HIGH])
            ))
        
        start_time = time.time()
        results = []
        
        # Send stimuli at a steady rate
        for stimuli in stimuli_list:
            if time.time() - start_time > duration:
                break
            
            task = asyncio.create_task(load_test_gateway.process_stimuli(stimuli))
            results.append(task)
            await asyncio.sleep(duration / num_stimuli)  # Steady rate
        
        # Wait for all to complete
        completed_results = await asyncio.gather(*results, return_exceptions=True)
        
        # Analyze results
        successful = sum(1 for r in completed_results 
                        if isinstance(r, ProcessingResult) and r.success)
        failed = len(completed_results) - successful
        
        processing_times = [
            r.processing_time for r in completed_results 
            if isinstance(r, ProcessingResult) and r.success
        ]
        
        # Performance assertions
        assert successful / len(completed_results) >= 0.95  # 95% success rate
        assert statistics.mean(processing_times) < 2.0  # Average < 2 seconds
        assert max(processing_times) < 5.0  # No extreme outliers
    
    @pytest.mark.asyncio
    async def test_burst_load(self, load_test_gateway):
        """Test handling of sudden burst load."""
        burst_size = 50
        
        # Create burst of stimuli
        burst_stimuli = [
            ExternalStimuli(
                content=f"Burst message {i}",
                source="burst_test",
                priority=Priority.HIGH  # All high priority
            ) for i in range(burst_size)
        ]
        
        # Send all at once
        start_time = time.time()
        results = await asyncio.gather(*[
            load_test_gateway.process_stimuli(s) for s in burst_stimuli
        ], return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify handling
        successful = sum(1 for r in results 
                        if isinstance(r, ProcessingResult) and r.success)
        
        assert successful >= burst_size * 0.9  # 90% success under burst
        assert total_time < 10.0  # Completed within reasonable time
        
        # Check for rate limiting or queueing behavior
        processing_times = [
            r.processing_time for r in results 
            if isinstance(r, ProcessingResult) and r.success
        ]
        
        # Some should process quickly, others may queue
        assert min(processing_times) < 1.0
        assert statistics.stdev(processing_times) > 0.1  # Some variance expected
    
    @pytest.mark.asyncio
    async def test_mixed_priority_load(self, load_test_gateway):
        """Test load with mixed priorities."""
        stimuli_by_priority = {
            Priority.CRITICAL: [],
            Priority.HIGH: [],
            Priority.MEDIUM: [],
            Priority.LOW: []
        }
        
        # Create stimuli with different priorities
        for priority in stimuli_by_priority:
            for i in range(10):
                stimuli = ExternalStimuli(
                    content=f"{priority.name} priority message {i}",
                    source="priority_test",
                    priority=priority
                )
                stimuli_by_priority[priority].append(stimuli)
        
        # Flatten and shuffle
        all_stimuli = []
        for priority_list in stimuli_by_priority.values():
            all_stimuli.extend(priority_list)
        random.shuffle(all_stimuli)
        
        # Process all
        start_times = {}
        end_times = {}
        
        async def process_and_track(stim):
            start_times[stim.id] = time.time()
            result = await load_test_gateway.process_stimuli(stim)
            end_times[stim.id] = time.time()
            return result
        
        results = await asyncio.gather(*[
            process_and_track(s) for s in all_stimuli
        ])
        
        # Analyze priority handling
        avg_wait_by_priority = {}
        for priority, stimuli_list in stimuli_by_priority.items():
            wait_times = [
                end_times[s.id] - start_times[s.id] 
                for s in stimuli_list if s.id in end_times
            ]
            avg_wait_by_priority[priority] = statistics.mean(wait_times)
        
        # Higher priority should generally process faster
        assert avg_wait_by_priority[Priority.CRITICAL] < avg_wait_by_priority[Priority.LOW]
        assert avg_wait_by_priority[Priority.HIGH] < avg_wait_by_priority[Priority.MEDIUM]
    
    @pytest.mark.asyncio
    async def test_memory_stability(self, load_test_gateway):
        """Test memory stability under sustained load."""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process many stimuli
        for batch in range(10):
            stimuli_batch = [
                ExternalStimuli(
                    content=f"Memory test batch {batch} item {i}",
                    source="memory_test"
                ) for i in range(100)
            ]
            
            results = await asyncio.gather(*[
                load_test_gateway.process_stimuli(s) for s in stimuli_batch
            ])
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0.1)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 100MB for this test)
        assert memory_growth < 100, f"Memory grew by {memory_growth}MB"


class TestEdgeCasesAndErrorScenarios:
    """Test edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_malformed_stimuli_handling(self, integrated_gateway):
        """Test handling of malformed stimuli."""
        test_cases = [
            # Empty content
            ExternalStimuli(content="", source="test"),
            # Very long content
            ExternalStimuli(content="x" * 100000, source="test"),
            # Special characters
            ExternalStimuli(content="🚀💻🤖\n\t\r", source="test"),
            # Null-like values
            ExternalStimuli(content="null", source="test"),
            ExternalStimuli(content="None", source="test"),
            ExternalStimuli(content="undefined", source="test"),
        ]
        
        for stimuli in test_cases:
            result = await integrated_gateway.process_stimuli(stimuli)
            
            # Should handle gracefully
            assert isinstance(result, ProcessingResult)
            assert result.stimuli_id == stimuli.id
            # May fail validation or process with low confidence
            if not result.success:
                assert result.error_details is not None
    
    @pytest.mark.asyncio
    async def test_system_recovery_after_failure(self, integrated_gateway):
        """Test system recovery after failures."""
        # First, make system fail
        integrated_gateway.system1_interface.trigger_avatar_response.side_effect = \
            Exception("System failure")
        
        stimuli1 = ExternalStimuli(content="This should fail", source="test")
        result1 = await integrated_gateway.process_stimuli(stimuli1)
        
        # Should handle failure
        assert result1.success is False or result1.metadata.get("partial_success")
        
        # Restore system
        integrated_gateway.system1_interface.trigger_avatar_response.side_effect = None
        integrated_gateway.system1_interface.trigger_avatar_response.return_value = True
        
        # System should recover
        stimuli2 = ExternalStimuli(content="This should work", source="test")
        result2 = await integrated_gateway.process_stimuli(stimuli2)
        
        # May succeed or use degraded mode
        assert isinstance(result2, ProcessingResult)
    
    @pytest.mark.asyncio
    async def test_timeout_cascade_prevention(self, integrated_gateway):
        """Test prevention of timeout cascades."""
        # Make System1 very slow
        async def very_slow_response(*args):
            await asyncio.sleep(60)  # 60 seconds
            return True
        
        integrated_gateway.system1_interface.trigger_avatar_response = AsyncMock(
            side_effect=very_slow_response
        )
        
        # Process multiple stimuli
        stimuli_list = [
            ExternalStimuli(content=f"Timeout test {i}", source="test")
            for i in range(5)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*[
            integrated_gateway.process_stimuli(s) for s in stimuli_list
        ], return_exceptions=True)
        total_time = time.time() - start_time
        
        # All should timeout independently, not cascade
        assert total_time < 35  # Should not be 5 * 30 seconds
        
        # Should handle timeouts gracefully
        for result in results:
            if isinstance(result, ProcessingResult):
                if not result.success:
                    assert "timeout" in result.error_details.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])