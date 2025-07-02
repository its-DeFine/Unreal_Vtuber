#!/usr/bin/env python3
"""
Visual Character Setup Test Script
Tests the visual appearance setup for both characters independently
"""

import sys
import time
import os

# Add the NeuroSync Player path to import our visual setup modules
sys.path.append('docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player')

try:
    from character_visual_setups import (
        apply_professor_smith_appearance, 
        apply_streamer_appearance,
        apply_character_appearance,
        CHARACTER_SETUPS
    )
    print("✅ Successfully imported character visual setup modules")
except ImportError as e:
    print(f"❌ Failed to import visual setup modules: {e}")
    print("💡 Make sure you're running this from the autonomy directory")
    sys.exit(1)

def test_professor_smith():
    """Test Professor Smith visual setup"""
    print("\n🎓 TESTING PROFESSOR SMITH VISUAL SETUP")
    print("=" * 60)
    print("Setting up: Blue hair, blue eyes, professional academic appearance")
    
    try:
        result = apply_professor_smith_appearance(enhanced=True)
        if result:
            print("✅ Professor Smith visual setup completed successfully!")
        else:
            print("⚠️ Professor Smith visual setup completed with some issues")
        return result
    except Exception as e:
        print(f"❌ Professor Smith visual setup failed: {e}")
        return False

def test_streamer():
    """Test Streamer visual setup"""
    print("\n🎬 TESTING STREAMER VISUAL SETUP")
    print("=" * 60)
    print("Setting up: Pink/purple hair, violet eyes, modern streaming appearance")
    
    try:
        result = apply_streamer_appearance(enhanced=True, dynamic=True)
        if result:
            print("✅ Streamer visual setup completed successfully!")
        else:
            print("⚠️ Streamer visual setup completed with some issues")
        return result
    except Exception as e:
        print(f"❌ Streamer visual setup failed: {e}")
        return False

def test_character_mapping():
    """Test the character ID mapping system"""
    print("\n🗺️ TESTING CHARACTER ID MAPPING")
    print("=" * 60)
    
    for character_id, setup_function in CHARACTER_SETUPS.items():
        print(f"Character ID: {character_id} → {setup_function.__name__}")
    
    # Test the apply_character_appearance function
    print("\n🧪 Testing apply_character_appearance function...")
    
    test_cases = [
        ("demo_teacher", "Professor Smith"),
        ("reactive_default", "Streamer"),
        ("unknown_character", "Unknown")
    ]
    
    for char_id, char_name in test_cases:
        print(f"\nTesting character ID: {char_id}")
        if char_id in CHARACTER_SETUPS:
            print(f"✅ {char_name} mapping found")
        else:
            print(f"❌ {char_name} mapping not found")

def interactive_test():
    """Interactive test menu"""
    print("\n🎭 INTERACTIVE VISUAL SETUP TEST")
    print("=" * 60)
    
    while True:
        print("\nChoose a test option:")
        print("  1. 🎓 Test Professor Smith Setup")
        print("  2. 🎬 Test Streamer Setup")
        print("  3. 🗺️ Test Character Mapping")
        print("  4. 🚀 Run All Tests")
        print("  5. ⏱️ Professor → Wait → Streamer (Full Demo)")
        print("  q. Quit")
        
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == 'q':
            print("👋 Goodbye!")
            break
        elif choice == '1':
            test_professor_smith()
        elif choice == '2':
            test_streamer()
        elif choice == '3':
            test_character_mapping()
        elif choice == '4':
            print("\n🚀 RUNNING ALL TESTS")
            print("=" * 60)
            test_character_mapping()
            test_professor_smith()
            time.sleep(3)
            test_streamer()
        elif choice == '5':
            print("\n🎬 FULL CHARACTER DEMO")
            print("=" * 60)
            print("Testing complete character transformation flow...")
            
            print("\n🎓 Step 1: Setting up Professor Smith...")
            test_professor_smith()
            
            print(f"\n⏱️ Waiting 10 seconds to see Professor Smith appearance...")
            for i in range(10, 0, -1):
                print(f"   {i} seconds remaining...", end='\r')
                time.sleep(1)
            print("   ✅ Wait complete!                    ")
            
            print("\n🎬 Step 2: Switching to Streamer...")
            test_streamer()
            
            print("\n✨ Full demo complete! Check the visual changes in the avatar!")
        else:
            print("❌ Invalid choice!")

def main():
    """Main test function"""
    print("🎭 NEUROSYNC CHARACTER VISUAL SETUP TEST")
    print("📡 This script tests the visual appearance setup for characters")
    print("🎯 Ensure NeuroSync container is running and Unreal Engine TCP is available")
    print("=" * 80)
    
    # Check if we can reach the TCP server (basic test)
    print("🔍 Checking system readiness...")
    print("💡 Note: Visual setup scripts use host.docker.internal when run inside container")
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 7777))  # Test from host perspective
        sock.close()
        
        if result == 0:
            print("✅ Unreal Engine TCP server (port 7777) is reachable from host")
        else:
            print("⚠️ Unreal Engine TCP server (port 7777) not reachable from host")
            print("💡 Visual commands will be sent but may not apply if TCP server is down")
    except Exception as e:
        print(f"⚠️ Could not test TCP connection: {e}")
    
    # Run interactive test
    interactive_test()

if __name__ == "__main__":
    main() 