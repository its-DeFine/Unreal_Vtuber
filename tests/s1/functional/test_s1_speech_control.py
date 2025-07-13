#!/usr/bin/env python3
"""
S1 Speech Control Functional Test
=================================

This test validates the speech control functionality of the S1 system by:
1. Starting a long speech request with interaction_mode="queue"
2. Testing stop/pause/resume actions via /speech/control endpoint
3. Verifying proper behavior through container logs and API responses

Usage:
    python test_s1_speech_control.py --url http://localhost:5001
"""

import asyncio
import aiohttp
import json
import time
import uuid
import logging
import argparse
import docker
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class S1SpeechControlTest:
    """
    S1 Speech Control Functional Test Suite
    
    Tests speech control endpoints and interaction modes
    """
    
    def __init__(self, s1_url: str = "http://localhost:5001", container_name: str = "neurosync_s1"):
        self.s1_url = s1_url
        self.container_name = container_name
        self.docker_client = docker.from_env()
        self.test_id = f"s1_speech_control_{int(time.time())}"
        
        # Create logs directory
        self.logs_dir = Path("logs/s1/functional")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized S1 Speech Control Test - ID: {self.test_id}")
        logger.info(f"Target URL: {s1_url}")
        logger.info(f"Container: {container_name}")
    
    async def send_long_speech_request(self, session: aiohttp.ClientSession) -> Dict:
        """Send a long speech request that will take time to process"""
        stimuli_id = str(uuid.uuid4())
        
        # Long text that should take several seconds to process
        long_text = """
        This is a very long speech request that should take several seconds to process completely.
        We are testing the speech control functionality to ensure that we can properly interrupt,
        pause, and resume speech playback in the NeuroSync Player system. This text contains
        multiple sentences and should generate multiple audio chunks that we can control during
        playback. The system should be able to handle stop commands that flush all queues,
        pause commands that temporarily halt playback, and resume commands that continue from
        where we left off. This comprehensive test ensures that the speech control API works
        as expected in real-world scenarios where users might want to interrupt or control
        the avatar's speech output dynamically.
        """
        
        payload = {
            "text": long_text.strip(),
            "interaction_mode": "queue",
            "autonomous_context": {
                "test_id": self.test_id,
                "stimuli_id": stimuli_id,
                "test_type": "speech_control"
            }
        }
        
        request_time = datetime.now()
        
        try:
            async with session.post(
                f"{self.s1_url}/process_text",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_data = await response.json()
                
                return {
                    "stimuli_id": stimuli_id,
                    "request_time": request_time,
                    "response_status": response.status,
                    "response_data": response_data,
                    "text_length": len(long_text.strip()),
                    "success": response.status == 200
                }
        except Exception as e:
            logger.error(f"Long speech request failed for {stimuli_id}: {e}")
            return {
                "stimuli_id": stimuli_id,
                "request_time": request_time,
                "response_status": 0,
                "response_data": {"error": str(e)},
                "text_length": len(long_text.strip()),
                "success": False
            }
    
    async def send_speech_control_command(self, session: aiohttp.ClientSession, action: str) -> Dict:
        """Send a speech control command"""
        payload = {"action": action}
        
        try:
            async with session.post(
                f"{self.s1_url}/speech/control",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_data = await response.json()
                
                return {
                    "action": action,
                    "response_status": response.status,
                    "response_data": response_data,
                    "success": response.status == 200,
                    "timestamp": datetime.now()
                }
        except Exception as e:
            logger.error(f"Speech control command '{action}' failed: {e}")
            return {
                "action": action,
                "response_status": 0,
                "response_data": {"error": str(e)},
                "success": False,
                "timestamp": datetime.now()
            }
    
    def parse_speech_events(self, since_time: datetime) -> Dict:
        """Parse container logs for speech-related events"""
        try:
            container = self.docker_client.containers.get(self.container_name)
            
            # Get logs since test start
            logs = container.logs(
                since=since_time,
                timestamps=True,
                tail=1000
            ).decode('utf-8')
            
            # Parse logs for speech events
            received_events = []
            wav_ready_events = []
            speech_control_events = []
            
            # Regex patterns for log parsing
            received_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z).*«S1_RECEIVED»\s+([a-f0-9-]+)'
            wav_ready_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z).*«S1_WAV_READY»\s+([a-f0-9-]+)'
            speech_control_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z).*(🛑|⏸️|▶️)\s*Speech playback\s+(stopped|paused|resumed)'
            
            for line in logs.split('\n'):
                # Parse S1_RECEIVED events
                received_match = re.search(received_pattern, line)
                if received_match:
                    log_timestamp, stimuli_id = received_match.groups()
                    received_events.append({
                        'timestamp': log_timestamp,
                        'stimuli_id': stimuli_id,
                        'event': 'received'
                    })
                
                # Parse S1_WAV_READY events
                wav_ready_match = re.search(wav_ready_pattern, line)
                if wav_ready_match:
                    log_timestamp, stimuli_id = wav_ready_match.groups()
                    wav_ready_events.append({
                        'timestamp': log_timestamp,
                        'stimuli_id': stimuli_id,
                        'event': 'wav_ready'
                    })
                
                # Parse speech control events
                control_match = re.search(speech_control_pattern, line)
                if control_match:
                    log_timestamp, emoji, action = control_match.groups()
                    speech_control_events.append({
                        'timestamp': log_timestamp,
                        'action': action,
                        'emoji': emoji,
                        'event': 'speech_control'
                    })
            
            logger.info(f"Parsed {len(received_events)} S1_RECEIVED events")
            logger.info(f"Parsed {len(wav_ready_events)} S1_WAV_READY events")
            logger.info(f"Parsed {len(speech_control_events)} speech control events")
            
            return {
                'received': received_events,
                'wav_ready': wav_ready_events,
                'speech_control': speech_control_events,
                'raw_logs': logs
            }
            
        except Exception as e:
            logger.error(f"Failed to parse container logs: {e}")
            return {'received': [], 'wav_ready': [], 'speech_control': [], 'raw_logs': ''}
    
    async def test_speech_stop(self) -> Dict:
        """Test speech stop functionality"""
        logger.info("🛑 Testing speech stop functionality")
        
        test_start_time = datetime.now()
        
        async with aiohttp.ClientSession() as session:
            # Send long speech request
            logger.info("Sending long speech request...")
            speech_request = await self.send_long_speech_request(session)
            
            if not speech_request['success']:
                return {
                    'test': 'speech_stop',
                    'success': False,
                    'error': 'Failed to send initial speech request',
                    'speech_request': speech_request
                }
            
            # Wait a moment for speech to start
            await asyncio.sleep(0.5)
            
            # Send stop command
            logger.info("Sending stop command...")
            stop_result = await self.send_speech_control_command(session, "stop")
            
            # Wait for logs to update
            await asyncio.sleep(2)
        
        # Parse logs to verify behavior
        log_events = self.parse_speech_events(test_start_time)
        
        # Analyze results
        success = (
            speech_request['success'] and
            stop_result['success'] and
            len(log_events['received']) > 0 and
            'streams_stopped' in stop_result.get('response_data', {}) and
            'queues_flushed' in stop_result.get('response_data', {})
        )
        
        return {
            'test': 'speech_stop',
            'success': success,
            'speech_request': speech_request,
            'stop_result': stop_result,
            'log_events': log_events,
            'analysis': {
                'speech_started': len(log_events['received']) > 0,
                'stop_response_correct': 'streams_stopped' in stop_result.get('response_data', {}),
                'wav_events_before_stop': len(log_events['wav_ready'])
            }
        }
    
    async def test_speech_pause_resume(self) -> Dict:
        """Test speech pause and resume functionality"""
        logger.info("⏸️▶️ Testing speech pause/resume functionality (expects RTMP mode errors)")
        
        test_start_time = datetime.now()
        
        async with aiohttp.ClientSession() as session:
            # Send long speech request
            logger.info("Sending long speech request...")
            speech_request = await self.send_long_speech_request(session)
            
            if not speech_request['success']:
                return {
                    'test': 'speech_pause_resume',
                    'success': False,
                    'error': 'Failed to send initial speech request',
                    'speech_request': speech_request
                }
            
            # Wait for speech to start
            await asyncio.sleep(1.0)
            
            # Send pause command
            logger.info("Sending pause command...")
            pause_result = await self.send_speech_control_command(session, "pause")
            
            # Wait while paused
            await asyncio.sleep(1.0)
            
            # Send resume command
            logger.info("Sending resume command...")
            resume_result = await self.send_speech_control_command(session, "resume")
            
            # Wait for completion
            await asyncio.sleep(3.0)
        
        # Parse logs to verify behavior
        log_events = self.parse_speech_events(test_start_time)
        
        # Analyze results - in RTMP mode, pause/resume should return 400 errors
        success = (
            speech_request['success'] and
            pause_result['response_status'] == 400 and  # Expected: not supported in RTMP mode
            resume_result['response_status'] == 400 and  # Expected: not supported in RTMP mode
            len(log_events['received']) > 0 and
            "not supported in RTMP" in str(pause_result.get('response_data', {})) and
            "not supported in RTMP" in str(resume_result.get('response_data', {}))
        )
        
        return {
            'test': 'speech_pause_resume',
            'success': success,
            'speech_request': speech_request,
            'pause_result': pause_result,
            'resume_result': resume_result,
            'log_events': log_events,
            'analysis': {
                'speech_started': len(log_events['received']) > 0,
                'pause_properly_rejected': pause_result['response_status'] == 400,
                'resume_properly_rejected': resume_result['response_status'] == 400,
                'total_control_events': len(log_events['speech_control'])
            }
        }
    
    async def test_invalid_speech_control(self) -> Dict:
        """Test invalid speech control commands"""
        logger.info("❌ Testing invalid speech control commands")
        
        async with aiohttp.ClientSession() as session:
            # Test invalid action
            invalid_result = await self.send_speech_control_command(session, "invalid_action")
            
            # Test missing action
            try:
                async with session.post(
                    f"{self.s1_url}/speech/control",
                    json={},  # Missing action
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_data = await response.json()
                    missing_action_result = {
                        "response_status": response.status,
                        "response_data": response_data,
                        "success": response.status == 400  # Should return 400 for missing action
                    }
            except Exception as e:
                missing_action_result = {
                    "response_status": 0,
                    "response_data": {"error": str(e)},
                    "success": False
                }
        
        success = (
            invalid_result['response_status'] == 400 and
            missing_action_result['success']
        )
        
        return {
            'test': 'invalid_speech_control',
            'success': success,
            'invalid_action_result': invalid_result,
            'missing_action_result': missing_action_result
        }
    
    async def test_speech_status(self) -> Dict:
        """Test speech status functionality"""
        logger.info("📊 Testing speech status functionality")
        
        async with aiohttp.ClientSession() as session:
            # Test status when idle
            idle_status = await self.send_speech_control_command(session, "status")
            
            # Start speech
            speech_request = await self.send_long_speech_request(session)
            
            # Test status when active (small delay to let speech start)
            await asyncio.sleep(0.5)
            active_status = await self.send_speech_control_command(session, "status")
            
            # Stop speech
            stop_result = await self.send_speech_control_command(session, "stop")
            
            # Test status after stop
            await asyncio.sleep(0.5)
            stopped_status = await self.send_speech_control_command(session, "status")
        
        success = (
            idle_status['success'] and
            active_status['success'] and
            stopped_status['success'] and
            speech_request['success'] and
            stop_result['success']
        )
        
        return {
            'test': 'speech_status',
            'success': success,
            'idle_status': idle_status,
            'active_status': active_status,
            'stopped_status': stopped_status,
            'analysis': {
                'idle_status_correct': idle_status.get('response_data', {}).get('status') == 'idle',
                'has_queue_info': 'chunk_queue_size' in active_status.get('response_data', {}),
                'has_stream_info': 'active_streams' in active_status.get('response_data', {})
            }
        }
    
    def save_test_results(self, results: Dict):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.logs_dir / f"{self.test_id}_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to {results_file}")
    
    async def run_all_tests(self) -> Dict:
        """Run all speech control tests"""
        logger.info("🚀 Starting S1 Speech Control Functional Tests")
        
        test_results = {
            'test_id': self.test_id,
            'start_time': datetime.now(),
            'tests': {}
        }
        
        # Test 1: Speech Stop
        try:
            stop_test = await self.test_speech_stop()
            test_results['tests']['speech_stop'] = stop_test
            logger.info(f"Speech Stop Test: {'✅ PASSED' if stop_test['success'] else '❌ FAILED'}")
        except Exception as e:
            logger.error(f"Speech stop test failed with exception: {e}")
            test_results['tests']['speech_stop'] = {'success': False, 'error': str(e)}
        
        # Wait between tests
        await asyncio.sleep(2)
        
        # Test 2: Speech Pause/Resume
        try:
            pause_resume_test = await self.test_speech_pause_resume()
            test_results['tests']['speech_pause_resume'] = pause_resume_test
            logger.info(f"Speech Pause/Resume Test: {'✅ PASSED' if pause_resume_test['success'] else '❌ FAILED'}")
        except Exception as e:
            logger.error(f"Speech pause/resume test failed with exception: {e}")
            test_results['tests']['speech_pause_resume'] = {'success': False, 'error': str(e)}
        
        # Wait between tests
        await asyncio.sleep(1)
        
        # Test 3: Invalid Commands
        try:
            invalid_test = await self.test_invalid_speech_control()
            test_results['tests']['invalid_speech_control'] = invalid_test
            logger.info(f"Invalid Commands Test: {'✅ PASSED' if invalid_test['success'] else '❌ FAILED'}")
        except Exception as e:
            logger.error(f"Invalid commands test failed with exception: {e}")
            test_results['tests']['invalid_speech_control'] = {'success': False, 'error': str(e)}
        
        # Wait between tests
        await asyncio.sleep(1)
        
        # Test 4: Status Functionality
        try:
            status_test = await self.test_speech_status()
            test_results['tests']['speech_status'] = status_test
            logger.info(f"Speech Status Test: {'✅ PASSED' if status_test['success'] else '❌ FAILED'}")
        except Exception as e:
            logger.error(f"Speech status test failed with exception: {e}")
            test_results['tests']['speech_status'] = {'success': False, 'error': str(e)}
        
        # Calculate overall success
        test_results['end_time'] = datetime.now()
        test_results['duration'] = (test_results['end_time'] - test_results['start_time']).total_seconds()
        test_results['overall_success'] = all(
            test.get('success', False) for test in test_results['tests'].values()
        )
        
        # Save results
        self.save_test_results(test_results)
        
        return test_results

async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="S1 Speech Control Functional Test")
    parser.add_argument('--url', type=str, default='http://localhost:5001', help='S1 service URL')
    parser.add_argument('--container', type=str, default='neurosync_s1', help='Container name for log parsing')
    
    args = parser.parse_args()
    
    # Create test instance
    test = S1SpeechControlTest(s1_url=args.url, container_name=args.container)
    
    try:
        # Run all tests
        results = await test.run_all_tests()
        
        # Print summary
        print(f"\n🎯 S1 Speech Control Test Summary")
        print(f"=================================")
        print(f"Test ID: {results['test_id']}")
        print(f"Duration: {results['duration']:.2f} seconds")
        print(f"Overall Success: {'✅ PASSED' if results['overall_success'] else '❌ FAILED'}")
        print(f"\nIndividual Test Results:")
        
        for test_name, test_result in results['tests'].items():
            status = '✅ PASSED' if test_result.get('success', False) else '❌ FAILED'
            print(f"  {test_name}: {status}")
            if not test_result.get('success', False) and 'error' in test_result:
                print(f"    Error: {test_result['error']}")
        
        return 0 if results['overall_success'] else 1
        
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 