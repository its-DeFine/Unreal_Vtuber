#!/usr/bin/env python3
"""
End-to-End Test Suite for Unified CORE System
==============================================

Comprehensive test suite for the unified CORE architecture covering:
- S1 (Avatar/VTuber) processing
- S2 (AutoGen Teams) processing  
- S1+S2 combined processing
- Character management and routing
- Queue system reliability
- Service health and monitoring

This test suite verifies the complete stimuli processing pipeline
after the architectural transformation from chaotic dual system
to clean unified architecture.
"""

import pytest
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

# Test configuration
CORE_BASE_URL = "http://localhost:8100"
S1_BASE_URL = "http://localhost:5000"  # NeuroSync Local API
S2_BASE_URL = "http://localhost:8200"  # AutoGen Agent
TIMEOUT = 30

@dataclass
class TestResult:
    """Test execution result"""
    test_name: str
    success: bool
    duration: float
    response_data: Any = None
    error_message: str = None


class CoreUnifiedE2ETest:
    """Comprehensive E2E test suite for unified CORE system"""
    
    def __init__(self):
        self.session = None
        self.test_results: List[TestResult] = []
        self.start_time = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=TIMEOUT))
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(
        self,
        method: str,
        url: str,
        json_data: Dict = None,
        expected_status: int = 200
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        try:
            async with self.session.request(method, url, json=json_data) as response:
                if response.status != expected_status:
                    text = await response.text()
                    raise Exception(f"HTTP {response.status}: {text}")
                return await response.json()
        except Exception as e:
            raise Exception(f"Request failed: {e}")
    
    async def _record_test_result(
        self,
        test_name: str,
        success: bool,
        response_data: Any = None,
        error_message: str = None,
        start_time: float = None
    ):
        """Record test result with timing"""
        duration = time.time() - (start_time or time.time())
        result = TestResult(
            test_name=test_name,
            success=success,
            duration=duration,
            response_data=response_data,
            error_message=error_message
        )
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name} ({duration:.2f}s)")
        if error_message:
            print(f"   Error: {error_message}")
    
    # === System Health Tests ===
    
    async def test_unified_core_health(self):
        """Test unified CORE system health"""
        test_start = time.time()
        try:
            health_data = await self._make_request("GET", f"{CORE_BASE_URL}/health")
            
            # Verify all services are healthy
            assert health_data["status"] == "running", "CORE system not running"
            assert health_data["healthy"] is True, "CORE system not healthy"
            
            required_services = ["ErrorHandler", "QueueService", "CharacterManager", "StimuliProcessor"]
            for service in required_services:
                assert health_data["services"][service] is True, f"Service {service} not healthy"
            
            # Verify characters are loaded
            assert health_data["statistics"]["characters"]["total_characters"] >= 3, "Insufficient characters loaded"
            
            await self._record_test_result(
                "test_unified_core_health",
                True,
                health_data,
                start_time=test_start
            )
            
        except Exception as e:
            await self._record_test_result(
                "test_unified_core_health",
                False,
                error_message=str(e),
                start_time=test_start
            )
    
    async def test_service_dependencies_health(self):
        """Test health of dependent services (S1, S2)"""
        test_start = time.time()
        errors = []
        
        # Test S1 (NeuroSync) health
        try:
            s1_health = await self._make_request("GET", f"{S1_BASE_URL}/health")
            if s1_health.get("status") != "ok":
                errors.append("S1 NeuroSync service not healthy")
        except Exception as e:
            errors.append(f"S1 health check failed: {e}")
        
        # Test S2 (AutoGen) health  
        try:
            s2_health = await self._make_request("GET", f"{S2_BASE_URL}/health")
            if s2_health.get("status") != "healthy":
                errors.append("S2 AutoGen service not healthy")
        except Exception as e:
            errors.append(f"S2 health check failed: {e}")
        
        success = len(errors) == 0
        await self._record_test_result(
            "test_service_dependencies_health",
            success,
            {"s1_healthy": "S1" not in str(errors), "s2_healthy": "S2" not in str(errors)},
            error_message="; ".join(errors) if errors else None,
            start_time=test_start
        )
    
    # === Character Management Tests ===
    
    async def test_character_management(self):
        """Test character management and availability"""
        test_start = time.time()
        try:
            # Get character list
            response = await self._make_request("GET", f"{CORE_BASE_URL}/api/characters")
            characters = response["characters"]  # Characters are in a wrapper object
            
            # Verify expected characters exist
            expected_characters = ["dr_house_trader", "emma_educator", "weatherman_streamer"]
            character_ids = [char["id"] for char in characters]
            
            for expected_id in expected_characters:
                assert expected_id in character_ids, f"Character {expected_id} not found"
            
            # Verify character capabilities
            for char in characters:
                assert "mission_type" in char, f"Character {char['id']} missing mission_type"
                assert "capabilities" in char, f"Character {char['id']} missing capabilities"
                assert char["current_state"] == "idle", f"Character {char['id']} not idle"
            
            await self._record_test_result(
                "test_character_management",
                True,
                {"character_count": len(characters), "character_ids": character_ids},
                start_time=test_start
            )
            
        except Exception as e:
            await self._record_test_result(
                "test_character_management",
                False,
                error_message=str(e),
                start_time=test_start
            )
    
    # === S1 Processing Tests ===
    
    async def test_s1_only_processing(self):
        """Test S1 (Avatar/VTuber) only processing"""
        test_start = time.time()
        try:
            stimuli_data = {
                "stimuli_id": f"s1_test_{int(time.time())}",
                "content": "avatar speak hello world immediately",
                "source": "e2e_test",
                "processing_mode": "s1_only",
                "priority": "high"
            }
            
            response = await self._make_request(
                "POST",
                f"{CORE_BASE_URL}/api/stimuli/receive",
                json_data=stimuli_data
            )
            
            # Verify S1 processing response
            assert response["status"] == "success", "S1 processing failed"
            assert response["processing_mode"] == "s1_only", "Wrong processing mode"
            assert response["error"] is None, "S1 processing had errors"
            assert "processing_time" in response, "Missing processing time"
            
            await self._record_test_result(
                "test_s1_only_processing",
                True,
                response,
                start_time=test_start
            )
            
        except Exception as e:
            await self._record_test_result(
                "test_s1_only_processing",
                False,
                error_message=str(e),
                start_time=test_start
            )
    
    # === S2 Processing Tests ===
    
    async def test_s2_only_processing(self):
        """Test S2 (AutoGen Teams) only processing"""
        test_start = time.time()
        try:
            stimuli_data = {
                "stimuli_id": f"s2_test_{int(time.time())}",
                "content": "analyze trading market trends and provide investment recommendations",
                "source": "e2e_test",
                "processing_mode": "s2_only",
                "team_preference": "trader",
                "priority": "medium"
            }
            
            response = await self._make_request(
                "POST",
                f"{CORE_BASE_URL}/api/stimuli/receive",
                json_data=stimuli_data
            )
            
            # Verify S2 processing response
            assert response["status"] == "success", "S2 processing failed"
            assert response["processing_mode"] in ["s2_only", "single"], "Wrong processing mode"
            
            # For single mode, check the result
            if response["processing_mode"] == "single":
                assert response["success"] is True, "S2 processing not successful"
                assert response["mode"] == "s2_only", "Wrong mode in response"
                assert response["team"] in ["trader", "general"], "Team not assigned correctly"
            else:
                # For s2_only mode, verify team assignment
                assert "team_type" in response or "team" in response, "No team assignment"
            
            await self._record_test_result(
                "test_s2_only_processing",
                True,
                response,
                start_time=test_start
            )
            
        except Exception as e:
            await self._record_test_result(
                "test_s2_only_processing",
                False,
                error_message=str(e),
                start_time=test_start
            )
    
    # === Combined S1+S2 Processing Tests ===
    
    async def test_s1_and_s2_combined_processing(self):
        """Test combined S1+S2 processing"""
        test_start = time.time()
        try:
            stimuli_data = {
                "stimuli_id": f"combined_test_{int(time.time())}",
                "content": "explain and demonstrate the current cryptocurrency market situation",
                "source": "e2e_test",
                "processing_mode": "auto",  # Let system decide, should trigger both
                "priority": "high"
            }
            
            response = await self._make_request(
                "POST",
                f"{CORE_BASE_URL}/api/stimuli/receive",
                json_data=stimuli_data
            )
            
            # Verify combined processing response
            assert response["status"] == "success", "Combined processing failed"
            
            if response["processing_mode"] == "multiple":
                # Both S1 and S2 results should be present
                assert "results" in response, "No results array for multiple processing"
                assert len(response["results"]) >= 2, "Insufficient results for combined processing"
                
                # Check for both S1 and S2 results
                modes = [result["mode"] for result in response["results"]]
                assert "s1_only" in modes, "S1 result missing from combined processing"
                assert "s2_only" in modes, "S2 result missing from combined processing"
                
                # Verify both succeeded
                for result in response["results"]:
                    assert result["success"] is True, f"Failed result in combined processing: {result}"
            
            await self._record_test_result(
                "test_s1_and_s2_combined_processing",
                True,
                response,
                start_time=test_start
            )
            
        except Exception as e:
            await self._record_test_result(
                "test_s1_and_s2_combined_processing",
                False,
                error_message=str(e),
                start_time=test_start
            )
    
    # === Intelligent Routing Tests ===
    
    async def test_intelligent_routing(self):
        """Test intelligent routing to appropriate teams"""
        test_start = time.time()
        try:
            test_cases = [
                {
                    "content": "buy bitcoin and ethereum for maximum profit",
                    "expected_team": "trader",
                    "description": "Trading content should route to trader team"
                },
                {
                    "content": "teach me about machine learning algorithms",
                    "expected_team": "educator", 
                    "description": "Educational content should route to educator team"
                },
                {
                    "content": "create engaging stream content about gaming",
                    "expected_team": "streamer",
                    "description": "Streaming content should route to streamer team"
                }
            ]
            
            routing_results = []
            
            for i, test_case in enumerate(test_cases):
                stimuli_data = {
                    "stimuli_id": f"routing_test_{i}_{int(time.time())}",
                    "content": test_case["content"],
                    "source": "e2e_routing_test",
                    "processing_mode": "s2_only"
                }
                
                response = await self._make_request(
                    "POST",
                    f"{CORE_BASE_URL}/api/stimuli/receive",
                    json_data=stimuli_data
                )
                
                # Extract team assignment
                team = None
                if response["processing_mode"] == "single":
                    team = response.get("team")
                elif "team_type" in response:
                    team = response["team_type"]
                elif "results" in response:
                    for result in response["results"]:
                        if result["mode"] == "s2_only":
                            team = result.get("team")
                            break
                
                routing_results.append({
                    "content": test_case["content"][:50] + "...",
                    "expected_team": test_case["expected_team"],
                    "actual_team": team,
                    "correct": team == test_case["expected_team"] or team == "general"  # General is acceptable fallback
                })
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            # Check routing accuracy
            correct_routes = sum(1 for result in routing_results if result["correct"])
            success = correct_routes >= len(test_cases) * 0.67  # At least 67% accuracy
            
            await self._record_test_result(
                "test_intelligent_routing",
                success,
                {
                    "routing_results": routing_results,
                    "accuracy": correct_routes / len(test_cases),
                    "correct_routes": correct_routes,
                    "total_routes": len(test_cases)
                },
                error_message=f"Routing accuracy too low: {correct_routes}/{len(test_cases)}" if not success else None,
                start_time=test_start
            )
            
        except Exception as e:
            await self._record_test_result(
                "test_intelligent_routing",
                False,
                error_message=str(e),
                start_time=test_start
            )
    
    # === Performance and Load Tests ===
    
    async def test_concurrent_processing(self):
        """Test concurrent stimuli processing"""
        test_start = time.time()
        try:
            # Create multiple concurrent requests
            concurrent_requests = []
            num_requests = 5
            
            for i in range(num_requests):
                stimuli_data = {
                    "stimuli_id": f"concurrent_test_{i}_{int(time.time())}",
                    "content": f"concurrent test request number {i}",
                    "source": "e2e_concurrent_test",
                    "processing_mode": "auto"
                }
                
                request_coro = self._make_request(
                    "POST",
                    f"{CORE_BASE_URL}/api/stimuli/receive",
                    json_data=stimuli_data
                )
                concurrent_requests.append(request_coro)
            
            # Execute all requests concurrently
            responses = await asyncio.gather(*concurrent_requests, return_exceptions=True)
            
            # Analyze results
            successful_responses = []
            failed_responses = []
            
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    failed_responses.append(f"Request {i}: {response}")
                else:
                    if response.get("status") == "success":
                        successful_responses.append(response)
                    else:
                        failed_responses.append(f"Request {i}: {response}")
            
            success_rate = len(successful_responses) / num_requests
            success = success_rate >= 0.8  # At least 80% success rate
            
            await self._record_test_result(
                "test_concurrent_processing",
                success,
                {
                    "total_requests": num_requests,
                    "successful_requests": len(successful_responses),
                    "failed_requests": len(failed_responses),
                    "success_rate": success_rate,
                    "failures": failed_responses[:3]  # Show first 3 failures
                },
                error_message=f"Low success rate: {success_rate:.2%}" if not success else None,
                start_time=test_start
            )
            
        except Exception as e:
            await self._record_test_result(
                "test_concurrent_processing",
                False,
                error_message=str(e),
                start_time=test_start
            )
    
    # === System Statistics Tests ===
    
    async def test_system_statistics(self):
        """Test system statistics and monitoring"""
        test_start = time.time()
        try:
            stats = await self._make_request("GET", f"{CORE_BASE_URL}/api/stats")
            
            # Verify statistics structure
            required_sections = ["characters", "processing", "queues", "errors"]
            for section in required_sections:
                assert section in stats, f"Missing statistics section: {section}"
            
            # Verify character statistics
            char_stats = stats["characters"]
            assert char_stats["total_characters"] >= 3, "Insufficient characters in stats"
            assert "state_distribution" in char_stats, "Missing character state distribution"
            assert "mission_type_distribution" in char_stats, "Missing mission type distribution"
            
            # Verify processing statistics
            proc_stats = stats["processing"]
            assert "total_processed" in proc_stats, "Missing total processed count"
            assert "by_mode" in proc_stats, "Missing processing mode breakdown"
            assert "by_team" in proc_stats, "Missing team processing breakdown"
            
            await self._record_test_result(
                "test_system_statistics",
                True,
                stats,
                start_time=test_start
            )
            
        except Exception as e:
            await self._record_test_result(
                "test_system_statistics",
                False,
                error_message=str(e),
                start_time=test_start
            )
    
    # === Configuration Tests ===
    
    async def test_system_configuration(self):
        """Test system configuration endpoint"""
        test_start = time.time()
        try:
            config = await self._make_request("GET", f"{CORE_BASE_URL}/api/config")
            
            # Verify configuration structure
            assert "system_mode" in config, "Missing system_mode in config"
            assert "environment" in config, "Missing environment in config"
            assert config["system_mode"] == "simplified", "Wrong system mode"
            
            await self._record_test_result(
                "test_system_configuration",
                True,
                config,
                start_time=test_start
            )
            
        except Exception as e:
            await self._record_test_result(
                "test_system_configuration",
                False,
                error_message=str(e),
                start_time=test_start
            )
    
    # === Main Test Runner ===
    
    async def run_all_tests(self):
        """Run complete E2E test suite"""
        print("🚀 Starting Unified CORE System E2E Test Suite")
        print("=" * 60)
        
        # Define test sequence
        tests = [
            self.test_unified_core_health,
            self.test_service_dependencies_health,
            self.test_character_management,
            self.test_system_configuration,
            self.test_system_statistics,
            self.test_s1_only_processing,
            self.test_s2_only_processing,
            self.test_s1_and_s2_combined_processing,
            self.test_intelligent_routing,
            self.test_concurrent_processing,
        ]
        
        # Run tests sequentially
        for test_func in tests:
            try:
                await test_func()
            except Exception as e:
                await self._record_test_result(
                    test_func.__name__,
                    False,
                    error_message=f"Test execution failed: {e}"
                )
            
            # Small delay between tests
            await asyncio.sleep(0.5)
        
        # Generate test report
        await self._generate_test_report()
    
    async def _generate_test_report(self):
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        passed_tests = [r for r in self.test_results if r.success]
        failed_tests = [r for r in self.test_results if not r.success]
        
        print("\n" + "=" * 60)
        print("📊 UNIFIED CORE SYSTEM E2E TEST REPORT")
        print("=" * 60)
        
        # Summary
        print(f"📈 Test Summary:")
        print(f"   Total Tests: {len(self.test_results)}")
        print(f"   Passed: {len(passed_tests)} ✅")
        print(f"   Failed: {len(failed_tests)} ❌")
        print(f"   Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        print(f"   Total Duration: {total_duration:.2f}s")
        
        # Failed tests details
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"   • {test.test_name}: {test.error_message}")
        
        # Performance summary
        avg_duration = sum(r.duration for r in self.test_results) / len(self.test_results)
        print(f"\n⚡ Performance Summary:")
        print(f"   Average Test Duration: {avg_duration:.2f}s")
        print(f"   Fastest Test: {min(r.duration for r in self.test_results):.2f}s")
        print(f"   Slowest Test: {max(r.duration for r in self.test_results):.2f}s")
        
        # System validation
        core_health_passed = any(r.test_name == "test_unified_core_health" and r.success for r in self.test_results)
        s1_passed = any(r.test_name == "test_s1_only_processing" and r.success for r in self.test_results)
        s2_passed = any(r.test_name == "test_s2_only_processing" and r.success for r in self.test_results)
        combined_passed = any(r.test_name == "test_s1_and_s2_combined_processing" and r.success for r in self.test_results)
        
        print(f"\n🎯 System Validation:")
        print(f"   CORE Health: {'✅ PASS' if core_health_passed else '❌ FAIL'}")
        print(f"   S1 Processing: {'✅ PASS' if s1_passed else '❌ FAIL'}")
        print(f"   S2 Processing: {'✅ PASS' if s2_passed else '❌ FAIL'}")
        print(f"   S1+S2 Combined: {'✅ PASS' if combined_passed else '❌ FAIL'}")
        
        # Final verdict
        overall_success = len(failed_tests) == 0 and core_health_passed
        print(f"\n🏆 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        if overall_success:
            print("🎉 Unified CORE System is fully operational and ready for production!")
        else:
            print("⚠️  Please review failed tests and fix issues before production deployment.")
        
        print("=" * 60)


# === Pytest Integration ===

@pytest.mark.asyncio
async def test_unified_core_e2e():
    """Pytest entry point for E2E tests"""
    async with CoreUnifiedE2ETest() as test_suite:
        await test_suite.run_all_tests()
        
        # Assert overall success for pytest
        failed_tests = [r for r in test_suite.test_results if not r.success]
        assert len(failed_tests) == 0, f"E2E tests failed: {[t.test_name for t in failed_tests]}"


# === CLI Runner ===

async def main():
    """CLI entry point for running E2E tests"""
    async with CoreUnifiedE2ETest() as test_suite:
        await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())