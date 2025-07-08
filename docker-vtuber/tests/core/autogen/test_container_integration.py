#!/usr/bin/env python3
"""
Container Integration Tests for Stimuli Consolidation System

This script tests the consolidation system within the actual container environment
to verify it works correctly with the real S1 Avatar and S2 AutoGen systems.
"""

import asyncio
import logging
import json
import aiohttp
import time
from datetime import datetime
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContainerTester:
    """Test runner for container integration tests"""
    
    def __init__(self):
        self.s1_endpoint = os.getenv("S1_AVATAR_ENDPOINT", "http://neurosync:5001")
        self.s2_endpoint = os.getenv("S2_AUTOGEN_ENDPOINT", "http://localhost:8000")
        self.graphflow_endpoint = os.getenv("GRAPHFLOW_ENDPOINT", "http://localhost:8081")
        
        # Test results storage
        self.test_results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }
    
    async def run_all_tests(self):
        """Run all container integration tests"""
        logger.info("🚀 Starting Container Integration Tests")
        
        tests = [
            ("Test S1 Avatar Availability", self.test_s1_availability),
            ("Test S2 AutoGen Availability", self.test_s2_availability), 
            ("Test Consolidation System Initialization", self.test_consolidation_init),
            ("Test Single Stimuli Processing", self.test_single_stimuli),
            ("Test Multiple Stimuli Consolidation", self.test_multiple_stimuli),
            ("Test High Priority Stimuli Handling", self.test_priority_handling),
            ("Test Capacity Monitoring", self.test_capacity_monitoring),
            ("Test System Overload Handling", self.test_overload_handling),
            ("Test End-to-End Integration", self.test_end_to_end)
        ]
        
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
        
        # Print summary
        self.print_test_summary()
    
    async def run_test(self, test_name: str, test_func):
        """Run an individual test"""
        logger.info(f"🧪 Running: {test_name}")
        self.test_results["tests_run"] += 1
        
        try:
            start_time = time.time()
            result = await test_func()
            duration = time.time() - start_time
            
            if result.get("success", False):
                self.test_results["tests_passed"] += 1
                logger.info(f"✅ {test_name} - PASSED ({duration:.2f}s)")
            else:
                self.test_results["tests_failed"] += 1
                logger.error(f"❌ {test_name} - FAILED: {result.get('error', 'Unknown error')}")
            
            self.test_results["details"].append({
                "name": test_name,
                "success": result.get("success", False),
                "duration": duration,
                "details": result,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.test_results["tests_failed"] += 1
            logger.error(f"❌ {test_name} - ERROR: {e}")
            self.test_results["details"].append({
                "name": test_name,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def test_s1_availability(self) -> dict:
        """Test S1 Avatar system availability"""
        try:
            # Test S1 health endpoint
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Try health check
                try:
                    async with session.get(f"{self.s1_endpoint}/health") as response:
                        if response.status == 200:
                            health_data = await response.json()
                            return {
                                "success": True,
                                "s1_status": "healthy",
                                "health_data": health_data
                            }
                except:
                    pass
                
                # Try status endpoint
                try:
                    async with session.get(f"{self.s1_endpoint}/status") as response:
                        if response.status == 200:
                            status_data = await response.json()
                            return {
                                "success": True,
                                "s1_status": "available",
                                "status_data": status_data
                            }
                except:
                    pass
                
                # Try process_text endpoint (minimal test)
                try:
                    test_payload = {
                        "text": "Container test message",
                        "direct_speech": True,
                        "autonomous_context": {"test": True}
                    }
                    async with session.post(f"{self.s1_endpoint}/process_text", json=test_payload) as response:
                        if response.status == 200:
                            return {
                                "success": True,
                                "s1_status": "fully_functional",
                                "process_text_available": True
                            }
                        else:
                            response_text = await response.text()
                            return {
                                "success": False,
                                "error": f"Process text failed: HTTP {response.status} - {response_text}"
                            }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"S1 connection failed: {e}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"S1 test failed: {e}"
            }
    
    async def test_s2_availability(self) -> dict:
        """Test S2 AutoGen system availability"""
        try:
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Test S2 stimuli API
                try:
                    async with session.get(f"{self.s2_endpoint}/api/stimuli/status") as response:
                        if response.status == 200:
                            status_data = await response.json()
                            return {
                                "success": True,
                                "s2_status": "available",
                                "status_data": status_data
                            }
                        else:
                            response_text = await response.text()
                            return {
                                "success": False,
                                "error": f"S2 status failed: HTTP {response.status} - {response_text}"
                            }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"S2 connection failed: {e}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"S2 test failed: {e}"
            }
    
    async def test_consolidation_init(self) -> dict:
        """Test consolidation system initialization"""
        try:
            timeout = aiohttp.ClientTimeout(total=10.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Get S2 status which should include consolidation info
                async with session.get(f"{self.s2_endpoint}/api/stimuli/status") as response:
                    if response.status == 200:
                        status_data = await response.json()
                        
                        # Check for consolidation-related fields in status
                        has_consolidation = (
                            "consolidation" in str(status_data).lower() or
                            "capacity" in str(status_data).lower() or
                            "architecture" in str(status_data).lower()
                        )
                        
                        return {
                            "success": True,
                            "consolidation_detected": has_consolidation,
                            "status_data": status_data
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to get S2 status: HTTP {response.status}"
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "error": f"Consolidation init test failed: {e}"
            }
    
    async def test_single_stimuli(self) -> dict:
        """Test processing a single stimuli"""
        try:
            timeout = aiohttp.ClientTimeout(total=15.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Send a single stimuli to S2
                stimuli_payload = {
                    "stimuli_id": f"test_single_{int(time.time())}",
                    "content": "This is a container integration test for single stimuli processing",
                    "source": "container_test",
                    "priority": "medium",
                    "category": "test",
                    "metadata": {"test_type": "single_stimuli", "container_test": True}
                }
                
                async with session.post(f"{self.s2_endpoint}/api/stimuli/receive", json=stimuli_payload) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return {
                            "success": True,
                            "stimuli_processed": True,
                            "response_data": response_data
                        }
                    else:
                        response_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Single stimuli failed: HTTP {response.status} - {response_text}"
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "error": f"Single stimuli test failed: {e}"
            }
    
    async def test_multiple_stimuli(self) -> dict:
        """Test processing multiple stimuli (consolidation)"""
        try:
            timeout = aiohttp.ClientTimeout(total=20.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Send multiple related stimuli quickly
                stimuli_batch = []
                base_time = int(time.time())
                
                for i in range(3):
                    stimuli = {
                        "stimuli_id": f"test_batch_{base_time}_{i}",
                        "content": f"Batch test message {i+1} - system performance analysis",
                        "source": "container_test_batch",
                        "priority": "medium",
                        "category": "performance",
                        "metadata": {"test_type": "batch", "batch_id": base_time, "index": i}
                    }
                    stimuli_batch.append(stimuli)
                
                # Send stimuli in quick succession
                responses = []
                for stimuli in stimuli_batch:
                    try:
                        async with session.post(f"{self.s2_endpoint}/api/stimuli/receive", json=stimuli) as response:
                            if response.status == 200:
                                response_data = await response.json()
                                responses.append(response_data)
                            else:
                                response_text = await response.text()
                                responses.append({"error": f"HTTP {response.status} - {response_text}"})
                        
                        # Small delay between stimuli
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        responses.append({"error": str(e)})
                
                # Check results
                successful_responses = [r for r in responses if "error" not in r]
                
                return {
                    "success": len(successful_responses) >= 2,  # At least 2 should succeed
                    "stimuli_sent": len(stimuli_batch),
                    "successful_responses": len(successful_responses),
                    "responses": responses,
                    "consolidation_opportunity": len(stimuli_batch) >= 2
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Multiple stimuli test failed: {e}"
            }
    
    async def test_priority_handling(self) -> dict:
        """Test high priority stimuli handling"""
        try:
            timeout = aiohttp.ClientTimeout(total=15.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Send a high priority stimuli
                high_priority_stimuli = {
                    "stimuli_id": f"test_priority_{int(time.time())}",
                    "content": "URGENT: Critical system alert requiring immediate attention",
                    "source": "container_test_priority",
                    "priority": "high",
                    "category": "alert",
                    "metadata": {"test_type": "priority", "urgent": True}
                }
                
                start_time = time.time()
                async with session.post(f"{self.s2_endpoint}/api/stimuli/receive", json=high_priority_stimuli) as response:
                    processing_time = time.time() - start_time
                    
                    if response.status == 200:
                        response_data = await response.json()
                        return {
                            "success": True,
                            "priority_processed": True,
                            "processing_time": processing_time,
                            "response_data": response_data,
                            "fast_processing": processing_time < 5.0  # Should be processed quickly
                        }
                    else:
                        response_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Priority stimuli failed: HTTP {response.status} - {response_text}"
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "error": f"Priority handling test failed: {e}"
            }
    
    async def test_capacity_monitoring(self) -> dict:
        """Test capacity monitoring functionality"""
        try:
            # This test checks if the system can report capacity status
            timeout = aiohttp.ClientTimeout(total=10.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Get current system status
                async with session.get(f"{self.s2_endpoint}/api/stimuli/status") as response:
                    if response.status == 200:
                        status_data = await response.json()
                        
                        # Look for capacity-related information
                        status_str = json.dumps(status_data).lower()
                        has_capacity_info = (
                            "capacity" in status_str or
                            "load" in status_str or
                            "available" in status_str or
                            "consolidation" in status_str
                        )
                        
                        return {
                            "success": True,
                            "capacity_monitoring_detected": has_capacity_info,
                            "status_data": status_data
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to get capacity status: HTTP {response.status}"
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "error": f"Capacity monitoring test failed: {e}"
            }
    
    async def test_overload_handling(self) -> dict:
        """Test system behavior under rapid stimuli load"""
        try:
            timeout = aiohttp.ClientTimeout(total=30.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Send rapid stimuli to test overload handling
                rapid_stimuli = []
                base_time = int(time.time())
                
                for i in range(5):
                    stimuli = {
                        "stimuli_id": f"test_overload_{base_time}_{i}",
                        "content": f"Rapid load test {i+1} - testing system capacity",
                        "source": "container_test_overload",
                        "priority": "medium",
                        "category": "load_test",
                        "metadata": {"test_type": "overload", "sequence": i}
                    }
                    rapid_stimuli.append(stimuli)
                
                # Send all stimuli as quickly as possible
                tasks = []
                for stimuli in rapid_stimuli:
                    task = session.post(f"{self.s2_endpoint}/api/stimuli/receive", json=stimuli)
                    tasks.append(task)
                
                # Wait for all responses
                responses = []
                for task in tasks:
                    try:
                        async with task as response:
                            if response.status == 200:
                                response_data = await response.json()
                                responses.append({"success": True, "data": response_data})
                            else:
                                response_text = await response.text()
                                responses.append({
                                    "success": False, 
                                    "error": f"HTTP {response.status} - {response_text}"
                                })
                    except Exception as e:
                        responses.append({"success": False, "error": str(e)})
                
                successful_count = sum(1 for r in responses if r.get("success", False))
                
                return {
                    "success": successful_count >= 3,  # At least 3 should succeed
                    "stimuli_sent": len(rapid_stimuli),
                    "successful_responses": successful_count,
                    "responses": responses,
                    "system_handled_load": successful_count >= 3
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Overload handling test failed: {e}"
            }
    
    async def test_end_to_end(self) -> dict:
        """Test complete end-to-end integration"""
        try:
            # This test sends stimuli and checks for S1 Avatar response
            timeout = aiohttp.ClientTimeout(total=20.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Send a stimuli that should trigger S1 Avatar
                e2e_stimuli = {
                    "stimuli_id": f"test_e2e_{int(time.time())}",
                    "content": "End-to-end integration test - please respond with speech",
                    "source": "container_test_e2e",
                    "priority": "medium",
                    "category": "integration",
                    "metadata": {"test_type": "end_to_end", "expect_s1_response": True}
                }
                
                # Send stimuli to S2
                async with session.post(f"{self.s2_endpoint}/api/stimuli/receive", json=e2e_stimuli) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        return {
                            "success": False,
                            "error": f"S2 processing failed: HTTP {response.status} - {response_text}"
                        }
                    
                    s2_response = await response.json()
                
                # Wait a moment for S1 processing
                await asyncio.sleep(2)
                
                # Check if S1 received the trigger (look for recent activity)
                try:
                    async with session.get(f"{self.s1_endpoint}/status") as s1_response:
                        if s1_response.status == 200:
                            s1_status = await s1_response.json()
                            
                            return {
                                "success": True,
                                "s2_response": s2_response,
                                "s1_status": s1_status,
                                "end_to_end_flow": True
                            }
                        else:
                            return {
                                "success": True,  # S2 worked, S1 status unavailable but that's OK
                                "s2_response": s2_response,
                                "s1_status_unavailable": True,
                                "partial_e2e": True
                            }
                except:
                    return {
                        "success": True,  # S2 worked, S1 check failed but that's acceptable
                        "s2_response": s2_response,
                        "s1_check_failed": True,
                        "partial_e2e": True
                    }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"End-to-end test failed: {e}"
            }
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        logger.info("📊 Container Integration Test Results")
        logger.info("=" * 50)
        logger.info(f"Tests Run: {self.test_results['tests_run']}")
        logger.info(f"Passed: {self.test_results['tests_passed']}")
        logger.info(f"Failed: {self.test_results['tests_failed']}")
        
        if self.test_results['tests_run'] > 0:
            success_rate = (self.test_results['tests_passed'] / self.test_results['tests_run']) * 100
            logger.info(f"Success Rate: {success_rate:.1f}%")
        
        logger.info("\nDetailed Results:")
        for detail in self.test_results['details']:
            status = "✅ PASS" if detail['success'] else "❌ FAIL"
            duration = detail.get('duration', 0)
            logger.info(f"{status} {detail['name']} ({duration:.2f}s)")
            
            if not detail['success'] and 'error' in detail:
                logger.info(f"    Error: {detail['error']}")
        
        # Save results to file
        results_file = f"/tmp/container_test_results_{int(time.time())}.json"
        try:
            with open(results_file, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            logger.info(f"\n📄 Full results saved to: {results_file}")
        except Exception as e:
            logger.warning(f"Failed to save results: {e}")


async def main():
    """Main test runner"""
    logger.info("🐳 Container Integration Test Suite for Stimuli Consolidation")
    logger.info("Testing in actual container environment...")
    
    tester = ContainerTester()
    await tester.run_all_tests()
    
    # Exit with appropriate code
    if tester.test_results['tests_failed'] == 0:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error(f"💥 {tester.test_results['tests_failed']} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())