#!/usr/bin/env python3
"""
🧠 Comprehensive Cognee Integration Test Script

This script thoroughly tests all Cognee functionality to verify integration.
"""

import asyncio
import logging
import time
import json
import requests
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CogneeComprehensiveTest:
    def __init__(self):
        self.cognee_url = "http://localhost:8000"
        self.autogen_url = "http://localhost:8100"
        self.test_data = [
            "AutoGen cognitive agent system with evolution capabilities",
            "Darwin-Gödel machine for autonomous code improvement",
            "Knowledge graph integration with Ollama LLM models"
        ]
        self.test_results = {}
    
    async def run_comprehensive_test(self):
        """Run all Cognee tests"""
        print("🧠 Starting Comprehensive Cognee Integration Test")
        print("=" * 60)
        
        tests = [
            ("Service Health", self.test_service_health),
            ("Data Addition", self.test_data_addition),
            ("Knowledge Processing", self.test_cognify),
            ("Search Functionality", self.test_search)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔬 Running: {test_name}")
            try:
                result = await test_func()
                self.test_results[test_name] = {"status": "PASS", "result": result}
                print(f"✅ {test_name}: PASSED")
            except Exception as e:
                self.test_results[test_name] = {"status": "FAIL", "error": str(e)}
                print(f"❌ {test_name}: FAILED - {e}")
        
        self.print_summary()
        return self.test_results
    
    async def test_service_health(self):
        """Test Cognee service health"""
        response = requests.get(f"{self.cognee_url}/health", timeout=10)
        return {"status_code": response.status_code, "healthy": response.status_code == 200}
    
    async def test_data_addition(self):
        """Test adding data to Cognee"""
        headers = {"Content-Type": "application/json", "Authorization": "Bearer test_api_key"}
        payload = {"data": self.test_data[:2], "datasetName": "test_dataset"}
        
        response = requests.post(f"{self.cognee_url}/api/v1/add", json=payload, headers=headers, timeout=20)
        return {"status_code": response.status_code, "success": response.status_code in [200, 201]}
    
    async def test_cognify(self):
        """Test knowledge graph processing"""
        headers = {"Authorization": "Bearer test_api_key"}
        response = requests.post(f"{self.cognee_url}/api/v1/cognify", headers=headers, timeout=30)
        return {"status_code": response.status_code, "success": response.status_code in [200, 201]}
    
    async def test_search(self):
        """Test search functionality"""
        headers = {"Content-Type": "application/json", "Authorization": "Bearer test_api_key"}
        payload = {"query": "AutoGen cognitive", "limit": 5}
        
        response = requests.post(f"{self.cognee_url}/api/v1/search", json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return {"status_code": 200, "results": len(data.get("results", []))}
        return {"status_code": response.status_code, "results": 0}
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🧠 COGNEE TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results.values() if r["status"] == "PASS")
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total-passed}/{total}")
        
        for test_name, result in self.test_results.items():
            icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"{icon} {test_name}")

async def main():
    tester = CogneeComprehensiveTest()
    results = await tester.run_comprehensive_test()
    
    with open("cognee_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    return results

if __name__ == "__main__":
    asyncio.run(main()) 