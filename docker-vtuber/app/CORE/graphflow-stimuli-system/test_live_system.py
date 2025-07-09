#!/usr/bin/env python3
"""
Live test script for GraphFlow External Stimuli System.

This script tests the system with various types of stimuli.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import time

API_BASE_URL = "http://localhost:8081"
API_KEY = "test-key-12345"  # From api_keys.json

async def test_health_check():
    """Test the health check endpoint."""
    print("\n=== Testing Health Check ===")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/api/v1/health") as resp:
            data = await resp.json()
            print(f"Status: {resp.status}")
            print(f"Response: {json.dumps(data, indent=2)}")
            return resp.status == 200

async def test_system_status():
    """Test the system status endpoint."""
    print("\n=== Testing System Status ===")
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        async with session.get(f"{API_BASE_URL}/api/v1/status", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"Status: {resp.status}")
                print(f"Response: {json.dumps(data, indent=2)}")
            else:
                print(f"Error: {resp.status}")
                print(await resp.text())
            return resp.status == 200

async def submit_stimuli(content, source, priority="medium", metadata=None):
    """Submit a stimuli to the system."""
    print(f"\n=== Submitting Stimuli: {source} ===")
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "content": content,
            "source": source,
            "priority": priority,
            "metadata": metadata or {}
        }
        
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        async with session.post(
            f"{API_BASE_URL}/api/v1/stimuli/submit", 
            headers=headers,
            json=payload
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"Status: {resp.status}")
                print(f"Response: {json.dumps(data, indent=2)}")
                return data.get("stimuli_id")
            else:
                print(f"Error: {resp.status}")
                print(await resp.text())
                return None

async def check_stimuli_status(stimuli_id):
    """Check the status of a submitted stimuli."""
    print(f"\n=== Checking Stimuli Status: {stimuli_id} ===")
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        async with session.get(
            f"{API_BASE_URL}/api/v1/stimuli/{stimuli_id}/status",
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"Status: {resp.status}")
                print(f"Response: {json.dumps(data, indent=2)}")
                return data
            else:
                print(f"Error: {resp.status}")
                print(await resp.text())
                return None

async def test_websocket_connection():
    """Test WebSocket connection for real-time updates."""
    print("\n=== Testing WebSocket Connection ===")
    try:
        import websockets
        
        uri = f"ws://localhost:8081/ws/stimuli"
        async with websockets.connect(uri) as websocket:
            # Send authentication
            await websocket.send(json.dumps({"api_key": API_KEY}))
            
            # Listen for a few messages
            print("Connected to WebSocket, listening for updates...")
            for _ in range(3):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"Received: {message}")
                except asyncio.TimeoutError:
                    print("No message received (timeout)")
                    break
                    
    except ImportError:
        print("websockets library not installed, skipping WebSocket test")
    except Exception as e:
        print(f"WebSocket error: {e}")

async def run_all_tests():
    """Run all test scenarios."""
    print("🚀 Starting GraphFlow External Stimuli System Live Tests")
    print("=" * 60)
    
    # 1. Health check
    await test_health_check()
    
    # 2. System status
    await test_system_status()
    
    # 3. Submit various stimuli
    test_cases = [
        {
            "content": "Hello, how are you today?",
            "source": "user_chat",
            "priority": "medium",
            "metadata": {"user_id": "test_user_123", "platform": "test"}
        },
        {
            "content": "/switch_character weather_presenter",
            "source": "admin_console",
            "priority": "high",
            "metadata": {"admin_id": "admin_test", "command_type": "character_switch"}
        },
        {
            "content": "System CPU usage at 85%",
            "source": "system_monitor",
            "priority": "high",
            "metadata": {"metric": "cpu_usage", "value": 85}
        },
        {
            "content": "Emergency: Server room temperature critical!",
            "source": "monitoring_system",
            "priority": "critical",
            "metadata": {"alert_type": "temperature", "severity": "critical"}
        },
        {
            "content": "@VTuberBot just mentioned in tweet",
            "source": "social_media",
            "priority": "low",
            "metadata": {"platform": "twitter", "mention_type": "direct"}
        }
    ]
    
    stimuli_ids = []
    for test_case in test_cases:
        stimuli_id = await submit_stimuli(**test_case)
        if stimuli_id:
            stimuli_ids.append(stimuli_id)
        await asyncio.sleep(1)  # Small delay between submissions
    
    # 4. Check status of submitted stimuli
    print("\n" + "=" * 60)
    print("Waiting 3 seconds for processing...")
    await asyncio.sleep(3)
    
    for stimuli_id in stimuli_ids:
        await check_stimuli_status(stimuli_id)
    
    # 5. Test WebSocket
    await test_websocket_connection()
    
    # 6. Check metrics
    print("\n=== Checking Metrics ===")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/metrics") as resp:
            if resp.status == 200:
                metrics = await resp.text()
                print("Sample metrics:")
                # Show first few lines of metrics
                for line in metrics.split('\n')[:20]:
                    if line and not line.startswith('#'):
                        print(f"  {line}")
            else:
                print(f"Metrics error: {resp.status}")
    
    print("\n" + "=" * 60)
    print("✅ Live tests completed!")

if __name__ == "__main__":
    asyncio.run(run_all_tests())