#!/usr/bin/env python3
"""
S2 Tool Usage Verification Test
===============================

Comprehensive testing framework for S2 AutoGen team tool usage validation.
Verifies that tools are invoked correctly and tracks decision-making patterns.

Usage:
    python test_tool_usage.py --teams trader,educator,streamer --scenarios 5
    python test_tool_usage.py --container autogen_s2 --verify-alignment
    python test_tool_usage.py --output tool_usage_report.json --team trader

Validation Targets:
    - Tool Invocation Alignment: 100% correct tool selection
    - Decision Tracking: Complete tool decision logging
    - Tool Performance: Individual tool execution success
    - Team Tool Coverage: All expected tools for each team type
"""

import argparse
import asyncio
import json
import time
import re
import requests
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import logging
import uuid
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class S2ToolUsageTester:
    """S2 Tool usage verification and alignment tester."""
    
    def __init__(
        self,
        container_name: str = "autogen_s2",
        s2_api_url: str = "http://localhost:8200",
        output_dir: str = "logs/s2/summaries"
    ):
        self.container_name = container_name
        self.s2_api_url = s2_api_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Test results
        self.results = []
        self.test_session_id = f"tool_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Expected tools per team type (from the codebase analysis)
        self.expected_tools = {
            'trader': {
                'market_data', 'trading_analysis', 'risk_assessment', 
                'technical_indicators', 'portfolio_analysis', 'market_trends',
                'system_status', 'communication', 'utility'  # Common tools
            },
            'educator': {
                'educational_content', 'curriculum_design', 'assessment_creation',
                'learning_analytics', 'lesson_planning', 'knowledge_assessment',
                'system_status', 'communication', 'utility'  # Common tools
            },
            'streamer': {
                'content_creation', 'community_management', 'streaming_analytics',
                'audience_engagement', 'social_media', 'performance_tracking',
                'system_status', 'communication', 'utility'  # Common tools
            }
        }
        
        # Tool invocation patterns
        self.tool_patterns = {
            'invoked': re.compile(r'S2_TOOL_INVOKED\s+(\S+)\s+(\S+)\s+(\S+)'),
            'completed': re.compile(r'S2_TOOL_COMPLETED\s+(\S+)\s+(\S+)\s+(\S+)')
        }
        
        # Test scenarios designed to trigger specific tools
        self.tool_scenarios = {
            'trader': [
                {
                    'content': 'Analyze Bitcoin market trends and provide trading insights',
                    'expected_tools': {'market_data', 'trading_analysis', 'technical_indicators'},
                    'scenario_name': 'crypto_analysis'
                },
                {
                    'content': 'Assess risk factors for a diversified portfolio investment',
                    'expected_tools': {'risk_assessment', 'portfolio_analysis', 'market_data'},
                    'scenario_name': 'risk_assessment'
                },
                {
                    'content': 'What are the current technical indicators for major indices?',
                    'expected_tools': {'technical_indicators', 'market_data'},
                    'scenario_name': 'technical_analysis'
                }
            ],
            'educator': [
                {
                    'content': 'Create a comprehensive lesson plan for machine learning basics',
                    'expected_tools': {'educational_content', 'curriculum_design', 'lesson_planning'},
                    'scenario_name': 'lesson_creation'
                },
                {
                    'content': 'Design assessment questions for Python programming course',
                    'expected_tools': {'assessment_creation', 'educational_content'},
                    'scenario_name': 'assessment_design'
                },
                {
                    'content': 'Structure a complete curriculum for data science fundamentals',
                    'expected_tools': {'curriculum_design', 'learning_analytics', 'educational_content'},
                    'scenario_name': 'curriculum_design'
                }
            ],
            'streamer': [
                {
                    'content': 'Generate engaging content ideas for a gaming livestream',
                    'expected_tools': {'content_creation', 'audience_engagement'},
                    'scenario_name': 'content_generation'
                },
                {
                    'content': 'Analyze streaming performance and suggest improvements',
                    'expected_tools': {'streaming_analytics', 'performance_tracking', 'community_management'},
                    'scenario_name': 'performance_analysis'
                },
                {
                    'content': 'Develop strategies to grow streaming community engagement',
                    'expected_tools': {'community_management', 'audience_engagement', 'social_media'},
                    'scenario_name': 'community_growth'
                }
            ]
        }
        
        logger.info(f"S2 Tool Usage Tester initialized for container: {container_name}")
        logger.info(f"API URL: {s2_api_url}")
    
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
    
    def get_available_tools(self) -> Dict[str, any]:
        """Get list of available tools from S2 API."""
        try:
            response = requests.get(f"{self.s2_api_url}/api/stimuli/tools", timeout=10)
            if response.status_code == 200:
                tools_info = response.json()
                logger.info(f"✅ Retrieved {tools_info.get('tool_count', 0)} available tools")
                return tools_info
            else:
                logger.error(f"❌ Failed to get tools: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"❌ Error getting available tools: {e}")
            return {}
    
    async def send_test_stimuli(self, team_type: str, scenario: Dict) -> str:
        """Send test stimuli designed to trigger specific tools."""
        stimuli_id = f"tool_test_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "stimuli_id": stimuli_id,
            "content": scenario['content'],
            "source": "tool_usage_test",
            "priority": "medium",
            "metadata": {
                "team_preference": team_type,
                "test_session": self.test_session_id,
                "scenario_name": scenario['scenario_name'],
                "expected_tools": list(scenario['expected_tools']),
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
                logger.info(f"📤 Sent tool test stimuli {stimuli_id} for {team_type} ({scenario['scenario_name']})")
                return stimuli_id
            else:
                logger.error(f"❌ Failed to send stimuli: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error sending stimuli: {e}")
            return None
    
    def parse_tool_usage_from_logs(self, stimuli_id: str, since_time: datetime) -> Dict[str, List]:
        """Parse container logs to extract tool usage for a specific stimuli."""
        try:
            # Get logs since the specified time
            since_str = since_time.strftime('%Y-%m-%dT%H:%M:%S')
            result = subprocess.run(
                ['docker', 'logs', '--since', since_str, self.container_name],
                capture_output=True, text=True, check=True
            )
            
            tool_events = {
                'invoked': [],
                'completed': [],
                'failed': []
            }
            
            for line in result.stdout.split('\n'):
                # Check for tool invocation
                invoked_match = self.tool_patterns['invoked'].search(line)
                if invoked_match and invoked_match.group(1) == stimuli_id:
                    tool_name = invoked_match.group(2)
                    timestamp_str = invoked_match.group(3)
                    tool_events['invoked'].append({
                        'tool': tool_name,
                        'timestamp': timestamp_str,
                        'stimuli_id': stimuli_id
                    })
                
                # Check for tool completion
                completed_match = self.tool_patterns['completed'].search(line)
                if completed_match and completed_match.group(1) == stimuli_id:
                    tool_name = completed_match.group(2)
                    timestamp_str = completed_match.group(3)
                    tool_events['completed'].append({
                        'tool': tool_name,
                        'timestamp': timestamp_str,
                        'stimuli_id': stimuli_id
                    })
                
                # Check for tool errors (basic pattern)
                if stimuli_id in line and 'ERROR' in line and 'tool' in line.lower():
                    tool_events['failed'].append({
                        'error_line': line.strip(),
                        'stimuli_id': stimuli_id
                    })
            
            return tool_events
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error parsing container logs: {e}")
            return {'invoked': [], 'completed': [], 'failed': []}
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing logs: {e}")
            return {'invoked': [], 'completed': [], 'failed': []}
    
    def analyze_tool_alignment(self, scenario: Dict, tool_events: Dict) -> Dict:
        """Analyze tool usage alignment with expected tools."""
        expected_tools = scenario['expected_tools']
        invoked_tools = set(event['tool'] for event in tool_events['invoked'])
        completed_tools = set(event['tool'] for event in tool_events['completed'])
        
        analysis = {
            'scenario_name': scenario['scenario_name'],
            'expected_tools': list(expected_tools),
            'invoked_tools': list(invoked_tools),
            'completed_tools': list(completed_tools),
            'alignment_score': 0.0,
            'coverage_score': 0.0,
            'precision_score': 0.0,
            'tool_success_rate': 0.0,
            'missing_tools': list(expected_tools - invoked_tools),
            'unexpected_tools': list(invoked_tools - expected_tools),
            'failed_tools': len(tool_events['failed'])
        }
        
        # Calculate alignment score (how many expected tools were invoked)
        if expected_tools:
            analysis['coverage_score'] = len(expected_tools & invoked_tools) / len(expected_tools)
        
        # Calculate precision score (how many invoked tools were expected)
        if invoked_tools:
            analysis['precision_score'] = len(expected_tools & invoked_tools) / len(invoked_tools)
        
        # Calculate tool success rate
        if invoked_tools:
            analysis['tool_success_rate'] = len(completed_tools) / len(invoked_tools)
        
        # Overall alignment score (balanced between coverage and precision)
        analysis['alignment_score'] = (analysis['coverage_score'] + analysis['precision_score']) / 2
        
        return analysis
    
    async def run_tool_scenario_test(self, team_type: str, scenario: Dict) -> Optional[Dict]:
        """Run a single tool usage scenario test."""
        logger.info(f"🔧 Testing {team_type} tool usage: {scenario['scenario_name']}")
        
        # Record start time for log parsing
        start_time = datetime.now()
        
        # Send stimuli
        stimuli_id = await self.send_test_stimuli(team_type, scenario)
        if not stimuli_id:
            return None
        
        # Wait for processing
        await asyncio.sleep(15)  # Give more time for tool usage
        
        # Parse tool usage from logs
        tool_events = self.parse_tool_usage_from_logs(stimuli_id, start_time)
        
        # Analyze tool alignment
        alignment_analysis = self.analyze_tool_alignment(scenario, tool_events)
        
        # Build result
        result = {
            'stimuli_id': stimuli_id,
            'team_type': team_type,
            'scenario': scenario,
            'timestamp': start_time.isoformat(),
            'tool_events': tool_events,
            'alignment_analysis': alignment_analysis,
            'success': len(tool_events['invoked']) > 0
        }
        
        # Log results
        logger.info(f"📊 {team_type}/{scenario['scenario_name']}: "
                   f"Alignment: {alignment_analysis['alignment_score']:.2f}, "
                   f"Tools: {len(tool_events['invoked'])} invoked, "
                   f"{len(tool_events['completed'])} completed")
        
        return result
    
    async def run_team_tool_tests(self, teams: List[str], scenarios_per_team: int) -> List[Dict]:
        """Run tool usage tests for multiple teams."""
        logger.info(f"🚀 Starting S2 tool usage tests for teams: {teams}")
        logger.info(f"Scenarios per team: {scenarios_per_team}")
        
        all_results = []
        
        for team in teams:
            team_scenarios = self.tool_scenarios.get(team, [])
            
            if not team_scenarios:
                logger.warning(f"⚠️ No scenarios defined for team: {team}")
                continue
            
            for i in range(scenarios_per_team):
                # Rotate through available scenarios
                scenario = team_scenarios[i % len(team_scenarios)]
                
                result = await self.run_tool_scenario_test(team, scenario)
                if result:
                    all_results.append(result)
                    self.results.append(result)
                
                # Brief pause between tests
                if i < scenarios_per_team - 1:
                    await asyncio.sleep(3)
        
        return all_results
    
    def calculate_tool_statistics(self, results: List[Dict]) -> Dict:
        """Calculate comprehensive tool usage statistics."""
        if not results:
            return {}
        
        # Overall statistics
        stats = {
            'test_count': len(results),
            'success_count': sum(1 for r in results if r['success']),
            'success_rate': sum(1 for r in results if r['success']) / len(results),
            'total_tools_invoked': sum(len(r['tool_events']['invoked']) for r in results),
            'total_tools_completed': sum(len(r['tool_events']['completed']) for r in results),
            'tool_completion_rate': 0.0,
            'average_alignment_score': 0.0,
            'average_coverage_score': 0.0,
            'average_precision_score': 0.0,
            'perfect_alignment_count': 0,
            'by_team': {},
            'tool_usage_frequency': defaultdict(int),
            'tool_success_frequency': defaultdict(int)
        }
        
        # Calculate tool completion rate
        if stats['total_tools_invoked'] > 0:
            stats['tool_completion_rate'] = stats['total_tools_completed'] / stats['total_tools_invoked']
        
        # Calculate average alignment scores
        alignment_scores = [r['alignment_analysis']['alignment_score'] for r in results]
        coverage_scores = [r['alignment_analysis']['coverage_score'] for r in results]
        precision_scores = [r['alignment_analysis']['precision_score'] for r in results]
        
        if alignment_scores:
            stats['average_alignment_score'] = sum(alignment_scores) / len(alignment_scores)
            stats['average_coverage_score'] = sum(coverage_scores) / len(coverage_scores)
            stats['average_precision_score'] = sum(precision_scores) / len(precision_scores)
            stats['perfect_alignment_count'] = sum(1 for score in alignment_scores if score >= 1.0)
        
        # Tool usage frequency analysis
        for result in results:
            for tool_event in result['tool_events']['invoked']:
                tool_name = tool_event['tool']
                stats['tool_usage_frequency'][tool_name] += 1
            
            for tool_event in result['tool_events']['completed']:
                tool_name = tool_event['tool']
                stats['tool_success_frequency'][tool_name] += 1
        
        # Per-team analysis
        teams = set(r['team_type'] for r in results)
        for team in teams:
            team_results = [r for r in results if r['team_type'] == team]
            team_alignments = [r['alignment_analysis']['alignment_score'] for r in team_results]
            team_coverages = [r['alignment_analysis']['coverage_score'] for r in team_results]
            
            stats['by_team'][team] = {
                'test_count': len(team_results),
                'success_rate': sum(1 for r in team_results if r['success']) / len(team_results),
                'average_alignment': sum(team_alignments) / len(team_alignments) if team_alignments else 0,
                'average_coverage': sum(team_coverages) / len(team_coverages) if team_coverages else 0,
                'perfect_alignment_rate': sum(1 for score in team_alignments if score >= 1.0) / len(team_alignments) if team_alignments else 0,
                'tools_invoked': sum(len(r['tool_events']['invoked']) for r in team_results),
                'tools_completed': sum(len(r['tool_events']['completed']) for r in team_results)
            }
        
        return stats
    
    def validate_tool_coverage(self, results: List[Dict]) -> Dict:
        """Validate that teams have access to expected tools."""
        coverage_analysis = {
            'teams_analyzed': set(),
            'expected_vs_available': {},
            'missing_tools_by_team': {},
            'coverage_scores': {}
        }
        
        for result in results:
            team = result['team_type']
            coverage_analysis['teams_analyzed'].add(team)
            
            if team not in coverage_analysis['missing_tools_by_team']:
                coverage_analysis['missing_tools_by_team'][team] = set()
            
            # Get tools that were invoked for this team
            invoked_tools = set(event['tool'] for event in result['tool_events']['invoked'])
            expected_tools = self.expected_tools.get(team, set())
            
            # Track missing tools
            missing_tools = expected_tools - invoked_tools
            coverage_analysis['missing_tools_by_team'][team].update(missing_tools)
        
        # Calculate coverage scores
        for team in coverage_analysis['teams_analyzed']:
            expected_tools = self.expected_tools.get(team, set())
            missing_tools = coverage_analysis['missing_tools_by_team'][team]
            
            if expected_tools:
                coverage_score = 1.0 - (len(missing_tools) / len(expected_tools))
                coverage_analysis['coverage_scores'][team] = coverage_score
                coverage_analysis['expected_vs_available'][team] = {
                    'expected_count': len(expected_tools),
                    'missing_count': len(missing_tools),
                    'missing_tools': list(missing_tools)
                }
        
        return coverage_analysis
    
    def save_results(self, results: List[Dict], stats: Dict, coverage: Dict) -> str:
        """Save test results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"s2_tool_usage_test_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # Convert sets to lists for JSON serialization
        coverage_json = {}
        for key, value in coverage.items():
            if isinstance(value, set):
                coverage_json[key] = list(value)
            elif isinstance(value, dict):
                coverage_json[key] = {}
                for k, v in value.items():
                    if isinstance(v, set):
                        coverage_json[key][k] = list(v)
                    else:
                        coverage_json[key][k] = v
            else:
                coverage_json[key] = value
        
        # Convert expected_tools sets to lists
        expected_tools_json = {}
        for team, tools in self.expected_tools.items():
            expected_tools_json[team] = list(tools)
        
        # Convert test_scenarios sets to lists
        test_scenarios_json = {}
        for team, scenarios in self.tool_scenarios.items():
            test_scenarios_json[team] = []
            for scenario in scenarios:
                scenario_copy = scenario.copy()
                scenario_copy['expected_tools'] = list(scenario['expected_tools'])
                test_scenarios_json[team].append(scenario_copy)
        
        output_data = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'session_id': self.test_session_id,
                'container_name': self.container_name,
                'api_url': self.s2_api_url,
                'total_tests': len(results)
            },
            'statistics': stats,
            'coverage_analysis': coverage_json,
            'expected_tools_by_team': expected_tools_json,
            'test_scenarios': test_scenarios_json,
            'results': results
        }
        
        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"📁 Results saved to: {filepath}")
        return str(filepath)
    
    def print_summary(self, stats: Dict, coverage: Dict):
        """Print test summary to console."""
        print("\n" + "="*70)
        print("S2 TOOL USAGE VERIFICATION SUMMARY")
        print("="*70)
        
        print(f"Total Tests: {stats['test_count']}")
        print(f"Success Rate: {stats['success_rate']:.1%}")
        print(f"Tools Invoked: {stats['total_tools_invoked']}")
        print(f"Tools Completed: {stats['total_tools_completed']}")
        print(f"Tool Completion Rate: {stats['tool_completion_rate']:.1%}")
        
        print(f"\nAlignment Scores:")
        print(f"  Average Alignment: {stats['average_alignment_score']:.3f}")
        print(f"  Average Coverage:  {stats['average_coverage_score']:.3f}")
        print(f"  Average Precision: {stats['average_precision_score']:.3f}")
        print(f"  Perfect Alignment: {stats['perfect_alignment_count']}/{stats['test_count']}")
        
        # Per-team performance
        print(f"\nPer-Team Performance:")
        for team, team_stats in stats['by_team'].items():
            status = "✅" if team_stats['average_alignment'] >= 0.8 else "❌"
            print(f"  {status} {team.upper()}: {team_stats['average_alignment']:.3f} alignment, "
                  f"{team_stats['tools_invoked']} tools invoked")
        
        # Tool coverage
        print(f"\nTool Coverage Analysis:")
        for team, coverage_info in coverage['expected_vs_available'].items():
            missing_count = coverage_info['missing_count']
            expected_count = coverage_info['expected_count']
            coverage_pct = (1 - missing_count / expected_count) * 100 if expected_count > 0 else 100
            status = "✅" if missing_count == 0 else "⚠️"
            print(f"  {status} {team.upper()}: {coverage_pct:.1f}% coverage "
                  f"({missing_count} missing of {expected_count} expected)")
        
        # Most used tools
        if stats['tool_usage_frequency']:
            print(f"\nMost Used Tools:")
            sorted_tools = sorted(stats['tool_usage_frequency'].items(), key=lambda x: x[1], reverse=True)
            for tool, count in sorted_tools[:5]:
                success_rate = (stats['tool_success_frequency'][tool] / count) * 100 if count > 0 else 0
                print(f"  {tool}: {count} uses, {success_rate:.1f}% success")
        
        print("="*70)
    
    def assert_tool_alignment_targets(self, stats: Dict, coverage: Dict) -> bool:
        """Assert that tool alignment targets are met."""
        success = True
        
        # Check overall alignment score
        if stats['average_alignment_score'] < 0.8:
            logger.error(f"❌ Average alignment score {stats['average_alignment_score']:.3f} < 0.8")
            success = False
        
        # Check tool completion rate
        if stats['tool_completion_rate'] < 0.9:
            logger.error(f"❌ Tool completion rate {stats['tool_completion_rate']:.1%} < 90%")
            success = False
        
        # Check per-team alignment
        for team, team_stats in stats['by_team'].items():
            if team_stats['average_alignment'] < 0.7:
                logger.error(f"❌ {team} team alignment {team_stats['average_alignment']:.3f} < 0.7")
                success = False
        
        # Check tool coverage
        for team, coverage_score in coverage['coverage_scores'].items():
            if coverage_score < 0.6:  # At least 60% of expected tools should be accessible
                logger.error(f"❌ {team} tool coverage {coverage_score:.1%} < 60%")
                success = False
        
        if success:
            logger.info("✅ All tool alignment targets met!")
        
        return success


async def main():
    parser = argparse.ArgumentParser(description='S2 Tool Usage Verification Test')
    parser.add_argument('--teams', default='trader,educator,streamer', 
                        help='Comma-separated list of teams to test')
    parser.add_argument('--scenarios', type=int, default=3,
                        help='Number of scenarios per team')
    parser.add_argument('--container', default='autogen_s2',
                        help='Docker container name')
    parser.add_argument('--api-url', default='http://localhost:8200',
                        help='S2 API URL')
    parser.add_argument('--output', help='Output JSON file path')
    parser.add_argument('--verify-alignment', action='store_true',
                        help='Verify tool alignment targets (exit code 1 if failed)')
    
    args = parser.parse_args()
    
    # Parse teams
    teams = [team.strip() for team in args.teams.split(',')]
    
    # Initialize tester
    tester = S2ToolUsageTester(
        container_name=args.container,
        s2_api_url=args.api_url
    )
    
    # Verify prerequisites
    if not tester.verify_s2_connectivity():
        logger.error("❌ S2 API not accessible")
        sys.exit(1)
    
    # Get available tools info
    tools_info = tester.get_available_tools()
    if tools_info:
        logger.info(f"Available tools: {list(tools_info.get('available_tools', []))}")
    
    # Run tests
    results = await tester.run_team_tool_tests(teams, args.scenarios)
    
    if not results:
        logger.error("❌ No test results obtained")
        sys.exit(1)
    
    # Calculate statistics and coverage
    stats = tester.calculate_tool_statistics(results)
    coverage = tester.validate_tool_coverage(results)
    
    # Save results
    if args.output:
        output_path = args.output
    else:
        output_path = tester.save_results(results, stats, coverage)
    
    # Print summary
    tester.print_summary(stats, coverage)
    
    # Verify alignment if requested
    if args.verify_alignment:
        if not tester.assert_tool_alignment_targets(stats, coverage):
            sys.exit(1)
    
    logger.info(f"✅ S2 tool usage test completed. Results: {output_path}")


if __name__ == '__main__':
    import sys
    asyncio.run(main()) 