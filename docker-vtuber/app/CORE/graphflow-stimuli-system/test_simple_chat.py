#!/usr/bin/env python3
"""
Simple test to send a chat message through GraphFlow.
"""

import asyncio
import aiohttp
import json
import sys

API_BASE_URL = "http://localhost:8081"
API_KEY = "test-key-12345"

async def send_chat_message(message):
    """Send a simple chat message."""
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "content": message,
            "source": "user_chat",
            "priority": "high",
            "metadata": {
                "user_id": "test_user",
                "expects_response": True
            }
        }
        
        print(f"Sending: {message}")
        
        async with session.post(
            f"{API_BASE_URL}/api/v1/stimuli/submit", 
            headers=headers,
            json=payload
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✓ Success!")
                print(f"  ID: {data['stimuli_id']}")
                print(f"  Status: {data['processing_status']}")
                print(f"  Decision: {data.get('message', 'N/A')}")
                
                # Wait and check status
                await asyncio.sleep(1)
                
                # Get detailed status
                async with session.get(
                    f"{API_BASE_URL}/api/v1/stimuli/{data['stimuli_id']}/status",
                    headers=headers
                ) as status_resp:
                    if status_resp.status == 200:
                        status_data = await status_resp.json()
                        print(f"\nDetailed Status:")
                        print(f"  Decision: {status_data.get('decision')}")
                        print(f"  Processing Time: {status_data.get('processing_time', 0):.3f}s")
                        print(f"  Metadata: {json.dumps(status_data.get('metadata', {}), indent=4)}")
            else:
                print(f"✗ Error: {resp.status}")
                print(await resp.text())

async def main():
    message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello! How are you today?"
    await send_chat_message(message)

if __name__ == "__main__":
    asyncio.run(main())