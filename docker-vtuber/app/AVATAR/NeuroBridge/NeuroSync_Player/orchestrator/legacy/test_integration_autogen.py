"""
Integration Tests for AutoGen VTuber System
==========================================

End-to-end integration tests that verify the complete system works correctly
with AutoGen orchestrator integrated into the NeuroSync Player.

Tests cover:
- Flask application integration
- API endpoint functionality
- Multi-agent decision flow
- Speech and environment control
- Performance under load
- Error recovery
"""

import unittest
import asyncio
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import requests
from flask import Flask
from flask.testing import FlaskClient
import aiohttp

# Import main application components
from orchestrator_integration_v3 import (
    AutoGenOrchestrationWrapper,
    AutoGenOrchestrationConfig,
    create_autogen_integration,
    AutoGenMiddleware
)
from autogen_api_routes import register_autogen_routes
from autogen_orchestrator_v3 import Priority, ActionType


class TestAutoGenIntegration(unittest.TestCase):
    """Integration tests for AutoGen VTuber system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test Flask application"""
        cls.app = Flask(__name__)
        cls.app.config['TESTING'] = True
        
        # Create test configuration
        cls.config = AutoGenOrchestrationConfig()
        cls.config.autogen_enabled = True
        cls.config.persona = 'interactive_streamer'
        
        # Create orchestration wrapper
        cls.orchestrator = AutoGenOrchestrationWrapper(cls.app, cls.config)
        
        # Register API routes
        register_autogen_routes(cls.app, cls.orchestrator)
        
        # Add basic test routes
        @cls.app.route('/health', methods=['GET'])
        def health():
            return {'status': 'healthy'}, 200
        
        @cls.app.route('/process_text', methods=['POST'])
        def process_text():
            """Mock process_text endpoint"""
            data = request.get_json()
            return {
                'status': 'processing',
                'message': 'Input processed',
                'text': data.get('text', ''),
                'direct_speech': data.get('direct_speech', False)
            }, 200
        
        @cls.app.route('/game_control', methods=['POST'])
        def game_control():
            """Mock game_control endpoint"""
            data = request.get_json()
            return {
                'status': 'completed',
                'prompt': data.get('prompt', ''),
                'commands_generated': 3,
                'commands_successful': 3
            }, 200
        
        # Create test client
        cls.client = cls.app.test_client()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        if cls.orchestrator and cls.orchestrator.orchestrator:
            asyncio.run(cls.orchestrator.stop_orchestrator())
    
    def test_flask_app_initialization(self):
        """Test Flask app is properly initialized"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
    
    def test_orchestrator_v3_process_endpoint(self):
        """Test the main process endpoint"""
        payload = {
            'input_type': 'viewer_comment',
            'content': 'Hello VTuber! How are you?',
            'metadata': {
                'viewer_name': 'TestViewer',
                'platform': 'twitch',
                'importance': 'medium'
            }
        }
        
        response = self.client.post(
            '/orchestrator/v3/process',
            json=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('processed', data)
        self.assertIn('decisions', data)
    
    def test_persona_management(self):
        """Test persona GET and PUT endpoints"""
        # GET current persona
        response = self.client.get('/orchestrator/v3/persona')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['current_persona'], 'interactive_streamer')
        self.assertIn('available_personas', data)
        
        # PUT new persona
        response = self.client.put(
            '/orchestrator/v3/persona',
            json={'persona': 'focused_artist'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
    
    def test_agent_status_endpoint(self):
        """Test agent status monitoring"""
        response = self.client.get('/orchestrator/v3/agents/status')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertIn('agents', data)
        self.assertIn('group_chat_status', data)
        self.assertIn('orchestrator_running', data)
        self.assertIn('metrics', data)
    
    def test_autonomous_control(self):
        """Test autonomous behavior control"""
        # Pause autonomous generation
        response = self.client.post(
            '/orchestrator/v3/autonomous/control',
            json={'action': 'pause'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertFalse(data['autonomous_state']['active'])
        
        # Resume autonomous generation
        response = self.client.post(
            '/orchestrator/v3/autonomous/control',
            json={'action': 'resume'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['autonomous_state']['active'])
        
        # Configure settings
        response = self.client.post(
            '/orchestrator/v3/autonomous/control',
            json={
                'action': 'configure',
                'settings': {
                    'min_idle_time': 20,
                    'max_idle_time': 60
                }
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
    
    def test_autonomous_stats(self):
        """Test autonomous statistics endpoint"""
        response = self.client.get('/orchestrator/v3/autonomous/stats?period=last_24_hours')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertIn('autonomous_metrics', data)
        metrics = data['autonomous_metrics']
        self.assertIn('total_content_generated', metrics)
        self.assertIn('content_by_type', metrics)
        self.assertIn('viewer_retention_during_idle', metrics)
    
    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        response = self.client.get('/orchestrator/v3/metrics')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/plain; version=0.0.4')
        
        metrics_text = response.get_data(as_text=True)
        self.assertIn('autogen_requests_total', metrics_text)
        self.assertIn('autogen_decisions_total', metrics_text)
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/orchestrator/v3/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertIn('status', data)
        self.assertIn('components', data)
        self.assertIn('timestamp', data)
    
    def test_external_event_handling(self):
        """Test external event processing"""
        # New viewers event
        response = self.client.post(
            '/orchestrator/v3/event',
            json={
                'event_type': 'new_viewers',
                'payload': {
                    'names': ['Viewer1', 'Viewer2', 'Viewer3']
                }
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Change subject event
        response = self.client.post(
            '/orchestrator/v3/event',
            json={
                'event_type': 'change_subject',
                'payload': {
                    'topic': 'Let\'s talk about AI and VTubers'
                }
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
    
    def test_activity_tracking(self):
        """Test activity update endpoint"""
        response = self.client.post(
            '/orchestrator/v3/activity',
            json={
                'activity': 'gaming',
                'metadata': {
                    'game_name': 'Minecraft'
                }
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['current_activity'], 'gaming')
    
    def test_viewer_count_update(self):
        """Test viewer count update"""
        response = self.client.post(
            '/orchestrator/v3/viewers',
            json={
                'count': 150,
                'delta': 10
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['viewer_count'], 150)
    
    def test_debug_endpoint(self):
        """Test debug information endpoint"""
        response = self.client.get('/orchestrator/v3/debug')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertIn('config', data)
        self.assertIn('state', data)
        self.assertIn('metrics', data)
        self.assertIn('performance_traces', data)
    
    def test_error_handling(self):
        """Test error handling for invalid requests"""
        # Missing required fields
        response = self.client.post(
            '/orchestrator/v3/process',
            json={'content': 'test'},  # Missing input_type
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('missing_fields', data)
        
        # Invalid JSON
        response = self.client.post(
            '/orchestrator/v3/process',
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        # Invalid action
        response = self.client.post(
            '/orchestrator/v3/autonomous/control',
            json={'action': 'invalid_action'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        import concurrent.futures
        
        def make_request(index):
            payload = {
                'input_type': 'viewer_comment',
                'content': f'Message {index}',
                'metadata': {
                    'viewer_name': f'Viewer{index}',
                    'platform': 'twitch',
                    'importance': 'medium'
                }
            }
            response = self.client.post(
                '/orchestrator/v3/process',
                json=payload,
                content_type='application/json'
            )
            return response.status_code, response.get_json()
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        for status_code, data in results:
            self.assertEqual(status_code, 200)
            self.assertIn('processed', data)


class TestIntegrationWithMockServices(unittest.TestCase):
    """Integration tests with mocked external services"""
    
    def setUp(self):
        """Set up test environment with mocks"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Create orchestration with mocked services
        self.config = AutoGenOrchestrationConfig()
        self.config.autogen_enabled = True
        
        # Mock system objects
        self.mock_system_objects = {
            'chunk_queue': Mock(),
            'audio_queue': Mock(),
            'chat_history': [],
            'full_history': []
        }
        
        self.orchestrator = AutoGenOrchestrationWrapper(
            self.app, 
            self.config,
            self.mock_system_objects
        )
        
        register_autogen_routes(self.app, self.orchestrator)
        self.client = self.app.test_client()
    
    def test_speech_interruption(self):
        """Test speech interruption functionality"""
        # Simulate ongoing speech
        self.orchestrator.state_hooks.hook_audio_start("This is a long speech...", 10.0)
        
        # Send high-priority input
        payload = {
            'input_type': 'viewer_comment',
            'content': 'URGENT: Stop everything!',
            'metadata': {
                'viewer_name': 'Moderator',
                'importance': 'high',
                'platform': 'twitch'
            }
        }
        
        with patch.object(self.orchestrator, 'process_with_autogen') as mock_process:
            mock_process.return_value = {
                'processed': True,
                'decisions': [{
                    'type': 'speech',
                    'action': 'Understood, stopping now!',
                    'priority': 'urgent'
                }]
            }
            
            response = self.client.post(
                '/orchestrator/v3/process',
                json=payload,
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            mock_process.assert_called_once()
    
    def test_environment_control_integration(self):
        """Test environment control through orchestrator"""
        # Mock environment decision
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_post.return_value = mock_response
            
            # Process input that should trigger environment change
            payload = {
                'input_type': 'viewer_comment',
                'content': 'Can you change the scene to medieval?',
                'metadata': {
                    'viewer_name': 'SceneFan',
                    'platform': 'youtube'
                }
            }
            
            with patch.object(self.orchestrator, 'process_with_autogen') as mock_process:
                mock_process.return_value = {
                    'processed': True,
                    'decisions': [{
                        'type': 'environment',
                        'action': 'change scene to medieval',
                        'reasoning': 'Viewer requested scene change'
                    }]
                }
                
                response = self.client.post(
                    '/orchestrator/v3/process',
                    json=payload,
                    content_type='application/json'
                )
                
                self.assertEqual(response.status_code, 200)
    
    def test_state_synchronization(self):
        """Test state synchronization between components"""
        # Update various states
        self.orchestrator.state_hooks.hook_audio_start("Speaking...", 5.0)
        self.orchestrator.state_hooks.hook_activity_change("drawing")
        self.orchestrator.state_hooks.hook_viewer_interaction("ArtLover", "Nice drawing!")
        
        # Get debug info to verify state
        response = self.client.get('/orchestrator/v3/debug')
        data = response.get_json()
        
        state = data['state']
        self.assertTrue(state['audio']['is_speaking'])
        self.assertEqual(state['activity']['current'], 'drawing')
        self.assertIn('ArtLover', state['viewers']['active_chatters'])
    
    def test_performance_monitoring(self):
        """Test performance monitoring and metrics"""
        # Make several requests to generate metrics
        for i in range(5):
            payload = {
                'input_type': 'viewer_comment',
                'content': f'Test message {i}',
                'metadata': {'viewer_name': f'Viewer{i}'}
            }
            self.client.post('/orchestrator/v3/process', json=payload)
        
        # Check metrics
        response = self.client.get('/orchestrator/v3/metrics')
        metrics_text = response.get_data(as_text=True)
        
        self.assertIn('autogen_requests_total 5', metrics_text)
        
        # Check performance in status
        response = self.client.get('/orchestrator/v3/agents/status')
        data = response.get_json()
        
        if 'performance' in data:
            self.assertIn('avg_decision_time', data['performance'])


class TestEndToEndScenarios(unittest.TestCase):
    """Test complete end-to-end scenarios"""
    
    @classmethod
    def setUpClass(cls):
        """Set up for scenario tests"""
        cls.app = Flask(__name__)
        cls.config = AutoGenOrchestrationConfig()
        cls.orchestrator = create_autogen_integration(
            cls.app,
            autogen_enabled=True,
            persona='interactive_streamer'
        )
        register_autogen_routes(cls.app, cls.orchestrator)
        cls.client = cls.app.test_client()
    
    def test_stream_startup_scenario(self):
        """Test typical stream startup scenario"""
        # 1. Update activity to streaming
        response = self.client.post(
            '/orchestrator/v3/activity',
            json={'activity': 'chatting'}
        )
        self.assertEqual(response.status_code, 200)
        
        # 2. Set initial viewer count
        response = self.client.post(
            '/orchestrator/v3/viewers',
            json={'count': 5}
        )
        self.assertEqual(response.status_code, 200)
        
        # 3. Process new viewer greetings
        response = self.client.post(
            '/orchestrator/v3/event',
            json={
                'event_type': 'new_viewers',
                'payload': {'names': ['EarlyBird1', 'StreamFan']}
            }
        )
        self.assertEqual(response.status_code, 200)
        
        # 4. Check autonomous behavior is active
        response = self.client.get('/orchestrator/v3/agents/status')
        data = response.get_json()
        self.assertTrue(data['orchestrator_running'])
    
    def test_interactive_conversation_flow(self):
        """Test interactive conversation with filtering"""
        # Set interactive persona
        self.client.put(
            '/orchestrator/v3/persona',
            json={'persona': 'interactive_streamer'}
        )
        
        # Process multiple viewer messages
        messages = [
            {'content': 'Hello! First time here!', 'viewer': 'NewViewer'},
            {'content': 'What game are you playing?', 'viewer': 'Gamer123'},
            {'content': 'spam spam spam', 'viewer': 'Spammer'},
            {'content': 'Your art is amazing!', 'viewer': 'ArtFan'}
        ]
        
        results = []
        for msg in messages:
            response = self.client.post(
                '/orchestrator/v3/process',
                json={
                    'input_type': 'viewer_comment',
                    'content': msg['content'],
                    'metadata': {'viewer_name': msg['viewer']}
                }
            )
            results.append(response.get_json())
        
        # Verify appropriate handling
        self.assertEqual(len(results), 4)
        for result in results:
            self.assertIn('processed', result)
    
    def test_focused_work_scenario(self):
        """Test focused work mode with filtering"""
        # Switch to focused artist persona
        response = self.client.put(
            '/orchestrator/v3/persona',
            json={'persona': 'focused_artist'}
        )
        self.assertEqual(response.status_code, 200)
        
        # Update activity
        response = self.client.post(
            '/orchestrator/v3/activity',
            json={'activity': 'drawing'}
        )
        self.assertEqual(response.status_code, 200)
        
        # Configure autonomous settings for focused work
        response = self.client.post(
            '/orchestrator/v3/autonomous/control',
            json={
                'action': 'configure',
                'settings': {
                    'min_idle_time': 30,
                    'max_idle_time': 90
                }
            }
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify configuration
        response = self.client.get('/orchestrator/v3/autonomous/stats')
        data = response.get_json()
        self.assertIsNotNone(data['autonomous_metrics'])


class TestErrorRecoveryAndResilience(unittest.TestCase):
    """Test error recovery and system resilience"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.config = AutoGenOrchestrationConfig()
        self.orchestrator = AutoGenOrchestrationWrapper(self.app, self.config)
        register_autogen_routes(self.app, self.orchestrator)
        self.client = self.app.test_client()
    
    def test_orchestrator_unavailable(self):
        """Test behavior when orchestrator is unavailable"""
        # Disable orchestrator
        self.app.config['AUTOGEN_ORCHESTRATOR'].config.autogen_enabled = False
        
        response = self.client.post(
            '/orchestrator/v3/process',
            json={
                'input_type': 'test',
                'content': 'test'
            }
        )
        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertIn('error', data)
        
        # Re-enable for other tests
        self.app.config['AUTOGEN_ORCHESTRATOR'].config.autogen_enabled = True
    
    def test_malformed_requests(self):
        """Test handling of malformed requests"""
        # Empty payload
        response = self.client.post('/orchestrator/v3/process', json={})
        self.assertEqual(response.status_code, 400)
        
        # Invalid persona
        response = self.client.put(
            '/orchestrator/v3/persona',
            json={'persona': 'nonexistent_persona'}
        )
        self.assertEqual(response.status_code, 400)
        
        # Invalid event type
        response = self.client.post(
            '/orchestrator/v3/event',
            json={
                'event_type': 'invalid_event',
                'payload': {}
            }
        )
        self.assertEqual(response.status_code, 200)  # Should still process
    
    def test_recovery_from_errors(self):
        """Test system recovery from errors"""
        # Force an error in processing
        with patch.object(self.orchestrator, 'process_with_autogen') as mock_process:
            mock_process.side_effect = Exception("Processing error")
            
            response = self.client.post(
                '/orchestrator/v3/process',
                json={
                    'input_type': 'test',
                    'content': 'test'
                }
            )
            self.assertEqual(response.status_code, 500)
        
        # System should recover for next request
        response = self.client.get('/orchestrator/v3/health')
        self.assertEqual(response.status_code, 200)


def run_integration_tests():
    """Run all integration tests"""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestAutoGenIntegration,
        TestIntegrationWithMockServices,
        TestEndToEndScenarios,
        TestErrorRecoveryAndResilience
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    exit(0 if success else 1)