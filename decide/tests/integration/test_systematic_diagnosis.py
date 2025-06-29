#!/usr/bin/env python3
"""
Systematic Cognee + Ollama Diagnosis
Testing step by step to identify exact failure points
"""

import asyncio
import aiohttp
import json
import time
import sys
import os
sys.path.append('/app')

class SystematicDiagnosis:
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
    
    def log(self, message):
        timestamp = time.time() - self.start_time
        print(f"[{timestamp:6.1f}s] {message}")
    
    async def test_1_ollama_basic_health(self):
        """Test 1: Basic Ollama Health Check"""
        self.log("🔍 TEST 1: Ollama Basic Health")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://ollama:11434/api/tags', 
                                     timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m['name'] for m in data.get('models', [])]
                        self.log(f"✅ Ollama responding. Models: {models}")
                        self.test_results['ollama_health'] = True
                        return True
                    else:
                        self.log(f"❌ Ollama returned {response.status}")
                        self.test_results['ollama_health'] = False
                        return False
        except Exception as e:
            self.log(f"❌ Ollama health failed: {e}")
            self.test_results['ollama_health'] = False
            return False
    
    async def test_2_simple_llm_request(self):
        """Test 2: Simple LLM Request with Timing"""
        self.log("🧪 TEST 2: Simple LLM Request")
        
        try:
            payload = {
                "model": "llama3-schema",
                "prompt": "Say 'OK' and nothing else",
                "stream": False
            }
            
            request_start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'http://ollama:11434/api/generate',
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    request_time = time.time() - request_start
                    
                    if response.status == 200:
                        data = await response.json()
                        response_text = data.get('response', '').strip()
                        self.log(f"✅ LLM responded in {request_time:.1f}s: '{response_text}'")
                        self.test_results['llm_request'] = True
                        self.test_results['llm_response_time'] = request_time
                        return True
                    else:
                        self.log(f"❌ LLM request failed: {response.status}")
                        self.test_results['llm_request'] = False
                        return False
        except asyncio.TimeoutError:
            self.log("⏰ LLM request timed out after 30s")
            self.test_results['llm_request'] = False
            self.test_results['llm_timeout'] = True
            return False
        except Exception as e:
            self.log(f"❌ LLM request error: {e}")
            self.test_results['llm_request'] = False
            return False
    
    async def test_3_cognee_initialization(self):
        """Test 3: Cognee Service Initialization"""
        self.log("🧠 TEST 3: Cognee Initialization")
        
        try:
            from autogen_agent.services.cognee_direct_service import CogneeDirectService
            
            init_start = time.time()
            service = CogneeDirectService()
            await service.initialize()
            init_time = time.time() - init_start
            
            self.log(f"✅ Cognee initialized in {init_time:.1f}s")
            self.test_results['cognee_init'] = True
            self.test_results['cognee_init_time'] = init_time
            return service
        except Exception as e:
            self.log(f"❌ Cognee initialization failed: {e}")
            self.test_results['cognee_init'] = False
            return None
    
    async def test_4_cognee_add_memory(self, service):
        """Test 4: Cognee Add Memory (without cognify)"""
        self.log("📝 TEST 4: Cognee Add Memory")
        
        if not service:
            self.log("❌ Skipped - no service")
            return False
        
        try:
            add_start = time.time()
            result = await service.add_memory("Test memory for diagnosis")
            add_time = time.time() - add_start
            
            self.log(f"✅ Memory added in {add_time:.1f}s: {result}")
            self.test_results['cognee_add'] = True
            self.test_results['cognee_add_time'] = add_time
            return True
        except Exception as e:
            self.log(f"❌ Add memory failed: {e}")
            self.test_results['cognee_add'] = False
            return False
    
    async def test_5_cognee_cognify_with_timeout(self, service):
        """Test 5: Cognee Cognify (the problematic operation)"""
        self.log("🔗 TEST 5: Cognee Cognify (with 60s timeout)")
        
        if not service:
            self.log("❌ Skipped - no service")
            return False
        
        try:
            cognify_start = time.time()
            result = await asyncio.wait_for(
                service.cognify(),
                timeout=60
            )
            cognify_time = time.time() - cognify_start
            
            self.log(f"✅ Cognify completed in {cognify_time:.1f}s: {result}")
            self.test_results['cognee_cognify'] = True
            self.test_results['cognee_cognify_time'] = cognify_time
            return True
        except asyncio.TimeoutError:
            cognify_time = time.time() - cognify_start
            self.log(f"⏰ Cognify timed out after {cognify_time:.1f}s")
            self.test_results['cognee_cognify'] = False
            self.test_results['cognee_cognify_timeout'] = True
            return False
        except Exception as e:
            cognify_time = time.time() - cognify_start
            self.log(f"❌ Cognify failed after {cognify_time:.1f}s: {e}")
            self.test_results['cognee_cognify'] = False
            return False
    
    async def test_6_cognee_search(self, service):
        """Test 6: Cognee Search"""
        self.log("🔍 TEST 6: Cognee Search")
        
        if not service:
            self.log("❌ Skipped - no service")
            return False
        
        try:
            search_start = time.time()
            results = await service.search("test")
            search_time = time.time() - search_start
            
            self.log(f"✅ Search completed in {search_time:.1f}s: {len(results)} results")
            self.test_results['cognee_search'] = True
            self.test_results['cognee_search_time'] = search_time
            return True
        except Exception as e:
            self.log(f"❌ Search failed: {e}")
            self.test_results['cognee_search'] = False
            return False
    
    async def run_full_diagnosis(self):
        """Run complete systematic diagnosis"""
        self.log("🚀 STARTING SYSTEMATIC DIAGNOSIS")
        self.log("="*50)
        
        # Test 1: Ollama Health
        ollama_ok = await self.test_1_ollama_basic_health()
        
        # Test 2: LLM Request
        llm_ok = await self.test_2_simple_llm_request() if ollama_ok else False
        
        # Test 3: Cognee Init
        service = await self.test_3_cognee_initialization()
        
        # Test 4: Memory Add
        add_ok = await self.test_4_cognee_add_memory(service)
        
        # Test 5: Cognify (the problem)
        cognify_ok = await self.test_5_cognee_cognify_with_timeout(service)
        
        # Test 6: Search
        search_ok = await self.test_6_cognee_search(service)
        
        self.log("="*50)
        self.log("📊 DIAGNOSIS RESULTS SUMMARY")
        self.log("="*50)
        
        for test, result in self.test_results.items():
            status = "✅ PASS" if result is True else "❌ FAIL" if result is False else f"📊 {result}"
            self.log(f"{test:25} | {status}")
        
        self.log("="*50)
        
        # Analysis
        self.log("🔍 ANALYSIS:")
        if not ollama_ok:
            self.log("❌ CRITICAL: Ollama not responding - system unusable")
        elif not llm_ok:
            self.log("❌ CRITICAL: LLM requests failing - cognify will fail")
        elif not cognify_ok:
            self.log("⚠️ ISSUE: Cognify failing but basic memory operations work")
            if 'llm_response_time' in self.test_results and self.test_results['llm_response_time'] > 10:
                self.log(f"🐌 ROOT CAUSE: LLM too slow ({self.test_results['llm_response_time']:.1f}s)")
        else:
            self.log("✅ ALL SYSTEMS WORKING")
        
        return self.test_results

async def main():
    diagnosis = SystematicDiagnosis()
    results = await diagnosis.run_full_diagnosis()
    
    # Final recommendation
    print("\n" + "="*50)
    print("💡 RECOMMENDATIONS:")
    print("="*50)
    
    if results.get('cognee_add') and not results.get('cognee_cognify'):
        print("✅ USE: Memory add/search operations (working)")
        print("❌ AVOID: cognify() operation (failing/slow)")
        print("🔧 FIX: Optimize Ollama or use smaller models for cognify")
    
    if results.get('llm_response_time', 0) > 10:
        print("🚨 URGENT: LLM responses too slow - restart Ollama")
    
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main()) 