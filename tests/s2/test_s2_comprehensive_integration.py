#!/usr/bin/env python3
"""
S2 Comprehensive Integration Testing

Complete testing suite for the S2 Performance & Tool Utilization system.
Tests all 12 tools across all 3 teams with cross-team integration validation.

Validates Phase 2 targets:
- P95 Latency < 2.0s
- Tool Alignment 100% 
- Processing Success > 95%
- Complete team coverage
"""

import asyncio
import json
import logging
import requests
import time
import statistics
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class S2ComprehensiveIntegrationTester:
    def __init__(self, base_url: str = "http://localhost:8200"):
        self.base_url = base_url
        self.test_results = {}
        self.performance_metrics = []
        self.tool_executions = {}
        
    async def run_comprehensive_tests(self) -> Dict[str, any]:
        """Run complete S2 integration test suite"""
        logger.info("🚀 Starting S2 Comprehensive Integration Testing Suite")
        
        # System readiness check
        if not await self.verify_system_readiness():
            return {"error": "System not ready for testing"}
            
        test_phases = [
            ("Phase 1: Individual Team Validation", self.phase_1_individual_teams),
            ("Phase 2: Cross-Team Integration", self.phase_2_cross_team_integration),
            ("Phase 3: Performance Validation", self.phase_3_performance_validation),
            ("Phase 4: Tool Utilization Analysis", self.phase_4_tool_utilization),
            ("Phase 5: Stress Testing", self.phase_5_stress_testing),
            ("Phase 6: End-to-End Workflows", self.phase_6_end_to_end_workflows)
        ]
        
        for phase_name, phase_method in test_phases:
            logger.info(f"📋 Starting {phase_name}")
            try:
                result = await phase_method()
                self.test_results[phase_name] = result
                logger.info(f"✅ {phase_name}: {'PASSED' if result.get('success', False) else 'FAILED'}")
            except Exception as e:
                logger.error(f"❌ {phase_name}: FAILED - {e}")
                self.test_results[phase_name] = {"success": False, "error": str(e)}
                
        return await self.generate_comprehensive_report()
    
    async def verify_system_readiness(self) -> bool:
        """Verify S2 system is ready for comprehensive testing"""
        logger.info("🔍 Verifying system readiness...")
        
        try:
            # Check API availability
            status_response = requests.get(f"{self.base_url}/api/stimuli/status", timeout=10)
            status_response.raise_for_status()
            status = status_response.json()
            
            # Check tool availability
            tools_response = requests.get(f"{self.base_url}/api/stimuli/tools", timeout=10)
            tools_response.raise_for_status()
            tools = tools_response.json()
            
            # Validate expected configuration
            if tools["total_tools"] != 12:
                logger.error(f"Expected 12 tools, found {tools['total_tools']}")
                return False
                
            if status["autonomous_state"] != "running":
                logger.error(f"System not running: {status['autonomous_state']}")
                return False
                
            logger.info("✅ System readiness verified")
            return True
            
        except Exception as e:
            logger.error(f"❌ System readiness check failed: {e}")
            return False
    
    def submit_stimuli_with_timing(self, content: str, stimuli_id: Optional[str] = None) -> Tuple[Dict, float]:
        """Submit stimuli and measure response time"""
        if not stimuli_id:
            stimuli_id = f"integration_test_{int(time.time() * 1000)}"
            
        payload = {
            "stimuli_id": stimuli_id,
            "content": content,
            "source": "s2_integration_test",
            "priority": "high"
        }
        
        start_time = time.time()
        response = requests.post(
            f"{self.base_url}/api/stimuli/receive",
            json=payload,
            timeout=60
        )
        response_time = time.time() - start_time
        
        response.raise_for_status()
        return response.json(), response_time
    
    def wait_for_queue_clear(self, timeout: int = 180) -> bool:
        """Wait for all stimuli to be processed"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                status = requests.get(f"{self.base_url}/api/stimuli/status", timeout=5).json()
                if status["queue_size"] == 0:
                    return True
                time.sleep(2)
            except:
                time.sleep(2)
        return False
    
    async def phase_1_individual_teams(self) -> Dict[str, any]:
        """Test each team individually with their specialized tools"""
        logger.info("🏪🎓🎮 Testing individual team capabilities...")
        
        team_tests = {
            "trader": [
                "Get AAPL market data and perform comprehensive trading analysis with risk assessment for $20,000 position",
                "Check system status and validate market data using utility functions",
                "Communicate trading insights and coordinate with other teams"
            ],
            "educator": [
                "Create comprehensive educational content about cryptocurrency trading for beginners",
                "Design assessment methods and create a structured 8-week curriculum",
                "Develop adaptive learning materials for different student levels"
            ],
            "streamer": [
                "Generate viral content ideas for financial education streaming channel",
                "Develop community management strategy and analyze streaming performance metrics",
                "Create cross-platform content strategy and engagement optimization"
            ]
        }
        
        results = {}
        for team, test_cases in team_tests.items():
            team_results = []
            for test_case in test_cases:
                response, response_time = self.submit_stimuli_with_timing(test_case)
                team_results.append({
                    "success": response["success"],
                    "response_time": response_time,
                    "stimuli_id": response["stimuli_id"]
                })
                self.performance_metrics.append(response_time)
                
            results[team] = {
                "tests_passed": sum(1 for r in team_results if r["success"]),
                "total_tests": len(team_results),
                "avg_response_time": statistics.mean([r["response_time"] for r in team_results])
            }
        
        # Wait for processing to complete
        self.wait_for_queue_clear()
        
        overall_success = all(r["tests_passed"] == r["total_tests"] for r in results.values())
        return {"success": overall_success, "team_results": results}
    
    async def phase_2_cross_team_integration(self) -> Dict[str, any]:
        """Test cross-team communication and coordination"""
        logger.info("🤝 Testing cross-team integration...")
        
        integration_scenarios = [
            """
            Cross-team collaboration scenario:
            1. Trader team: Analyze current market trends and identify educational opportunities
            2. Educator team: Create educational content based on trader insights
            3. Streamer team: Develop streaming strategy for the educational content
            4. All teams: Coordinate on timing and promotion strategy
            """,
            """
            Educational trading program development:
            1. Educator team: Plan curriculum for trading education program
            2. Trader team: Provide real-world examples and risk assessment guidance
            3. Streamer team: Create engaging content delivery strategy
            4. Integrate assessment methods with practical trading exercises
            """,
            """
            Community-driven financial literacy initiative:
            1. Streamer team: Analyze community interests and engagement patterns
            2. Educator team: Develop appropriate educational materials
            3. Trader team: Provide expert validation and practical insights
            4. Create comprehensive program with assessment and community engagement
            """
        ]
        
        integration_results = []
        for scenario in integration_scenarios:
            response, response_time = self.submit_stimuli_with_timing(scenario)
            integration_results.append({
                "success": response["success"],
                "response_time": response_time
            })
            self.performance_metrics.append(response_time)
        
        self.wait_for_queue_clear()
        
        success_rate = sum(1 for r in integration_results if r["success"]) / len(integration_results)
        avg_response_time = statistics.mean([r["response_time"] for r in integration_results])
        
        return {
            "success": success_rate >= 0.95,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "total_scenarios": len(integration_scenarios)
        }
    
    async def phase_3_performance_validation(self) -> Dict[str, any]:
        """Validate Phase 2 performance targets"""
        logger.info("⚡ Validating performance targets...")
        
        # P95 Latency Test
        latency_tests = [
            "Quick market data check for NVDA",
            "Generate brief educational summary on blockchain",
            "Create short streaming content idea for tech channel"
        ] * 10  # 30 total tests for statistical significance
        
        latency_measurements = []
        for test in latency_tests:
            response, response_time = self.submit_stimuli_with_timing(test)
            latency_measurements.append(response_time)
            if not response["success"]:
                logger.warning(f"Performance test failed: {test}")
        
        self.wait_for_queue_clear()
        
        # Calculate metrics
        p95_latency = statistics.quantiles(latency_measurements, n=20)[18]  # 95th percentile
        avg_latency = statistics.mean(latency_measurements)
        max_latency = max(latency_measurements)
        
        # Tool alignment check
        tools_response = requests.get(f"{self.base_url}/api/stimuli/tools").json()
        tool_alignment = (tools_response["total_tools"] == 12)
        
        # Success rate check
        status_response = requests.get(f"{self.base_url}/api/stimuli/status").json()
        total_errors = status_response["statistics"]["total_errors"]
        total_processed = status_response["statistics"]["total_received"]
        success_rate = (total_processed - total_errors) / total_processed if total_processed > 0 else 0
        
        targets_met = {
            "p95_latency_under_2s": p95_latency < 2.0,
            "tool_alignment_100_percent": tool_alignment,
            "success_rate_over_95_percent": success_rate >= 0.95
        }
        
        return {
            "success": all(targets_met.values()),
            "p95_latency": p95_latency,
            "avg_latency": avg_latency,
            "max_latency": max_latency,
            "tool_alignment": tool_alignment,
            "success_rate": success_rate,
            "targets_met": targets_met
        }
    
    async def phase_4_tool_utilization(self) -> Dict[str, any]:
        """Analyze tool utilization across all teams"""
        logger.info("🛠️ Analyzing tool utilization...")
        
        # Submit stimuli designed to trigger each tool
        tool_specific_tests = {
            "market_data": "Get detailed market data for AAPL with technical indicators",
            "trading_analysis": "Perform comprehensive trading analysis for TSLA with strategy recommendations",
            "risk_assessment": "Assess portfolio risk for $50,000 tech stock allocation",
            "educational_content": "Create detailed educational content about machine learning basics",
            "assessment_creation": "Design comprehensive assessment for AI course with rubrics",
            "curriculum_planning": "Plan 6-week curriculum for data science bootcamp",
            "content_creation": "Generate viral content ideas for educational tech streaming",
            "community_management": "Develop community engagement strategy for growing channel",
            "streaming_analytics": "Analyze streaming performance and provide optimization recommendations",
            "communication": "Coordinate cross-team collaboration on educational project",
            "system_status": "Check system health and performance metrics",
            "utility": "Process and validate educational content format"
        }
        
        tool_results = {}
        for tool_name, test_content in tool_specific_tests.items():
            response, response_time = self.submit_stimuli_with_timing(test_content)
            tool_results[tool_name] = {
                "triggered": response["success"],
                "response_time": response_time
            }
            self.performance_metrics.append(response_time)
        
        self.wait_for_queue_clear()
        
        tools_triggered = sum(1 for result in tool_results.values() if result["triggered"])
        tool_utilization_rate = tools_triggered / len(tool_specific_tests)
        
        return {
            "success": tool_utilization_rate >= 0.95,
            "tools_triggered": tools_triggered,
            "total_tools": len(tool_specific_tests),
            "utilization_rate": tool_utilization_rate,
            "tool_results": tool_results
        }
    
    async def phase_5_stress_testing(self) -> Dict[str, any]:
        """Test system under concurrent load"""
        logger.info("💪 Running stress testing...")
        
        # Submit multiple stimuli concurrently
        concurrent_tests = [
            "Analyze AAPL market trends and create educational content",
            "Generate streaming strategy for financial education",
            "Assess portfolio risk and create trading curriculum",
            "Develop community engagement for trading education",
            "Create viral content about cryptocurrency basics"
        ] * 4  # 20 concurrent requests
        
        stress_results = []
        start_time = time.time()
        
        # Submit all requests rapidly
        for test in concurrent_tests:
            try:
                response, response_time = self.submit_stimuli_with_timing(test)
                stress_results.append({
                    "success": response["success"],
                    "response_time": response_time
                })
            except Exception as e:
                stress_results.append({
                    "success": False,
                    "error": str(e)
                })
                
        total_submission_time = time.time() - start_time
        
        # Wait for all processing to complete
        processing_start = time.time()
        queue_cleared = self.wait_for_queue_clear(300)  # 5 minute timeout
        processing_time = time.time() - processing_start
        
        success_count = sum(1 for r in stress_results if r.get("success", False))
        success_rate = success_count / len(stress_results)
        
        return {
            "success": success_rate >= 0.90 and queue_cleared,
            "requests_submitted": len(stress_results),
            "successful_requests": success_count,
            "success_rate": success_rate,
            "submission_time": total_submission_time,
            "processing_time": processing_time,
            "queue_cleared": queue_cleared
        }
    
    async def phase_6_end_to_end_workflows(self) -> Dict[str, any]:
        """Test complex end-to-end workflows"""
        logger.info("🔄 Testing end-to-end workflows...")
        
        complex_workflows = [
            """
            Complete financial education program development:
            1. Market analysis: Get current market data for major stocks and analyze trends
            2. Risk assessment: Evaluate different portfolio strategies for educational examples
            3. Content creation: Develop comprehensive educational materials about trading
            4. Curriculum planning: Create structured 12-week trading education program
            5. Assessment design: Create evaluation methods for student progress
            6. Streaming strategy: Develop content delivery and community engagement plan
            7. Analytics: Monitor performance and optimize for better engagement
            8. Cross-team coordination: Ensure all components work together effectively
            """,
            """
            Interactive community-driven learning platform:
            1. Community analysis: Understand audience interests and engagement patterns
            2. Educational content: Create adaptive learning materials for different levels
            3. Assessment integration: Design progressive evaluation methods
            4. Streaming content: Develop live and recorded educational content
            5. Market integration: Include real-world trading examples and case studies
            6. System monitoring: Ensure platform performance and reliability
            7. Utility optimization: Process and format all content for delivery
            8. Communication: Coordinate ongoing updates and improvements
            """
        ]
        
        workflow_results = []
        for workflow in complex_workflows:
            start_time = time.time()
            response, response_time = self.submit_stimuli_with_timing(workflow)
            
            # Wait for this specific workflow to complete
            self.wait_for_queue_clear(300)
            
            total_time = time.time() - start_time
            workflow_results.append({
                "success": response["success"],
                "response_time": response_time,
                "total_processing_time": total_time
            })
        
        success_rate = sum(1 for r in workflow_results if r["success"]) / len(workflow_results)
        avg_processing_time = statistics.mean([r["total_processing_time"] for r in workflow_results])
        
        return {
            "success": success_rate >= 0.95,
            "workflows_completed": len(workflow_results),
            "success_rate": success_rate,
            "avg_processing_time": avg_processing_time,
            "workflow_results": workflow_results
        }
    
    async def generate_comprehensive_report(self) -> Dict[str, any]:
        """Generate comprehensive test report with all metrics"""
        timestamp = datetime.now().isoformat()
        
        # Calculate overall metrics
        total_tests = sum(1 for phase in self.test_results.values() if isinstance(phase, dict))
        successful_phases = sum(1 for phase in self.test_results.values() 
                               if isinstance(phase, dict) and phase.get("success", False))
        overall_success_rate = successful_phases / total_tests if total_tests > 0 else 0
        
        # Performance metrics
        if self.performance_metrics:
            avg_response_time = statistics.mean(self.performance_metrics)
            p95_response_time = statistics.quantiles(self.performance_metrics, n=20)[18] if len(self.performance_metrics) >= 20 else max(self.performance_metrics)
            max_response_time = max(self.performance_metrics)
        else:
            avg_response_time = p95_response_time = max_response_time = 0
        
        # System status
        try:
            final_status = requests.get(f"{self.base_url}/api/stimuli/status").json()
            final_tools = requests.get(f"{self.base_url}/api/stimuli/tools").json()
        except:
            final_status = {"error": "Could not fetch final status"}
            final_tools = {"error": "Could not fetch final tools"}
        
        report = {
            "test_execution": {
                "timestamp": timestamp,
                "total_phases": total_tests,
                "successful_phases": successful_phases,
                "overall_success_rate": overall_success_rate,
                "phase_results": self.test_results
            },
            "performance_metrics": {
                "total_requests": len(self.performance_metrics),
                "avg_response_time": avg_response_time,
                "p95_response_time": p95_response_time,
                "max_response_time": max_response_time,
                "p95_under_2s": p95_response_time < 2.0 if self.performance_metrics else False
            },
            "system_status": {
                "final_status": final_status,
                "final_tools": final_tools
            },
            "phase_2_targets": {
                "p95_latency_target": "< 2.0s",
                "tool_alignment_target": "100%",
                "success_rate_target": "> 95%",
                "team_coverage_target": "All teams operational",
                "results": self.test_results.get("Phase 3: Performance Validation", {})
            }
        }
        
        return report

async def main():
    """Main integration test execution"""
    tester = S2ComprehensiveIntegrationTester()
    
    logger.info("🚀 Starting S2 Comprehensive Integration Testing")
    logger.info("Testing Phase 2 S2 Performance & Tool Utilization Implementation")
    
    # Run comprehensive tests
    results = await tester.run_comprehensive_tests()
    
    # Generate detailed report
    print("\n" + "="*80)
    print("🚀 S2 COMPREHENSIVE INTEGRATION TEST REPORT")
    print("="*80)
    
    if "error" in results:
        print(f"❌ Test Suite Failed: {results['error']}")
        return
    
    # Test execution summary
    exec_results = results["test_execution"]
    print(f"""
