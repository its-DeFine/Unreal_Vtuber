#!/usr/bin/env python3
"""
Test Stimuli Rejection Mechanism
================================

This script tests the new stimuli rejection mechanism by:
1. Sending a long-running stimuli to make system busy
2. Attempting to send additional stimuli while processing
3. Verifying that new stimuli are rejected appropriately

Created: 2025-07-14
"""

import asyncio
import json
import time
from datetime import datetime
import httpx
import argparse


class StimuliRejectionTest:
    """Test the stimuli rejection mechanism"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.endpoints = {
            "receive_stimuli": f"{base_url}/api/stimuli/receive",
            "processing_state": f"{base_url}/api/stimuli/processing-state",
            "orchestrator_status": f"{base_url}/api/stimuli/status"
        }
    
    async def send_stimuli(self, content: str, stimuli_id: str = None) -> dict:
        """Send a stimuli to the system"""
        if stimuli_id is None:
            stimuli_id = f"test_{int(time.time() * 1000)}"
        
        payload = {
            "stimuli_id": stimuli_id,
            "content": content,
            "source": "test_script",
            "priority": "medium",
            "metadata": {
                "test": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.endpoints["receive_stimuli"], json=payload)
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text,
                    "stimuli_id": stimuli_id
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stimuli_id": stimuli_id
            }
    
    async def check_processing_state(self) -> dict:
        """Check if system is currently processing"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.endpoints["processing_state"])
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def wait_for_processing_to_start(self, timeout: float = 30.0) -> bool:
        """Wait for system to start processing"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            state = await self.check_processing_state()
            if state.get("is_processing", False):
                return True
            await asyncio.sleep(1.0)
        
        return False
    
    async def wait_for_processing_to_finish(self, timeout: float = 600.0) -> bool:
        """Wait for system to finish processing"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            state = await self.check_processing_state()
            if not state.get("is_processing", False):
                return True
            await asyncio.sleep(2.0)
        
        return False
    
    async def run_rejection_test(self):
        """Run the main rejection test"""
        print("🧪 Starting Stimuli Rejection Test")
        print("=" * 50)
        
        # Step 1: Check initial state
        print("1️⃣ Checking initial processing state...")
        initial_state = await self.check_processing_state()
        
        if initial_state.get("error"):
            print(f"❌ Failed to check initial state: {initial_state['error']}")
            return False
        
        if initial_state.get("is_processing", False):
            print(f"⚠️ System is already processing: {initial_state.get('current_stimuli_id')}")
            print("   Waiting for current processing to finish...")
            if not await self.wait_for_processing_to_finish():
                print("❌ Timeout waiting for processing to finish")
                return False
        
        print("✅ System is idle and ready")
        
        # Step 2: Send a long-running stimuli
        print("\n2️⃣ Sending long-running stimuli...")
        long_stimuli_content = """
        Please analyze the following complex trading scenario and provide comprehensive insights:
        
        Scenario: A cryptocurrency trader is considering a multi-asset portfolio strategy 
        involving Bitcoin, Ethereum, and several altcoins. The trader wants to understand 
        market correlations, risk management strategies, optimal position sizing, and 
        technical analysis indicators. Please provide detailed analysis including:
        
        1. Market correlation analysis between major cryptocurrencies
        2. Risk management strategies for volatile assets
        3. Position sizing recommendations
        4. Technical indicators to monitor
        5. Entry and exit strategies
        6. Portfolio diversification recommendations
        
        Please be thorough in your analysis and provide actionable insights.
        """
        
        long_stimuli_result = await self.send_stimuli(long_stimuli_content, "long_running_test")
        
        if not long_stimuli_result.get("success"):
            print(f"❌ Failed to send long-running stimuli: {long_stimuli_result}")
            return False
        
        print(f"✅ Long-running stimuli sent: {long_stimuli_result['stimuli_id']}")
        
        # Step 3: Wait for processing to start
        print("\n3️⃣ Waiting for processing to start...")
        if not await self.wait_for_processing_to_start():
            print("❌ Timeout waiting for processing to start")
            return False
        
        processing_state = await self.check_processing_state()
        print(f"✅ Processing started: {processing_state.get('current_stimuli_id')}")
        
        # Step 4: Send additional stimuli while processing (these should be rejected)
        print("\n4️⃣ Testing rejection mechanism...")
        
        test_stimuli = [
            "What is the weather today?",
            "Tell me a joke",
            "Explain machine learning",
            "What are the best stocks to buy?"
        ]
        
        rejection_results = []
        for i, content in enumerate(test_stimuli, 1):
            print(f"   Sending test stimuli {i}/{len(test_stimuli)}: {content[:30]}...")
            result = await self.send_stimuli(content, f"rejection_test_{i}")
            rejection_results.append(result)
            
            if result.get("success"):
                print(f"   ❌ Stimuli {i} was ACCEPTED (should be rejected)")
            else:
                response = result.get("response", {})
                if isinstance(response, dict) and "rejected_busy" in str(response):
                    print(f"   ✅ Stimuli {i} was REJECTED (correct behavior)")
                else:
                    print(f"   ⚠️ Stimuli {i} failed unexpectedly: {result}")
            
            await asyncio.sleep(1.0)  # Small delay between tests
        
        # Step 5: Verify system is still processing original stimuli
        print("\n5️⃣ Verifying system state...")
        current_state = await self.check_processing_state()
        
        if current_state.get("is_processing", False):
            current_id = current_state.get("current_stimuli_id")
            duration = current_state.get("processing_duration_seconds", 0)
            print(f"✅ System still processing original stimuli: {current_id} ({duration:.1f}s)")
        else:
            print("⚠️ System is no longer processing (may have finished)")
        
        # Step 6: Analyze results
        print("\n6️⃣ Test Results Summary")
        print("=" * 30)
        
        rejected_count = sum(1 for r in rejection_results if not r.get("success"))
        accepted_count = sum(1 for r in rejection_results if r.get("success"))
        
        print(f"Total test stimuli sent: {len(rejection_results)}")
        print(f"Rejected (correct): {rejected_count}")
        print(f"Accepted (incorrect): {accepted_count}")
        
        if rejected_count == len(rejection_results):
            print("✅ ALL TESTS PASSED: Rejection mechanism working correctly")
            success = True
        else:
            print("❌ SOME TESTS FAILED: Rejection mechanism not working properly")
            success = False
        
        # Step 7: Wait for original processing to finish
        print("\n7️⃣ Waiting for original processing to complete...")
        if await self.wait_for_processing_to_finish():
            print("✅ Original processing completed")
        else:
            print("⚠️ Original processing still running (may take a while)")
        
        return success
    
    async def run_quick_test(self):
        """Run a quick test to verify system is working"""
        print("⚡ Running Quick Test")
        print("=" * 20)
        
        # Check processing state
        state = await self.check_processing_state()
        if state.get("error"):
            print(f"❌ Cannot check processing state: {state['error']}")
            return False
        
        print(f"Processing: {state.get('is_processing', False)}")
        print(f"Current stimuli: {state.get('current_stimuli_id', 'None')}")
        print(f"Can accept new: {state.get('can_accept_new_stimuli', False)}")
        
        # Send a simple test stimuli
        result = await self.send_stimuli("Hello, this is a test message")
        
        if result.get("success"):
            print(f"✅ Test stimuli accepted: {result['stimuli_id']}")
        else:
            print(f"❌ Test stimuli rejected: {result}")
        
        return result.get("success", False)


async def main():
    parser = argparse.ArgumentParser(description="Test stimuli rejection mechanism")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL for S2 API (default: http://localhost:8000)")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick test instead of full rejection test")
    
    args = parser.parse_args()
    
    tester = StimuliRejectionTest(args.url)
    
    if args.quick:
        success = await tester.run_quick_test()
    else:
        success = await tester.run_rejection_test()
    
    if success:
        print("\n🎉 Test completed successfully!")
        return 0
    else:
        print("\n💥 Test failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)