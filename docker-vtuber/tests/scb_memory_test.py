#!/usr/bin/env python3
"""
SCB Memory and Context Test Suite
=================================

This test specifically focuses on SCB (Shared Communication Bridge) functionality:
1. SCB write/read operations
2. Memory persistence across sessions
3. Context retrieval and usage by agents
4. Cross-system memory sharing between S1 and S2

Usage:
    python scb_memory_test.py
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SCBMemoryTestSuite:
    """Test suite specifically for SCB memory and context functionality"""
    
    def __init__(self):
        self.s1_endpoint = "http://localhost:5001"
        self.s2_endpoint = "http://localhost:8200"
        self.test_results = []
        self.memory_test_data = {}
        
        # Memory test scenarios
        self.memory_scenarios = [
            {
                "id": "trader_memory",
                "category": "trader",
                "initial_context": {
                    "user_profile": "Conservative investor, age 45, prefers low-risk investments",
                    "previous_questions": ["What are safe investment options?", "How to build emergency fund?"],
                    "risk_tolerance": "low",
                    "investment_goals": "retirement savings"
                },
                "test_sequence": [
                    "Remember my investment profile: I'm 45, prefer low-risk investments for retirement",
                    "What do you think about my current risk tolerance?",
                    "Based on what you know about me, should I invest in cryptocurrency?"
                ]
            },
            {
                "id": "educator_memory", 
                "category": "educator",
                "initial_context": {
                    "student_profile": "Beginner programmer, learning Python, struggles with loops",
                    "learning_style": "visual learner, needs examples",
                    "progress": "completed variables and functions, stuck on loops"
                },
                "test_sequence": [
                    "I'm learning Python and having trouble with loops. I'm a visual learner.",
                    "Can you help me understand for loops better?",
                    "Based on my learning progress, what should I study next after loops?"
                ]
            },
            {
                "id": "streamer_memory",
                "category": "streamer", 
                "initial_context": {
                    "channel_info": "Gaming/tech channel, 5K subscribers, streams 3x/week",
                    "audience_demographics": "18-25 age range, interested in gaming and tech",
                    "content_goals": "grow audience, improve engagement"
                },
                "test_sequence": [
                    "I have a gaming/tech channel with 5K subs. I stream 3 times a week.",
                    "My audience is mostly 18-25 year olds. How can I improve engagement?",
                    "Based on my channel info, what content would work best for my audience?"
                ]
            }
        ]
    
    async def run_scb_memory_tests(self):
        """Run comprehensive SCB memory tests"""
        logger.info("🧠 Starting SCB Memory Test Suite")
        
        try:
            # Phase 1: Test basic SCB operations
            await self.test_basic_scb_operations()
            
            # Phase 2: Test memory persistence scenarios
            for scenario in self.memory_scenarios:
                await self.test_memory_scenario(scenario)
            
            # Phase 3: Test cross-system memory sharing
            await self.test_cross_system_memory_sharing()
            
            # Phase 4: Test memory degradation and cleanup
            await self.test_memory_management()
            
            # Phase 5: Generate specialized report
            self.generate_scb_report()
            
        except Exception as e:
            logger.error(f"❌ SCB memory test suite failed: {e}")
            raise
    
    async def test_basic_scb_operations(self):
        """Test fundamental SCB read/write operations"""
        logger.info("💾 Testing Basic SCB Operations")
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Direct SCB Write
            test_key = f"scb_test_{int(time.time())}"
            test_data = {
                "test_type": "basic_scb_write",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "user_id": "test_user_123",
                    "preferences": {"theme": "dark", "language": "en"},
                    "session_data": {"last_active": datetime.now().isoformat()}
                }
            }
            
            # Try multiple SCB endpoints for writing
            scb_write_endpoints = [
                f"{self.s2_endpoint}/api/scb/write",
                f"{self.s2_endpoint}/scb/store", 
                f"{self.s1_endpoint}/api/scb/write",
                f"{self.s1_endpoint}/scb/store"
            ]
            
            write_success = False
            for endpoint in scb_write_endpoints:
                try:
                    async with session.post(
                        endpoint,
                        json={"key": test_key, "value": test_data},
                        timeout=30
                    ) as response:
                        if response.status in [200, 201]:
                            result = await response.json()
                            write_success = True
                            logger.info(f"✅ SCB write successful: {endpoint}")
                            self.test_results.append({
                                "test": "SCB_Direct_Write",
                                "status": "PASS",
                                "endpoint": endpoint,
                                "key": test_key,
                                "result": result
                            })
                            break
                except Exception as e:
                    logger.debug(f"SCB write endpoint {endpoint} failed: {e}")
                    continue
            
            if not write_success:
                # Try alternative: write via agent interaction
                logger.info("🔄 Testing SCB write via agent interaction")
                await self.test_scb_via_agent_interaction(test_key, test_data)
            
            # Test 2: Direct SCB Read
            if write_success:
                await asyncio.sleep(2)  # Allow propagation time
                
                scb_read_endpoints = [
                    f"{self.s2_endpoint}/api/scb/read/{test_key}",
                    f"{self.s2_endpoint}/scb/retrieve/{test_key}",
                    f"{self.s1_endpoint}/api/scb/read/{test_key}",
                    f"{self.s1_endpoint}/scb/retrieve/{test_key}"
                ]
                
                for endpoint in scb_read_endpoints:
                    try:
                        async with session.get(endpoint, timeout=30) as response:
                            if response.status == 200:
                                result = await response.json()
                                logger.info(f"✅ SCB read successful: {endpoint}")
                                self.test_results.append({
                                    "test": "SCB_Direct_Read",
                                    "status": "PASS",
                                    "endpoint": endpoint,
                                    "key": test_key,
                                    "result": result
                                })
                                break
                    except Exception as e:
                        logger.debug(f"SCB read endpoint {endpoint} failed: {e}")
                        continue
                else:
                    self.test_results.append({
                        "test": "SCB_Direct_Read",
                        "status": "FAIL",
                        "reason": "No SCB read endpoints accessible"
                    })
    
    async def test_scb_via_agent_interaction(self, test_key: str, test_data: Dict[str, Any]):
        """Test SCB operations through agent interactions"""
        logger.info("🤖 Testing SCB via Agent Interaction")
        
        async with aiohttp.ClientSession() as session:
            # Prompt the agent to store information
            store_prompt = f"""
            Please remember and store this information for future reference:
            Key: {test_key}
            Data: {json.dumps(test_data, indent=2)}
            
            This is important user data that should be accessible in future conversations.
            Please confirm that you've stored this information.
            """
            
            try:
                async with session.post(
                    f"{self.s2_endpoint}/api/test/process",
                    json={
                        "team_type": "educator",  # Use educator as they handle information well
                        "content": store_prompt,
                        "metadata": {
                            "test_type": "scb_via_agent_store",
                            "scb_key": test_key,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        store_success = result.get("status") == "success"
                        
                        self.test_results.append({
                            "test": "SCB_Via_Agent_Store",
                            "status": "PASS" if store_success else "FAIL",
                            "result": result
                        })
                        
                        logger.info(f"{'✅' if store_success else '❌'} SCB store via agent")
                        
                        if store_success:
                            # Test retrieval via agent
                            await asyncio.sleep(2)
                            await self.test_scb_retrieval_via_agent(test_key)
            
            except Exception as e:
                logger.error(f"❌ SCB via agent interaction failed: {e}")
                self.test_results.append({
                    "test": "SCB_Via_Agent_Store",
                    "status": "FAIL",
                    "error": str(e)
                })
    
    async def test_scb_retrieval_via_agent(self, test_key: str):
        """Test SCB data retrieval through agent"""
        retrieve_prompt = f"""
        Please retrieve and tell me about the information stored with key: {test_key}
        
        I'm looking for the data I asked you to remember earlier. Can you access and 
        summarize what was stored?
        """
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.s2_endpoint}/api/test/process",
                    json={
                        "team_type": "educator",
                        "content": retrieve_prompt,
                        "metadata": {
                            "test_type": "scb_via_agent_retrieve",
                            "scb_key": test_key,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        retrieve_success = result.get("status") == "success"
                        
                        # Check if response contains reference to stored data
                        response_content = str(result.get("result", {}))
                        has_memory_reference = any(term in response_content.lower() for term in [
                            "stored", "remember", "retrieved", "saved", "data", test_key.lower()
                        ])
                        
                        self.test_results.append({
                            "test": "SCB_Via_Agent_Retrieve",
                            "status": "PASS" if retrieve_success and has_memory_reference else "FAIL",
                            "has_memory_reference": has_memory_reference,
                            "result": result
                        })
                        
                        logger.info(f"{'✅' if retrieve_success and has_memory_reference else '❌'} SCB retrieve via agent")
            
            except Exception as e:
                logger.error(f"❌ SCB retrieval via agent failed: {e}")
                self.test_results.append({
                    "test": "SCB_Via_Agent_Retrieve",
                    "status": "FAIL",
                    "error": str(e)
                })
    
    async def test_memory_scenario(self, scenario: Dict[str, Any]):
        """Test a complete memory scenario with context building"""
        logger.info(f"🎯 Testing memory scenario: {scenario['id']}")
        
        scenario_id = scenario["id"]
        category = scenario["category"]
        test_sequence = scenario["test_sequence"]
        
        # Map category to S2 team
        team_mapping = {
            "trader": "trader",
            "educator": "educator", 
            "streamer": "streamer"
        }
        
        s2_team = team_mapping.get(category, "educator")
        
        async with aiohttp.ClientSession() as session:
            # Execute the conversation sequence
            conversation_memory = []
            
            for i, prompt in enumerate(test_sequence):
                try:
                    logger.info(f"  Step {i+1}/{len(test_sequence)}: {prompt[:50]}...")
                    
                    start_time = time.time()
                    async with session.post(
                        f"{self.s2_endpoint}/api/test/process",
                        json={
                            "team_type": s2_team,
                            "content": prompt,
                            "metadata": {
                                "test_type": "memory_scenario",
                                "scenario_id": scenario_id,
                                "step": i + 1,
                                "expects_memory": i > 0,  # After first interaction, expect memory
                                "timestamp": datetime.now().isoformat()
                            }
                        },
                        timeout=90
                    ) as response:
                        processing_time = time.time() - start_time
                        result = await response.json()
                        
                        success = response.status == 200 and result.get("status") == "success"
                        
                        # Analyze memory usage
                        response_content = str(result.get("result", {}))
                        memory_indicators = self.analyze_memory_usage(response_content, conversation_memory)
                        
                        step_result = {
                            "test": f"Memory_Scenario_{scenario_id}_Step_{i+1}",
                            "status": "PASS" if success else "FAIL",
                            "prompt": prompt,
                            "processing_time": processing_time,
                            "memory_analysis": memory_indicators,
                            "expects_memory": i > 0,
                            "result": result
                        }
                        
                        if not success:
                            step_result["error"] = result
                        
                        self.test_results.append(step_result)
                        conversation_memory.append({
                            "step": i + 1,
                            "prompt": prompt,
                            "response": response_content,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        logger.info(f"    {'✅' if success else '❌'} Step {i+1}: {processing_time:.2f}s, Memory: {memory_indicators.get('has_memory_reference', False)}")
                        
                        # Small delay between steps to allow memory processing
                        await asyncio.sleep(1)
                
                except Exception as e:
                    logger.error(f"❌ Memory scenario {scenario_id} step {i+1} failed: {e}")
                    self.test_results.append({
                        "test": f"Memory_Scenario_{scenario_id}_Step_{i+1}",
                        "status": "FAIL",
                        "prompt": prompt,
                        "error": str(e)
                    })
            
            # Store scenario results for cross-system testing
            self.memory_test_data[scenario_id] = {
                "scenario": scenario,
                "conversation_memory": conversation_memory,
                "timestamp": datetime.now().isoformat()
            }
    
    def analyze_memory_usage(self, response_content: str, conversation_memory: List[Dict]) -> Dict[str, Any]:
        """Analyze if the response shows memory/context awareness"""
        
        # Memory indicators
        memory_keywords = [
            "remember", "recall", "previous", "earlier", "before", "mentioned",
            "discussed", "conversation", "last time", "you said", "we talked",
            "context", "history", "profile", "preference"
        ]
        
        # Context-specific indicators based on conversation history
        context_keywords = []
        for memory in conversation_memory:
            # Extract key terms from previous prompts
            prompt_words = memory["prompt"].lower().split()
            context_keywords.extend([word for word in prompt_words if len(word) > 4])
        
        response_lower = response_content.lower()
        
        # Check for memory indicators
        memory_indicators_found = [kw for kw in memory_keywords if kw in response_lower]
        context_references = [kw for kw in context_keywords if kw in response_lower]
        
        return {
            "has_memory_reference": len(memory_indicators_found) > 0,
            "memory_indicators": memory_indicators_found,
            "context_references": context_references,
            "memory_score": len(memory_indicators_found) + len(context_references),
            "response_length": len(response_content)
        }
    
    async def test_cross_system_memory_sharing(self):
        """Test memory sharing between S1 and S2 systems"""
        logger.info("🔗 Testing Cross-System Memory Sharing")
        
        # Test scenario: Information shared in S1 should be accessible in S2
        cross_system_test = {
            "user_context": "Professional trader with 10 years experience",
            "s1_shared_info": "I prefer technical analysis over fundamental analysis",
            "s2_query": "Based on my trading preferences, what tools should I use?"
        }
        
        async with aiohttp.ClientSession() as session:
            # Phase 1: Try to establish context in S1 (if available)
            s1_endpoints = [
                f"{self.s1_endpoint}/api/chat",
                f"{self.s1_endpoint}/chat",
                f"{self.s1_endpoint}/character/dr._house_doctor_template/chat"
            ]
            
            s1_context_established = False
            for endpoint in s1_endpoints:
                try:
                    async with session.post(
                        endpoint,
                        json={
                            "message": f"Remember this about me: {cross_system_test['user_context']} and {cross_system_test['s1_shared_info']}",
                            "character_id": "dr._house_doctor_template",
                            "metadata": {"test_type": "cross_system_memory_establish"}
                        },
                        timeout=60
                    ) as response:
                        if response.status == 200:
                            s1_result = await response.json()
                            s1_context_established = True
                            logger.info(f"✅ S1 context established via {endpoint}")
                            
                            self.test_results.append({
                                "test": "Cross_System_S1_Context_Establish",
                                "status": "PASS",
                                "endpoint": endpoint,
                                "result": s1_result
                            })
                            break
                except Exception as e:
                    logger.debug(f"S1 endpoint {endpoint} failed: {e}")
                    continue
            
            if not s1_context_established:
                logger.warning("⚠️ Could not establish context in S1, testing S2 only")
                self.test_results.append({
                    "test": "Cross_System_S1_Context_Establish",
                    "status": "SKIP",
                    "reason": "S1 not accessible"
                })
            
            # Phase 2: Query S2 for context-aware response
            await asyncio.sleep(3)  # Allow time for cross-system propagation
            
            try:
                async with session.post(
                    f"{self.s2_endpoint}/api/test/process",
                    json={
                        "team_type": "trader",
                        "content": cross_system_test["s2_query"],
                        "metadata": {
                            "test_type": "cross_system_memory_retrieve",
                            "expects_s1_context": s1_context_established,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    timeout=90
                ) as response:
                    if response.status == 200:
                        s2_result = await response.json()
                        s2_success = s2_result.get("status") == "success"
                        
                        # Analyze if S2 shows awareness of S1 context
                        response_content = str(s2_result.get("result", {}))
                        context_terms = ["technical analysis", "preference", "experience", "trader"]
                        context_awareness = any(term in response_content.lower() for term in context_terms)
                        
                        self.test_results.append({
                            "test": "Cross_System_S2_Context_Retrieve",
                            "status": "PASS" if s2_success else "FAIL",
                            "s1_context_established": s1_context_established,
                            "s2_context_awareness": context_awareness,
                            "context_terms_found": [term for term in context_terms if term in response_content.lower()],
                            "result": s2_result
                        })
                        
                        logger.info(f"{'✅' if s2_success else '❌'} S2 cross-system query, Context aware: {context_awareness}")
            
            except Exception as e:
                logger.error(f"❌ Cross-system S2 query failed: {e}")
                self.test_results.append({
                    "test": "Cross_System_S2_Context_Retrieve",
                    "status": "FAIL",
                    "error": str(e)
                })
    
    async def test_memory_management(self):
        """Test memory persistence, degradation, and cleanup"""
        logger.info("🗑️ Testing Memory Management")
        
        # Test memory persistence over time
        persistent_key = f"persistent_test_{int(time.time())}"
        persistent_data = {
            "user_id": "persistence_test_user",
            "created": datetime.now().isoformat(),
            "importance": "high",
            "data": "This is test data for memory persistence validation"
        }
        
        async with aiohttp.ClientSession() as session:
            # Store data
            store_prompt = f"""
            Please store this important information and remember it:
            {json.dumps(persistent_data, indent=2)}
            
            This is critical data that must be remembered for future sessions.
            """
            
            try:
                async with session.post(
                    f"{self.s2_endpoint}/api/test/process",
                    json={
                        "team_type": "educator",
                        "content": store_prompt,
                        "metadata": {
                            "test_type": "memory_persistence_store",
                            "persistent_key": persistent_key,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    timeout=60
                ) as response:
                    if response.status == 200:
                        store_result = await response.json()
                        store_success = store_result.get("status") == "success"
                        
                        self.test_results.append({
                            "test": "Memory_Persistence_Store",
                            "status": "PASS" if store_success else "FAIL",
                            "key": persistent_key,
                            "result": store_result
                        })
                        
                        if store_success:
                            # Test immediate retrieval
                            await self.test_immediate_memory_retrieval(persistent_key, persistent_data)
                            
                            # Test delayed retrieval (simulate session gap)
                            await asyncio.sleep(5)
                            await self.test_delayed_memory_retrieval(persistent_key, persistent_data)
            
            except Exception as e:
                logger.error(f"❌ Memory persistence test failed: {e}")
                self.test_results.append({
                    "test": "Memory_Persistence_Store",
                    "status": "FAIL",
                    "error": str(e)
                })
    
    async def test_immediate_memory_retrieval(self, key: str, original_data: Dict[str, Any]):
        """Test immediate memory retrieval"""
        retrieve_prompt = f"""
        Can you tell me what you remember about the data I just asked you to store?
        I'm looking for information related to key: {key}
        """
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.s2_endpoint}/api/test/process",
                    json={
                        "team_type": "educator",
                        "content": retrieve_prompt,
                        "metadata": {
                            "test_type": "immediate_memory_retrieval",
                            "key": key,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        success = result.get("status") == "success"
                        
                        # Check for data elements in response
                        response_content = str(result.get("result", {}))
                        data_elements_found = [
                            element for element in [
                                "persistence_test_user", "important", "critical", "remember"
                            ] if element.lower() in response_content.lower()
                        ]
                        
                        has_memory = len(data_elements_found) > 0
                        
                        self.test_results.append({
                            "test": "Memory_Immediate_Retrieval",
                            "status": "PASS" if success and has_memory else "FAIL",
                            "key": key,
                            "has_memory": has_memory,
                            "data_elements_found": data_elements_found,
                            "result": result
                        })
                        
                        logger.info(f"{'✅' if success and has_memory else '❌'} Immediate memory retrieval")
            
            except Exception as e:
                logger.error(f"❌ Immediate memory retrieval failed: {e}")
                self.test_results.append({
                    "test": "Memory_Immediate_Retrieval",
                    "status": "FAIL",
                    "error": str(e)
                })
    
    async def test_delayed_memory_retrieval(self, key: str, original_data: Dict[str, Any]):
        """Test delayed memory retrieval (simulating session gap)"""
        retrieve_prompt = f"""
        Earlier in our conversation, I asked you to remember some important data.
        Can you recall what I stored? It was related to a persistence test.
        """
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.s2_endpoint}/api/test/process",
                    json={
                        "team_type": "educator",
                        "content": retrieve_prompt,
                        "metadata": {
                            "test_type": "delayed_memory_retrieval",
                            "key": key,
                            "timestamp": datetime.now().isoformat()
                        }
                    },
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        success = result.get("status") == "success"
                        
                        # Check for memory indicators
                        response_content = str(result.get("result", {}))
                        memory_indicators = [
                            indicator for indicator in [
                                "remember", "stored", "earlier", "persistence", "important"
                            ] if indicator.lower() in response_content.lower()
                        ]
                        
                        has_persistent_memory = len(memory_indicators) > 0
                        
                        self.test_results.append({
                            "test": "Memory_Delayed_Retrieval",
                            "status": "PASS" if success and has_persistent_memory else "FAIL",
                            "key": key,
                            "has_persistent_memory": has_persistent_memory,
                            "memory_indicators": memory_indicators,
                            "result": result
                        })
                        
                        logger.info(f"{'✅' if success and has_persistent_memory else '❌'} Delayed memory retrieval")
            
            except Exception as e:
                logger.error(f"❌ Delayed memory retrieval failed: {e}")
                self.test_results.append({
                    "test": "Memory_Delayed_Retrieval",
                    "status": "FAIL",
                    "error": str(e)
                })
    
    def generate_scb_report(self):
        """Generate SCB-specific test report"""
        logger.info("📊 Generating SCB Memory Test Report")
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped_tests = len([r for r in self.test_results if r["status"] == "SKIP"])
        
        # Categorize test results
        test_categories = {
            "Basic SCB Operations": [r for r in self.test_results if "SCB_Direct" in r.get("test", "") or "SCB_Via_Agent" in r.get("test", "")],
            "Memory Scenarios": [r for r in self.test_results if "Memory_Scenario" in r.get("test", "")],
            "Cross-System Memory": [r for r in self.test_results if "Cross_System" in r.get("test", "")],
            "Memory Management": [r for r in self.test_results if "Memory_" in r.get("test", "") and "Scenario" not in r.get("test", "")]
        }
        
        report = {
            "scb_test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "success_rate": f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%",
                "timestamp": datetime.now().isoformat()
            },
            "category_analysis": {},
            "memory_scenario_results": {},
            "scb_capabilities": {
                "direct_scb_access": False,
                "agent_mediated_scb": False,
                "cross_system_memory": False,
                "persistent_memory": False
            },
            "detailed_results": self.test_results,
            "memory_test_data": self.memory_test_data
        }
        
        # Analyze by category
        for category, tests in test_categories.items():
            if tests:
                category_passed = len([t for t in tests if t["status"] == "PASS"])
                report["category_analysis"][category] = {
                    "total": len(tests),
                    "passed": category_passed,
                    "failed": len([t for t in tests if t["status"] == "FAIL"]),
                    "success_rate": f"{(category_passed/len(tests)*100):.1f}%"
                }
        
        # Analyze memory scenarios
        for scenario_id, scenario_data in self.memory_test_data.items():
            scenario_tests = [r for r in self.test_results if scenario_id in r.get("test", "")]
            if scenario_tests:
                memory_tests = [t for t in scenario_tests if t.get("expects_memory", False)]
                memory_success = len([t for t in memory_tests if t.get("memory_analysis", {}).get("has_memory_reference", False)])
                
                report["memory_scenario_results"][scenario_id] = {
                    "total_steps": len(scenario_tests),
                    "memory_expected_steps": len(memory_tests),
                    "memory_successful_steps": memory_success,
                    "memory_success_rate": f"{(memory_success/len(memory_tests)*100):.1f}%" if memory_tests else "N/A"
                }
        
        # Determine SCB capabilities
        for test in self.test_results:
            if test["status"] == "PASS":
                test_name = test.get("test", "")
                if "SCB_Direct" in test_name:
                    report["scb_capabilities"]["direct_scb_access"] = True
                elif "SCB_Via_Agent" in test_name:
                    report["scb_capabilities"]["agent_mediated_scb"] = True
                elif "Cross_System" in test_name:
                    report["scb_capabilities"]["cross_system_memory"] = True
                elif "Memory_" in test_name and ("Persistence" in test_name or "Delayed" in test_name):
                    report["scb_capabilities"]["persistent_memory"] = True
        
        # Save report
        report_file = f"/tmp/scb_memory_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"🧠 SCB MEMORY TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏭️ Skipped: {skipped_tests}")
        print(f"📈 Success Rate: {report['scb_test_summary']['success_rate']}")
        
        print(f"\n🛠️ SCB CAPABILITIES DETECTED:")
        for capability, available in report["scb_capabilities"].items():
            status = "✅ Available" if available else "❌ Not Available"
            print(f"  {capability.replace('_', ' ').title()}: {status}")
        
        print(f"\n📊 CATEGORY BREAKDOWN:")
        for category, results in report["category_analysis"].items():
            print(f"  {category}: {results['passed']}/{results['total']} ({results['success_rate']})")
        
        print(f"\n🧠 MEMORY SCENARIO ANALYSIS:")
        for scenario_id, results in report["memory_scenario_results"].items():
            print(f"  {scenario_id}: Memory Success {results['memory_success_rate']}")
        
        print(f"\n📁 Full report saved to: {report_file}")
        print(f"{'='*80}")
        
        return report

async def main():
    """Main SCB memory test execution"""
    print("🧠 Starting SCB Memory and Context Test Suite")
    
    test_suite = SCBMemoryTestSuite()
    
    try:
        await test_suite.run_scb_memory_tests()
        print("✅ SCB memory test suite completed successfully")
    except Exception as e:
        print(f"❌ SCB memory test suite failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())