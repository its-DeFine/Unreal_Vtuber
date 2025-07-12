"""
Unit tests for the ContextAnalyzerNode.

Tests all 5 analysis dimensions:
1. System state (speaking, idle, busy, error)
2. User interaction history and patterns
3. Environmental context (autonomous mode, streaming)
4. Resource availability (CPU, memory, agent status)
5. Temporal factors (time of day, recent activity)
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.models.stimuli import (
    CategorizedStimuli,
    StimuliCategory,
    Priority
)
from src.models.context import (
    SystemStateAnalysis,
    UserContextAnalysis,
    EnvironmentalAnalysis,
    ResourceAnalysis,
    AnalyzedStimuli
)
from src.gateway.nodes.analyzer_node import (
    ContextAnalyzerNode,
    AnalyzerConfig
)
from src.services.context_service import ContextService


class TestContextAnalyzerNode:
    """Test suite for ContextAnalyzerNode."""
    
    @pytest.fixture
    def mock_context_service(self):
        """Create a mock context service."""
        service = Mock(spec=ContextService)
        service.get_system_state = AsyncMock()
        service.get_user_context = AsyncMock()
        service.get_environmental_context = AsyncMock()
        service.get_resource_availability = AsyncMock()
        service.save_analysis = AsyncMock()
        return service
    
    @pytest.fixture
    def analyzer_config(self):
        """Create analyzer configuration."""
        return AnalyzerConfig(
            analysis_depth="deep",
            enable_caching=True,
            cache_ttl=300,
            resource_check_interval=10.0,
            user_history_window=3600  # 1 hour
        )
    
    @pytest.fixture
    def analyzer_node(self, mock_context_service, analyzer_config):
        """Create analyzer node for testing."""
        return ContextAnalyzerNode(mock_context_service, analyzer_config)
    
    @pytest.fixture
    def sample_categorized_stimuli(self):
        """Create sample categorized stimuli."""
        return CategorizedStimuli(
            id="test-123",
            content="Hello, how are you today?",
            source="user_chat",
            category=StimuliCategory.USER_INTERACTION,
            confidence=0.95,
            priority=Priority.MEDIUM,
            metadata={"user_id": "user123"}
        )
    
    # Test System State Analysis (Dimension 1)
    
    @pytest.mark.asyncio
    async def test_analyze_system_state_speaking(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test system state analysis when avatar is speaking."""
        mock_context_service.get_system_state.return_value = {
            "is_speaking": True,
            "is_idle": False,
            "is_busy": False,
            "has_errors": False,
            "queue_size": 3,
            "resource_utilization": {"cpu": 0.6, "memory": 0.4},
            "avatar_status": "speaking"
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        assert isinstance(result, AnalyzedStimuli)
        assert result.system_state_analysis.is_speaking is True
        assert result.system_state_analysis.is_idle is False
        assert result.system_state_analysis.availability_score < 0.5  # Low availability when speaking
        mock_context_service.get_system_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_system_state_idle(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test system state analysis when avatar is idle."""
        mock_context_service.get_system_state.return_value = {
            "is_speaking": False,
            "is_idle": True,
            "is_busy": False,
            "has_errors": False,
            "queue_size": 0,
            "resource_utilization": {"cpu": 0.1, "memory": 0.2},
            "avatar_status": "idle"
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        assert result.system_state_analysis.is_idle is True
        assert result.system_state_analysis.availability_score > 0.8  # High availability when idle
        assert result.system_state_analysis.queue_size == 0
    
    @pytest.mark.asyncio
    async def test_analyze_system_state_error(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test system state analysis when system has errors."""
        mock_context_service.get_system_state.return_value = {
            "is_speaking": False,
            "is_idle": False,
            "is_busy": False,
            "has_errors": True,
            "queue_size": 10,
            "resource_utilization": {"cpu": 0.9, "memory": 0.8},
            "avatar_status": "error",
            "error_details": ["TTS service unavailable", "High memory usage"]
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        assert result.system_state_analysis.has_errors is True
        assert result.system_state_analysis.availability_score < 0.2  # Very low availability with errors
        assert "error_details" in result.analysis_metadata
    
    # Test User Context Analysis (Dimension 2)
    
    @pytest.mark.asyncio
    async def test_analyze_user_context_high_engagement(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test user context analysis with high engagement."""
        mock_context_service.get_user_context.return_value = {
            "interaction_frequency": 12.5,  # interactions per hour
            "engagement_level": "high",
            "recent_topics": ["AI", "technology", "conversation"],
            "user_preference_match": 0.85,
            "historical_response_patterns": {
                "average_response_time": 2.3,
                "preferred_interaction_types": ["chat", "voice"],
                "sentiment_trend": "positive"
            },
            "last_interaction": datetime.now() - timedelta(minutes=5)
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        assert result.user_context_analysis.engagement_level == "high"
        assert result.user_context_analysis.interaction_frequency > 10
        assert result.user_context_analysis.user_preference_match > 0.8
        assert "AI" in result.user_context_analysis.recent_topics
    
    @pytest.mark.asyncio
    async def test_analyze_user_context_new_user(self, analyzer_node, mock_context_service):
        """Test user context analysis for new user with no history."""
        stimuli = CategorizedStimuli(
            content="Hi, this is my first time here",
            source="user_chat",
            category=StimuliCategory.USER_INTERACTION,
            confidence=0.9,
            metadata={"user_id": "new_user"}
        )
        
        mock_context_service.get_user_context.return_value = {
            "interaction_frequency": 0.0,
            "engagement_level": "unknown",
            "recent_topics": [],
            "user_preference_match": 0.5,  # neutral
            "historical_response_patterns": {
                "average_response_time": None,
                "preferred_interaction_types": [],
                "sentiment_trend": "neutral"
            },
            "first_interaction": True
        }
        
        result = await analyzer_node.process(stimuli)
        
        assert result.user_context_analysis.engagement_level == "unknown"
        assert result.user_context_analysis.interaction_frequency == 0.0
        assert len(result.user_context_analysis.recent_topics) == 0
        assert result.analysis_metadata.get("first_interaction") is True
    
    # Test Environmental Context Analysis (Dimension 3)
    
    @pytest.mark.asyncio
    async def test_analyze_environmental_autonomous_mode(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test environmental analysis in autonomous mode."""
        mock_context_service.get_environmental_context.return_value = {
            "autonomous_mode_active": True,
            "streaming_status": "live",
            "time_of_day_factor": 0.8,  # evening prime time
            "recent_activity_level": "high",
            "external_event_context": {
                "special_event": "gaming_stream",
                "viewer_count": 1500,
                "chat_activity": "very_active"
            }
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        assert result.environmental_analysis.autonomous_mode_active is True
        assert result.environmental_analysis.streaming_status == "live"
        assert result.environmental_analysis.recent_activity_level == "high"
        assert result.environmental_analysis.external_event_context["viewer_count"] == 1500
    
    @pytest.mark.asyncio
    async def test_analyze_environmental_offline(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test environmental analysis when offline."""
        mock_context_service.get_environmental_context.return_value = {
            "autonomous_mode_active": False,
            "streaming_status": "offline",
            "time_of_day_factor": 0.2,  # late night
            "recent_activity_level": "low",
            "external_event_context": {}
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        assert result.environmental_analysis.autonomous_mode_active is False
        assert result.environmental_analysis.streaming_status == "offline"
        assert result.environmental_analysis.time_of_day_factor < 0.3
        assert result.environmental_analysis.recent_activity_level == "low"
    
    # Test Resource Availability Analysis (Dimension 4)
    
    @pytest.mark.asyncio
    async def test_analyze_resource_high_availability(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test resource analysis with high availability."""
        mock_context_service.get_resource_availability.return_value = {
            "cpu_availability": 0.85,
            "memory_availability": 0.75,
            "agent_availability": {
                "conversation_agent": True,
                "analysis_agent": True,
                "evolution_agent": True
            },
            "system1_availability": True,
            "system2_availability": True,
            "estimated_processing_capacity": 100
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        assert result.resource_analysis.cpu_availability > 0.8
        assert result.resource_analysis.memory_availability > 0.7
        assert all(result.resource_analysis.agent_availability.values())
        assert result.resource_analysis.system1_availability is True
        assert result.resource_analysis.system2_availability is True
        assert result.resource_analysis.estimated_processing_capacity >= 100
    
    @pytest.mark.asyncio
    async def test_analyze_resource_constrained(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test resource analysis under constrained conditions."""
        mock_context_service.get_resource_availability.return_value = {
            "cpu_availability": 0.25,
            "memory_availability": 0.15,
            "agent_availability": {
                "conversation_agent": True,
                "analysis_agent": False,  # Some agents unavailable
                "evolution_agent": False
            },
            "system1_availability": True,
            "system2_availability": False,  # System2 down
            "estimated_processing_capacity": 10
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        assert result.resource_analysis.cpu_availability < 0.3
        assert result.resource_analysis.memory_availability < 0.2
        assert result.resource_analysis.agent_availability["analysis_agent"] is False
        assert result.resource_analysis.system2_availability is False
        assert result.resource_analysis.estimated_processing_capacity <= 10
    
    # Test Temporal Factors (Dimension 5)
    
    @pytest.mark.asyncio
    async def test_analyze_temporal_prime_time(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test temporal analysis during prime time."""
        with patch('src.gateway.nodes.analyzer_node.datetime') as mock_datetime:
            # Set time to 8 PM
            mock_datetime.now.return_value = datetime(2024, 1, 15, 20, 0, 0)
            
            mock_context_service.get_environmental_context.return_value = {
                "autonomous_mode_active": True,
                "streaming_status": "live",
                "time_of_day_factor": 0.9,  # High activity time
                "recent_activity_level": "very_high",
                "external_event_context": {
                    "peak_hours": True,
                    "day_of_week": "Friday"
                }
            }
            
            result = await analyzer_node.process(sample_categorized_stimuli)
            
            assert result.environmental_analysis.time_of_day_factor > 0.8
            assert result.environmental_analysis.external_event_context["peak_hours"] is True
            assert "temporal_analysis" in result.analysis_metadata
    
    @pytest.mark.asyncio
    async def test_analyze_temporal_quiet_hours(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test temporal analysis during quiet hours."""
        with patch('src.gateway.nodes.analyzer_node.datetime') as mock_datetime:
            # Set time to 3 AM
            mock_datetime.now.return_value = datetime(2024, 1, 15, 3, 0, 0)
            
            mock_context_service.get_environmental_context.return_value = {
                "autonomous_mode_active": False,
                "streaming_status": "offline",
                "time_of_day_factor": 0.1,  # Low activity time
                "recent_activity_level": "minimal",
                "external_event_context": {
                    "peak_hours": False,
                    "day_of_week": "Monday"
                }
            }
            
            result = await analyzer_node.process(sample_categorized_stimuli)
            
            assert result.environmental_analysis.time_of_day_factor < 0.2
            assert result.environmental_analysis.external_event_context["peak_hours"] is False
    
    # Test Context Aggregation
    
    @pytest.mark.asyncio
    async def test_context_aggregation_complete(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test complete context aggregation from all dimensions."""
        # Set up all context dimensions
        mock_context_service.get_system_state.return_value = {
            "is_speaking": False,
            "is_idle": True,
            "is_busy": False,
            "has_errors": False,
            "queue_size": 2,
            "resource_utilization": {"cpu": 0.3, "memory": 0.4}
        }
        
        mock_context_service.get_user_context.return_value = {
            "interaction_frequency": 8.0,
            "engagement_level": "medium",
            "recent_topics": ["weather", "news"],
            "user_preference_match": 0.7,
            "historical_response_patterns": {}
        }
        
        mock_context_service.get_environmental_context.return_value = {
            "autonomous_mode_active": True,
            "streaming_status": "live",
            "time_of_day_factor": 0.6,
            "recent_activity_level": "moderate",
            "external_event_context": {}
        }
        
        mock_context_service.get_resource_availability.return_value = {
            "cpu_availability": 0.7,
            "memory_availability": 0.6,
            "agent_availability": {"all": True},
            "system1_availability": True,
            "system2_availability": True,
            "estimated_processing_capacity": 50
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        # Verify all dimensions are present
        assert result.system_state_analysis is not None
        assert result.user_context_analysis is not None
        assert result.environmental_analysis is not None
        assert result.resource_analysis is not None
        assert result.analysis_timestamp is not None
        
        # Verify aggregated metadata
        assert "analysis_depth" in result.analysis_metadata
        assert result.analysis_metadata["analysis_depth"] == "deep"
        assert "context_completeness" in result.analysis_metadata
    
    # Test Error Handling
    
    @pytest.mark.asyncio
    async def test_handle_partial_context_failure(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test handling when some context services fail."""
        # System state works
        mock_context_service.get_system_state.return_value = {
            "is_speaking": False,
            "is_idle": True,
            "is_busy": False,
            "has_errors": False,
            "queue_size": 0,
            "resource_utilization": {"cpu": 0.2, "memory": 0.3}
        }
        
        # User context fails
        mock_context_service.get_user_context.side_effect = Exception("User service error")
        
        # Environmental context works
        mock_context_service.get_environmental_context.return_value = {
            "autonomous_mode_active": True,
            "streaming_status": "live",
            "time_of_day_factor": 0.5,
            "recent_activity_level": "moderate",
            "external_event_context": {}
        }
        
        # Resource analysis works
        mock_context_service.get_resource_availability.return_value = {
            "cpu_availability": 0.6,
            "memory_availability": 0.5,
            "agent_availability": {},
            "system1_availability": True,
            "system2_availability": True,
            "estimated_processing_capacity": 40
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        # Should still return result with partial data
        assert result.system_state_analysis is not None
        assert result.user_context_analysis is not None  # Should have defaults
        assert result.environmental_analysis is not None
        assert result.resource_analysis is not None
        
        # Check error was logged
        assert "errors" in result.analysis_metadata
        assert "user_context" in result.analysis_metadata["errors"]
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test that analysis results are cached appropriately."""
        # Configure all mocks
        mock_context_service.get_system_state.return_value = {"is_idle": True}
        mock_context_service.get_user_context.return_value = {"engagement_level": "high"}
        mock_context_service.get_environmental_context.return_value = {"autonomous_mode_active": True}
        mock_context_service.get_resource_availability.return_value = {"cpu_availability": 0.7}
        
        # First call
        result1 = await analyzer_node.process(sample_categorized_stimuli)
        
        # Second call with same stimuli (should use cache)
        result2 = await analyzer_node.process(sample_categorized_stimuli)
        
        # Context service should only be called once due to caching
        assert mock_context_service.get_system_state.call_count == 1
        assert mock_context_service.get_user_context.call_count == 1
        
        # Results should be the same
        assert result1.analysis_timestamp == result2.analysis_timestamp
    
    @pytest.mark.asyncio
    async def test_health_check(self, analyzer_node):
        """Test analyzer health check functionality."""
        health = await analyzer_node.health_check()
        
        assert health["healthy"] is True
        assert health["component"] == "ContextAnalyzerNode"
        assert "config" in health
        assert health["config"]["analysis_depth"] == "deep"
        assert "cache_stats" in health
    
    @pytest.mark.asyncio
    async def test_analysis_depth_minimal(self, analyzer_node, mock_context_service, sample_categorized_stimuli):
        """Test minimal analysis depth configuration."""
        analyzer_node.config.analysis_depth = "minimal"
        
        # Only basic info should be fetched
        mock_context_service.get_system_state.return_value = {
            "is_speaking": False,
            "is_idle": True,
            "is_busy": False,
            "has_errors": False,
            "queue_size": 0,
            "resource_utilization": {}
        }
        
        result = await analyzer_node.process(sample_categorized_stimuli)
        
        # Should skip detailed analysis
        assert result.system_state_analysis is not None
        assert result.analysis_metadata["analysis_depth"] == "minimal"
        
        # Some services shouldn't be called in minimal mode
        assert mock_context_service.get_user_context.call_count == 0


class TestAnalysisAggregation:
    """Test analysis aggregation and scoring logic."""
    
    @pytest.fixture
    def analyzer_node(self):
        """Create analyzer with mock service."""
        mock_service = Mock(spec=ContextService)
        config = AnalyzerConfig(analysis_depth="standard")
        return ContextAnalyzerNode(mock_service, config)
    
    def test_calculate_overall_availability_score(self, analyzer_node):
        """Test overall availability score calculation."""
        system_state = SystemStateAnalysis(
            is_speaking=False,
            is_idle=True,
            is_busy=False,
            has_errors=False,
            queue_size=1,
            resource_utilization={"cpu": 0.3, "memory": 0.4},
            availability_score=0.8
        )
        
        resource_analysis = ResourceAnalysis(
            cpu_availability=0.7,
            memory_availability=0.6,
            agent_availability={"agent1": True, "agent2": True},
            system1_availability=True,
            system2_availability=True,
            estimated_processing_capacity=80
        )
        
        score = analyzer_node._calculate_overall_availability(
            system_state, resource_analysis
        )
        
        assert 0.6 <= score <= 0.8  # Should be weighted average
    
    def test_determine_processing_recommendation(self, analyzer_node):
        """Test processing recommendation based on analysis."""
        # High availability scenario
        high_availability_analysis = AnalyzedStimuli(
            content="Test",
            source="user",
            category=StimuliCategory.USER_INTERACTION,
            confidence=0.9,
            system_state_analysis=SystemStateAnalysis(
                is_speaking=False,
                is_idle=True,
                is_busy=False,
                has_errors=False,
                queue_size=0,
                resource_utilization={},
                availability_score=0.9
            ),
            user_context_analysis=UserContextAnalysis(
                interaction_frequency=10.0,
                engagement_level="high",
                recent_topics=[],
                user_preference_match=0.8,
                historical_response_patterns={}
            ),
            environmental_analysis=EnvironmentalAnalysis(
                autonomous_mode_active=True,
                streaming_status="live",
                time_of_day_factor=0.8,
                recent_activity_level="high",
                external_event_context={}
            ),
            resource_analysis=ResourceAnalysis(
                cpu_availability=0.8,
                memory_availability=0.7,
                agent_availability={},
                system1_availability=True,
                system2_availability=True,
                estimated_processing_capacity=100
            )
        )
        
        recommendation = analyzer_node._determine_processing_recommendation(
            high_availability_analysis
        )
        
        assert recommendation == "full_processing"
        
        # Low availability scenario
        low_availability_analysis = AnalyzedStimuli(
            content="Test",
            source="user",
            category=StimuliCategory.USER_INTERACTION,
            confidence=0.9,
            system_state_analysis=SystemStateAnalysis(
                is_speaking=True,
                is_idle=False,
                is_busy=True,
                has_errors=False,
                queue_size=10,
                resource_utilization={},
                availability_score=0.2
            ),
            user_context_analysis=UserContextAnalysis(
                interaction_frequency=1.0,
                engagement_level="low",
                recent_topics=[],
                user_preference_match=0.3,
                historical_response_patterns={}
            ),
            environmental_analysis=EnvironmentalAnalysis(
                autonomous_mode_active=False,
                streaming_status="offline",
                time_of_day_factor=0.1,
                recent_activity_level="minimal",
                external_event_context={}
            ),
            resource_analysis=ResourceAnalysis(
                cpu_availability=0.2,
                memory_availability=0.1,
                agent_availability={},
                system1_availability=False,
                system2_availability=False,
                estimated_processing_capacity=5
            )
        )
        
        recommendation = analyzer_node._determine_processing_recommendation(
            low_availability_analysis
        )
        
        assert recommendation in ["minimal_processing", "defer_processing"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])