#!/usr/bin/env python3
"""
🧠 Standalone Cognee Testing Script

This script tests Cognee functionality in isolation to debug issues
without the complexity of the full autonomous agent system.
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CogneeStandaloneTest:
    """Standalone test class for Cognee functionality"""
    
    def __init__(self, cognee_url: str = "http://localhost:8000"):
        self.cognee_url = cognee_url
        self.session = None
        self.jwt_token = None
        self.username = "default_user@example.com"
        self.password = "default_password"
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def authenticate(self) -> bool:
        """Authenticate with Cognee and get JWT token"""
        try:
            logger.info("🔐 [COGNEE_TEST] Authenticating with Cognee...")
            
            login_data = {
                "username": self.username,
                "password": self.password
            }
            
            async with self.session.post(
                f"{self.cognee_url}/api/v1/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.jwt_token = result["access_token"]
                    logger.info("✅ [COGNEE_TEST] Authentication successful")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ [COGNEE_TEST] Authentication failed with status {response.status}: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ [COGNEE_TEST] Authentication error: {e}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API calls"""
        if not self.jwt_token:
            return {}
        return {"Authorization": f"Bearer {self.jwt_token}"}
    
    async def test_health_check(self) -> bool:
        """Test if Cognee service is healthy"""
        try:
            logger.info("🔍 [COGNEE_TEST] Testing health check...")
            async with self.session.get(f"{self.cognee_url}/health", timeout=10) as response:
                if response.status == 200:
                    # Health endpoint may return empty response
                    try:
                        result = await response.json()
                        logger.info(f"✅ [COGNEE_TEST] Health check passed with JSON: {result}")
                    except:
                        # Empty response is also healthy
                        logger.info("✅ [COGNEE_TEST] Health check passed (empty response)")
                    return True
                else:
                    logger.error(f"❌ [COGNEE_TEST] Health check failed with status {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ [COGNEE_TEST] Health check error: {e}")
            return False
    
    async def test_add_data(self, text: str, dataset_name: str = "test_dataset") -> bool:
        """Test adding data to Cognee"""
        try:
            logger.info(f"📝 [COGNEE_TEST] Adding data to dataset '{dataset_name}': {text[:50]}...")
            
            # Create multipart form data
            data = aiohttp.FormData()
            data.add_field('data', text, filename='test_data.txt', content_type='text/plain')
            data.add_field('datasetName', dataset_name)
            
            async with self.session.post(
                f"{self.cognee_url}/api/v1/add/",
                data=data,
                headers=self.get_auth_headers(),
                timeout=30
            ) as response:
                if response.status == 200:
                    result_text = await response.text()
                    logger.info(f"✅ [COGNEE_TEST] Data added successfully: {result_text}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ [COGNEE_TEST] Add data failed with status {response.status}: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ [COGNEE_TEST] Add data error: {e}")
            return False
    
    async def test_cognify(self, dataset_name: str = "test_dataset") -> bool:
        """Test the cognify process"""
        try:
            logger.info(f"🧠 [COGNEE_TEST] Running cognify on dataset '{dataset_name}'...")
            
            # Create JSON payload for cognify
            payload = {
                "datasets": [dataset_name]
            }
            
            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json"
            
            async with self.session.post(
                f"{self.cognee_url}/api/v1/cognify/",
                json=payload,
                headers=headers,
                timeout=60  # Cognify can take longer
            ) as response:
                if response.status == 200:
                    try:
                        result = await response.json()
                        logger.info(f"✅ [COGNEE_TEST] Cognify completed successfully: {result}")
                    except:
                        result_text = await response.text()
                        logger.info(f"✅ [COGNEE_TEST] Cognify completed successfully: {result_text}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ [COGNEE_TEST] Cognify failed with status {response.status}: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ [COGNEE_TEST] Cognify error: {e}")
            return False
    
    async def test_search(self, query: str, dataset_name: str = "test_dataset") -> bool:
        """Test searching in Cognee"""
        try:
            logger.info(f"🔍 [COGNEE_TEST] Searching for '{query}' in dataset '{dataset_name}'...")
            
            # Create JSON payload for search
            payload = {
                "searchType": "CHUNKS",  # Use CHUNKS for semantic search
                "query": query,
                "topK": 5
            }
            
            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json"
            
            async with self.session.post(
                f"{self.cognee_url}/api/v1/search/",
                json=payload,
                headers=headers,
                timeout=30
            ) as response:
                if response.status == 200:
                    try:
                        result = await response.json()
                        logger.info(f"✅ [COGNEE_TEST] Search completed: {len(result)} results found")
                        if result:
                            logger.info(f"📋 [COGNEE_TEST] Sample result: {result[0]}")
                    except:
                        result_text = await response.text()
                        logger.info(f"✅ [COGNEE_TEST] Search completed: {result_text}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ [COGNEE_TEST] Search failed with status {response.status}: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ [COGNEE_TEST] Search error: {e}")
            return False
    
    async def test_list_datasets(self) -> bool:
        """Test listing available datasets"""
        try:
            logger.info("📂 [COGNEE_TEST] Listing datasets...")
            
            async with self.session.get(
                f"{self.cognee_url}/api/v1/datasets/",
                headers=self.get_auth_headers(),
                timeout=10
            ) as response:
                if response.status == 200:
                    try:
                        result = await response.json()
                        logger.info(f"✅ [COGNEE_TEST] Datasets listed: {result}")
                    except:
                        result_text = await response.text()
                        logger.info(f"✅ [COGNEE_TEST] Datasets listed: {result_text}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ [COGNEE_TEST] List datasets failed with status {response.status}: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ [COGNEE_TEST] List datasets error: {e}")
            return False
    
    async def run_full_test_suite(self) -> Dict[str, bool]:
        """Run the complete test suite"""
        test_results = {}
        
        logger.info("🚀 [COGNEE_TEST] Starting full Cognee test suite...")
        
        # Test 1: Health Check
        test_results['health_check'] = await self.test_health_check()
        if not test_results['health_check']:
            logger.error("❌ [COGNEE_TEST] Health check failed - stopping tests")
            return test_results
        
        # Test 2: Authentication
        test_results['authentication'] = await self.authenticate()
        if not test_results['authentication']:
            logger.error("❌ [COGNEE_TEST] Authentication failed - stopping tests")
            return test_results
        
        # Wait a bit for service to be fully ready
        await asyncio.sleep(2)
        
        # Test 3: List datasets
        test_results['list_datasets'] = await self.test_list_datasets()
        
        # Test 4: Add data
        test_data = """
        This is a test document for Cognee functionality.
        It contains information about autonomous agents and their capabilities.
        The agent can make decisions, learn from experience, and evolve over time.
        Performance metrics include decision time, success rate, and memory usage.
        """
        test_results['add_data'] = await self.test_add_data(test_data.strip())
        
        if test_results['add_data']:
            # Test 5: Cognify
            test_results['cognify'] = await self.test_cognify()
            
            if test_results['cognify']:
                # Test 6: Search
                test_results['search'] = await self.test_search("autonomous agents")
            else:
                test_results['search'] = False
        else:
            test_results['cognify'] = False
            test_results['search'] = False
        
        # Summary
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        
        logger.info(f"📊 [COGNEE_TEST] Test suite completed: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 [COGNEE_TEST] All tests passed! Cognee is working correctly.")
        else:
            logger.warning("⚠️ [COGNEE_TEST] Some tests failed. Check logs for details.")
        
        return test_results

async def main():
    """Main test function"""
    print("🧠 Starting Cognee Standalone Testing...")
    
    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    await asyncio.sleep(5)
    
    async with CogneeStandaloneTest() as tester:
        results = await tester.run_full_test_suite()
        
        print("\n" + "="*50)
        print("📋 TEST RESULTS SUMMARY")
        print("="*50)
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name:20} | {status}")
        
        print("="*50)
        
        if all(results.values()):
            print("🎉 All tests passed! Cognee is working correctly.")
            return 0
        else:
            print("⚠️ Some tests failed. Check the logs above for details.")
            return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        exit(1) 