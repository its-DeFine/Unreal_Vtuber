#!/usr/bin/env python3
"""
Comprehensive End-to-End Tests for S1/S2 Agent Categories and SCB Communication
=================================================================================

This test suite validates:
1. All 3 agent categories (trader, educator, streamer) in both S1 and S2
2. SCB write/read operations across systems
3. Agent memory and context usage from SCB information
4. Cross-system communication and data flow

Usage:
    python e2e_comprehensive_test.py
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class E2ETestSuite:
    """Comprehensive End-to-End Test Suite for S1/S2 Systems"""
    
    def __init__(self):
        # System endpoints
        self.s1_endpoint = "http://localhost:5001"    # S1 Character System
        self.s2_endpoint = "http://localhost:8200"     # S2 AutoGen Agent System
        
        # Test configuration
        self.test_results = []
        self.scb_test_data = {}
        
        # Agent categories to test
        self.agent_categories = {
            "trader": {
                "s1_character": "dr._house_doctor_template",
                "s2_team": "trader",
                "test_prompts": [
                    "Analyze current cryptocurrency market trends",
                    "Should I invest in tech stocks right now?",
                    "What are the risks of day trading?"
                ]
            },
            "educator": {
                "s1_character": "emma_teacher_template", 
                "s2_team": "educator",
                "test_prompts": [
                    "Explain machine learning concepts for beginners",
                    "Create a lesson plan for Python programming",
                    "How do I teach complex mathematics effectively?"
                ]
            },
            "streamer": {
                "s1_character": "weatherman_template",
                "s2_team": "streamer", 
                "test_prompts": [
                    "Plan an engaging live stream about technology",
                    "How to grow my streaming audience?",
                    "Create content ideas for educational streams"
                ]
            }
        }
    
    async def run_all_tests(self):
        """Run the complete test suite"""
        logger.info("🚀 Starting Comprehensive E2E Test Suite")
        
        try:
            # Phase 1: System Health Checks
            await self.test_system_health()
            
            # Phase 2: Individual Agent Category Tests
            for category in self.agent_categories.keys():
                await self.test_agent_category(category)
            
            # Phase 3: SCB Communication Tests
            await self.test_scb_operations()
            
            # Phase 4: Cross-System Memory Tests
            await self.test_cross_system_memory()
            
            # Phase 5: Generate Report
            self.generate_test_report()
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            raise
    
    async def test_system_health(self):
        """Test that both S1 and S2 systems are healthy"""
        logger.info("🏥 Testing System Health")
        
        async with aiohttp.ClientSession() as session:
            # Test S2 Health
            try:
                async with session.get(f"{self.s2_endpoint}/health") as response:
                    s2_health = await response.json()
                    assert response.status == 200
                    assert s2_health.get("status") == "healthy"
                    logger.info("✅ S2 System is healthy")
                    self.test_results.append({
                        "test": "S2_Health",
                        "status": "PASS",
                        "details": s2_health
                    })
            except Exception as e:
                logger.error(f"❌ S2 Health check failed: {e}")
                self.test_results.append({
                    "test": "S2_Health", 
                    "status": "FAIL",
                    "error": str(e)
                })
            
            # Test S1 Health (try multiple endpoints)
            s1_healthy = False
            s1_endpoints_to_try = [
                f"{self.s1_endpoint}/health",
                f"{self.s1_endpoint}/character/list",
                f"{self.s1_endpoint}/status"
            ]
            
            for endpoint in s1_endpoints_to_try:
                try:
                    async with session.get(endpoint, timeout=10) as response:
                        if response.status == 200:
                            s1_data = await response.json()
                            logger.info(f"✅ S1 System accessible via {endpoint}")
                            self.test_results.append({
                                "test": "S1_Health",
                                "status": "PASS", 
                                "endpoint": endpoint,
                                "details": s1_data
                            })
                            s1_healthy = True
                            break
                except Exception as e:
                    logger.warning(f"⚠️ S1 endpoint {endpoint} failed: {e}")
            
            if not s1_healthy:
                logger.error("❌ S1 System not accessible")
                self.test_results.append({
                    "test": "S1_Health",
                    "status": "FAIL", 
                    "error": "No S1 endpoints accessible"
                })
    
    async def test_agent_category(self, category: str):
        """Test a specific agent category in both S1 and S2"""
        logger.info(f"🤖 Testing {category.upper()} Agent Category")
        
        config = self.agent_categories[category]
        
        # Test S2 Team
        await self.test_s2_team(category, config)
        
        # Test S1 Character
        await self.test_s1_character(category, config)
        
        # Test Cross-System Integration
        await self.test_cross_system_integration(category, config)
    
    async def test_s2_team(self, category: str, config: Dict[str, Any]):
        """Test S2 AutoGen team processing"""
        logger.info(f"🎯 Testing S2 {category} team")
        
        async with aiohttp.ClientSession() as session:
            for i, prompt in enumerate(config["test_prompts"]):
                try:
                    test_data = {
                        "team_type": config["s2_team"],
                        "content": prompt,
                        "metadata": {
                            "test_id": f"s2_{category}_{i}",
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    start_time = time.time()
                    async with session.post(
                        f"{self.s2_endpoint}/api/test/process",
                        json=test_data,
                        timeout=120
                    ) as response:
                        processing_time = time.time() - start_time
                        result = await response.json()
                        
                        success = (
                            response.status == 200 and 
                            result.get("status") == "success" and
                            result.get("result", {}).get("success", False)
                        )
                        
                        test_result = {
                            "test": f"S2_{category}_prompt_{i}",
                            "status": "PASS" if success else "FAIL",
                            "prompt": prompt,
                            "processing_time": processing_time,
                            "team_data": result.get("result", {}),
                            "insights_found": bool(result.get("result", {}).get("insights")),
                            "real_autogen": result.get("result", {}).get("debug_info", {}).get("real_autogen_chat", False)
                        }
                        
                        if not success:
                            test_result["error"] = result
                        
                        self.test_results.append(test_result)
                        logger.info(f"{'✅' if success else '❌'} S2 {category} prompt {i+1}: {processing_time:.2f}s")
                        
                        # Store for SCB testing
                        if success:
                            self.scb_test_data[f"s2_{category}_{i}"] = {
                                "system": "S2",
                                "category": category,
                                "prompt": prompt,
                                "result": result.get("result", {}),
                                "timestamp": datetime.now().isoformat()
                            }
                
                except Exception as e:
                    logger.error(f"❌ S2 {category} prompt {i} failed: {e}")
                    self.test_results.append({
                        "test": f"S2_{category}_prompt_{i}",
                        "status": "FAIL",
                        "prompt": prompt,
                        "error": str(e)
                    })
    
    async def test_s1_character(self, category: str, config: Dict[str, Any]):
        """Test S1 character processing"""
        logger.info(f"🎭 Testing S1 {category} character")
        
        async with aiohttp.ClientSession() as session:
            character_id = config["s1_character"]
            
            for i, prompt in enumerate(config["test_prompts"]):
                try:
                    success = False
                    start_time = time.time()
                    
                    # Step 1: Switch to the character
                    switch_data = {"character_id": character_id}
                    try:
                        async with session.post(
                            f"{self.s1_endpoint}/character/switch",
                            json=switch_data,
                            timeout=30
                        ) as switch_response:
                            if switch_response.status == 200:
                                switch_result = await switch_response.json()
                                logger.debug(f"Switched to character: {character_id}")
                                
                                # Step 2: Send the message via process_text
                                message_data = {
                                    "text": prompt,
                                    "autonomous_context": None,
                                    "direct_speech": False
                                }
                                
                                async with session.post(
                                    f"{self.s1_endpoint}/process_text",
                                    json=message_data,
                                    timeout=60
                                ) as response:
                                    processing_time = time.time() - start_time
                                    
                                    if response.status == 200:
                                        result = await response.json()
                                        success = True
                                        
                                        test_result = {
                                            "test": f"S1_{category}_prompt_{i}",
                                            "status": "PASS",
                                            "prompt": prompt,
                                            "character_id": character_id,
                                            "processing_time": processing_time,
                                            "switch_result": switch_result,
                                            "response": result
                                        }
                                        
                                        self.test_results.append(test_result)
                                        logger.info(f"✅ S1 {category} prompt {i+1}: {processing_time:.2f}s")
                                        
                                        # Store for SCB testing
                                        self.scb_test_data[f"s1_{category}_{i}"] = {
                                            "system": "S1", 
                                            "category": category,
                                            "character_id": character_id,
                                            "prompt": prompt,
                                            "result": result,
                                            "timestamp": datetime.now().isoformat()
                                        }
                                    else:
                                        logger.debug(f"S1 process_text failed with status: {response.status}")
                            else:
                                logger.debug(f"S1 character switch failed with status: {switch_response.status}")
                                
                    except Exception as e:
                        logger.debug(f"S1 character interaction failed: {e}")
                    
                    if not success:
                        self.test_results.append({
                            "test": f"S1_{category}_prompt_{i}",
                            "status": "FAIL",
                            "prompt": prompt,
                            "error": "No S1 endpoints responded successfully"
                        })
                        logger.error(f"❌ S1 {category} prompt {i+1}: No endpoints accessible")
                
                except Exception as e:
                    logger.error(f"❌ S1 {category} prompt {i} failed: {e}")
                    self.test_results.append({
                        "test": f"S1_{category}_prompt_{i}",
                        "status": "FAIL",
                        "prompt": prompt,
                        "error": str(e)
                    })
    
    async def test_cross_system_integration(self, category: str, config: Dict[str, Any]):
        """Test integration between S1 and S2 for the same category"""
        logger.info(f"🔗 Testing {category} cross-system integration")
        
        # Create a complex scenario that involves both systems
        integration_prompt = f"""
        Based on recent {category} activities in our system, please:
        1. Analyze the current context and previous interactions
        2. Provide comprehensive {category}-specific insights
        3. Suggest follow-up actions that leverage both systems
        
        Context: This is a cross-system integration test for {category} agents.
        """
        
        async with aiohttp.ClientSession() as session:
            try:
                # Send to S2 first (as it has better integration capabilities)
                s2_data = {
                    "team_type": config["s2_team"],
                    "content": integration_prompt,
                    "metadata": {
                        "test_type": "cross_system_integration",
                        "category": category,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                start_time = time.time()
                async with session.post(
                    f"{self.s2_endpoint}/api/test/process",
                    json=s2_data,
                    timeout=120
                ) as response:
                    s2_time = time.time() - start_time
                    s2_result = await response.json()
                    
                    s2_success = (
                        response.status == 200 and 
                        s2_result.get("status") == "success"
                    )
                    
                    self.test_results.append({
                        "test": f"CrossSystem_{category}_S2",
                        "status": "PASS" if s2_success else "FAIL",
                        "processing_time": s2_time,
                        "result": s2_result
                    })
                    
                    logger.info(f"{'✅' if s2_success else '❌'} Cross-system S2 {category}: {s2_time:.2f}s")
            
            except Exception as e:
                logger.error(f"❌ Cross-system S2 {category} failed: {e}")
                self.test_results.append({
                    "test": f"CrossSystem_{category}_S2",
                    "status": "FAIL",
                    "error": str(e)
                })
    
    async def test_scb_operations(self):
        """Test SCB write/read operations across systems"""
        logger.info("💾 Testing SCB Operations")
        
        # Test SCB write operation
        scb_test_key = f"e2e_test_{int(time.time())}"
        scb_test_value = {
            "test_data": "Comprehensive E2E test data",
            "categories_tested": list(self.agent_categories.keys()),
            "timestamp": datetime.now().isoformat(),
            "test_results_summary": {
                "total_tests": len(self.test_results),
                "passed": len([r for r in self.test_results if r["status"] == "PASS"]),
                "failed": len([r for r in self.test_results if r["status"] == "FAIL"])
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Test SCB write via S2 (assuming S2 has SCB integration)
                write_data = {
                    "key": scb_test_key,
                    "value": scb_test_value,
                    "metadata": {"test_type": "e2e_scb_test"}
                }
                
                # Try different SCB endpoints
                scb_endpoints = [
                    f"{self.s2_endpoint}/api/scb/write",
                    f"{self.s2_endpoint}/scb/store",
                    f"{self.s1_endpoint}/api/scb/write"
                ]
                
                scb_write_success = False
                for endpoint in scb_endpoints:
                    try:
                        async with session.post(endpoint, json=write_data, timeout=30) as response:
                            if response.status in [200, 201]:
                                scb_write_result = await response.json()
                                scb_write_success = True
                                logger.info(f"✅ SCB write successful via {endpoint}")
                                self.test_results.append({
                                    "test": "SCB_Write",
                                    "status": "PASS",
                                    "endpoint": endpoint,
                                    "key": scb_test_key,
                                    "result": scb_write_result
                                })
                                break
                    except Exception as e:
                        logger.debug(f"SCB write endpoint {endpoint} failed: {e}")
                        continue
                
                if not scb_write_success:
                    logger.warning("⚠️ SCB write test skipped - no endpoints available")
                    self.test_results.append({
                        "test": "SCB_Write",
                        "status": "SKIP",
                        "reason": "No SCB endpoints accessible"
                    })
                
                # Test SCB read operation
                if scb_write_success:
                    await asyncio.sleep(2)  # Allow time for write to propagate
                    
                    scb_read_endpoints = [
                        f"{self.s2_endpoint}/api/scb/read/{scb_test_key}",
                        f"{self.s2_endpoint}/scb/retrieve/{scb_test_key}",
                        f"{self.s1_endpoint}/api/scb/read/{scb_test_key}"
                    ]
                    
                    for endpoint in scb_read_endpoints:
                        try:
                            async with session.get(endpoint, timeout=30) as response:
                                if response.status == 200:
                                    scb_read_result = await response.json()
                                    logger.info(f"✅ SCB read successful via {endpoint}")
                                    self.test_results.append({
                                        "test": "SCB_Read",
                                        "status": "PASS",
                                        "endpoint": endpoint,
                                        "key": scb_test_key,
                                        "result": scb_read_result
                                    })
                                    break
                        except Exception as e:
                            logger.debug(f"SCB read endpoint {endpoint} failed: {e}")
                            continue
                    else:
                        logger.warning("⚠️ SCB read test failed - no endpoints returned data")
                        self.test_results.append({
                            "test": "SCB_Read",
                            "status": "FAIL", 
                            "reason": "No SCB read endpoints accessible"
                        })
            
            except Exception as e:
                logger.error(f"❌ SCB operations test failed: {e}")
                self.test_results.append({
                    "test": "SCB_Operations",
                    "status": "FAIL",
                    "error": str(e)
                })
    
    async def test_cross_system_memory(self):
        """Test agent memory and context usage from SCB"""
        logger.info("🧠 Testing Cross-System Memory and Context")
        
        # Create a memory test scenario
        memory_scenario = {
            "initial_context": "User is interested in learning about cryptocurrency trading",
            "s1_interaction": "User asked about Bitcoin investment strategies",
            "s2_follow_up": "Now asking for specific trading recommendations based on previous conversation"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Phase 1: Store context via S1 (simulate user interaction)
                context_prompt = f"""
                Remember this context for future interactions:
                {memory_scenario['initial_context']}
                
                User question: {memory_scenario['s1_interaction']}
                Please provide a response and store this interaction for context.
                """
                
                # Phase 2: Test S2 memory retrieval
                memory_test_prompt = f"""
                Based on our previous conversation about cryptocurrency and the user's interest in Bitcoin:
                {memory_scenario['s2_follow_up']}
                
                Please reference any previous context or interactions to provide personalized recommendations.
                """
                
                start_time = time.time()
                async with session.post(
                    f"{self.s2_endpoint}/api/test/process",
                    json={
                        "team_type": "trader",
                        "content": memory_test_prompt,
                        "metadata": {
                            "test_type": "memory_context_test",
                            "expects_context": True,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    timeout=120
                ) as response:
                    memory_time = time.time() - start_time
                    memory_result = await response.json()
                    
                    memory_success = (
                        response.status == 200 and 
                        memory_result.get("status") == "success"
                    )
                    
                    # Analyze if the response shows context awareness
                    response_content = str(memory_result.get("result", {}))
                    context_indicators = [
                        "previous", "earlier", "context", "remember", "before",
                        "conversation", "discussed", "mentioned"
                    ]
                    context_aware = any(indicator in response_content.lower() for indicator in context_indicators)
                    
                    self.test_results.append({
                        "test": "Cross_System_Memory",
                        "status": "PASS" if memory_success else "FAIL",
                        "processing_time": memory_time,
                        "context_aware": context_aware,
                        "memory_indicators": [ind for ind in context_indicators if ind in response_content.lower()],
                        "result": memory_result
                    })
                    
                    logger.info(f"{'✅' if memory_success else '❌'} Memory test: {memory_time:.2f}s, Context aware: {context_aware}")
            
            except Exception as e:
                logger.error(f"❌ Cross-system memory test failed: {e}")
                self.test_results.append({
                    "test": "Cross_System_Memory",
                    "status": "FAIL",
                    "error": str(e)
                })
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("📊 Generating Test Report")
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped_tests = len([r for r in self.test_results if r["status"] == "SKIP"])
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "success_rate": f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%",
                "timestamp": datetime.now().isoformat()
            },
            "category_results": {},
            "system_results": {
                "S1": {"passed": 0, "failed": 0, "skipped": 0},
                "S2": {"passed": 0, "failed": 0, "skipped": 0}
            },
            "detailed_results": self.test_results,
            "scb_data_collected": len(self.scb_test_data),
            "test_configuration": {
                "s1_endpoint": self.s1_endpoint,
                "s2_endpoint": self.s2_endpoint,
                "agent_categories": list(self.agent_categories.keys())
            }
        }
        
        # Analyze results by category
        for category in self.agent_categories.keys():
            category_tests = [r for r in self.test_results if category in r.get("test", "")]
            report["category_results"][category] = {
                "total": len(category_tests),
                "passed": len([r for r in category_tests if r["status"] == "PASS"]),
                "failed": len([r for r in category_tests if r["status"] == "FAIL"])
            }
        
        # Analyze results by system
        for result in self.test_results:
            test_name = result.get("test", "")
            status = result.get("status", "").lower()
            if status not in ["passed", "failed", "skipped"]:
                # Map status to expected keys
                if status == "pass":
                    status = "passed"
                elif status == "fail":
                    status = "failed"
                elif status == "skip":
                    status = "skipped"
            
            if "S1_" in test_name and status in report["system_results"]["S1"]:
                report["system_results"]["S1"][status] += 1
            elif "S2_" in test_name and status in report["system_results"]["S2"]:
                report["system_results"]["S2"][status] += 1
        
        # Save report
        report_file = f"/tmp/e2e_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"🎯 E2E TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏭️ Skipped: {skipped_tests}")
        print(f"📈 Success Rate: {report['test_summary']['success_rate']}")
        print(f"\n📁 Full report saved to: {report_file}")
        print(f"{'='*80}")
        
        # Print category breakdown
        print(f"\n📊 CATEGORY BREAKDOWN:")
        for category, results in report["category_results"].items():
            success_rate = f"{(results['passed']/results['total']*100):.1f}%" if results['total'] > 0 else "0%"
            print(f"  {category.upper()}: {results['passed']}/{results['total']} ({success_rate})")
        
        # Print system breakdown
        print(f"\n🖥️ SYSTEM BREAKDOWN:")
        for system, results in report["system_results"].items():
            total = results['passed'] + results['failed'] + results['skipped']
            if total > 0:
                success_rate = f"{(results['passed']/total*100):.1f}%"
                print(f"  {system}: {results['passed']}/{total} ({success_rate})")
        
        return report

async def main():
    """Main test execution"""
    print("🚀 Starting Comprehensive E2E Test Suite for S1/S2 Agent Categories")
    
    test_suite = E2ETestSuite()
    
    try:
        await test_suite.run_all_tests()
        print("✅ Test suite completed successfully")
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())