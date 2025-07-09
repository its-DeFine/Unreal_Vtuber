#!/usr/bin/env python3
"""
Integration test for GraphFlow with System1 (VTuber) and System2 (AutoGen).
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import time

API_BASE_URL = "http://localhost:8081"
API_KEY = "test-key-12345"

async def check_system_status():
    """Check if both systems are connected."""
    print("\n=== Checking System Integration Status ===")
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        # Check GraphFlow status
        async with session.get(f"{API_BASE_URL}/api/v1/status", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"\nGraphFlow Status: {data['status']}")
                print(f"Uptime: {data['uptime_seconds']:.2f} seconds")
                print("\nComponent Status:")
                for component, info in data['components'].items():
                    print(f"  - {component}: {info['status']}")
                    if 'details' in info:
                        print(f"    Details: {json.dumps(info['details'], indent=6)}")
                return data
            else:
                print(f"Error getting status: {resp.status}")
                return None

async def test_vtuber_interaction():
    """Test interaction that should trigger VTuber response."""
    print("\n=== Testing VTuber Interaction ===")
    
    test_cases = [
        {
            "content": "Hello! Can you tell me about the weather today?",
            "source": "user_chat",
            "priority": "high",
            "metadata": {
                "user_id": "integration_test",
                "platform": "test",
                "expects_voice_response": True
            }
        },
        {
            "content": "What's your favorite color?",
            "source": "user_chat", 
            "priority": "medium",
            "metadata": {
                "user_id": "integration_test",
                "platform": "test",
                "conversation_context": "casual_chat"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- Testing: {test_case['content'][:50]}... ---")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            
            start_time = time.time()
            
            async with session.post(
                f"{API_BASE_URL}/api/v1/stimuli/submit", 
                headers=headers,
                json=test_case
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    processing_time = time.time() - start_time
                    
                    print(f"✓ Submitted successfully")
                    print(f"  Stimuli ID: {data['stimuli_id']}")
                    print(f"  Status: {data['processing_status']}")
                    print(f"  Decision: {data.get('message', 'N/A')}")
                    print(f"  Processing time: {processing_time:.2f}s")
                    
                    # Wait a bit and check status
                    await asyncio.sleep(2)
                    
                    # Check detailed status
                    async with session.get(
                        f"{API_BASE_URL}/api/v1/stimuli/{data['stimuli_id']}/status",
                        headers=headers
                    ) as status_resp:
                        if status_resp.status == 200:
                            status_data = await status_resp.json()
                            print(f"  Final Decision: {status_data.get('decision', 'N/A')}")
                            print(f"  Reasoning: {status_data.get('metadata', {}).get('reasoning', 'N/A')}")
                else:
                    print(f"✗ Error: {resp.status}")
                    print(await resp.text())

async def test_admin_commands():
    """Test admin commands that should affect VTuber state."""
    print("\n\n=== Testing Admin Commands ===")
    
    commands = [
        {
            "content": "/status",
            "source": "admin_console",
            "priority": "high",
            "metadata": {"admin_id": "test_admin", "command_type": "status"}
        },
        {
            "content": "/set_mode autonomous",
            "source": "admin_console",
            "priority": "critical",
            "metadata": {"admin_id": "test_admin", "command_type": "mode_change"}
        }
    ]
    
    for cmd in commands:
        print(f"\n--- Testing command: {cmd['content']} ---")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            
            async with session.post(
                f"{API_BASE_URL}/api/v1/stimuli/submit", 
                headers=headers,
                json=cmd
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Command submitted")
                    print(f"  Response: {data.get('message', 'N/A')}")
                else:
                    print(f"✗ Error: {resp.status}")

async def test_system2_complex_task():
    """Test a complex task that should be routed to System2 (AutoGen)."""
    print("\n\n=== Testing System2 (AutoGen) Complex Task ===")
    
    complex_task = {
        "content": "Analyze the performance metrics from the last hour and create a summary report with recommendations for optimization.",
        "source": "admin_console",
        "priority": "medium",
        "metadata": {
            "task_type": "analysis",
            "requires_multi_agent": True,
            "output_format": "report"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        print(f"Submitting complex analytical task...")
        
        async with session.post(
            f"{API_BASE_URL}/api/v1/stimuli/submit", 
            headers=headers,
            json=complex_task
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✓ Task submitted successfully")
                print(f"  Stimuli ID: {data['stimuli_id']}")
                print(f"  Initial Status: {data['processing_status']}")
                print(f"  Decision: {data.get('message', 'N/A')}")
            else:
                print(f"✗ Error: {resp.status}")
                print(await resp.text())

async def monitor_websocket():
    """Monitor WebSocket for real-time updates."""
    print("\n\n=== Monitoring WebSocket for Real-time Updates ===")
    try:
        import websockets
        
        uri = f"ws://localhost:8081/ws/stimuli"
        print(f"Connecting to WebSocket at {uri}...")
        
        async with websockets.connect(uri) as websocket:
            # Send authentication
            await websocket.send(json.dumps({"api_key": API_KEY}))
            print("✓ Connected and authenticated")
            print("Listening for updates (10 seconds)...")
            
            # Listen for updates
            end_time = time.time() + 10
            while time.time() < end_time:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    print(f"\n📢 Update: {data.get('type', 'unknown')}")
                    print(f"   Data: {json.dumps(data, indent=4)}")
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Error: {e}")
                    break
                    
    except ImportError:
        print("websockets library not installed")
    except Exception as e:
        print(f"WebSocket error: {e}")

async def run_integration_tests():
    """Run all integration tests."""
    print("🚀 GraphFlow Integration Tests with System1 & System2")
    print("=" * 60)
    
    # Check system status
    status = await check_system_status()
    
    if not status:
        print("\n❌ Cannot proceed - GraphFlow not responding")
        return
    
    # Run tests
    await test_vtuber_interaction()
    await test_admin_commands()
    await test_system2_complex_task()
    
    # Monitor WebSocket
    await monitor_websocket()
    
    print("\n" + "=" * 60)
    print("✅ Integration tests completed!")
    print("\nNote: Check the VTuber output and AutoGen logs for actual responses.")

if __name__ == "__main__":
    asyncio.run(run_integration_tests())