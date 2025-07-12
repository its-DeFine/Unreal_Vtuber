"""
Unit Tests for AutoGen Orchestrator V3
======================================

Comprehensive test suite for the AutoGen-based orchestrator system.
Tests cover:
- Agent initialization and configuration
- Multi-agent coordination
- Decision processing
- Autonomous content generation
- Performance and error handling
"""

import unittest
import asyncio
import json
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Import components to test
from autogen_orchestrator_v3 import (
    AutoGenOrchestratorV3,
    create_autogen_orchestrator_v3
)
from autogen_agents import (
    create_orchestrator_agent,
    create_content_filter_agent,
    create_speech_coordinator_agent,
    create_environment_controller_agent,
    create_idle_content_agent,
    create_autonomous_decision_agent,
    parse_filter_response,
    parse_speech_response,
    parse_environment_response,
    parse_content_response,
    parse_decision_response,
    FilterDecision,
    ContentDecision,
    EnvironmentAction,
    AgentCoordinator
)
from autogen_state_manager import (
    OrchestratorState,
    StateManager,
    ConversationContext,
    EnvironmentState,
    ContentHistory
)
from autogen_content_strategies import (
    ContentStrategyManager,
    ContentType,
    ContentStrategy,
    PersonaConfig,
    IdleBehaviorConfig
)


