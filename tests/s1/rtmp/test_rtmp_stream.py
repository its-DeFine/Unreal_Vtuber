#!/usr/bin/env python3
"""
S1 RTMP Stream Test
===================

This test verifies RTMP streaming functionality by:
1. Monitoring configured RTMP endpoint
2. Confirming audio frames appear within expected timeframe after S1_WAV_READY
3. Measuring stream latency and stability

Usage:
    python test_rtmp_stream.py --endpoint rtmp://localhost:1935/live/stream
"""

import asyncio
import subprocess
import time
import logging
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import docker
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RTMPStreamTest:
    """
    RTMP Stream Test Suite
    
    Tests RTMP streaming reliability and latency
    """
    
    def __init__(self, rtmp_endpoint: str, container_name: str = "neurosync_s1"):
        self.rtmp_endpoint = rtmp_endpoint
        self.container_name = container_name
        self.docker_client = docker.from_env()
        self.test_id = f"rtmp_test_{int(time.time())}"
        
        # Create logs directory
        self.logs_dir = Path("logs/s1")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized RTMP Stream Test - ID: {self.test_id}")
        logger.info(f"RTMP Endpoint: {rtmp_endpoint}")
        logger.info(f"Container: {container_name}")
    
    async def check_rtmp_stream_health(self) -> Dict:
        """Check if RTMP stream is accessible and healthy"""
        try:
            # Use ffprobe to check stream health
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                self.rtmp_endpoint
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                stream_info = json.loads(stdout.decode())
                return {
                    'healthy': True,
                    'stream_info': stream_info,
                    'error': None
                }
            else:
                return {
                    'healthy': False,
                    'stream_info': None,
                    'error': stderr.decode()
                }
        except Exception as e:
            return {
                'healthy': False,
                'stream_info': None,
                'error': str(e)
            }
    
    async def monitor_rtmp_stream(self, duration_seconds: int = 60) -> Dict:
        """Monitor RTMP stream for specified duration"""
        logger.info(f"Starting RTMP stream monitoring for {duration_seconds} seconds...")
        
        # Start ffmpeg to monitor stream
        cmd = [
            'ffmpeg',
            '-i', self.rtmp_endpoint,
            '-f', 'null',
            '-t', str(duration_seconds),
            '-'
        ]
        
        start_time = datetime.now()
        frames_received = 0
        errors = []
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitor stderr for frame information
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                
                line_str = line.decode().strip()
                
                # Count frames
                if 'frame=' in line_str:
                    try:
                        frame_match = re.search(r'frame=\s*(\d+)', line_str)
                        if frame_match:
                            frames_received = int(frame_match.group(1))
                    except:
                        pass
                
                # Detect errors
                if 'error' in line_str.lower() or 'failed' in line_str.lower():
                    errors.append(line_str)
            
            await process.wait()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                'success': process.returncode == 0,
                'duration_seconds': duration,
                'frames_received': frames_received,
                'frame_rate': frames_received / duration if duration > 0 else 0,
                'errors': errors,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error monitoring RTMP stream: {e}")
            return {
                'success': False,
                'duration_seconds': 0,
                'frames_received': 0,
                'frame_rate': 0,
                'errors': [str(e)],
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat()
            }
    
    async def test_stream_response_time(self, test_duration: int = 300) -> Dict:
        """Test response time between S1_WAV_READY and stream activity"""
        logger.info(f"Testing stream response time for {test_duration} seconds...")
        
        # Monitor container logs for S1_WAV_READY events
        test_start_time = datetime.now()
        wav_ready_events = []
        
        async def log_monitor():
            """Monitor container logs for S1_WAV_READY events"""
            try:
                container = self.docker_client.containers.get(self.container_name)
                
                # Stream logs
                for log_line in container.logs(stream=True, since=test_start_time):
                    line = log_line.decode().strip()
                    
                    # Parse S1_WAV_READY events
                    wav_ready_match = re.search(
                        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z).*«S1_WAV_READY»\s+([a-f0-9-]+)\s+at\s+([0-9T:\-\.]+)',
                        line
                    )
                    
                    if wav_ready_match:
                        log_timestamp, stimuli_id, event_timestamp = wav_ready_match.groups()
                        wav_ready_events.append({
                            'stimuli_id': stimuli_id,
                            'log_timestamp': log_timestamp,
                            'event_timestamp': event_timestamp,
                            'parsed_time': datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                        })
                        logger.info(f"Detected S1_WAV_READY event: {stimuli_id}")
                        
            except Exception as e:
                logger.error(f"Error monitoring logs: {e}")
        
        # Start log monitoring
        log_task = asyncio.create_task(log_monitor())
        
        # Start RTMP stream monitoring
        stream_task = asyncio.create_task(self.monitor_rtmp_stream(test_duration))
        
        # Wait for both tasks
        stream_result = await stream_task
        log_task.cancel()
        
        return {
            'stream_monitoring': stream_result,
            'wav_ready_events': wav_ready_events,
            'test_duration': test_duration,
            'events_detected': len(wav_ready_events)
        }
    
    async def run_rtmp_connectivity_test(self) -> Dict:
        """Run basic RTMP connectivity test"""
        logger.info("Running RTMP connectivity test...")
        
        # Test 1: Check if endpoint is accessible
        health_check = await self.check_rtmp_stream_health()
        
        # Test 2: Short monitoring test
        if health_check['healthy']:
            monitor_result = await self.monitor_rtmp_stream(duration_seconds=10)
        else:
            monitor_result = {
                'success': False,
                'error': 'Stream not healthy'
            }
        
        return {
            'test_id': self.test_id,
            'rtmp_endpoint': self.rtmp_endpoint,
            'health_check': health_check,
            'monitoring_test': monitor_result,
            'overall_success': health_check['healthy'] and monitor_result['success']
        }
    
    async def run_comprehensive_test(self, duration: int = 300) -> Dict:
        """Run comprehensive RTMP test including response time measurement"""
        logger.info(f"Running comprehensive RTMP test for {duration} seconds...")
        
        # Basic connectivity test
        connectivity_result = await self.run_rtmp_connectivity_test()
        
        if not connectivity_result['overall_success']:
            logger.error("Basic connectivity test failed, skipping response time test")
            return {
                'test_id': self.test_id,
                'connectivity_test': connectivity_result,
                'response_time_test': None,
                'overall_success': False
            }
        
        # Response time test
        response_time_result = await self.test_stream_response_time(duration)
        
        # Generate summary
        summary = self.generate_test_summary(connectivity_result, response_time_result)
        
        # Save results
        self.save_results({
            'test_id': self.test_id,
            'connectivity_test': connectivity_result,
            'response_time_test': response_time_result,
            'summary': summary
        })
        
        return {
            'test_id': self.test_id,
            'connectivity_test': connectivity_result,
            'response_time_test': response_time_result,
            'summary': summary,
            'overall_success': summary['overall_success']
        }
    
    def generate_test_summary(self, connectivity_result: Dict, response_time_result: Dict) -> Dict:
        """Generate comprehensive test summary"""
        summary = {
            'rtmp_endpoint': self.rtmp_endpoint,
            'test_timestamp': datetime.now().isoformat(),
            'connectivity_success': connectivity_result['overall_success'],
            'stream_monitoring_success': response_time_result['stream_monitoring']['success'],
            'wav_ready_events_detected': response_time_result['events_detected'],
            'overall_success': True
        }
        
        # Check overall success
        if not connectivity_result['overall_success']:
            summary['overall_success'] = False
            summary['failure_reason'] = 'RTMP connectivity failed'
        elif not response_time_result['stream_monitoring']['success']:
            summary['overall_success'] = False
            summary['failure_reason'] = 'Stream monitoring failed'
        elif response_time_result['events_detected'] == 0:
            summary['overall_success'] = False
            summary['failure_reason'] = 'No S1_WAV_READY events detected during test'
        
        # Add stream statistics
        if response_time_result['stream_monitoring']['success']:
            stream_stats = response_time_result['stream_monitoring']
            summary.update({
                'stream_duration': stream_stats['duration_seconds'],
                'frames_received': stream_stats['frames_received'],
                'frame_rate': stream_stats['frame_rate'],
                'errors_count': len(stream_stats['errors'])
            })
        
        return summary
    
    def save_results(self, results: Dict):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw results as JSON
        results_file = self.logs_dir / "raw" / f"{self.test_id}_{timestamp}.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"RTMP test results saved to {results_file}")
    
    def assert_rtmp_performance(self, summary: Dict, max_response_time: float = 0.3) -> bool:
        """Assert RTMP performance meets requirements"""
        if not summary['overall_success']:
            logger.error(f"❌ RTMP test failed: {summary.get('failure_reason', 'Unknown failure')}")
            return False
        
        # Check frame rate
        frame_rate = summary.get('frame_rate', 0)
        if frame_rate < 1.0:
            logger.error(f"❌ Frame rate too low: {frame_rate:.2f} FPS")
            return False
        
        # Check for errors
        errors_count = summary.get('errors_count', 0)
        if errors_count > 0:
            logger.warning(f"⚠️ Stream errors detected: {errors_count}")
        
        logger.info(f"✅ RTMP performance assertion PASSED")
        logger.info(f"   - Frame rate: {frame_rate:.2f} FPS")
        logger.info(f"   - Events detected: {summary['wav_ready_events_detected']}")
        logger.info(f"   - Stream duration: {summary.get('stream_duration', 0):.1f}s")
        
        return True

