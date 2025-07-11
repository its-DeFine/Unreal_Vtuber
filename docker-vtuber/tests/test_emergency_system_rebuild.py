#!/usr/bin/env python3
"""
EMERGENCY SYSTEM REBUILD TEST
=============================

Test script to validate the rebuilt stimuli system with:
1. Simplified decision matrix (emergency override)
2. Fixed health check endpoints 
3. S2 agent termination fixes
4. Environment variable overrides

This test validates that the drastic changes actually work!
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, Any, List
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmergencySystemTester:
    """Test the rebuilt emergency stimuli system."""
    
    def __init__(self):
        self.graphflow_url = "http://localhost:8000"
        self.autogen_url = "http://localhost:8200"
        self.neurosync_url = "http://localhost:5001"
        
        self.session = None
        self.results = {
            "health_checks": {},
            "routing_tests": {},
            "speech_tests": {},
            "analysis_tests": {},
            "admin_tests": {},
            "timestamp": datetime.now().isoformat()
        }
    
    async def setup(self):
        """Initialize test session."""
        connector = aiohttp.TCPConnector(limit=100)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        logger.info("🚀 Emergency system tester initialized")
    
    async def cleanup(self):
        """Clean up test session."""
        if self.session:
            await self.session.close()
        logger.info("🧹 Test session cleaned up")
    
    async def test_health_checks(self):
        """Test that all /health endpoints work correctly."""
        logger.info("🔍 Testing health check endpoints...")
        
        endpoints = [
            (self.graphflow_url, "/api/v1/health", "GraphFlow"),
            (self.autogen_url, "/api/semantic-map/health", "AutoGen Semantic Map"),
            (self.autogen_url, "/api/persona/health", "AutoGen Persona"),
            (self.neurosync_url, "/health", "NeuroSync")
        ]
        
        for base_url, endpoint, service in endpoints:
            try:
                async with self.session.get(f"{base_url}{endpoint}") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.results["health_checks"][service] = {
                            "status": "PASS",
                            "endpoint": endpoint,
                            "response_data": data
                        }
                        logger.info(f"✅ {service} health check PASSED")
                    else:
                        self.results["health_checks"][service] = {
                            "status": "FAIL",
                            "error": f"HTTP {response.status}",
                            "endpoint": endpoint
                        }
                        logger.error(f"❌ {service} health check FAILED: HTTP {response.status}")
            except Exception as e:
                self.results["health_checks"][service] = {
                    "status": "ERROR",
                    "error": str(e),
                    "endpoint": endpoint
                }
                logger.error(f"💥 {service} health check ERROR: {e}")
    
    async def test_speech_routing(self):
        """Test that speech requests are routed to S1 (AVATAR_AND_ANALYSIS)."""
        logger.info("🎤 Testing speech routing...")
        
        test_cases = [
            {"content": "Hello, please speak to me", "expected": "AVATAR_AND_ANALYSIS"},
            {"content": "Say hello world", "expected": "AVATAR_AND_ANALYSIS"},
            {"content": "voice test message", "expected": "AVATAR_AND_ANALYSIS"},
            {"content": "avatar tell me a joke", "expected": "AVATAR_AND_ANALYSIS"},
            {"content": "respond with speech", "expected": "AVATAR_AND_ANALYSIS"}
        ]
        
        for i, test_case in enumerate(test_cases):
            try:
                stimuli_data = {
                    "content": test_case["content"],
                    "source": "emergency_test",
                    "priority": "high",
                    "metadata": {
                        "request_type": "speech",
                        "test_id": f"speech_test_{i+1}"
                    }
                }
                
                async with self.session.post(
                    f"{self.graphflow_url}/api/v1/stimuli/submit",
                    json=stimuli_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        stimuli_id = data.get("stimuli_id")
                        
                        # Wait a bit for processing
                        await asyncio.sleep(2)
                        
                        # Check the decision result
                        async with self.session.get(
                            f"{self.graphflow_url}/api/v1/stimuli/{stimuli_id}/status"
                        ) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                decision = status_data.get("decision", "UNKNOWN")
                                
                                test_result = {
                                    "content": test_case["content"],
                                    "expected": test_case["expected"],
                                    "actual": decision,
                                    "status": "PASS" if decision == test_case["expected"] else "FAIL",
                                    "stimuli_id": stimuli_id
                                }
                                
                                self.results["speech_tests"][f"test_{i+1}"] = test_result
                                
                                if decision == test_case["expected"]:
                                    logger.info(f"✅ Speech test {i+1} PASSED: '{test_case['content']}' → {decision}")
                                else:
                                    logger.error(f"❌ Speech test {i+1} FAILED: '{test_case['content']}' → {decision} (expected {test_case['expected']})")
                            else:
                                logger.error(f"Failed to get status for speech test {i+1}")
                    else:
                        logger.error(f"Failed to submit speech test {i+1}: HTTP {response.status}")
                        
            except Exception as e:
                logger.error(f"💥 Speech test {i+1} ERROR: {e}")
                self.results["speech_tests"][f"test_{i+1}"] = {
                    "content": test_case["content"],
                    "status": "ERROR",
                    "error": str(e)
                }
    
    async def test_analysis_routing(self):
        """Test that analysis requests are routed to S2 (ANALYSIS_ONLY)."""
        logger.info("🧠 Testing analysis routing...")
        
        test_cases = [
            {"content": "analyze this data pattern", "expected": "ANALYSIS_ONLY"},
            {"content": "think about this problem", "expected": "ANALYSIS_ONLY"},
            {"content": "evaluate the situation", "expected": "ANALYSIS_ONLY"},
            {"content": "process this information", "expected": "ANALYSIS_ONLY"}
        ]
        
        for i, test_case in enumerate(test_cases):
            try:
                stimuli_data = {
                    "content": test_case["content"],
                    "source": "emergency_test",
                    "priority": "medium",
                    "metadata": {
                        "request_type": "analysis",
                        "test_id": f"analysis_test_{i+1}"
                    }
                }
                
                async with self.session.post(
                    f"{self.graphflow_url}/api/v1/stimuli/submit",
                    json=stimuli_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        stimuli_id = data.get("stimuli_id")
                        
                        # Wait a bit for processing
                        await asyncio.sleep(2)
                        
                        # Check the decision result
                        async with self.session.get(
                            f"{self.graphflow_url}/api/v1/stimuli/{stimuli_id}/status"
                        ) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                decision = status_data.get("decision", "UNKNOWN")
                                
                                test_result = {
                                    "content": test_case["content"],
                                    "expected": test_case["expected"],
                                    "actual": decision,
                                    "status": "PASS" if decision == test_case["expected"] else "FAIL",
                                    "stimuli_id": stimuli_id
                                }
                                
                                self.results["analysis_tests"][f"test_{i+1}"] = test_result
                                
                                if decision == test_case["expected"]:
                                    logger.info(f"✅ Analysis test {i+1} PASSED: '{test_case['content']}' → {decision}")
                                else:
                                    logger.error(f"❌ Analysis test {i+1} FAILED: '{test_case['content']}' → {decision} (expected {test_case['expected']})")
                            else:
                                logger.error(f"Failed to get status for analysis test {i+1}")
                    else:
                        logger.error(f"Failed to submit analysis test {i+1}: HTTP {response.status}")
                        
            except Exception as e:
                logger.error(f"💥 Analysis test {i+1} ERROR: {e}")
                self.results["analysis_tests"][f"test_{i+1}"] = {
                    "content": test_case["content"],
                    "status": "ERROR",
                    "error": str(e)
                }
    
    async def test_admin_routing(self):
        """Test that admin requests trigger both S1+S2 (AVATAR_AND_ANALYSIS)."""
        logger.info("⚙️ Testing admin routing...")
        
        test_cases = [
            {"content": "admin create character Emma", "expected": "AVATAR_AND_ANALYSIS"},
            {"content": "system configuration update", "expected": "AVATAR_AND_ANALYSIS"},
            {"content": "emergency override test", "expected": "AVATAR_AND_ANALYSIS"}
        ]
        
        for i, test_case in enumerate(test_cases):
            try:
                stimuli_data = {
                    "content": test_case["content"],
                    "source": "test_user",  # Should trigger admin override
                    "priority": "high",
                    "metadata": {
                        "request_type": "admin",
                        "test_id": f"admin_test_{i+1}"
                    }
                }
                
                async with self.session.post(
                    f"{self.graphflow_url}/api/v1/stimuli/submit",
                    json=stimuli_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        stimuli_id = data.get("stimuli_id")
                        
                        # Wait a bit for processing
                        await asyncio.sleep(2)
                        
                        # Check the decision result
                        async with self.session.get(
                            f"{self.graphflow_url}/api/v1/stimuli/{stimuli_id}/status"
                        ) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                decision = status_data.get("decision", "UNKNOWN")
                                
                                test_result = {
                                    "content": test_case["content"],
                                    "expected": test_case["expected"],
                                    "actual": decision,
                                    "status": "PASS" if decision == test_case["expected"] else "FAIL",
                                    "stimuli_id": stimuli_id
                                }
                                
                                self.results["admin_tests"][f"test_{i+1}"] = test_result
                                
                                if decision == test_case["expected"]:
                                    logger.info(f"✅ Admin test {i+1} PASSED: '{test_case['content']}' → {decision}")
                                else:
                                    logger.error(f"❌ Admin test {i+1} FAILED: '{test_case['content']}' → {decision} (expected {test_case['expected']})")
                            else:
                                logger.error(f"Failed to get status for admin test {i+1}")
                    else:
                        logger.error(f"Failed to submit admin test {i+1}: HTTP {response.status}")
                        
            except Exception as e:
                logger.error(f"💥 Admin test {i+1} ERROR: {e}")
                self.results["admin_tests"][f"test_{i+1}"] = {
                    "content": test_case["content"],
                    "status": "ERROR",
                    "error": str(e)
                }
    
    async def run_all_tests(self):
        """Run all emergency system tests."""
        start_time = time.time()
        logger.info("🎯 STARTING EMERGENCY SYSTEM REBUILD TESTS")
        logger.info("=" * 60)
        
        await self.test_health_checks()
        await self.test_speech_routing()
        await self.test_analysis_routing()
        await self.test_admin_routing()
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info("=" * 60)
        logger.info(f"🏁 EMERGENCY SYSTEM TESTS COMPLETED in {duration:.2f}s")
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        with open("/home/geo/directories/autonomy/docker-vtuber/tests/emergency_rebuild_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        logger.info("📊 Results saved to emergency_rebuild_results.json")
    
    def generate_summary(self):
        """Generate test summary."""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        error_tests = 0
        
        for category in ["health_checks", "speech_tests", "analysis_tests", "admin_tests"]:
            for test_name, result in self.results[category].items():
                total_tests += 1
                status = result.get("status", "UNKNOWN")
                if status == "PASS":
                    passed_tests += 1
                elif status == "FAIL":
                    failed_tests += 1
                else:
                    error_tests += 1
        
        logger.info(f"📈 TEST SUMMARY:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   ✅ Passed: {passed_tests}")
        logger.info(f"   ❌ Failed: {failed_tests}")
        logger.info(f"   💥 Errors: {error_tests}")
        
        if failed_tests == 0 and error_tests == 0:
            logger.info("🎉 ALL TESTS PASSED! Emergency rebuild is successful!")
        else:
            logger.warning(f"⚠️ {failed_tests + error_tests} tests need attention.")
        
        self.results["summary"] = {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
        }


async def main():
    """Main test runner."""
    tester = EmergencySystemTester()
    
    try:
        await tester.setup()
        await tester.run_all_tests()
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())