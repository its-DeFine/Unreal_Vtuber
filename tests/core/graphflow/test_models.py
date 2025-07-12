#!/usr/bin/env python3
"""
Test script to verify the GraphFlow models are working correctly.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from models import (
    # Stimuli models
    ExternalStimuli, CategorizedStimuli, AnalyzedStimuli, RoutingDecision,
    StimuliCategory, Priority,
    # Context models
    SystemStateAnalysis, UserContextAnalysis, EnvironmentalAnalysis,
    ResourceAnalysis, ProcessingContext,
    # Decision models
    ProcessingDecision, ExecutionPlan, ExecutionResult, ProcessingResult,
    RetryPolicy
)


def test_stimuli_models():
    """Test stimuli model creation and validation."""
    print("Testing Stimuli Models...")
    
    # Create base stimuli
    stimuli = ExternalStimuli(
        content="Hello, how are you today?",
        source="user_chat",
        priority=Priority.MEDIUM,
        metadata={"user_id": "user123", "platform": "discord"}
    )
    
    assert stimuli.validate()
    print(f"✓ Created ExternalStimuli: {stimuli.id}")
    
    # Create categorized stimuli
    categorized = CategorizedStimuli(
        content=stimuli.content,
        source=stimuli.source,
        category=StimuliCategory.USER_INTERACTION,
        confidence=0.95,
        classification_metadata={"method": "llm_classification"}
    )
    
    assert categorized.is_high_confidence()
    print(f"✓ Created CategorizedStimuli with category: {categorized.category.value}")
    
    # Create analyzed stimuli with context
    system_state = SystemStateAnalysis(
        is_speaking=False,
        is_idle=True,
        is_busy=False,
        has_errors=False,
        queue_size=5,
        resource_utilization={"cpu": 0.3, "memory": 0.4},
        availability_score=0.85
    )
    
    user_context = UserContextAnalysis(
        interaction_frequency=0.8,
        engagement_level="high",
        recent_topics=["weather", "news", "games"],
        user_preference_match=0.75,
        historical_response_patterns={"greeting": 10, "question": 25}
    )
    
    analyzed = AnalyzedStimuli(
        content=categorized.content,
        source=categorized.source,
        category=categorized.category,
        confidence=categorized.confidence,
        system_state_analysis=system_state,
        user_context_analysis=user_context
    )
    
    context_score = analyzed.get_context_score()
    print(f"✓ Created AnalyzedStimuli with context score: {context_score:.2f}")
    
    return analyzed


def test_context_models():
    """Test context analysis models."""
    print("\nTesting Context Models...")
    
    # Environmental analysis
    env_analysis = EnvironmentalAnalysis(
        autonomous_mode_active=False,
        streaming_status="live",
        time_of_day_factor=0.8,
        recent_activity_level="moderate",
        external_event_context={"event": "user_joined"},
        audience_size=150
    )
    
    assert env_analysis.is_live_streaming()
    print("✓ Created EnvironmentalAnalysis for live streaming")
    
    # Resource analysis
    resource_analysis = ResourceAnalysis(
        cpu_availability=0.7,
        memory_availability=0.6,
        agent_availability={"agent1": True, "agent2": True},
        system1_availability=True,
        system2_availability=True,
        estimated_processing_capacity=10,
        gpu_availability=0.8
    )
    
    assert resource_analysis.has_sufficient_resources()
    limiting = resource_analysis.get_limiting_resource()
    print(f"✓ Created ResourceAnalysis, limiting resource: {limiting}")
    
    return env_analysis, resource_analysis


def test_decision_models(analyzed_stimuli):
    """Test decision and execution models."""
    print("\nTesting Decision Models...")
    
    # Create retry policy
    retry_policy = RetryPolicy(
        max_attempts=3,
        initial_delay=1.0,
        backoff_factor=2.0
    )
    
    delay = retry_policy.calculate_delay(2)
    print(f"✓ Created RetryPolicy with 2nd attempt delay: {delay}s")
    
    # Create execution plan
    execution_plan = ExecutionPlan(
        id="exec-123",
        stimuli_id=analyzed_stimuli.id,
        decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
        target_systems=["system1", "system2"],
        execution_order=["parallel"],
        timeout_settings={"system1": 5.0, "system2": 10.0},
        retry_policies={"system1": retry_policy, "system2": retry_policy},
        success_criteria={"min_success_rate": 0.8},
        priority_level=75
    )
    
    total_timeout = execution_plan.get_total_timeout()
    print(f"✓ Created ExecutionPlan with total timeout: {total_timeout}s")
    
    # Create routing decision
    routing = RoutingDecision(
        stimuli_id=analyzed_stimuli.id,
        decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
        execution_plan=execution_plan,
        confidence_score=0.9,
        reasoning="User is highly engaged and system is available"
    )
    
    print(f"✓ Created RoutingDecision: {routing.decision.value}")
    
    # Create execution result
    exec_result = ExecutionResult(
        stimuli_id=analyzed_stimuli.id,
        execution_plan_id=execution_plan.id,
        success=True,
        results={"system1": "Avatar responded", "system2": "Analysis complete"},
        execution_time=3.5,
        performance_metrics={"latency": 0.5, "throughput": 100}
    )
    
    assert exec_result.is_complete_success()
    print("✓ Created successful ExecutionResult")
    
    # Create processing result
    processing_result = ProcessingResult(
        stimuli_id=analyzed_stimuli.id,
        routing_decision=ProcessingDecision.AVATAR_AND_ANALYSIS,
        execution_results=[exec_result],
        total_processing_time=4.0,
        processing_stages={
            "categorization": {"duration": 0.3, "success": True},
            "analysis": {"duration": 0.2, "success": True},
            "routing": {"duration": 0.1, "success": True},
            "execution": {"duration": 3.4, "success": True}
        }
    )
    
    success_rate = processing_result.get_success_rate()
    print(f"✓ Created ProcessingResult with success rate: {success_rate:.0%}")
    
    return processing_result


def test_full_processing_context():
    """Test creating a full processing context."""
    print("\nTesting Full Processing Context...")
    
    # Create all analyses
    system_state = SystemStateAnalysis(
        is_speaking=False,
        is_idle=True,
        is_busy=False,
        has_errors=False,
        queue_size=2,
        resource_utilization={"cpu": 0.25, "memory": 0.35},
        availability_score=0.9
    )
    
    user_context = UserContextAnalysis(
        interaction_frequency=1.2,
        engagement_level="high",
        recent_topics=["technology", "ai", "coding"],
        user_preference_match=0.85,
        historical_response_patterns={"technical": 50, "casual": 20}
    )
    
    environment = EnvironmentalAnalysis(
        autonomous_mode_active=True,
        streaming_status="live",
        time_of_day_factor=0.9,
        recent_activity_level="high",
        external_event_context={"viewers": 200}
    )
    
    resources = ResourceAnalysis(
        cpu_availability=0.75,
        memory_availability=0.65,
        agent_availability={"all": True},
        system1_availability=True,
        system2_availability=True,
        estimated_processing_capacity=20
    )
    
    # Create processing context
    context = ProcessingContext(
        system_state=system_state,
        user_context=user_context,
        environment=environment,
        resources=resources,
        processing_recommendations=["Use fast response mode", "Prioritize technical content"],
        risk_factors=["High viewer count may impact latency"]
    )
    
    assert context.is_favorable_for_processing()
    print(f"✓ Created ProcessingContext with quality score: {context.context_quality_score:.2f}")
    
    return context


def main():
    """Run all model tests."""
    print("GraphFlow Models Test Suite")
    print("=" * 50)
    
    try:
        # Test stimuli models
        analyzed_stimuli = test_stimuli_models()
        
        # Test context models
        env_analysis, resource_analysis = test_context_models()
        
        # Test decision models
        processing_result = test_decision_models(analyzed_stimuli)
        
        # Test full processing context
        full_context = test_full_processing_context()
        
        print("\n" + "=" * 50)
        print("✅ All model tests passed successfully!")
        
        # Demonstrate serialization
        print("\nExample serialization:")
        result_dict = processing_result.to_dict()
        print(f"Processing result keys: {list(result_dict.keys())}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()