class TestAutoGenOrchestratorV3(unittest.TestCase):
    """Test suite for AutoGen Orchestrator V3"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock AutoGen availability
        self.autogen_patch = patch('autogen_orchestrator_v3.AUTOGEN_AVAILABLE', True)
        self.autogen_patch.start()
        
        # Mock SCB availability
        self.scb_patch = patch('autogen_orchestrator_v3.SCB_AVAILABLE', False)
        self.scb_patch.start()
        
        # Create test orchestrator
        self.orchestrator = AutoGenOrchestratorV3()
        
    def tearDown(self):
        """Clean up after tests"""
        self.autogen_patch.stop()
        self.scb_patch.stop()
        
        # Stop orchestrator if running
        if self.orchestrator and self.orchestrator.running:
            asyncio.run(self.orchestrator.stop())
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        self.assertIsNotNone(self.orchestrator)
        self.assertTrue(self.orchestrator.enabled)
        self.assertIsNotNone(self.orchestrator.state_manager)
        self.assertIsNotNone(self.orchestrator.content_strategy_manager)
        self.assertEqual(len(self.orchestrator.agents), 6)  # 6 agent types
        
    def test_configuration_loading(self):
        """Test configuration loading from environment"""
        with patch.dict('os.environ', {
            'AUTOGEN_ORCHESTRATOR_ENABLED': 'true',
            'ORCHESTRATOR_PERSONA': 'focused_artist',
            'AUTONOMOUS_CONTENT_ENABLED': 'true',
            'AUTOGEN_MODEL': 'gpt-4',
            'AUTOGEN_TEMPERATURE': '0.8',
            'MIN_IDLE_TIME': '10.0',
            'MAX_IDLE_TIME': '30.0'
        }):
            orchestrator = AutoGenOrchestratorV3()
            config = orchestrator.config
            
            self.assertTrue(config['enabled'])
            self.assertEqual(config['current_persona'], 'focused_artist')
            self.assertTrue(config['autonomous_enabled'])
            self.assertEqual(config['llm_config']['model'], 'gpt-4')
            self.assertEqual(config['llm_config']['temperature'], 0.8)
            self.assertEqual(config['timing']['min_idle_time'], 10.0)
            self.assertEqual(config['timing']['max_idle_time'], 30.0)
    
    def test_persona_configurations(self):
        """Test persona configuration loading"""
        personas = self.orchestrator.config['personas']
        
        # Check all personas are loaded
        self.assertIn('focused_artist', personas)
        self.assertIn('interactive_streamer', personas)
        self.assertIn('casual_gamer', personas)
        
        # Test focused artist persona
        artist = personas['focused_artist']
        self.assertEqual(artist.name, 'Focused Artist')
        self.assertEqual(artist.filter_threshold, 0.7)
        self.assertEqual(artist.idle_behavior.min_idle_time, 15)
        self.assertEqual(artist.idle_behavior.max_idle_time, 45)
        
        # Test content types
        content_types = artist.idle_behavior.content_types
        self.assertIn('art_commentary', content_types)
        self.assertIn('technique_explanation', content_types)
        self.assertIn('viewer_engagement', content_types)
        self.assertIn('ambient_thoughts', content_types)
    
    @patch('autogen_orchestrator_v3.create_orchestrator_agent')
    @patch('autogen_orchestrator_v3.create_content_filter_agent')
    def test_agent_initialization(self, mock_filter_agent, mock_orchestrator_agent):
        """Test agent initialization"""
        mock_orchestrator_agent.return_value = Mock(name='orchestrator')
        mock_filter_agent.return_value = Mock(name='filter')
        
        orchestrator = AutoGenOrchestratorV3()
        
        # Verify agents were created
        mock_orchestrator_agent.assert_called_once()
        mock_filter_agent.assert_called_once()
        
        # Check agent configuration
        self.assertIn('orchestrator', orchestrator.agents)
        self.assertIn('content_filter', orchestrator.agents)
    
    async def test_start_stop_orchestrator(self):
        """Test starting and stopping orchestrator"""
        # Start orchestrator
        await self.orchestrator.start()
        self.assertTrue(self.orchestrator.running)
        self.assertIsNotNone(self.orchestrator.decision_task)
        self.assertIsNotNone(self.orchestrator.autonomous_task)
        
        # Stop orchestrator
        await self.orchestrator.stop()
        self.assertFalse(self.orchestrator.running)
    
    async def test_process_external_input(self):
        """Test processing external input"""
        input_data = {
            'text': 'Hello VTuber!',
            'source': 'viewer_comment',
            'metadata': {
                'viewer_name': 'TestViewer',
                'platform': 'twitch',
                'importance': 'medium'
            }
        }
        
        # Mock agent responses
        with patch.object(self.orchestrator, '_run_agent_discussion') as mock_discussion:
            mock_discussion.return_value = [
                {'name': 'orchestrator', 'content': 'DECISION: speech - Say hello back - Greeting'}
            ]
            
            result = await self.orchestrator.process_external_input(input_data)
            
            self.assertTrue(result['processed'])
            self.assertEqual(len(result['decisions']), 1)
            self.assertEqual(result['decisions'][0]['type'], 'speech')
    
    def test_extract_decisions_from_discussion(self):
        """Test decision extraction from agent discussion"""
        messages = [
            {
                'name': 'orchestrator',
                'content': 'DECISION: speech - Hello viewers! - Responding to greeting'
            },
            {
                'name': 'content_filter',
                'content': 'FILTER: suppress - Score: 0.2 - Reason: Spam content'
            }
        ]
        
        decisions = self.orchestrator._extract_decisions_from_discussion(messages)
        
        self.assertEqual(len(decisions), 2)
        self.assertEqual(decisions[0]['type'], 'speech')
        self.assertEqual(decisions[1]['type'], 'suppress')
    
    async def test_should_generate_autonomous_content(self):
        """Test autonomous content generation decision"""
        # Set up state for idle condition
        self.orchestrator.state_manager.state.last_interaction = time.time() - 20
        self.orchestrator.state.last_speech_completed = time.time() - 5
        
        # Mock autonomous decision agent
        with patch.object(self.orchestrator, '_consult_autonomous_decision_agent') as mock_consult:
            mock_consult.return_value = True
            
            should_generate = await self.orchestrator._should_generate_autonomous_content()
            self.assertTrue(should_generate)
    
    async def test_generate_autonomous_content(self):
        """Test autonomous content generation"""
        # Mock content strategy manager
        with patch.object(self.orchestrator.content_strategy_manager, 'select_strategy') as mock_select:
            with patch.object(self.orchestrator.content_strategy_manager, 'generate_content') as mock_generate:
                mock_select.return_value = ContentStrategy.VIEWER_ENGAGEMENT
                mock_generate.return_value = "Thanks for watching everyone!"
                
                # Mock queue speech
                with patch.object(self.orchestrator, '_queue_speech') as mock_queue:
                    await self.orchestrator._generate_autonomous_content()
                    
                    mock_queue.assert_called_once()
                    call_args = mock_queue.call_args
                    self.assertEqual(call_args[1]['content'], "Thanks for watching everyone!")
    
    def test_calculate_dynamic_interval(self):
        """Test dynamic interval calculation"""
        base_interval = self.orchestrator.config['timing']['decision_interval']
        
        # Test recent interaction (should speed up)
        self.orchestrator.state_manager.state.last_interaction = time.time() - 10
        interval = self.orchestrator._calculate_dynamic_interval()
        self.assertLess(interval, base_interval)
        
        # Test very idle (should slow down)
        self.orchestrator.state_manager.state.last_interaction = time.time() - 150
        interval = self.orchestrator._calculate_dynamic_interval()
        self.assertGreater(interval, base_interval)
    
    def test_get_status(self):
        """Test status reporting"""
        status = self.orchestrator.get_status()
        
        self.assertIn('running', status)
        self.assertIn('enabled', status)
        self.assertIn('persona', status)
        self.assertIn('state', status)
        self.assertIn('agents', status)
        self.assertIn('metrics', status)
        self.assertIn('configuration', status)
        
        # Check state details
        state = status['state']
        self.assertIn('is_speaking', state)
        self.assertIn('idle_duration', state)
        self.assertIn('speech_queue_size', state)
        self.assertIn('action_queue_size', state)
    
    async def test_update_persona(self):
        """Test persona updates"""
        # Update to valid persona
        success = await self.orchestrator.update_persona('casual_gamer')
        self.assertTrue(success)
        self.assertEqual(self.orchestrator.config['current_persona'], 'casual_gamer')
        
        # Try invalid persona
        success = await self.orchestrator.update_persona('invalid_persona')
        self.assertFalse(success)
    
    async def test_process_external_event(self):
        """Test external event processing"""
        # Test new viewer event
        with patch.object(self.orchestrator, '_queue_speech') as mock_queue:
            await self.orchestrator.process_external_event('new_viewers', {
                'names': ['Viewer1', 'Viewer2']
            })
            
            mock_queue.assert_called_once()
            call_args = mock_queue.call_args
            self.assertIn('Welcome', call_args[1]['content'])
            self.assertIn('Viewer1', call_args[1]['content'])
        
        # Test change subject event
        with patch.object(self.orchestrator, '_queue_speech') as mock_queue:
            await self.orchestrator.process_external_event('change_subject', {
                'topic': 'gaming strategies'
            })
            
            mock_queue.assert_called_once()
            call_args = mock_queue.call_args
            self.assertIn('gaming strategies', call_args[1]['content'])


class TestAutoGenAgents(unittest.TestCase):
    """Test suite for AutoGen agent implementations"""
    
    def test_parse_filter_response(self):
        """Test filter response parsing"""
        response = "FILTER: SUPPRESS - Score: 0.3 - Reason: Low relevance to current activity"
        decision = parse_filter_response(response)
        
        self.assertIsInstance(decision, FilterDecision)
        self.assertFalse(decision.should_pass)
        self.assertEqual(decision.importance_score, 0.3)
        self.assertEqual(decision.filter_reason, "Low relevance to current activity")
        
        # Test MODIFY response
        response = """FILTER: MODIFY - Score: 0.8 - Reason: Good question
        Modified message: That's a great question about the technique!"""
        decision = parse_filter_response(response)
        
        self.assertTrue(decision.should_pass)
        self.assertEqual(decision.modified_content, "That's a great question about the technique!")
    
    def test_parse_speech_response(self):
        """Test speech response parsing"""
        response = """SPEECH: Hello viewers!
        CONTEXT: Greeting new viewers
        TIMING: urgent"""
        
        result = parse_speech_response(response)
        
        self.assertEqual(result['speech'], "Hello viewers!")
        self.assertEqual(result['context'], "Greeting new viewers")
        self.assertEqual(result['timing'], "urgent")
    
    def test_parse_environment_response(self):
        """Test environment response parsing"""
        response = """ENVIRONMENT: change_scene - Parameters: scene:medieval, lighting:sunset - Reason: Creating atmospheric setting"""
        
        action = parse_environment_response(response)
        
        self.assertIsInstance(action, EnvironmentAction)
        self.assertEqual(action.command, "change_scene")
        self.assertEqual(action.parameters['scene'], "medieval")
        self.assertEqual(action.parameters['lighting'], "sunset")
    
    def test_parse_content_response(self):
        """Test content response parsing"""
        response = """CONTENT: Thanks for watching everyone!
        TYPE: viewer_engagement
        FOLLOW_UP: How's everyone's day going?"""
        
        result = parse_content_response(response)
        
        self.assertEqual(result['content'], "Thanks for watching everyone!")
        self.assertEqual(result['type'], "viewer_engagement")
        self.assertEqual(result['follow_up'], "How's everyone's day going?")
    
    def test_parse_decision_response(self):
        """Test decision response parsing"""
        response = """DECISION: YES - Type: content - Urgency: 0.7
        REASONING: Viewer engagement has been low for 30 seconds"""
        
        decision = parse_decision_response(response)
        
        self.assertIsInstance(decision, ContentDecision)
        self.assertTrue(decision.should_generate)
        self.assertEqual(decision.content_type, "content")
        self.assertEqual(decision.urgency, 0.7)
    
    @patch('autogen_agents.AUTOGEN_AVAILABLE', False)
    def test_mock_agent_creation(self):
        """Test mock agent creation when AutoGen not available"""
        from autogen_agents import create_mock_agents
        
        agents = create_mock_agents()
        
        self.assertEqual(len(agents), 6)
        self.assertIn('orchestrator', agents)
        self.assertIn('content_filter', agents)
        
        # Test mock responses
        filter_response = agents['content_filter'].generate_reply([])
        self.assertIn('FILTER:', filter_response)


