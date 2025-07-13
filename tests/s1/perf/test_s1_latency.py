#!/usr/bin/env python3
"""
S1 Performance Test - Latency Measurement
==========================================

This test measures the end-to-end latency of the S1 system by:
1. Sending requests to /process_text endpoint
2. Parsing Docker logs for S1_RECEIVED and S1_WAV_READY timestamps
3. Calculating latency statistics with P95 assertion

Usage:
    python test_s1_latency.py --requests 10 --threshold 1.0
"""

import asyncio
import aiohttp
import json
import time
import uuid
import logging
import argparse
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import docker
import re
import csv
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class S1PerformanceTest:
    """
    S1 Performance Test Suite
    
    Measures end-to-end latency from request reception to WAV file ready
    """
    
    def __init__(self, s1_url: str = "http://localhost:5001", container_name: str = "neurosync_s1"):
        self.s1_url = s1_url
        self.container_name = container_name
        self.docker_client = docker.from_env()
        self.results: List[Dict] = []
        self.test_id = f"s1_perf_{int(time.time())}"
        
        # Create logs directory
        self.logs_dir = Path("logs/s1")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized S1 Performance Test - ID: {self.test_id}")
        logger.info(f"Target URL: {s1_url}")
        logger.info(f"Container: {container_name}")
    
    async def send_request(self, session: aiohttp.ClientSession, text: str) -> Dict:
        """Send a single request to the S1 /process_text endpoint"""
        stimuli_id = str(uuid.uuid4())
        
        payload = {
            "text": text,
            "autonomous_context": {
                "test_id": self.test_id,
                "stimuli_id": stimuli_id
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
                    "text": text,
                    "success": response.status == 200
                }
        except Exception as e:
            logger.error(f"Request failed for {stimuli_id}: {e}")
            return {
                "stimuli_id": stimuli_id,
                "request_time": request_time,
                "response_status": 0,
                "response_data": {"error": str(e)},
                "text": text,
                "success": False
            }
    
    def parse_container_logs(self, since_time: datetime) -> Dict[str, Dict]:
        """Parse Docker container logs to extract S1_RECEIVED and S1_WAV_READY timestamps"""
        try:
            container = self.docker_client.containers.get(self.container_name)
            
            # Get logs since test start
            logs = container.logs(
                since=since_time,
                timestamps=True,
                tail=1000
            ).decode('utf-8')
            
            # Parse logs for S1 events
            received_events = {}
            wav_ready_events = {}
            
            # Regex patterns for log parsing
            received_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z).*«S1_RECEIVED»\s+([a-f0-9-]+)\s+at\s+([0-9T:\-\.]+)'
            wav_ready_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z).*«S1_WAV_READY»\s+([a-f0-9-]+)\s+at\s+([0-9T:\-\.]+)'
            
            for line in logs.split('\n'):
                # Parse S1_RECEIVED events
                received_match = re.search(received_pattern, line)
                if received_match:
                    log_timestamp, stimuli_id, event_timestamp = received_match.groups()
                    received_events[stimuli_id] = {
                        'log_timestamp': log_timestamp,
                        'event_timestamp': event_timestamp,
                        'parsed_time': datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                    }
                
                # Parse S1_WAV_READY events
                wav_ready_match = re.search(wav_ready_pattern, line)
                if wav_ready_match:
                    log_timestamp, stimuli_id, event_timestamp = wav_ready_match.groups()
                    wav_ready_events[stimuli_id] = {
                        'log_timestamp': log_timestamp,
                        'event_timestamp': event_timestamp,
                        'parsed_time': datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                    }
            
            logger.info(f"Parsed {len(received_events)} S1_RECEIVED events")
            logger.info(f"Parsed {len(wav_ready_events)} S1_WAV_READY events")
            
            return {
                'received': received_events,
                'wav_ready': wav_ready_events,
                'raw_logs': logs
            }
            
        except Exception as e:
            logger.error(f"Failed to parse container logs: {e}")
            return {'received': {}, 'wav_ready': {}, 'raw_logs': ''}
    
    def calculate_latencies(self, requests: List[Dict], log_events: Dict) -> List[Dict]:
        """Calculate latency for each request"""
        latency_results = []
        
        for req in requests:
            stimuli_id = req['stimuli_id']
            result = {
                'stimuli_id': stimuli_id,
                'text': req['text'],
                'request_success': req['success'],
                'request_time': req['request_time'],
                'response_status': req['response_status']
            }
            
            # Check if we have both timestamps
            if stimuli_id in log_events['received'] and stimuli_id in log_events['wav_ready']:
                received_time = log_events['received'][stimuli_id]['parsed_time']
                wav_ready_time = log_events['wav_ready'][stimuli_id]['parsed_time']
                
                # Calculate latency
                latency = (wav_ready_time - received_time).total_seconds()
                
                result.update({
                    'latency_seconds': latency,
                    'received_timestamp': received_time.isoformat(),
                    'wav_ready_timestamp': wav_ready_time.isoformat(),
                    'latency_success': True
                })
            else:
                result.update({
                    'latency_seconds': None,
                    'received_timestamp': None,
                    'wav_ready_timestamp': None,
                    'latency_success': False,
                    'missing_events': {
                        'received': stimuli_id not in log_events['received'],
                        'wav_ready': stimuli_id not in log_events['wav_ready']
                    }
                })
            
            latency_results.append(result)
        
        return latency_results
    
    def generate_test_texts(self, count: int) -> List[str]:
        """Generate test texts of varying lengths"""
        texts = [
            "Hello world, this is a simple test.",
            "The quick brown fox jumps over the lazy dog.",
            "Artificial intelligence is transforming the way we interact with technology.",
            "In the realm of autonomous systems, real-time processing is crucial for maintaining responsive user experiences.",
            "The integration of text-to-speech technology with facial animation creates immersive virtual characters that can engage users through both auditory and visual channels.",
            "Performance optimization in distributed systems requires careful analysis of latency patterns, bottleneck identification, and systematic improvements to achieve sub-second response times.",
            "Machine learning models trained on diverse datasets can generate more natural speech patterns, but they must be balanced against computational efficiency to ensure real-time processing capabilities.",
            "The future of human-computer interaction lies in seamless integration of multiple modalities, where speech synthesis, facial animation, and contextual understanding work together to create truly intelligent virtual assistants.",
            "Testing methodologies for real-time systems must account for various factors including network latency, processing delays, and system load to ensure consistent performance under different operational conditions."
        ]
        
        # Cycle through texts to get the desired count
        return [texts[i % len(texts)] for i in range(count)]
    
    async def run_performance_test(self, num_requests: int = 10, concurrent_requests: int = 1) -> Dict:
        """Run the complete performance test"""
        logger.info(f"Starting S1 Performance Test - {num_requests} requests, {concurrent_requests} concurrent")
        
        # Generate test texts
        test_texts = self.generate_test_texts(num_requests)
        
        # Record test start time
        test_start_time = datetime.now()
        
        # Send requests
        async with aiohttp.ClientSession() as session:
            if concurrent_requests == 1:
                # Sequential requests
                requests = []
                for text in test_texts:
                    result = await self.send_request(session, text)
                    requests.append(result)
                    logger.info(f"Sent request {len(requests)}/{num_requests} - {result['stimuli_id']}")
                    
                    # Small delay to avoid overwhelming the system
                    await asyncio.sleep(0.1)
            else:
                # Concurrent requests
                tasks = [self.send_request(session, text) for text in test_texts]
                requests = await asyncio.gather(*tasks)
        
        # Wait for processing to complete
        logger.info("Waiting for processing to complete...")
        await asyncio.sleep(max(10, num_requests * 2))  # Wait based on number of requests
        
        # Parse logs
        logger.info("Parsing container logs...")
        log_events = self.parse_container_logs(test_start_time)
        
        # Calculate latencies
        latency_results = self.calculate_latencies(requests, log_events)
        
        # Generate statistics
        stats = self.generate_statistics(latency_results)
        
        # Save results
        self.save_results(latency_results, stats, log_events)
        
        return {
            'test_id': self.test_id,
            'results': latency_results,
            'statistics': stats,
            'test_metadata': {
                'num_requests': num_requests,
                'concurrent_requests': concurrent_requests,
                'test_start_time': test_start_time.isoformat(),
                'test_duration': (datetime.now() - test_start_time).total_seconds()
            }
        }
    
    def generate_statistics(self, results: List[Dict]) -> Dict:
        """Generate comprehensive statistics from test results"""
        # Filter successful latency measurements
        successful_latencies = [r['latency_seconds'] for r in results if r['latency_success'] and r['latency_seconds'] is not None]
        
        if not successful_latencies:
            return {
                'error': 'No successful latency measurements',
                'total_requests': len(results),
                'successful_requests': 0,
                'failed_requests': len(results)
            }
        
        # Calculate statistics
        stats = {
            'total_requests': len(results),
            'successful_requests': len([r for r in results if r['request_success']]),
            'successful_latency_measurements': len(successful_latencies),
            'failed_requests': len([r for r in results if not r['request_success']]),
            'failed_latency_measurements': len([r for r in results if not r['latency_success']]),
            
            'latency_stats': {
                'mean_seconds': statistics.mean(successful_latencies),
                'median_seconds': statistics.median(successful_latencies),
                'min_seconds': min(successful_latencies),
                'max_seconds': max(successful_latencies),
                'std_dev_seconds': statistics.stdev(successful_latencies) if len(successful_latencies) > 1 else 0,
            }
        }
        
        # Add percentiles
        sorted_latencies = sorted(successful_latencies)
        stats['latency_stats']['p50_seconds'] = sorted_latencies[int(len(sorted_latencies) * 0.5)]
        stats['latency_stats']['p95_seconds'] = sorted_latencies[int(len(sorted_latencies) * 0.95)]
        stats['latency_stats']['p99_seconds'] = sorted_latencies[int(len(sorted_latencies) * 0.99)]
        
        return stats
    
    def save_results(self, results: List[Dict], stats: Dict, log_events: Dict):
        """Save test results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw results as JSON
        raw_file = self.logs_dir / "raw" / f"{self.test_id}_{timestamp}.json"
        raw_file.parent.mkdir(exist_ok=True)
        
        with open(raw_file, 'w') as f:
            json.dump({
                'test_id': self.test_id,
                'results': results,
                'statistics': stats,
                'log_events': {
                    'received': {k: v['event_timestamp'] for k, v in log_events['received'].items()},
                    'wav_ready': {k: v['event_timestamp'] for k, v in log_events['wav_ready'].items()}
                },
                'timestamp': timestamp
            }, f, indent=2, default=str)
        
        # Save summary as CSV
        summary_file = self.logs_dir / "summaries" / f"{self.test_id}_{timestamp}.csv"
        summary_file.parent.mkdir(exist_ok=True)
        
        with open(summary_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'stimuli_id', 'text_length', 'request_success', 'latency_success',
                'latency_seconds', 'received_timestamp', 'wav_ready_timestamp'
            ])
            writer.writeheader()
            
            for result in results:
                writer.writerow({
                    'stimuli_id': result['stimuli_id'],
                    'text_length': len(result['text']),
                    'request_success': result['request_success'],
                    'latency_success': result['latency_success'],
                    'latency_seconds': result.get('latency_seconds', ''),
                    'received_timestamp': result.get('received_timestamp', ''),
                    'wav_ready_timestamp': result.get('wav_ready_timestamp', '')
                })
        
        logger.info(f"Results saved to {raw_file} and {summary_file}")
    
    def assert_performance_threshold(self, stats: Dict, threshold_seconds: float = 1.0) -> bool:
        """Assert that P95 latency is below threshold"""
        if 'latency_stats' not in stats:
            logger.error("No latency statistics available for assertion")
            return False
        
        p95_latency = stats['latency_stats']['p95_seconds']
        success = p95_latency < threshold_seconds
        
        if success:
            logger.info(f"✅ Performance assertion PASSED: P95 latency {p95_latency:.3f}s < {threshold_seconds}s")
        else:
            logger.error(f"❌ Performance assertion FAILED: P95 latency {p95_latency:.3f}s >= {threshold_seconds}s")
        
        return success

async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="S1 Performance Test")
    parser.add_argument('--requests', type=int, default=10, help='Number of requests to send')
    parser.add_argument('--concurrent', type=int, default=1, help='Number of concurrent requests')
    parser.add_argument('--threshold', type=float, default=1.0, help='P95 latency threshold in seconds')
    parser.add_argument('--url', type=str, default='http://localhost:5001', help='S1 service URL')
    parser.add_argument('--container', type=str, default='neurosync_s1', help='Container name for log parsing')
    
    args = parser.parse_args()
    
    # Create test instance
    test = S1PerformanceTest(s1_url=args.url, container_name=args.container)
    
    try:
        # Run performance test
        results = await test.run_performance_test(
            num_requests=args.requests,
            concurrent_requests=args.concurrent
        )
        
        # Print results
        stats = results['statistics']
        print(f"\n📊 S1 Performance Test Results")
        print(f"================================")
        print(f"Test ID: {results['test_id']}")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Successful Requests: {stats['successful_requests']}")
        print(f"Failed Requests: {stats['failed_requests']}")
        print(f"Successful Latency Measurements: {stats['successful_latency_measurements']}")
        
        if 'latency_stats' in stats:
            ls = stats['latency_stats']
            print(f"\n⏱️  Latency Statistics:")
            print(f"Mean: {ls['mean_seconds']:.3f}s")
            print(f"Median: {ls['median_seconds']:.3f}s")
            print(f"P95: {ls['p95_seconds']:.3f}s")
            print(f"P99: {ls['p99_seconds']:.3f}s")
            print(f"Min: {ls['min_seconds']:.3f}s")
            print(f"Max: {ls['max_seconds']:.3f}s")
            print(f"Std Dev: {ls['std_dev_seconds']:.3f}s")
        
        # Assert performance threshold
        success = test.assert_performance_threshold(stats, args.threshold)
        
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 