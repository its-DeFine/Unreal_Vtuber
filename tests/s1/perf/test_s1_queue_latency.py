#!/usr/bin/env python3
"""
S1 Queue Performance Test - Latency Measurement with Queue Mode
==============================================================

This test measures the end-to-end latency of the S1 system in queue mode by:
1. Sending requests to /process_text endpoint with interaction_mode="queue"
2. Parsing Docker logs for S1_RECEIVED and S1_WAV_READY timestamps
3. Calculating latency statistics with P95 assertion

Queue mode allows multiple requests to process sequentially without interruption,
ensuring all stimuli complete processing for comprehensive latency measurement.

Usage:
    python test_s1_queue_latency.py --requests 10 --threshold 1.5
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add the parent directory to path to import the base test
sys.path.append(str(Path(__file__).parent))
from test_s1_latency import S1PerformanceTest

class S1QueuePerformanceTest(S1PerformanceTest):
    """
    S1 Queue Performance Test Suite
    
    Extends S1PerformanceTest to measure latency with interaction_mode="queue"
    """
    
    def __init__(self, s1_url: str = "http://localhost:5001", container_name: str = "neurosync_s1"):
        super().__init__(s1_url, container_name)
        self.test_id = f"s1_queue_perf_{int(time.time())}"
        
        # Update logs directory for queue tests
        self.logs_dir = Path("logs/s1/queue")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Initialized S1 Queue Performance Test - ID: {self.test_id}")
        print(f"Mode: Queue (sequential processing)")
    
    async def send_request(self, session, text: str):
        """Send a single request to the S1 /process_text endpoint with queue mode"""
        import uuid
        import time
        from datetime import datetime
        
        stimuli_id = str(uuid.uuid4())
        
        payload = {
            "text": text,
            "interaction_mode": "queue",  # Key difference: use queue mode
            "autonomous_context": {
                "test_id": self.test_id,
                "stimuli_id": stimuli_id,
                "mode": "queue"
            }
        }
        
        request_time = datetime.now()
        
        try:
            async with session.post(
                f"{self.s1_url}/process_text",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)  # Longer timeout for queue mode
            ) as response:
                response_data = await response.json()
                
                return {
                    "stimuli_id": stimuli_id,
                    "request_time": request_time,
                    "response_status": response.status,
                    "response_data": response_data,
                    "text": text,
                    "success": response.status == 200,
                    "mode": "queue"
                }
        except Exception as e:
            print(f"Request failed for {stimuli_id}: {e}")
            return {
                "stimuli_id": stimuli_id,
                "request_time": request_time,
                "response_status": 0,
                "response_data": {"error": str(e)},
                "text": text,
                "success": False,
                "mode": "queue"
            }
    
    async def run_performance_test(self, num_requests: int = 10, concurrent_requests: int = 1):
        """Run the queue mode performance test - always sequential for queue mode"""
        print(f"Starting S1 Queue Performance Test - {num_requests} requests (sequential)")
        print("📋 Queue mode: Each request waits for previous to complete")
        
        # Generate test texts
        test_texts = self.generate_test_texts(num_requests)
        
        # Record test start time
        test_start_time = datetime.now()
        
        # Send requests sequentially (queue mode works best this way)
        import aiohttp
        async with aiohttp.ClientSession() as session:
            requests = []
            for i, text in enumerate(test_texts):
                result = await self.send_request(session, text)
                requests.append(result)
                print(f"Sent queue request {i+1}/{num_requests} - {result['stimuli_id']}")
                
                # Small delay between requests to avoid overwhelming
                await asyncio.sleep(0.2)
        
        # Wait for processing to complete - longer for queue mode
        print("Waiting for queue processing to complete...")
        queue_wait_time = max(15, num_requests * 3)  # More time for sequential processing
        await asyncio.sleep(queue_wait_time)
        
        # Parse logs
        print("Parsing container logs...")
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
                'concurrent_requests': 1,  # Always sequential for queue mode
                'interaction_mode': 'queue',
                'test_start_time': test_start_time.isoformat(),
                'test_duration': (datetime.now() - test_start_time).total_seconds()
            }
        }
    
    def assert_performance_threshold(self, stats, threshold_seconds: float = 1.5):
        """Assert that P95 latency is below threshold - higher default for queue mode"""
        if 'latency_stats' not in stats:
            print("No latency statistics available for assertion")
            return False
        
        p95_latency = stats['latency_stats']['p95_seconds']
        success = p95_latency < threshold_seconds
        
        if success:
            print(f"✅ Queue Performance assertion PASSED: P95 latency {p95_latency:.3f}s < {threshold_seconds}s")
        else:
            print(f"❌ Queue Performance assertion FAILED: P95 latency {p95_latency:.3f}s >= {threshold_seconds}s")
        
        return success

async def main():
    """Main test runner for queue mode"""
    parser = argparse.ArgumentParser(description="S1 Queue Performance Test")
    parser.add_argument('--requests', type=int, default=10, help='Number of requests to send')
    parser.add_argument('--threshold', type=float, default=1.5, help='P95 latency threshold in seconds (higher for queue mode)')
    parser.add_argument('--url', type=str, default='http://localhost:5001', help='S1 service URL')
    parser.add_argument('--container', type=str, default='neurosync_s1', help='Container name for log parsing')
    
    args = parser.parse_args()
    
    # Create test instance
    test = S1QueuePerformanceTest(s1_url=args.url, container_name=args.container)
    
    try:
        # Run performance test
        results = await test.run_performance_test(
            num_requests=args.requests,
            concurrent_requests=1  # Always sequential for queue mode
        )
        
        # Print results
        stats = results['statistics']
        print(f"\n📊 S1 Queue Performance Test Results")
        print(f"=====================================")
        print(f"Test ID: {results['test_id']}")
        print(f"Mode: Queue (sequential processing)")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Successful Requests: {stats['successful_requests']}")
        print(f"Failed Requests: {stats['failed_requests']}")
        print(f"Successful Latency Measurements: {stats['successful_latency_measurements']}")
        
        if 'latency_stats' in stats:
            ls = stats['latency_stats']
            print(f"\n⏱️  Queue Mode Latency Statistics:")
            print(f"Mean: {ls['mean_seconds']:.3f}s")
            print(f"Median: {ls['median_seconds']:.3f}s")
            print(f"P95: {ls['p95_seconds']:.3f}s")
            print(f"P99: {ls['p99_seconds']:.3f}s")
            print(f"Min: {ls['min_seconds']:.3f}s")
            print(f"Max: {ls['max_seconds']:.3f}s")
            print(f"Std Dev: {ls['std_dev_seconds']:.3f}s")
        
        # Assert performance threshold
        success = test.assert_performance_threshold(stats, args.threshold)
        
        print(f"\n💡 Queue mode ensures all requests complete sequentially")
        print(f"💡 Expected higher latency due to sequential processing")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        return 1

if __name__ == "__main__":
    import time
    import aiohttp
    from datetime import datetime
    exit(asyncio.run(main())) 