📊 TEST EXECUTION SUMMARY:
- Total Phases: {exec_results['total_phases']}
- Successful Phases: {exec_results['successful_phases']}
- Overall Success Rate: {exec_results['overall_success_rate']:.1%}
- Test Timestamp: {exec_results['timestamp']}
""")
    
    # Performance metrics
    perf_metrics = results["performance_metrics"]
    print(f"""
⚡ PERFORMANCE METRICS:
- Total Requests: {perf_metrics['total_requests']}
- Average Response Time: {perf_metrics['avg_response_time']:.3f}s
- P95 Response Time: {perf_metrics['p95_response_time']:.3f}s
- Max Response Time: {perf_metrics['max_response_time']:.3f}s
- P95 Under 2s Target: {'✅ ACHIEVED' if perf_metrics['p95_under_2s'] else '❌ MISSED'}
""")
    
    # Phase 2 targets validation
    if "Phase 3: Performance Validation" in exec_results["phase_results"]:
        targets = exec_results["phase_results"]["Phase 3: Performance Validation"]
        if "targets_met" in targets:
            print(f"""
🎯 PHASE 2 TARGETS VALIDATION:
- P95 Latency < 2.0s: {'✅ ACHIEVED' if targets['targets_met']['p95_latency_under_2s'] else '❌ MISSED'} ({targets.get('p95_latency', 'N/A'):.3f}s)
- Tool Alignment 100%: {'✅ ACHIEVED' if targets['targets_met']['tool_alignment_100_percent'] else '❌ MISSED'}
- Success Rate > 95%: {'✅ ACHIEVED' if targets['targets_met']['success_rate_over_95_percent'] else '❌ MISSED'} ({targets.get('success_rate', 0):.1%})
""")
    
    # Individual phase results
    print("\n📋 INDIVIDUAL PHASE RESULTS:")
    for phase_name, phase_result in exec_results["phase_results"].items():
        if isinstance(phase_result, dict):
            status = "✅ PASSED" if phase_result.get("success", False) else "❌ FAILED"
            print(f"- {phase_name}: {status}")
    
    # Final system status
    system_status = results["system_status"]["final_status"]
    if "error" not in system_status:
        print(f"""
💻 FINAL SYSTEM STATUS:
- State: {system_status.get('autonomous_state', 'Unknown')}
- Queue Size: {system_status.get('queue_size', 'Unknown')}
- Total Processed: {system_status.get('statistics', {}).get('total_received', 'Unknown')}
- Total Errors: {system_status.get('statistics', {}).get('total_errors', 'Unknown')}
""")
    
    print("\n🎉 S2 Comprehensive Integration Testing Complete!")
    
    # Save detailed report
    with open("s2_comprehensive_test_report.json", "w") as f:
        json.dump(results, f, indent=2)
    logger.info("📝 Detailed report saved to s2_comprehensive_test_report.json")

if __name__ == "__main__":
    asyncio.run(main()) 