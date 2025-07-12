#!/usr/bin/env python3
"""
Test script for the NeuroSync Game Control System
Tests the /game_control endpoint and TCP controller functionality
"""
import requests
import json
import time
import argparse

def test_game_control_health(base_url="http://localhost:5001"):
    """Test the game control health endpoint"""
    print("🔍 Testing Game Control Health Endpoint")
    print("=" * 50)
    
    try:
        response = requests.get(f"{base_url}/game_control/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data.get('status', 'unknown')}")
            
            if 'tcp_connection' in data:
                tcp_info = data['tcp_connection']
                print(f"🔌 TCP Connection: {tcp_info.get('overall', 'unknown')}")
                print(f"📡 TCP Host: {tcp_info.get('config', {}).get('host', 'unknown')}")
                print(f"🚪 TCP Port: {tcp_info.get('config', {}).get('port', 'unknown')}")
            
            print(f"🎮 Processor Available: {data.get('processor_available', False)}")
            print(f"🎯 Controller Available: {data.get('controller_available', False)}")
            
        else:
            print(f"❌ Health check failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing health endpoint: {e}")
    
    print()

def test_game_control_features(base_url="http://localhost:5001"):
    """Test the game control features endpoint"""
    print("🎮 Testing Game Control Features Endpoint")
    print("=" * 50)
    
    try:
        response = requests.get(f"{base_url}/game_control/features", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data.get('status', 'unknown')}")
            
            if 'features' in data:
                features = data['features']
                print(f"🏰 Levels: {len(features.get('levels', []))} available")
                print(f"👤 Presets: {len(features.get('presets', []))} available")
                print(f"👗 Outfits: {len(features.get('outfits', []))} available")
                print(f"💇 Hair Styles: {len(features.get('hair_styles', []))} available")
                print(f"🎭 Animations: {len(features.get('animations', []))} available")
            
            if 'example_commands' in data:
                examples = data['example_commands']
                print("\n📝 Example Commands:")
                for name, commands in examples.items():
                    print(f"  {name}: {commands}")
                    
        else:
            print(f"❌ Features request failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing features endpoint: {e}")
    
    print()

def test_game_control_prompt(prompt, base_url="http://localhost:5001"):
    """Test a specific game control prompt"""
    print(f"🎯 Testing Game Control Prompt: '{prompt}'")
    print("=" * 50)
    
    payload = {"prompt": prompt}
    
    try:
        start_time = time.time()
        response = requests.post(f"{base_url}/game_control", json=payload, timeout=30)
        end_time = time.time()
        
        print(f"Status Code: {response.status_code}")
        print(f"⏱️ Response Time: {end_time - start_time:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data.get('status', 'unknown')}")
            print(f"🎮 Commands Generated: {data.get('commands_generated', 0)}")
            print(f"✅ Commands Successful: {data.get('commands_successful', 0)}")
            print(f"❌ Commands Failed: {data.get('commands_failed', 0)}")
            print(f"🔌 TCP Host: {data.get('tcp_host', 'unknown')}")
            print(f"🚪 TCP Port: {data.get('tcp_port', 'unknown')}")
            
            if 'command_details' in data:
                print("\n📝 Command Details:")
                for detail in data['command_details']:
                    command = detail.get('command', 'unknown')
                    status = detail.get('status', 'unknown')
                    emoji = "✅" if status == "success" else "❌"
                    print(f"  {emoji} {command} - {status}")
            
            if 'error' in data:
                print(f"⚠️ Error: {data['error']}")
                
        else:
            print(f"❌ Game control request failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing game control prompt: {e}")
    
    print()

def run_comprehensive_test(base_url="http://localhost:5001"):
    """Run a comprehensive test of the game control system"""
    print("🚀 NeuroSync Game Control System Test")
    print("=" * 60)
    print()
    
    # Test health endpoint
    test_game_control_health(base_url)
    
    # Test features endpoint
    test_game_control_features(base_url)
    
    # Test various game control prompts
    test_prompts = [
        "yellow hair, medieval scene",
        "blue hair, bigger eyes, DJ scene",
        "feminine character, maid dress, red hair",
        "night time, bright stars",
        "dance animation",
        "reset to default",
        "invalid nonsense request"  # Test error handling
    ]
    
    for prompt in test_prompts:
        test_game_control_prompt(prompt, base_url)
        time.sleep(1)  # Small delay between tests

def main():
    parser = argparse.ArgumentParser(description="Test NeuroSync Game Control System")
    parser.add_argument("--url", default="http://localhost:5001", 
                       help="Base URL for NeuroSync server (default: http://localhost:5001)")
    parser.add_argument("--prompt", help="Test a specific game control prompt")
    parser.add_argument("--health", action="store_true", help="Test only health endpoint")
    parser.add_argument("--features", action="store_true", help="Test only features endpoint")
    
    args = parser.parse_args()
    
    if args.health:
        test_game_control_health(args.url)
    elif args.features:
        test_game_control_features(args.url)
    elif args.prompt:
        test_game_control_prompt(args.prompt, args.url)
    else:
        run_comprehensive_test(args.url)

if __name__ == "__main__":
    main() 