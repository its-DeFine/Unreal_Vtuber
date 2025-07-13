#!/usr/bin/env python3
"""
S2 Team Latency Performance Test
================================

Comprehensive testing framework for S2 AutoGen team processing performance.
Measures end-to-end latency from S2_RECEIVED to S2_TEAM_COMPLETE.

Usage:
    python test_s2_latency.py --teams trader,educator,streamer --requests 10
    python test_s2_latency.py --container autogen_s2 --threshold 2.0
    python test_s2_latency.py --output results.json --team trader --requests 20

Performance Targets:
    - P95 Latency: < 2.0 seconds (configurable)
    - Success Rate: > 95%
    - Team Processing: All teams functional
    - Tool Invocation: Trackable and measurable
"""

import argparse
import asyncio
import json
import time
import re
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import subprocess
import sys
import uuid
import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class S2LatencyTester:
    """S2 Team processing latency tester with Docker log parsing."""
    
    def __init__(
        self,
        container_name: str = "autogen_s2",
        s2_api_url: str = "http://localhost:8200",
        threshold_seconds: float = 2.0,
        output_dir: str = "logs/s2/summaries"
    ):
        self.container_name = container_name
        self.s2_api_url = s2_api_url
        self.threshold_seconds = threshold_seconds
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Test results
        self.results = []
        self.test_session_id = f"s2_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Timestamp patterns for S2 events
        self.timestamp_patterns = {
            'S2_RECEIVED': re.compile(r'S2_RECEIVED\s+(\S+)\s+(\S+)'),
            'S2_PROCESSING_START': re.compile(r'S2_PROCESSING_START\s+(\S+)\s+(\S+)'),
            'S2_TEAM_START': re.compile(r'S2_TEAM_START\s+(\S+)\s+(\S+)'),
            'S2_TOOLS_AVAILABLE': re.compile(r'S2_TOOLS_AVAILABLE\s+(\S+)\s+(\S+)'),
            'S2_TOOL_INVOKED': re.compile(r'S2_TOOL_INVOKED\s+(\S+)\s+(\S+)\s+(\S+)'),
            'S2_TOOL_COMPLETED': re.compile(r'S2_TOOL_COMPLETED\s+(\S+)\s+(\S+)\s+(\S+)'),
            'S2_INSIGHTS_EXTRACTED': re.compile(r'S2_INSIGHTS_EXTRACTED\s+(\S+)\s+(\S+)'),
            'S2_TEAM_COMPLETE': re.compile(r'S2_TEAM_COMPLETE\s+(\S+)\s+(\S+)'),
            'S2_PROCESSING_COMPLETE': re.compile(r'S2_PROCESSING_COMPLETE\s+(\S+)\s+(\S+)')
        }
        
        logger.info(f"S2 Latency Tester initialized for container: {container_name}")
        logger.info(f"API URL: {s2_api_url}")
        logger.info(f"Latency threshold: {threshold_seconds}s")
    
    def verify_s2_connectivity(self) -> bool:
        """Verify S2 API is accessible."""
        try:
            response = requests.get(f"{self.s2_api_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("✅ S2 API connectivity verified")
                return True
            else:
                logger.error(f"❌ S2 API returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ S2 API connectivity failed: {e}")
            return False
    
    def verify_container_logs(self) -> bool:
        """Verify we can access container logs."""
        try:
            result = subprocess.run(
                ['docker', 'logs', '--tail', '10', self.container_name],
                capture_output=True, text=True, check=True
            )
            logger.info("✅ Container log access verified")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Cannot access container logs: {e}")
            return False
        except FileNotFoundError:
            logger.error("❌ Docker command not found")
            return False
    
    async def send_test_stimuli(self, team_type: str, test_content: str) -> str:
        """Send test stimuli to S2 API and return stimuli_id."""
        stimuli_id = f"test_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "stimuli_id": stimuli_id,
            "content": test_content,
            "source": "latency_test",
            "priority": "medium",
            "metadata": {
                "team_preference": team_type,
                "test_session": self.test_session_id,
                "processing_mode": "s2_only"
            }
        }
        
        try:
            response = requests.post(
                f"{self.s2_api_url}/api/stimuli/receive",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"📤 Sent stimuli {stimuli_id} for {team_type} team")
                return stimuli_id
            else:
                logger.error(f"❌ Failed to send stimuli: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error sending stimuli: {e}")
            return None
    
    def parse_container_logs_for_stimuli(self, stimuli_id: str, since_time: datetime) -> Dict[str, datetime]:
        """Parse container logs to extract timestamps for a specific stimuli."""
        try:
            # Get logs since the specified time
            since_str = since_time.strftime('%Y-%m-%dT%H:%M:%S')
            result = subprocess.run(
                ['docker', 'logs', '--since', since_str, self.container_name],
                capture_output=True, text=True, check=True
            )
            
            events = {}
            tool_events = []
            
            for line in result.stdout.split('\n'):
                for event_name, pattern in self.timestamp_patterns.items():
                    match = pattern.search(line)
                    if match:
                        matched_stimuli_id = match.group(1)
                        if matched_stimuli_id == stimuli_id:
                            timestamp_str = match.group(2)
                            if event_name in ['S2_TOOL_INVOKED', 'S2_TOOL_COMPLETED']:
                                tool_name = match.group(3) if len(match.groups()) >= 3 else 'unknown'
                                tool_events.append({
                                    'event': event_name,
                                    'tool': tool_name,
                                    'timestamp': datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                })
                            else:
                                try:
                                    events[event_name] = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                except ValueError:
                                    logger.warning(f"Could not parse timestamp: {timestamp_str}")
            
            # Add tool events to main events dict
            events['tool_events'] = tool_events
            
            return events
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error parsing container logs: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing logs: {e}")
            return {}
    
    def calculate_latencies(self, events: Dict[str, datetime]) -> Dict[str, float]:
        """Calculate various latency metrics from parsed events."""
        latencies = {}
        
        try:
            # Core S2 processing latency (S2_RECEIVED to S2_PROCESSING_COMPLETE)
            if 'S2_RECEIVED' in events and 'S2_PROCESSING_COMPLETE' in events:
                latencies['total_processing'] = (
                    events['S2_PROCESSING_COMPLETE'] - events['S2_RECEIVED']
                ).total_seconds()
            
            # Team processing latency (S2_TEAM_START to S2_TEAM_COMPLETE)
            if 'S2_TEAM_START' in events and 'S2_TEAM_COMPLETE' in events:
                latencies['team_processing'] = (
                    events['S2_TEAM_COMPLETE'] - events['S2_TEAM_START']
                ).total_seconds()
            
            # Processing overhead (S2_RECEIVED to S2_TEAM_START)
            if 'S2_RECEIVED' in events and 'S2_TEAM_START' in events:
                latencies['processing_overhead'] = (
                    events['S2_TEAM_START'] - events['S2_RECEIVED']
                ).total_seconds()
            
            # Insights extraction time (S2_INSIGHTS_EXTRACTED to S2_TEAM_COMPLETE)
            if 'S2_INSIGHTS_EXTRACTED' in events and 'S2_TEAM_COMPLETE' in events:
                latencies['insights_extraction'] = (
                    events['S2_TEAM_COMPLETE'] - events['S2_INSIGHTS_EXTRACTED']
                ).total_seconds()
            
            # Tool processing time
            tool_events = events.get('tool_events', [])
            if tool_events:
                tool_latencies = []
                invoked_tools = [e for e in tool_events if e['event'] == 'S2_TOOL_INVOKED']
                completed_tools = [e for e in tool_events if e['event'] == 'S2_TOOL_COMPLETED']
                
                for invoked in invoked_tools:
                    for completed in completed_tools:
                        if invoked['tool'] == completed['tool']:
                            tool_latency = (completed['timestamp'] - invoked['timestamp']).total_seconds()
                            tool_latencies.append(tool_latency)
                            break
                
                if tool_latencies:
                    latencies['tool_processing_avg'] = statistics.mean(tool_latencies)
                    latencies['tool_processing_max'] = max(tool_latencies)
                    latencies['tool_count'] = len(tool_latencies)
        
        except Exception as e:
            logger.error(f"❌ Error calculating latencies: {e}")
        
        return latencies
    
    async def run_single_test(self, team_type: str, test_content: str) -> Optional[Dict]:
        """Run a single latency test for a specific team."""
        logger.info(f"🔄 Testing {team_type} team latency...")
        
        # Record start time for log parsing
        start_time = datetime.now()
        
        # Send stimuli
        stimuli_id = await self.send_test_stimuli(team_type, test_content)
        if not stimuli_id:
            return None
        
        # Wait for processing (with timeout)
        await asyncio.sleep(10)  # Give time for processing
        
        # Parse logs to get events
        events = self.parse_container_logs_for_stimuli(stimuli_id, start_time)
        
        if not events:
            logger.warning(f"⚠️ No events found for stimuli {stimuli_id}")
            return None
        
        # Calculate latencies
        latencies = self.calculate_latencies(events)
        
        # Build result
        result = {
            'stimuli_id': stimuli_id,
            'team_type': team_type,
            'test_content': test_content[:50],
            'timestamp': start_time.isoformat(),
            'events': {k: v.isoformat() if isinstance(v, datetime) else v for k, v in events.items()},
            'latencies': latencies,
            'success': len(latencies) > 0,
            'tool_events_count': len(events.get('tool_events', []))
        }
        
        # Check if we met the latency threshold
        total_latency = latencies.get('total_processing', float('inf'))
        result['meets_threshold'] = total_latency <= self.threshold_seconds
        
        logger.info(f"📊 {team_type} team: {total_latency:.3f}s (threshold: {self.threshold_seconds}s)")
        
        return result
    
    async def run_team_tests(self, teams: List[str], requests_per_team: int) -> List[Dict]:
        """Run latency tests for multiple teams."""
        logger.info(f"🚀 Starting S2 latency tests for teams: {teams}")
        logger.info(f"Requests per team: {requests_per_team}")
        
        all_results = []
        
        # Test content templates for different teams
        test_templates = {
            'trader': [
                "Analyze Bitcoin's current market position and potential trading opportunities",
                "What are the key technical indicators for Ethereum right now?",
                "Evaluate the risk-reward ratio for a swing trade on AAPL",
                "Assess the impact of recent Fed policy on cryptocurrency markets"
            ],
            'educator': [
                "Explain quantum computing concepts for undergraduate students",
                "Create a lesson plan for teaching Python programming basics",
                "Design an assessment for machine learning fundamentals",
                "Develop educational content about sustainable energy systems"
            ],
            'streamer': [
                "Generate engaging content ideas for a gaming livestream",
                "Plan a community event to increase audience engagement",
                "Create interactive segments for a variety show format",
                "Develop strategies for growing a streaming audience"
            ]
        }
        
        for team in teams:
            team_templates = test_templates.get(team, [f"Analyze and provide insights about {team} topics"])
            
            for i in range(requests_per_team):
                # Rotate through test templates
                test_content = team_templates[i % len(team_templates)]
                
                result = await self.run_single_test(team, test_content)
                if result:
                    all_results.append(result)
                    self.results.append(result)
                
                # Brief pause between requests
                if i < requests_per_team - 1:
                    await asyncio.sleep(2)
        
        return all_results
    
    def calculate_statistics(self, results: List[Dict]) -> Dict:
        """Calculate performance statistics from test results."""
        if not results:
            return {}
        
        # Extract total processing latencies
        total_latencies = [r['latencies'].get('total_processing') for r in results if r['latencies'].get('total_processing')]
        team_latencies = [r['latencies'].get('team_processing') for r in results if r['latencies'].get('team_processing')]
        
        if not total_latencies:
            return {'error': 'No valid latencies found'}
        
        # Calculate statistics
        stats = {
            'test_count': len(results),
            'success_count': sum(1 for r in results if r['success']),
            'success_rate': sum(1 for r in results if r['success']) / len(results),
            'threshold_met_count': sum(1 for r in results if r['meets_threshold']),
            'threshold_met_rate': sum(1 for r in results if r['meets_threshold']) / len(results),
            
            # Total processing latencies
            'total_processing': {
                'mean': statistics.mean(total_latencies),
                'median': statistics.median(total_latencies),
                'std_dev': statistics.stdev(total_latencies) if len(total_latencies) > 1 else 0,
                'min': min(total_latencies),
                'max': max(total_latencies),
                'p95': self.percentile(total_latencies, 95),
                'p99': self.percentile(total_latencies, 99)
            },
            
            # Team processing latencies (if available)
            'team_processing': {},
            
            # Per-team breakdown
            'by_team': {}
        }
        
        if team_latencies:
            stats['team_processing'] = {
                'mean': statistics.mean(team_latencies),
                'median': statistics.median(team_latencies),
                'std_dev': statistics.stdev(team_latencies) if len(team_latencies) > 1 else 0,
                'min': min(team_latencies),
                'max': max(team_latencies),
                'p95': self.percentile(team_latencies, 95),
                'p99': self.percentile(team_latencies, 99)
            }
        
        # Per-team statistics
        teams = set(r['team_type'] for r in results)
        for team in teams:
            team_results = [r for r in results if r['team_type'] == team]
            team_total_latencies = [r['latencies'].get('total_processing') for r in team_results if r['latencies'].get('total_processing')]
            
            if team_total_latencies:
                stats['by_team'][team] = {
                    'count': len(team_results),
                    'success_rate': sum(1 for r in team_results if r['success']) / len(team_results),
                    'mean_latency': statistics.mean(team_total_latencies),
                    'p95_latency': self.percentile(team_total_latencies, 95),
                    'threshold_met_rate': sum(1 for r in team_results if r['meets_threshold']) / len(team_results)
                }
        
        return stats
    
    @staticmethod
    def percentile(data: List[float], percentile: float) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index == int(index):
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def save_results(self, results: List[Dict], stats: Dict) -> str:
        """Save test results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"s2_latency_test_{timestamp}.json"
        filepath = self.output_dir / filename
        
        output_data = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'session_id': self.test_session_id,
                'container_name': self.container_name,
                'api_url': self.s2_api_url,
                'threshold_seconds': self.threshold_seconds,
                'total_tests': len(results)
            },
            'statistics': stats,
            'results': results
        }
        
        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"📁 Results saved to: {filepath}")
        return str(filepath)
    
    def print_summary(self, stats: Dict):
        """Print test summary to console."""
        print("\n" + "="*60)
        print("S2 TEAM LATENCY TEST SUMMARY")
        print("="*60)
        
        if 'error' in stats:
            print(f"❌ Error: {stats['error']}")
            return
        
        print(f"Total Tests: {stats['test_count']}")
        print(f"Success Rate: {stats['success_rate']:.1%}")
        print(f"Threshold Met: {stats['threshold_met_rate']:.1%} (< {self.threshold_seconds}s)")
        
        total_proc = stats.get('total_processing', {})
        if total_proc:
            print(f"\nTotal Processing Latency:")
            print(f"  Mean: {total_proc['mean']:.3f}s")
            print(f"  P95:  {total_proc['p95']:.3f}s")
            print(f"  P99:  {total_proc['p99']:.3f}s")
            print(f"  Max:  {total_proc['max']:.3f}s")
        
        team_proc = stats.get('team_processing', {})
        if team_proc:
            print(f"\nTeam Processing Latency:")
            print(f"  Mean: {team_proc['mean']:.3f}s")
            print(f"  P95:  {team_proc['p95']:.3f}s")
            print(f"  P99:  {team_proc['p99']:.3f}s")
        
        # Per-team breakdown
        by_team = stats.get('by_team', {})
        if by_team:
            print(f"\nPer-Team Performance:")
            for team, team_stats in by_team.items():
                status = "✅" if team_stats['p95_latency'] <= self.threshold_seconds else "❌"
                print(f"  {status} {team.upper()}: {team_stats['mean_latency']:.3f}s avg, {team_stats['p95_latency']:.3f}s P95")
        
        print("="*60)
    
    def assert_performance_targets(self, stats: Dict) -> bool:
        """Assert that performance targets are met."""
        if 'error' in stats:
            logger.error(f"❌ Performance test failed: {stats['error']}")
            return False
        
        success = True
        
        # Check success rate
        if stats['success_rate'] < 0.95:
            logger.error(f"❌ Success rate {stats['success_rate']:.1%} < 95%")
            success = False
        
        # Check P95 latency
        total_proc = stats.get('total_processing', {})
        if total_proc and total_proc['p95'] > self.threshold_seconds:
            logger.error(f"❌ P95 latency {total_proc['p95']:.3f}s > {self.threshold_seconds}s")
            success = False
        
        # Check per-team performance
        by_team = stats.get('by_team', {})
        for team, team_stats in by_team.items():
            if team_stats['p95_latency'] > self.threshold_seconds:
                logger.error(f"❌ {team} team P95 {team_stats['p95_latency']:.3f}s > {self.threshold_seconds}s")
                success = False
        
        if success:
            logger.info("✅ All performance targets met!")
        
        return success


async def main():
    parser = argparse.ArgumentParser(description='S2 Team Latency Performance Test')
    parser.add_argument('--teams', default='trader,educator,streamer', 
                        help='Comma-separated list of teams to test')
    parser.add_argument('--requests', type=int, default=5,
                        help='Number of requests per team')
    parser.add_argument('--container', default='autogen_s2',
                        help='Docker container name')
    parser.add_argument('--api-url', default='http://localhost:8200',
                        help='S2 API URL')
    parser.add_argument('--threshold', type=float, default=2.0,
                        help='Latency threshold in seconds')
    parser.add_argument('--output', help='Output JSON file path')
    parser.add_argument('--assert-targets', action='store_true',
                        help='Assert performance targets (exit code 1 if failed)')
    
    args = parser.parse_args()
    
    # Parse teams
    teams = [team.strip() for team in args.teams.split(',')]
    
    # Initialize tester
    tester = S2LatencyTester(
        container_name=args.container,
        s2_api_url=args.api_url,
        threshold_seconds=args.threshold
    )
    
    # Verify prerequisites
    if not tester.verify_s2_connectivity():
        logger.error("❌ S2 API not accessible")
        sys.exit(1)
    
    if not tester.verify_container_logs():
        logger.error("❌ Container logs not accessible")
        sys.exit(1)
    
    # Run tests
    results = await tester.run_team_tests(teams, args.requests)
    
    if not results:
        logger.error("❌ No test results obtained")
        sys.exit(1)
    
    # Calculate statistics
    stats = tester.calculate_statistics(results)
    
    # Save results
    if args.output:
        output_path = args.output
    else:
        output_path = tester.save_results(results, stats)
    
    # Print summary
    tester.print_summary(stats)
    
    # Assert performance if requested
    if args.assert_targets:
        if not tester.assert_performance_targets(stats):
            sys.exit(1)
    
    logger.info(f"✅ S2 latency test completed. Results: {output_path}")


if __name__ == '__main__':
    asyncio.run(main()) 