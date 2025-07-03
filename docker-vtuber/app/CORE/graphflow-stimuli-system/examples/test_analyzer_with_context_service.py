#!/usr/bin/env python3
"""
Test script demonstrating the Context Analyzer Node with Context Service integration.

This example shows how the analyzer node performs comprehensive context analysis
across 5 dimensions using the centralized context service.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.stimuli import CategorizedStimuli, StimuliCategory, Priority
from src.gateway.nodes.analyzer_node import ContextAnalyzerNode
from src.services.context_service import ContextService
from src.config.settings import AnalyzerConfig, GraphFlowConfig, ContextAnalysisDepth
from src.utils.logging import setup_logging


async def test_analyzer_with_context_service():
    """Test the analyzer node with context service."""
    # Setup logging
    setup_logging("DEBUG")
    
    print("=" * 80)
    print("Context Analyzer Node Test with Context Service")
    print("=" * 80)
    
    # Create configuration
    config = GraphFlowConfig()
    analyzer_config = AnalyzerConfig(
        analysis_depth=ContextAnalysisDepth.STANDARD,
        include_user_history=True,
        history_window_size=100,
        cache_enabled=True,
        cache_ttl=60
    )
    
    # Create context service
    context_service = ContextService(config)
    await context_service.initialize()
    
    # Create analyzer node with context service
    analyzer = ContextAnalyzerNode(analyzer_config, context_service)
    await analyzer.initialize()
    
    # Test stimuli samples
    test_cases = [
        {
            "content": "Hey, can you change your hair color to blue?",
            "category": StimuliCategory.DIRECT_ADMIN,
            "source": "admin_console",
            "priority": Priority.HIGH,
            "confidence": 0.95,
            "metadata": {"user_id": "admin_001"}
        },
        {
            "content": "System notification: Avatar is now speaking",
            "category": StimuliCategory.SYSTEM_NOTIFICATION,
            "source": "system",
            "priority": Priority.HIGH,
            "confidence": 1.0,
            "metadata": {"notification_type": "avatar_state"}
        },
        {
            "content": "Hello! How are you doing today?",
            "category": StimuliCategory.USER_INTERACTION,
            "source": "user_chat",
            "priority": Priority.MEDIUM,
            "confidence": 0.88,
            "metadata": {"user_id": "user_123", "platform": "twitch"}
        },
        {
            "content": "New follower: TechEnthusiast42",
            "category": StimuliCategory.SOCIAL_MEDIA,
            "source": "social_media",
            "priority": Priority.LOW,
            "confidence": 0.92,
            "metadata": {"platform": "twitter", "event_type": "follow"}
        }
    ]
    
    # Test different analysis depths
    depths = [
        ContextAnalysisDepth.MINIMAL,
        ContextAnalysisDepth.STANDARD,
        ContextAnalysisDepth.DEEP
    ]
    
    for depth in depths:
        print(f"\n{'=' * 60}")
        print(f"Testing with analysis depth: {depth.value.upper()}")
        print(f"{'=' * 60}")
        
        # Update analyzer configuration
        analyzer.config.analysis_depth = depth
        
        for i, test_case in enumerate(test_cases):
            print(f"\nTest Case {i + 1}: {test_case['category'].value}")
            print(f"Content: {test_case['content']}")
            print(f"Source: {test_case['source']}")
            print(f"Priority: {test_case['priority'].value}")
            
            # Create categorized stimuli
            stimuli = CategorizedStimuli(
                content=test_case["content"],
                source=test_case["source"],
                priority=test_case["priority"],
                category=test_case["category"],
                confidence=test_case["confidence"],
                metadata=test_case["metadata"]
            )
            
            # Analyze context
            start_time = datetime.now()
            analyzed = await analyzer.process(stimuli)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Display results
            print(f"\nAnalysis Results:")
            print(f"  Processing Time: {processing_time:.3f}s")
            
            # System State Analysis
            if analyzed.system_state_analysis:
                sys_state = analyzed.system_state_analysis
                print(f"\n  System State:")
                print(f"    - Is Speaking: {sys_state.is_speaking}")
                print(f"    - Is Idle: {sys_state.is_idle}")
                print(f"    - Is Busy: {sys_state.is_busy}")
                print(f"    - Has Errors: {sys_state.has_errors}")
                print(f"    - Queue Size: {sys_state.queue_size}")
                print(f"    - Availability Score: {sys_state.availability_score:.2f}")
                if sys_state.resource_utilization:
                    print(f"    - CPU Usage: {sys_state.resource_utilization.get('cpu', 0)*100:.1f}%")
                    print(f"    - Memory Usage: {sys_state.resource_utilization.get('memory', 0)*100:.1f}%")
            
            # User Context Analysis
            if analyzed.user_context_analysis:
                user_ctx = analyzed.user_context_analysis
                print(f"\n  User Context:")
                print(f"    - User ID: {user_ctx.user_id}")
                print(f"    - Engagement Level: {user_ctx.engagement_level}")
                print(f"    - Interaction Frequency: {user_ctx.interaction_frequency:.2f}/min")
                print(f"    - Preference Match: {user_ctx.user_preference_match:.2f}")
                print(f"    - Sentiment Score: {user_ctx.sentiment_score:.2f}")
                if user_ctx.recent_topics:
                    print(f"    - Recent Topics: {', '.join(user_ctx.recent_topics)}")
            
            # Environmental Analysis
            if analyzed.environmental_analysis:
                env = analyzed.environmental_analysis
                print(f"\n  Environmental Context:")
                print(f"    - Autonomous Mode: {env.autonomous_mode_active}")
                print(f"    - Streaming Status: {env.streaming_status}")
                print(f"    - Time Factor: {env.time_of_day_factor:.2f}")
                print(f"    - Activity Level: {env.recent_activity_level}")
                if env.audience_size is not None:
                    print(f"    - Audience Size: {env.audience_size}")
                
                # Temporal factors (if deep analysis)
                if depth == ContextAnalysisDepth.DEEP and env.external_event_context:
                    temporal = env.external_event_context
                    if 'day_of_week' in temporal:
                        print(f"\n  Temporal Factors:")
                        print(f"    - Day: {temporal.get('day_of_week')}")
                        print(f"    - Is Weekend: {temporal.get('is_weekend')}")
                        print(f"    - Is Peak Hours: {temporal.get('is_peak_hours')}")
                        print(f"    - Season: {temporal.get('season')}")
            
            # Resource Analysis
            if analyzed.resource_analysis:
                res = analyzed.resource_analysis
                print(f"\n  Resource Availability:")
                print(f"    - CPU Available: {res.cpu_availability*100:.1f}%")
                print(f"    - Memory Available: {res.memory_availability*100:.1f}%")
                print(f"    - System1 Available: {res.system1_availability}")
                print(f"    - System2 Available: {res.system2_availability}")
                print(f"    - Processing Capacity: {res.estimated_processing_capacity}")
                print(f"    - Resource Pressure: {res.resource_pressure_level}")
                if res.bottlenecks:
                    print(f"    - Bottlenecks: {', '.join(res.bottlenecks)}")
            
            # Context Score
            context_score = await context_service.get_context_score(
                analyzed.system_state_analysis,
                analyzed.user_context_analysis,
                analyzed.environmental_analysis,
                analyzed.resource_analysis
            )
            print(f"\n  Overall Context Score: {context_score:.2f}")
            
            # Add delay between tests to simulate real usage
            await asyncio.sleep(0.5)
    
    # Test state updates through context service
    print(f"\n{'=' * 60}")
    print("Testing Context Service State Updates")
    print(f"{'=' * 60}")
    
    # Update system state
    await context_service.update_system_state({
        'autonomous_mode': True,
        'streaming_active': True,
        'platform': 'twitch'
    })
    print("\nUpdated system state: Autonomous mode ON, Streaming ON (Twitch)")
    
    # Analyze again to see the changes
    stimuli = CategorizedStimuli(
        content="Testing after state update",
        source="test",
        category=StimuliCategory.USER_INTERACTION,
        confidence=0.9,
        metadata={"user_id": "test_user"}
    )
    
    analyzed = await analyzer.process(stimuli)
    if analyzed.environmental_analysis:
        env = analyzed.environmental_analysis
        print(f"\nEnvironmental Context After Update:")
        print(f"  - Autonomous Mode: {env.autonomous_mode_active}")
        print(f"  - Streaming Status: {env.streaming_status}")
        print(f"  - Platform: {env.platform_context}")
    
    # Cleanup
    await analyzer.shutdown()
    await context_service.shutdown()
    
    print("\n" + "=" * 80)
    print("Test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_analyzer_with_context_service())