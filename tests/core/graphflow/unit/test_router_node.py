"""
Unit tests for the DecisionRouterNode.

Tests decision matrix application, all decision types, validation logic,
and execution plan generation.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.models.stimuli import (
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
from src.models.decisions import (
    ProcessingDecision,
    ExecutionPlan,
    RoutingDecision,
    RetryPolicy
)
from src.gateway.nodes.router_node import (
    DecisionRouterNode,
    RouterConfig
)
from src.gateway.nodes.decision_engine import DecisionEngine
from src.config.decision_matrix import DecisionMatrix


class TestDecisionRouterNode:
    """Test suite for DecisionRouterNode."""
    
    @pytest.fixture
    def mock_decision_engine(self):
        """Create a mock decision engine."""
        engine = Mock(spec=DecisionEngine)
        engine.apply_rules = Mock()
        engine.validate_decision = Mock(return_value=True)
        return engine
    
    @pytest.fixture
    def router_config(self):
        """Create router configuration."""
        return RouterConfig(
            enable_emergency_override=True,
            enable_validation=True,
            max_retry_attempts=3,
            decision_timeout=5.0,
            confidence_threshold=0.7
        )
    
    @pytest.fixture
    def router_node(self, mock_decision_engine, router_config):
        """Create router node for testing."""
        return DecisionRouterNode(mock_decision_engine, router_config)
    
    @pytest.fixture
    def sample_analyzed_stimuli(self):
        """Create sample analyzed stimuli."""
        return AnalyzedStimuli(
            id="test-123",
            content="Hello, how are you?",
            source="user_chat",
            category=StimuliCategory.USER_INTERACTION,
            confidence=0.95,
            priority=Priority.MEDIUM,
            system_state_analysis=SystemStateAnalysis(
                is_speaking=False,
                is_idle=True,
                is_busy=False,
                has_errors=False,
                queue_size=0,
                resource_utilization={"cpu": 0.3, "memory": 0.4},
                availability_score=0.8
            ),
            user_context_analysis=UserContextAnalysis(
                interaction_frequency=5.0,
                engagement_level="medium",
                recent_topics=["greeting", "conversation"],
                user_preference_match=0.7,
                historical_response_patterns={}
            ),
            environmental_analysis=EnvironmentalAnalysis(
                autonomous_mode_active=True,
                streaming_status="live",
                time_of_day_factor=0.6,
                recent_activity_level="moderate",
                external_event_context={}
            ),
            resource_analysis=ResourceAnalysis(
                cpu_availability=0.7,
                memory_availability=0.6,
                agent_availability={"all": True},
                system1_availability=True,
                system2_availability=True,
                estimated_processing_capacity=50
            )
        )
    
    # Test Decision Matrix Application
    
    @pytest.mark.asyncio
    async def test_route_avatar_and_analysis_decision(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test routing for avatar and analysis decision."""
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.AVATAR_AND_ANALYSIS
        
        result = await router_node.process(sample_analyzed_stimuli)
        
        assert isinstance(result, RoutingDecision)
        assert result.decision == ProcessingDecision.AVATAR_AND_ANALYSIS
        assert result.stimuli_id == "test-123"
        assert result.confidence_score > 0
        assert len(result.execution_plan.target_systems) == 2
        assert "system1" in result.execution_plan.target_systems
        assert "system2" in result.execution_plan.target_systems
        assert result.execution_plan.execution_order == "parallel"
    
    @pytest.mark.asyncio
    async def test_route_analysis_only_decision(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test routing for analysis only decision."""
        # Modify stimuli to indicate avatar is speaking
        sample_analyzed_stimuli.system_state_analysis.is_speaking = True
        sample_analyzed_stimuli.system_state_analysis.availability_score = 0.3
        
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.ANALYSIS_ONLY
        
        result = await router_node.process(sample_analyzed_stimuli)
        
        assert result.decision == ProcessingDecision.ANALYSIS_ONLY
        assert len(result.execution_plan.target_systems) == 1
        assert "system2" in result.execution_plan.target_systems
        assert "system1" not in result.execution_plan.target_systems
        assert "is_speaking" in result.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_route_log_only_decision(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test routing for log only decision."""
        # Modify stimuli to indicate low priority contextual update
        sample_analyzed_stimuli.category = StimuliCategory.CONTEXTUAL_UPDATE
        sample_analyzed_stimuli.priority = Priority.LOW
        
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.LOG_ONLY
        
        result = await router_node.process(sample_analyzed_stimuli)
        
        assert result.decision == ProcessingDecision.LOG_ONLY
        assert len(result.execution_plan.target_systems) == 0
        assert result.execution_plan.execution_order == "none"
        assert "log" in result.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_route_emergency_override_decision(self, router_node, mock_decision_engine):
        """Test routing for emergency override decision."""
        emergency_stimuli = AnalyzedStimuli(
            id="emergency-123",
            content="EMERGENCY: System critical failure!",
            source="monitoring",
            category=StimuliCategory.EMERGENCY,
            confidence=0.99,
            priority=Priority.CRITICAL,
            system_state_analysis=SystemStateAnalysis(
                is_speaking=True,
                is_idle=False,
                is_busy=True,
                has_errors=True,
                queue_size=100,
                resource_utilization={"cpu": 0.95, "memory": 0.90},
                availability_score=0.1
            ),
            user_context_analysis=UserContextAnalysis(
                interaction_frequency=0,
                engagement_level="none",
                recent_topics=[],
                user_preference_match=0,
                historical_response_patterns={}
            ),
            environmental_analysis=EnvironmentalAnalysis(
                autonomous_mode_active=True,
                streaming_status="live",
                time_of_day_factor=0.5,
                recent_activity_level="critical",
                external_event_context={"alert": "system_failure"}
            ),
            resource_analysis=ResourceAnalysis(
                cpu_availability=0.05,
                memory_availability=0.10,
                agent_availability={},
                system1_availability=False,
                system2_availability=False,
                estimated_processing_capacity=0
            )
        )
        
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.EMERGENCY_OVERRIDE
        
        result = await router_node.process(emergency_stimuli)
        
        assert result.decision == ProcessingDecision.EMERGENCY_OVERRIDE
        assert result.priority == Priority.CRITICAL
        assert result.execution_plan.execution_order == "immediate"
        assert "emergency" in result.reasoning.lower()
        assert result.execution_plan.timeout_settings.get("global") <= 10.0
    
    # Test Decision Types
    
    @pytest.mark.asyncio
    async def test_all_decision_types_coverage(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test that all decision types can be properly routed."""
        decision_types = [
            ProcessingDecision.AVATAR_AND_ANALYSIS,
            ProcessingDecision.ANALYSIS_ONLY,
            ProcessingDecision.LOG_ONLY,
            ProcessingDecision.EMERGENCY_OVERRIDE
        ]
        
        for decision_type in decision_types:
            mock_decision_engine.apply_rules.return_value = decision_type
            result = await router_node.process(sample_analyzed_stimuli)
            
            assert result.decision == decision_type
            assert result.execution_plan is not None
            assert result.confidence_score >= 0
            assert result.reasoning != ""
    
    # Test Validation Logic
    
    @pytest.mark.asyncio
    async def test_validation_success(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test successful validation of routing decision."""
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.AVATAR_AND_ANALYSIS
        mock_decision_engine.validate_decision.return_value = True
        
        result = await router_node.process(sample_analyzed_stimuli)
        
        assert result is not None
        mock_decision_engine.validate_decision.assert_called_once()
        assert "validation" in result.metadata
        assert result.metadata["validation"]["passed"] is True
    
    @pytest.mark.asyncio
    async def test_validation_failure_fallback(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test fallback when validation fails."""
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.AVATAR_AND_ANALYSIS
        mock_decision_engine.validate_decision.return_value = False
        
        result = await router_node.process(sample_analyzed_stimuli)
        
        # Should fallback to safer option
        assert result.decision in [ProcessingDecision.ANALYSIS_ONLY, ProcessingDecision.LOG_ONLY]
        assert "validation_failed" in result.metadata
        assert "fallback" in result.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_validation_disabled(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test behavior when validation is disabled."""
        router_node.config.enable_validation = False
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.AVATAR_AND_ANALYSIS
        
        result = await router_node.process(sample_analyzed_stimuli)
        
        # Validation should not be called
        mock_decision_engine.validate_decision.assert_not_called()
        assert result.decision == ProcessingDecision.AVATAR_AND_ANALYSIS
    
    # Test Execution Plan Generation
    
    @pytest.mark.asyncio
    async def test_execution_plan_parallel_systems(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test execution plan for parallel system execution."""
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.AVATAR_AND_ANALYSIS
        
        result = await router_node.process(sample_analyzed_stimuli)
        
        plan = result.execution_plan
        assert plan.decision == ProcessingDecision.AVATAR_AND_ANALYSIS
        assert plan.target_systems == ["system1", "system2"]
        assert plan.execution_order == "parallel"
        assert "system1" in plan.timeout_settings
        assert "system2" in plan.timeout_settings
        assert plan.retry_policies["system1"].max_attempts == 3
        assert plan.retry_policies["system2"].max_attempts == 3
    
    @pytest.mark.asyncio
    async def test_execution_plan_sequential_fallback(self, router_node, mock_decision_engine):
        """Test execution plan for sequential fallback scenario."""
        # Create stimuli where System1 is unavailable
        stimuli = AnalyzedStimuli(
            content="Test",
            source="user",
            category=StimuliCategory.USER_INTERACTION,
            confidence=0.9,
            priority=Priority.MEDIUM,
            system_state_analysis=SystemStateAnalysis(
                is_speaking=False,
                is_idle=True,
                is_busy=False,
                has_errors=False,
                queue_size=0,
                resource_utilization={},
                availability_score=0.5
            ),
            user_context_analysis=UserContextAnalysis(
                interaction_frequency=5.0,
                engagement_level="medium",
                recent_topics=[],
                user_preference_match=0.7,
                historical_response_patterns={}
            ),
            environmental_analysis=EnvironmentalAnalysis(
                autonomous_mode_active=True,
                streaming_status="live",
                time_of_day_factor=0.6,
                recent_activity_level="moderate",
                external_event_context={}
            ),
            resource_analysis=ResourceAnalysis(
                cpu_availability=0.7,
                memory_availability=0.6,
                agent_availability={},
                system1_availability=False,  # System1 unavailable
                system2_availability=True,
                estimated_processing_capacity=30
            )
        )
        
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.ANALYSIS_ONLY
        
        result = await router_node.process(stimuli)
        
        plan = result.execution_plan
        assert plan.target_systems == ["system2"]
        assert plan.execution_order == "sequential"
        assert "fallback_reason" in plan.metadata
    
    @pytest.mark.asyncio
    async def test_execution_plan_timeout_adjustment(self, router_node, mock_decision_engine):
        """Test timeout adjustment based on system load."""
        # Create high load scenario
        stimuli = AnalyzedStimuli(
            content="Test",
            source="user",
            category=StimuliCategory.USER_INTERACTION,
            confidence=0.9,
            priority=Priority.HIGH,
            system_state_analysis=SystemStateAnalysis(
                is_speaking=False,
                is_idle=False,
                is_busy=True,
                has_errors=False,
                queue_size=50,  # High queue
                resource_utilization={"cpu": 0.8, "memory": 0.7},
                availability_score=0.3
            ),
            user_context_analysis=UserContextAnalysis(
                interaction_frequency=5.0,
                engagement_level="medium",
                recent_topics=[],
                user_preference_match=0.7,
                historical_response_patterns={}
            ),
            environmental_analysis=EnvironmentalAnalysis(
                autonomous_mode_active=True,
                streaming_status="live",
                time_of_day_factor=0.8,  # Peak time
                recent_activity_level="very_high",
                external_event_context={}
            ),
            resource_analysis=ResourceAnalysis(
                cpu_availability=0.2,  # Low resources
                memory_availability=0.3,
                agent_availability={},
                system1_availability=True,
                system2_availability=True,
                estimated_processing_capacity=10
            )
        )
        
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.AVATAR_AND_ANALYSIS
        
        result = await router_node.process(stimuli)
        
        plan = result.execution_plan
        # Timeouts should be increased due to high load
        assert plan.timeout_settings["system1"] > 10.0
        assert plan.timeout_settings["system2"] > 10.0
        assert "load_adjusted" in plan.metadata
    
    @pytest.mark.asyncio
    async def test_execution_plan_retry_policy_critical(self, router_node, mock_decision_engine):
        """Test retry policy for critical priority stimuli."""
        stimuli = AnalyzedStimuli(
            content="Critical system update",
            source="admin",
            category=StimuliCategory.DIRECT_ADMIN,
            confidence=0.95,
            priority=Priority.CRITICAL,
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
                interaction_frequency=0,
                engagement_level="none",
                recent_topics=[],
                user_preference_match=0,
                historical_response_patterns={}
            ),
            environmental_analysis=EnvironmentalAnalysis(
                autonomous_mode_active=True,
                streaming_status="live",
                time_of_day_factor=0.5,
                recent_activity_level="moderate",
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
        
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.AVATAR_AND_ANALYSIS
        
        result = await router_node.process(stimuli)
        
        plan = result.execution_plan
        # Critical items should have more aggressive retry
        assert plan.retry_policies["system1"].max_attempts >= 5
        assert plan.retry_policies["system1"].backoff_factor == 1.5
        assert plan.success_criteria["min_systems_success"] == 2  # Both must succeed
    
    # Test Decision Confidence
    
    @pytest.mark.asyncio
    async def test_confidence_calculation_high(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test confidence calculation for clear decision."""
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.AVATAR_AND_ANALYSIS
        
        result = await router_node.process(sample_analyzed_stimuli)
        
        # High confidence when all systems available and clear category
        assert result.confidence_score >= 0.8
        assert "confidence_factors" in result.metadata
    
    @pytest.mark.asyncio
    async def test_confidence_calculation_low(self, router_node, mock_decision_engine):
        """Test confidence calculation for uncertain decision."""
        stimuli = AnalyzedStimuli(
            content="Ambiguous request",
            source="unknown",
            category=StimuliCategory.CONTEXTUAL_UPDATE,
            confidence=0.4,  # Low categorization confidence
            priority=Priority.LOW,
            system_state_analysis=SystemStateAnalysis(
                is_speaking=False,
                is_idle=True,
                is_busy=False,
                has_errors=True,  # System errors
                queue_size=0,
                resource_utilization={},
                availability_score=0.5
            ),
            user_context_analysis=UserContextAnalysis(
                interaction_frequency=0,
                engagement_level="unknown",
                recent_topics=[],
                user_preference_match=0.5,
                historical_response_patterns={}
            ),
            environmental_analysis=EnvironmentalAnalysis(
                autonomous_mode_active=False,
                streaming_status="offline",
                time_of_day_factor=0.5,
                recent_activity_level="unknown",
                external_event_context={}
            ),
            resource_analysis=ResourceAnalysis(
                cpu_availability=0.5,
                memory_availability=0.5,
                agent_availability={},
                system1_availability=True,
                system2_availability=False,  # System2 down
                estimated_processing_capacity=25
            )
        )
        
        mock_decision_engine.apply_rules.return_value = ProcessingDecision.LOG_ONLY
        
        result = await router_node.process(stimuli)
        
        # Low confidence due to multiple uncertainty factors
        assert result.confidence_score < 0.5
        assert "low_confidence_reason" in result.metadata
    
    # Test Health Check
    
    @pytest.mark.asyncio
    async def test_health_check(self, router_node):
        """Test router health check functionality."""
        health = await router_node.health_check()
        
        assert health["healthy"] is True
        assert health["component"] == "DecisionRouterNode"
        assert "config" in health
        assert health["config"]["enable_emergency_override"] is True
        assert "routing_stats" in health
    
    # Test Error Handling
    
    @pytest.mark.asyncio
    async def test_handle_decision_engine_failure(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test handling when decision engine fails."""
        mock_decision_engine.apply_rules.side_effect = Exception("Engine failure")
        
        result = await router_node.process(sample_analyzed_stimuli)
        
        # Should fallback to safe default
        assert result.decision == ProcessingDecision.LOG_ONLY
        assert "error" in result.reasoning.lower()
        assert result.confidence_score < 0.3
        assert "decision_engine_error" in result.metadata
    
    @pytest.mark.asyncio
    async def test_handle_timeout(self, router_node, mock_decision_engine, sample_analyzed_stimuli):
        """Test handling of decision timeout."""
        async def slow_decision(*args):
            await asyncio.sleep(10)  # Longer than timeout
            return ProcessingDecision.AVATAR_AND_ANALYSIS
        
        mock_decision_engine.apply_rules = slow_decision
        router_node.config.decision_timeout = 0.1  # Very short timeout
        
        result = await router_node.process(sample_analyzed_stimuli)
        
        # Should timeout and use fallback
        assert result.decision in [ProcessingDecision.ANALYSIS_ONLY, ProcessingDecision.LOG_ONLY]
        assert "timeout" in result.reasoning.lower()
        assert "decision_timeout" in result.metadata


class TestDecisionEngine:
    """Test the decision engine rule application."""
    
    @pytest.fixture
    def decision_matrix(self):
        """Create a test decision matrix."""
        return {
            "emergency_rules": [
                {
                    "condition": "category == EMERGENCY",
                    "decision": "EMERGENCY_OVERRIDE",
                    "priority": 100
                }
            ],
            "system_state_rules": [
                {
                    "condition": "system_state.is_speaking == True",
                    "decision": "ANALYSIS_ONLY",
                    "priority": 90
                },
                {
                    "condition": "system_state.is_idle == True AND category == USER_INTERACTION",
                    "decision": "AVATAR_AND_ANALYSIS",
                    "priority": 80
                }
            ],
            "category_rules": [
                {
                    "condition": "category == DIRECT_ADMIN",
                    "decision": "AVATAR_AND_ANALYSIS",
                    "priority": 70
                },
                {
                    "condition": "category == CONTEXTUAL_UPDATE",
                    "decision": "LOG_ONLY",
                    "priority": 30
                }
            ],
            "resource_rules": [
                {
                    "condition": "resource_analysis.cpu_availability < 0.3",
                    "decision": "LOG_ONLY",
                    "priority": 60
                }
            ],
            "default_rules": [
                {
                    "condition": "True",
                    "decision": "ANALYSIS_ONLY",
                    "priority": 10
                }
            ]
        }
    
    @pytest.fixture
    def decision_engine(self, decision_matrix):
        """Create decision engine with test matrix."""
        engine = DecisionEngine(decision_matrix)
        return engine
    
    def test_apply_emergency_rule(self, decision_engine):
        """Test emergency rule takes precedence."""
        stimuli = Mock()
        stimuli.category = StimuliCategory.EMERGENCY
        
        decision = decision_engine.apply_rules(stimuli)
        
        assert decision == ProcessingDecision.EMERGENCY_OVERRIDE
    
    def test_apply_system_state_rule_speaking(self, decision_engine):
        """Test system state rule when speaking."""
        stimuli = Mock()
        stimuli.category = StimuliCategory.USER_INTERACTION
        stimuli.system_state_analysis.is_speaking = True
        
        decision = decision_engine.apply_rules(stimuli)
        
        assert decision == ProcessingDecision.ANALYSIS_ONLY
    
    def test_apply_resource_constraint_rule(self, decision_engine):
        """Test resource constraint rule."""
        stimuli = Mock()
        stimuli.category = StimuliCategory.USER_INTERACTION
        stimuli.system_state_analysis.is_speaking = False
        stimuli.resource_analysis.cpu_availability = 0.2
        
        decision = decision_engine.apply_rules(stimuli)
        
        assert decision == ProcessingDecision.LOG_ONLY
    
    def test_rule_priority_ordering(self, decision_engine):
        """Test that higher priority rules are evaluated first."""
        # Create stimuli that matches multiple rules
        stimuli = Mock()
        stimuli.category = StimuliCategory.EMERGENCY
        stimuli.system_state_analysis.is_speaking = True
        stimuli.resource_analysis.cpu_availability = 0.1
        
        decision = decision_engine.apply_rules(stimuli)
        
        # Emergency rule (priority 100) should win
        assert decision == ProcessingDecision.EMERGENCY_OVERRIDE
    
    def test_default_rule_fallback(self, decision_engine):
        """Test default rule when no specific rules match."""
        stimuli = Mock()
        stimuli.category = StimuliCategory.SOCIAL_MEDIA
        stimuli.system_state_analysis.is_speaking = False
        stimuli.system_state_analysis.is_idle = False
        stimuli.resource_analysis.cpu_availability = 0.8
        
        decision = decision_engine.apply_rules(stimuli)
        
        # Should fall through to default
        assert decision == ProcessingDecision.ANALYSIS_ONLY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])