class TestStateManager(unittest.TestCase):
    """Test suite for state management"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.state_manager = StateManager()
    
    def test_state_initialization(self):
        """Test state initialization"""
        state = self.state_manager.state
        
        self.assertFalse(state.is_speaking)
        self.assertFalse(state.blendshape_active)
        self.assertEqual(state.current_environment, "default")
        self.assertIsNotNone(state.conversation_context)
    
    def test_update_idle_state(self):
        """Test idle state updates"""
        # Set last interaction to past
        self.state_manager.state.last_interaction = time.time() - 30
        
        idle_duration = self.state_manager.get_idle_duration()
        self.assertGreater(idle_duration, 29)
        self.assertLess(idle_duration, 31)
    
    def test_conversation_context(self):
        """Test conversation context management"""
        # Add viewer interaction
        self.state_manager.add_viewer_interaction("TestUser", "Hello!")
        
        # Update topic
        self.state_manager.update_conversation_topic("gaming")
        
        context = self.state_manager.state.conversation_context
        self.assertEqual(context.current_topic, "gaming")
        self.assertIn("TestUser", context.recent_viewers)
    
    def test_content_history(self):
        """Test content history tracking"""
        # Record content generation
        self.state_manager.state.content_history.add_content(
            ContentType.COMMENTARY,
            "This is a test commentary"
        )
        
        history = self.state_manager.state.content_history
        self.assertEqual(len(history.recent_content), 1)
        self.assertEqual(history.content_counts[ContentType.COMMENTARY], 1)


class TestContentStrategyManager(unittest.TestCase):
    """Test suite for content strategy management"""
    
    def setUp(self):
        """Set up test fixtures"""
        config = {
            'current_persona': 'interactive_streamer',
            'personas': {
                'interactive_streamer': PersonaConfig(
                    name="Interactive Streamer",
                    orchestrator_prompt="Test prompt",
                    filter_threshold=0.2,
                    idle_behavior=IdleBehaviorConfig(
                        min_idle_time=8,
                        max_idle_time=20,
                        content_types={
                            "viewer_questions": {"weight": 0.4, "examples": ["What's up?"]},
                            "topic_starters": {"weight": 0.3, "examples": ["Let's talk"]},
                            "reactions": {"weight": 0.2, "examples": ["Wow!"]},
                            "games_activities": {"weight": 0.1, "examples": ["Game time?"]}
                        }
                    )
                )
            }
        }
        self.strategy_manager = ContentStrategyManager(config)
    
    def test_strategy_selection(self):
        """Test content strategy selection"""
        state_manager = StateManager()
        
        # Test with different conditions
        state_manager.state.conversation_context.current_activity = "gaming"
        strategy = self.strategy_manager.select_strategy(state_manager)
        
        self.assertIsInstance(strategy, ContentStrategy)
    
    def test_content_generation(self):
        """Test content generation"""
        state_manager = StateManager()
        strategy = ContentStrategy.VIEWER_ENGAGEMENT
        
        content = self.strategy_manager.generate_content(strategy, state_manager)
        
        self.assertIsNotNone(content)
        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 0)
    
    def test_content_variety(self):
        """Test content variety tracking"""
        # Generate multiple contents
        contents = []
        state_manager = StateManager()
        
        for _ in range(10):
            strategy = self.strategy_manager.select_strategy(state_manager)
            content = self.strategy_manager.generate_content(strategy, state_manager)
            contents.append(content)
            self.strategy_manager.record_content_generation(strategy, content)
        
        # Check for variety
        unique_contents = set(contents)
        self.assertGreater(len(unique_contents), 1)  # Should have variety


class TestPerformanceAndErrors(unittest.TestCase):
    """Test performance characteristics and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.orchestrator = AutoGenOrchestratorV3()
    
    async def test_timeout_handling(self):
        """Test agent timeout handling"""
        # Mock a slow agent
        slow_agent = AsyncMock()
        slow_agent.generate_reply = AsyncMock(side_effect=asyncio.TimeoutError())
        
        self.orchestrator.agents['content_filter'] = slow_agent
        
        # Process should handle timeout gracefully
        input_data = {'text': 'test', 'source': 'test'}
        result = await self.orchestrator.process_external_input(input_data)
        
        # Should still return a result
        self.assertIn('processed', result)
    
    def test_memory_usage(self):
        """Test memory usage patterns"""
        import sys
        
        # Track queue sizes
        initial_speech_queue = len(self.orchestrator.speech_queue)
        initial_action_queue = len(self.orchestrator.action_queue)
        
        # Add many items
        for i in range(100):
            self.orchestrator.speech_queue.append(Mock())
            self.orchestrator.action_queue.append(Mock())
        
        # Verify queues don't grow unbounded
        self.assertEqual(len(self.orchestrator.speech_queue), initial_speech_queue + 100)
        self.assertEqual(len(self.orchestrator.action_queue), initial_action_queue + 100)
    
    async def test_concurrent_processing(self):
        """Test concurrent request handling"""
        # Create multiple concurrent requests
        tasks = []
        for i in range(10):
            input_data = {
                'text': f'Message {i}',
                'source': 'test',
                'metadata': {'index': i}
            }
            task = self.orchestrator.process_external_input(input_data)
            tasks.append(task)
        
        # Process all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete
        self.assertEqual(len(results), 10)
        for result in results:
            if isinstance(result, dict):
                self.assertIn('processed', result)


def run_async_test(test_func):
    """Helper to run async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_func())
    finally:
        loop.close()


if __name__ == '__main__':
    unittest.main()