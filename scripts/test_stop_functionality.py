#!/usr/bin/env python3
"""
Test Stop Functionality for S2 System
=====================================

This script tests all the stop mechanisms we implemented:
1. Direct API stop command
2. Orchestrator CLI stop command
3. Natural language stop command processing

Created: 2025-07-14
"""

import asyncio
import json
import time
from datetime import datetime
import httpx
import argparse


class StopFunctionalityTester:
    """Test all stop mechanisms for S2 system"""
    
    def __init__(self, s2_url: str = "http://localhost:8200", orchestrator_url: str = "http://localhost:8082"):
        self.s2_url = s2_url
        self.orchestrator_url = orchestrator_url
        self.endpoints = {
            "s2_stop": f"{s2_url}/api/stimuli/stop",
            "s2_receive": f"{s2_url}/api/stimuli/receive",
            "s2_state": f"{s2_url}/api/stimuli/processing-state",
            "orchestrator_process": f"{orchestrator_url}/process"
        }
    
    async def send_complex_stimuli(self, stimuli_id: str) -> dict:
        """Send a complex stimuli to S2 that will take time to process"""
        payload = {
            "stimuli_id": stimuli_id,
            "content": """
            Please provide a comprehensive analysis of cryptocurrency market trends including:
            1. Technical analysis of Bitcoin, Ethereum, and top altcoins
            2. Market sentiment analysis and social media influence
            3. Regulatory impact assessment across major markets
            4. Risk management strategies for different portfolio sizes
            5. Short-term and long-term price predictions with reasoning
            6. Trading strategies for different market conditions
            7. DeFi protocol analysis and yield farming opportunities
            8. NFT market trends and investment opportunities
            Please be thorough and provide actionable insights with detailed explanations.
            """,
            "source": "test_script",
            "priority": "high"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.endpoints["s2_receive"], json=payload)
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def check_processing_state(self) -> dict:
        """Check current S2 processing state"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.endpoints["s2_state"])
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def test_direct_api_stop(self) -> dict:
        """Test direct API stop command"""
        print("🧪 Testing Direct API Stop Command")
        print("-" * 40)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.endpoints["s2_stop"])
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Direct API stop: {result.get('message', 'Success')}")
                    if result.get('was_processing'):
                        print(f"   Stopped: {result.get('stopped_stimuli_id')}")
                        print(f"   Duration: {result.get('processing_duration_seconds', 0):.1f}s")
                    else:
                        print("   No processing was active")
                    return {"success": True, "result": result}
                else:
                    print(f"❌ Direct API stop failed: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
        except Exception as e:
            print(f"❌ Direct API stop error: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_orchestrator_cli_stop(self) -> dict:
        """Test orchestrator CLI stop command"""
        print("🧪 Testing Orchestrator CLI Stop Command")
        print("-" * 40)
        
        # Test the stop command via orchestrator
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # First try the natural language stop
                payload = {
                    "stimulus_id": f"stop_test_{int(time.time())}",
                    "text": "stop system 2 talk",
                    "context": {"source": "cli"}
                }
                
                response = await client.post(self.endpoints["orchestrator_process"], json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    routing = result.get("routing_decision", {})
                    execution = result.get("execution_results", {})
                    
                    print(f"✅ Orchestrator processed stop command")
                    print(f"   Routed to: {routing.get('system', 'unknown')}")
                    print(f"   Reasoning: {routing.get('reasoning', 'N/A')}")
                    
                    if "stop" in execution:
                        stop_result = execution["stop"]
                        print(f"   Stop result: {stop_result.get('message', 'Success')}")
                        return {"success": True, "result": result}
                    else:
                        print("   ⚠️ Command not routed to stop system")
                        return {"success": False, "message": "Not routed to stop system"}
                else:
                    print(f"❌ Orchestrator stop failed: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
        except Exception as e:
            print(f"❌ Orchestrator stop error: {e}")
            return {"success": False, "error": str(e)}
    
    async def wait_for_processing_to_start(self, timeout: float = 30.0) -> bool:
        """Wait for processing to start"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            state = await self.check_processing_state()
            if state.get("is_processing", False):
                return True
            await asyncio.sleep(1.0)
        return False
    
    async def run_comprehensive_test(self):
        """Run comprehensive test of all stop mechanisms"""
        print("🧪 COMPREHENSIVE STOP FUNCTIONALITY TEST")
        print("=" * 60)
        
        # Test 1: Direct API stop when not processing
        print("\n1️⃣ Test Direct API Stop (No Processing)")
        result1 = await self.test_direct_api_stop()
        
        # Test 2: Start processing and test direct API stop
        print("\n2️⃣ Test Direct API Stop (During Processing)")
        
        # Send complex stimuli
        print("   Sending complex stimuli...")
        stimuli_result = await self.send_complex_stimuli("comprehensive_test_stimuli")
        
        if stimuli_result.get("success"):
            print("   ✅ Complex stimuli sent successfully")
            
            # Wait for processing to start
            print("   Waiting for processing to start...")
            if await self.wait_for_processing_to_start():
                print("   ✅ Processing started")
                
                # Test direct stop
                await asyncio.sleep(2.0)  # Let it process for 2 seconds
                result2 = await self.test_direct_api_stop()
                
                # Check state after stop
                await asyncio.sleep(1.0)
                state = await self.check_processing_state()
                if not state.get("is_processing", False):
                    print("   ✅ Processing successfully stopped")
                else:
                    print("   ⚠️ Processing still active after stop")
            else:
                print("   ❌ Processing did not start")
                result2 = {"success": False, "message": "Processing did not start"}
        else:
            print("   ❌ Failed to send complex stimuli")
            result2 = {"success": False, "message": "Failed to start processing"}
        
        # Test 3: Orchestrator CLI stop command
        print("\n3️⃣ Test Orchestrator CLI Stop Command")
        result3 = await self.test_orchestrator_cli_stop()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        tests = [
            ("Direct API Stop (No Processing)", result1),
            ("Direct API Stop (During Processing)", result2),
            ("Orchestrator CLI Stop", result3)
        ]
        
        passed = 0
        for test_name, result in tests:
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            print(f"{status}: {test_name}")
            if result.get("success"):
                passed += 1
        
        print(f"\n🎯 Results: {passed}/{len(tests)} tests passed")
        
        if passed == len(tests):
            print("🎉 All stop mechanisms working correctly!")
        else:
            print("⚠️ Some stop mechanisms need attention")
        
        return passed == len(tests)
    
    async def test_simple_stop(self):
        """Simple test of stop functionality"""
        print("⚡ SIMPLE STOP TEST")
        print("=" * 30)
        
        # Check current state
        state = await self.check_processing_state()
        print(f"Current processing: {state.get('is_processing', False)}")
        
        if state.get("is_processing"):
            print(f"Currently processing: {state.get('current_stimuli_id')}")
        
        # Test stop
        result = await self.test_direct_api_stop()
        
        return result.get("success", False)


async def main():
    parser = argparse.ArgumentParser(description="Test stop functionality for S2 system")
    parser.add_argument("--s2-url", default="http://localhost:8200", 
                       help="S2 system URL (default: http://localhost:8200)")
    parser.add_argument("--orchestrator-url", default="http://localhost:8082",
                       help="Orchestrator URL (default: http://localhost:8082)")
    parser.add_argument("--simple", action="store_true",
                       help="Run simple test instead of comprehensive test")
    
    args = parser.parse_args()
    
    tester = StopFunctionalityTester(args.s2_url, args.orchestrator_url)
    
    if args.simple:
        success = await tester.test_simple_stop()
    else:
        success = await tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 Test completed successfully!")
        return 0
    else:
        print("\n💥 Test failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)