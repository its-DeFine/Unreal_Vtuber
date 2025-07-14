#!/usr/bin/env python3
"""
Test CLI Functionality Non-Interactively
=========================================

This script tests the CLI functionality by simulating the commands
that would be sent through the orchestrator CLI.

Created: 2025-07-14
"""

import asyncio
import time
import httpx
from datetime import datetime


async def test_cli_functionality():
    """Test CLI functionality through orchestrator"""
    print("🧪 Testing CLI Functionality")
    print("=" * 40)
    
    orchestrator_url = "http://localhost:8082"
    
    # Test 1: Send a complex command that should route to S2
    print("\n1️⃣ Testing Complex Command (should route to S2)")
    print("-" * 50)
    
    complex_command = {
        "stimulus_id": f"cli_test_{int(time.time())}",
        "text": "Please provide detailed analysis of trading strategies for cryptocurrency markets",
        "context": {"source": "cli"}
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{orchestrator_url}/process", json=complex_command)
            
            if response.status_code == 200:
                result = response.json()
                routing = result.get("routing_decision", {})
                execution = result.get("execution_results", {})
                
                system = routing.get("system", "unknown")
                confidence = routing.get("confidence", 0)
                
                print(f"✅ Command processed successfully")
                print(f"   Routed to: {system}")
                print(f"   Confidence: {confidence}")
                
                if "s2" in execution:
                    s2_result = execution["s2"]
                    if s2_result.get("success"):
                        print(f"   S2 Result: {s2_result.get('agent_decision', 'Success')}")
                    else:
                        print(f"   S2 Error: {s2_result.get('error_message', 'Unknown error')}")
                
                # Check if it's actually processing
                print("\n   Checking if processing started...")
                await asyncio.sleep(2.0)
                
                state_response = await client.get("http://localhost:8200/api/stimuli/processing-state")
                if state_response.status_code == 200:
                    state = state_response.json()
                    if state.get("is_processing"):
                        print(f"   ✅ Processing active: {state.get('current_stimuli_id')}")
                        
                        # Test stop functionality
                        print("\n2️⃣ Testing Stop Functionality")
                        print("-" * 30)
                        
                        stop_response = await client.post("http://localhost:8200/api/stimuli/stop")
                        if stop_response.status_code == 200:
                            stop_result = stop_response.json()
                            print("✅ Stop command successful")
                            if stop_result.get("was_processing"):
                                print(f"   Stopped: {stop_result.get('stopped_stimuli_id')}")
                                print(f"   Duration: {stop_result.get('processing_duration_seconds', 0):.1f}s")
                            else:
                                print("   No processing was active")
                        else:
                            print(f"❌ Stop command failed: {stop_response.status_code}")
                    else:
                        print("   ⚠️ Processing not active")
                else:
                    print(f"   ❌ Could not check processing state: {state_response.status_code}")
                
            else:
                print(f"❌ Command failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Test simple command
    print("\n3️⃣ Testing Simple Command (should route to S1)")
    print("-" * 50)
    
    simple_command = {
        "stimulus_id": f"cli_simple_{int(time.time())}",
        "text": "What is the current bitcoin price?",
        "context": {"source": "cli"}
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{orchestrator_url}/process", json=simple_command)
            
            if response.status_code == 200:
                result = response.json()
                routing = result.get("routing_decision", {})
                
                system = routing.get("system", "unknown")
                confidence = routing.get("confidence", 0)
                
                print(f"✅ Command processed successfully")
                print(f"   Routed to: {system}")
                print(f"   Confidence: {confidence}")
                
            else:
                print(f"❌ Command failed: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Test rejection mechanism
    print("\n4️⃣ Testing Rejection Mechanism")
    print("-" * 40)
    
    # First send a long-running command
    long_command = {
        "stimulus_id": f"cli_long_{int(time.time())}",
        "text": "Please create a comprehensive analysis of cryptocurrency market trends with detailed technical analysis and predictions",
        "context": {"source": "cli"}
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("   Sending long-running command...")
            response = await client.post(f"{orchestrator_url}/process", json=long_command)
            
            if response.status_code == 200:
                print("   ✅ Long command sent")
                
                # Wait for processing to start
                await asyncio.sleep(3.0)
                
                # Try to send another command (should be rejected)
                print("   Trying to send another command while processing...")
                
                reject_command = {
                    "stimulus_id": f"cli_reject_{int(time.time())}",
                    "text": "This should be rejected",
                    "context": {"source": "cli"}
                }
                
                response2 = await client.post(f"{orchestrator_url}/process", json=reject_command)
                
                if response2.status_code == 200:
                    result2 = response2.json()
                    execution2 = result2.get("execution_results", {})
                    
                    if "s2" in execution2:
                        s2_result = execution2["s2"]
                        if not s2_result.get("success") and "rejected_busy" in s2_result.get("agent_decision", ""):
                            print("   ✅ Command correctly rejected (system busy)")
                        else:
                            print("   ⚠️ Command was accepted (should have been rejected)")
                    else:
                        print("   ⚠️ Command not routed to S2")
                else:
                    print(f"   ❌ Rejection test failed: {response2.status_code}")
                
                # Clean up - stop the long-running command
                print("   Stopping long-running command...")
                stop_response = await client.post("http://localhost:8200/api/stimuli/stop")
                if stop_response.status_code == 200:
                    print("   ✅ Long command stopped")
                
            else:
                print(f"   ❌ Long command failed: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 CLI Functionality Test Complete")
    print("=" * 60)
    
    print("\n💡 CLI Usage:")
    print("   python scripts/orchestrator_cli_fixed.py")
    print("   > tell me about trading strategies")
    print("   > stop")
    print("   > exit")


if __name__ == "__main__":
    asyncio.run(test_cli_functionality())