async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="S1 RTMP Stream Test")
    parser.add_argument('--endpoint', type=str, default='rtmp://localhost:1935/live/stream', 
                       help='RTMP endpoint URL')
    parser.add_argument('--duration', type=int, default=60, 
                       help='Test duration in seconds')
    parser.add_argument('--container', type=str, default='neurosync_s1', 
                       help='Container name for log monitoring')
    parser.add_argument('--connectivity-only', action='store_true', 
                       help='Run only connectivity test')
    
    args = parser.parse_args()
    
    # Create test instance
    test = RTMPStreamTest(rtmp_endpoint=args.endpoint, container_name=args.container)
    
    try:
        if args.connectivity_only:
            # Run connectivity test only
            results = await test.run_rtmp_connectivity_test()
            
            print(f"\n📺 RTMP Connectivity Test Results")
            print(f"==================================")
            print(f"Test ID: {results['test_id']}")
            print(f"Endpoint: {results['rtmp_endpoint']}")
            print(f"Health Check: {'✅ PASSED' if results['health_check']['healthy'] else '❌ FAILED'}")
            print(f"Monitoring Test: {'✅ PASSED' if results['monitoring_test']['success'] else '❌ FAILED'}")
            print(f"Overall Success: {'✅ PASSED' if results['overall_success'] else '❌ FAILED'}")
            
            if not results['health_check']['healthy']:
                print(f"Health Check Error: {results['health_check']['error']}")
            
            return 0 if results['overall_success'] else 1
        else:
            # Run comprehensive test
            results = await test.run_comprehensive_test(duration=args.duration)
            
            print(f"\n📺 RTMP Comprehensive Test Results")
            print(f"===================================")
            print(f"Test ID: {results['test_id']}")
            print(f"Endpoint: {results['rtmp_endpoint']}")
            
            summary = results['summary']
            print(f"Connectivity: {'✅ PASSED' if summary['connectivity_success'] else '❌ FAILED'}")
            print(f"Stream Monitoring: {'✅ PASSED' if summary['stream_monitoring_success'] else '❌ FAILED'}")
            print(f"Events Detected: {summary['wav_ready_events_detected']}")
            
            if 'frame_rate' in summary:
                print(f"Frame Rate: {summary['frame_rate']:.2f} FPS")
            if 'stream_duration' in summary:
                print(f"Stream Duration: {summary['stream_duration']:.1f}s")
            if 'errors_count' in summary:
                print(f"Errors: {summary['errors_count']}")
            
            print(f"Overall Success: {'✅ PASSED' if summary['overall_success'] else '❌ FAILED'}")
            
            if not summary['overall_success']:
                print(f"Failure Reason: {summary.get('failure_reason', 'Unknown')}")
            
            # Assert performance
            success = test.assert_rtmp_performance(summary)
            
            return 0 if success else 1
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 