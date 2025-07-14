#!/usr/bin/env python3
"""
Diagnose Visual Identity System
===============================

This script tests the visual identity TCP command system and helps diagnose issues.

Created: 2025-07-14
"""

import asyncio
import httpx
import socket
import time
import os


def test_tcp_connection(host="127.0.0.1", port=7777):
    """Test direct TCP connection to Unreal Engine"""
    print(f"\n🔌 Testing TCP connection to {host}:{port}")
    print("-" * 50)
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((host, port))
            print(f"✅ TCP connection successful to {host}:{port}")
            
            # Try sending a test command
            test_cmd = "MENU.\n"
            s.sendall(test_cmd.encode())
            print(f"✅ Sent test command: {test_cmd.strip()}")
            
            # Close menu
            s.sendall("CMENU.\n".encode())
            return True
            
    except socket.timeout:
        print(f"❌ Connection timeout to {host}:{port}")
        return False
    except ConnectionRefusedError:
        print(f"❌ Connection refused to {host}:{port}")
        print("   Make sure Unreal Engine is running and TCP server is enabled")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


async def test_character_switch():
    """Test character switching via S1 API"""
    print("\n🎭 Testing character switching via S1 API")
    print("-" * 50)
    
    s1_url = "http://localhost:5001"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get current character
            response = await client.get(f"{s1_url}/character/current")
            if response.status_code == 200:
                current = response.json()
                current_char = current.get('character', {})
                print(f"Current character: {current_char.get('name', 'Unknown')} ({current_char.get('id', 'Unknown')})")
                
                # Check visual identity
                visual_identity = current_char.get('visual_identity', {})
                if visual_identity:
                    print(f"Visual identity: {visual_identity.get('preset_name', 'None')}")
                    print(f"TCP commands: {len(visual_identity.get('tcp_commands', []))} commands")
                else:
                    print("❌ No visual identity defined for current character")
            else:
                print(f"❌ Failed to get current character: {response.status_code}")
                
            # Test switching to each character
            test_characters = [
                ("sophia_trader_template", "Sophia Trader", "golden_goddess"),
                ("diana_educator_template", "Diana Code", "emerald_elegance"),
                ("luna_streamer_template", "Luna Streamer", "ruby_sensation")
            ]
            
            for char_id, char_name, expected_visual in test_characters:
                print(f"\n📋 Testing: {char_name}")
                
                # Switch character
                switch_response = await client.post(
                    f"{s1_url}/character/activate",
                    json={"character_id": char_id}
                )
                
                if switch_response.status_code == 200:
                    print(f"✅ Switched to {char_name}")
                    
                    # Give time for visual identity to apply
                    await asyncio.sleep(2.0)
                    
                    # Check if visual identity was applied
                    current_response = await client.get(f"{s1_url}/character/current")
                    if current_response.status_code == 200:
                        current = current_response.json()
                        actual_visual = current.get('character', {}).get('visual_identity', {}).get('preset_name')
                        if actual_visual == expected_visual:
                            print(f"   ✅ Visual identity applied: {actual_visual}")
                        else:
                            print(f"   ❌ Wrong visual: {actual_visual} (expected: {expected_visual})")
                else:
                    print(f"❌ Failed to switch to {char_name}: {switch_response.status_code}")
                    
    except Exception as e:
        print(f"❌ API test error: {e}")


async def check_logs():
    """Check S1 logs for visual identity messages"""
    print("\n📜 Checking S1 logs for visual identity activity")
    print("-" * 50)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to get recent logs (this endpoint might not exist, but worth trying)
            response = await client.get("http://localhost:5001/logs/recent")
            if response.status_code == 200:
                logs = response.json()
                visual_logs = [log for log in logs if "visual" in log.lower() or "tcp" in log.lower()]
                for log in visual_logs[-10:]:  # Last 10 relevant logs
                    print(f"   {log}")
            else:
                print("   ℹ️ Log endpoint not available")
    except:
        print("   ℹ️ Could not retrieve logs via API")


def check_environment():
    """Check environment configuration"""
    print("\n🔧 Environment Configuration")
    print("-" * 50)
    
    tcp_host = os.getenv("UNREAL_TCP_HOST", "host.docker.internal")
    tcp_port = os.getenv("UNREAL_TCP_PORT", "7777")
    
    print(f"UNREAL_TCP_HOST: {tcp_host}")
    print(f"UNREAL_TCP_PORT: {tcp_port}")
    
    if tcp_host == "host.docker.internal":
        print("ℹ️ Using Docker default host (host.docker.internal)")
        print("   If running outside Docker, set UNREAL_TCP_HOST=127.0.0.1")


async def main():
    """Run all diagnostics"""
    print("🔍 VISUAL IDENTITY SYSTEM DIAGNOSTICS")
    print("=" * 60)
    
    # Check environment
    check_environment()
    
    # Test direct TCP connection
    tcp_hosts = ["127.0.0.1", "host.docker.internal", "localhost"]
    tcp_ok = False
    
    for host in tcp_hosts:
        if test_tcp_connection(host, 7777):
            tcp_ok = True
            print(f"\n✅ TCP connection works with host: {host}")
            break
    
    if not tcp_ok:
        print("\n❌ No TCP connection could be established")
        print("   Please ensure:")
        print("   1. Unreal Engine is running")
        print("   2. TCP server is enabled on port 7777")
        print("   3. Firewall allows connections")
        return
    
    # Test character switching
    await test_character_switch()
    
    # Check logs
    await check_logs()
    
    print("\n" + "=" * 60)
    print("🏁 Diagnostics complete!")
    print("\nIf visual identities are not applying:")
    print("1. Check that TCP commands are reaching Unreal Engine")
    print("2. Verify the TCP host configuration matches your setup")
    print("3. Ensure Unreal Engine recognizes the commands")
    print("4. Check S1 container logs: docker logs neurosync_s1")


if __name__ == "__main__":
    asyncio.run(main())