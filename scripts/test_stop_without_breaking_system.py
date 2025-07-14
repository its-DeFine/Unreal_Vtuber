#!/usr/bin/env python3
"""
Test Stop Functionality Without Breaking System
==============================================

This test specifically verifies that:
1. Stop commands work properly
2. After stopping, the system can process new requests
3. Both S1 and S2 remain functional after stop

Created: 2025-07-14
"""

import asyncio
import time
import httpx
from datetime import datetime


async def test_stop_without_breaking():
    """Test that stop functionality doesn't break subsequent processing"""
    print("🧪 TESTING STOP FUNCTIONALITY WITHOUT BREAKING SYSTEM")
    print("=" * 60)
    
    orchestrator_url = "http://localhost:8082"
    s2_url = "http://localhost:8200"
    
    # Test results
    results = {
        "s2_before_stop": False,
        "s1_before_stop": False,
        "stop_command": False,
        "s2_after_stop": False,
        "s1_after_stop": False,
        "multiple_stops": False
    }
    
    try:
        print("\n1️⃣ Testing S2 Request Before Stop")
        print("-" * 40)
        
        # Send S2 request
        s2_request = {
            "stimulus_id": f"test_s2_before_{int(time.time())}",
            "text": "Provide comprehensive analysis of cryptocurrency trading strategies",
            "context": {"test": "before_stop"}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{orchestrator_url}/process", json=s2_request)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✅ S2 request successful before stop")
                    results["s2_before_stop"] = True
                    
                    # Wait for processing to start
                    await asyncio.sleep(2.0)
                    
                    # Stop the processing
                    print("\n2️⃣ Sending Stop Command")
                    print("-" * 30)
                    
                    stop_response = await client.post(f"{s2_url}/api/stimuli/stop")
                    if stop_response.status_code == 200:
                        stop_result = stop_response.json()
                        if stop_result.get("success"):
                            print(f"✅ Stop successful: {stop_result.get('message')}")
                            results["stop_command"] = True
                        else:
                            print(f"❌ Stop failed: {stop_result}")
                    else:
                        print(f"❌ Stop request failed: {stop_response.status_code}")
                else:
                    print(f"❌ S2 request failed: {result}")
            else:
                print(f"❌ S2 request returned: {response.status_code}")
        
        # Wait a moment after stop
        await asyncio.sleep(2.0)
        
        print("\n3️⃣ Testing S1 Request After Stop")
        print("-" * 40)
        
        # Test S1 request after stop
        s1_request = {
            "stimulus_id": f"test_s1_after_{int(time.time())}",
            "text": "What is the current bitcoin price?",
            "context": {"test": "after_stop"}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{orchestrator_url}/process", json=s1_request)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    routing = result.get("routing_decision", {})
                    execution = result.get("execution_results", {})
                    
                    print(f"✅ S1 request successful after stop")
                    print(f"   Routed to: {routing.get('system')}")
                    
                    # Check if S1 actually processed it
                    if "s1" in execution:
                        s1_result = execution["s1"]
                        if s1_result.get("success") != False:
                            print("   ✅ S1 processed successfully")
                            results["s1_after_stop"] = True
                        else:
                            print(f"   ❌ S1 processing failed: {s1_result.get('error')}")
                else:
                    print(f"❌ S1 request failed: {result}")
            else:
                print(f"❌ S1 request returned: {response.status_code}")
        
        # Wait a moment
        await asyncio.sleep(2.0)
        
        print("\n4️⃣ Testing S2 Request After Stop")
        print("-" * 40)
        
        # Test S2 request after stop
        s2_request_after = {
            "stimulus_id": f"test_s2_after_{int(time.time())}",
            "text": "Create a detailed educational guide on blockchain technology",
            "context": {"test": "after_stop"}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{orchestrator_url}/process", json=s2_request_after)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    routing = result.get("routing_decision", {})
                    execution = result.get("execution_results", {})
                    
                    print(f"✅ S2 request successful after stop")
                    print(f"   Routed to: {routing.get('system')}")
                    
                    # Check if S2 accepted it
                    if "s2" in execution:
                        s2_result = execution["s2"]
                        if s2_result.get("success"):
                            print("   ✅ S2 accepted and processing")
                            results["s2_after_stop"] = True
                        else:
                            print(f"   ❌ S2 rejected: {s2_result.get('agent_decision')}")
                else:
                    print(f"❌ S2 request failed: {result}")
            else:
                print(f"❌ S2 request returned: {response.status_code}")
        
        # Test multiple stops don't break the system
        print("\n5️⃣ Testing Multiple Stop Commands")
        print("-" * 40)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Send multiple stops
            for i in range(3):
                stop_response = await client.post(f"{s2_url}/api/stimuli/stop")
                if stop_response.status_code == 200:
                    print(f"   Stop {i+1}: {stop_response.json().get('message')}")
                await asyncio.sleep(0.5)
            
            # Test S1 still works after multiple stops
            response = await client.post(f"{orchestrator_url}/process", json={
                "stimulus_id": f"test_after_multiple_{int(time.time())}",
                "text": "Hello, how are you?",
                "context": {"test": "after_multiple_stops"}
            })
            
            if response.status_code == 200 and response.json().get("success"):
                print("✅ System still functional after multiple stops")
                results["multiple_stops"] = True
            else:
                print("❌ System broken after multiple stops")
        
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    # Final Results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 SUCCESS: Stop functionality works without breaking the system!")
        return True
    else:
        print("\n⚠️ FAILURE: Some tests failed - stop functionality may break the system")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_stop_without_breaking())
    exit(0 if success else 1)