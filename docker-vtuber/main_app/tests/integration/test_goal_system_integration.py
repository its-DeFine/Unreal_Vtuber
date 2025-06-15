#!/usr/bin/env python3
"""
🎯 Test Goal Management System Integration

Test the complete goal management system integration with the running AutoGen container.
"""

import asyncio
import json
import requests
import time

async def test_goal_system_endpoints():
    """Test the goal management system via the running container"""
    
    print("🎯 TESTING GOAL MANAGEMENT SYSTEM INTEGRATION")
    print("=" * 60)
    
    base_url = "http://localhost:8200"  # AutoGen standalone container port
    
    # Test 1: Check health endpoint
    print("\n1. 🏥 Testing Health Endpoint...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   Response: {json.dumps(health_data, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
    
    # Test 2: Check if goal management endpoints exist
    print("\n2. 🎯 Testing Goal Management Endpoints...")
    goal_endpoints = [
        "/api/goals",
        "/api/goals/define", 
        "/api/goals/status",
        "/api/metrics/performance"
    ]
    
    for endpoint in goal_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            print(f"   {endpoint}: Status {response.status_code}")
            if response.status_code == 200:
                print(f"      ✅ Available")
            elif response.status_code == 404:
                print(f"      ⚠️ Not found - endpoint may not be implemented yet")
            else:
                print(f"      ❌ Error: {response.text[:100]}...")
        except Exception as e:
            print(f"   {endpoint}: ❌ Connection error: {e}")
    
    # Test 3: Check container logs for goal system initialization
    print("\n3. 📋 Checking Container Logs for Goal System...")
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "logs", "autogen_cognitive_standalone", "--tail=50"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        logs = result.stdout
        goal_related_logs = []
        
        for line in logs.split('\n'):
            if any(keyword in line.lower() for keyword in ['goal', 'metrics', 'tool_registry']):
                goal_related_logs.append(line.strip())
        
        if goal_related_logs:
            print("   📋 Goal-related log entries:")
            for log in goal_related_logs[-10:]:  # Last 10 entries
                print(f"      {log}")
        else:
            print("   ⚠️ No goal-related log entries found")
            
    except Exception as e:
        print(f"   ❌ Log check failed: {e}")
    
    # Test 4: Test basic API functionality
    print("\n4. 🚀 Testing Basic API Functionality...")
    test_endpoints = [
        ("/", "GET", "Root endpoint"),
        ("/docs", "GET", "API documentation"),
        ("/api/status", "GET", "System status")
    ]
    
    for endpoint, method, description in test_endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
            else:
                response = requests.post(f"{base_url}{endpoint}", timeout=5)
                
            print(f"   {description} ({endpoint}): Status {response.status_code}")
            
            if response.status_code == 200:
                print(f"      ✅ Working")
            elif response.status_code == 404:
                print(f"      ⚠️ Not found")
            else:
                print(f"      ❌ Error: {response.text[:50]}...")
                
        except Exception as e:
            print(f"   {description}: ❌ Error: {e}")
    
    # Test 5: Check for Cognee integration
    print("\n5. 🧠 Testing Cognee Integration...")
    try:
        # Check if Cognee container is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=cognee_standalone", "--format", "table {{.Names}}\\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "cognee_standalone" in result.stdout:
            print("   ✅ Cognee container is running")
            
            # Test Cognee endpoint
            try:
                cognee_response = requests.get("http://localhost:8000/health", timeout=3)
                print(f"   Cognee health: Status {cognee_response.status_code}")
            except Exception as e:
                print(f"   ⚠️ Cognee endpoint error: {e}")
        else:
            print("   ⚠️ Cognee container not found")
            
    except Exception as e:
        print(f"   ❌ Cognee check failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 GOAL SYSTEM INTEGRATION TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_goal_system_endpoints()) 