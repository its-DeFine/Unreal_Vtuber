#!/usr/bin/env python3
"""
Streamer Character Visual Setup Script
Automatically configures the visual appearance for the Streamer character
- Vibrant pink/purple hair for streaming appeal
- Bright, engaging eyes
- Modern streaming outfit and environment
"""

import socket
import time
import logging
import sys
import random
import os
from typing import Optional

logger = logging.getLogger(__name__)

def get_tcp_host() -> str:
    """Auto-detect correct TCP host based on environment"""
    return "host.docker.internal" if os.path.exists('/.dockerenv') else "127.0.0.1"

# TCP Connection Configuration
HOST = get_tcp_host()  # Dynamic host detection for Docker/host environments
PORT = 7777
TIMEOUT = 2.0

class StreamerVisualSetup:
    """Visual setup controller for Streamer character"""
    
    def __init__(self):
        self.character_name = "Streaming Star"
        self.character_id = "reactive_default"  # Using reactive assistant as base
        logger.info(f"🎭 Initializing visual setup for {self.character_name}")
    
    def send_command(self, command: str) -> bool:
        """Send TCP command to Unreal Engine with error handling"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(TIMEOUT)
                s.connect((HOST, PORT))
                s.sendall((command + "\n").encode())
                logger.info(f"✅ Applied: {command}")
                print(f"✅ Applied: {command}")
                return True
        except Exception as e:
            logger.error(f"❌ Connection error for '{command}': {e}")
            print(f"❌ Connection error for '{command}': {e}")
            return False
    
    def apply_basic_streamer_setup(self) -> bool:
        """Apply Streamer's signature vibrant streaming look"""
        print(f"🎬 Applying {self.character_name} Visual Setup...")
        print("=" * 60)
        
        success_count = 0
        total_commands = 0
        
        # 1. Set Feminine Preset for Streaming Appeal
        print("👩‍💻 Setting streaming feminine preset...")
        if self.send_command("PRS.Fem"):
            success_count += 1
        total_commands += 1
        time.sleep(0.5)
        
        # 2. Apply Vibrant Pink/Purple Hair
        print("💖 Setting vibrant pink/purple streaming hair...")
        commands = [
            ("HCR.0.9", "High red for pink base"),      # Strong red for pink
            ("HCG.0.4", "Moderate green for balance"),  # Some green for depth
            ("HCB.0.8", "High blue for purple tint")    # Strong blue for purple
        ]
        
        for cmd, desc in commands:
            print(f"  {desc}...")
            if self.send_command(cmd):
                success_count += 1
            total_commands += 1
            time.sleep(0.3)
        
        # 3. Apply Bright Streaming Eyes
        print("✨ Setting bright, engaging streaming eyes...")
        eye_commands = [
            ("EC.0.8", "Bright violet hue for eyes"),     # Bright violet/purple
            ("ES.25000", "High saturation for appeal")    # High saturation for streaming
        ]
        
        for cmd, desc in eye_commands:
            print(f"  {desc}...")
            if self.send_command(cmd):
                success_count += 1
            total_commands += 1
            time.sleep(0.3)
        
        # 4. Apply Trendy Streaming Outfit
        print("👗 Setting trendy streaming outfit...")
        if self.send_command("OF.Pop Star"):  # Modern and trendy
            success_count += 1
        total_commands += 1
        time.sleep(0.5)
        
        # 5. Set Streaming Environment
        print("🎵 Setting streaming environment...")
        if self.send_command("LVL.DJ"):  # Perfect for streaming/content creation
            success_count += 1
        total_commands += 1
        time.sleep(0.5)
        
        # 6. Add Streaming Animation
        print("💃 Adding streaming dance animation...")
        if self.send_command("ANIM.Dance"):  # Engaging animation for streams
            success_count += 1
        total_commands += 1
        time.sleep(0.5)
        
        print("\n" + "=" * 60)
        print(f"🎬 STREAMER SETUP COMPLETE! ✨")
        print(f"👩‍💻 Character: {self.character_name}")
        print("💖 Hair: Vibrant pink/purple")
        print("✨ Eyes: Bright violet with high appeal")
        print("👗 Outfit: Trendy Pop Star style")
        print("🎵 Environment: DJ/Streaming setup")
        print("💃 Animation: Engaging dance moves")
        print(f"📊 Success Rate: {success_count}/{total_commands} commands")
        print("=" * 60)
        
        return success_count == total_commands
    
    def apply_enhanced_streamer_features(self) -> bool:
        """Apply enhanced facial features for a vibrant, engaging streaming look"""
        print("\n🌟 Applying Enhanced Streamer Features...")
        print("=" * 50)
        
        success_count = 0
        total_commands = 0
        
        # Enhanced facial features for streaming appeal
        enhanced_features = [
            ("MTEYW.0.2", "Wider eyes for streaming appeal"),
            ("MTEYH.0.1", "Taller eyes for expressiveness"),
            ("MTEB.-0.05", "Reduce eye bags for youthful look"),
            ("MTEBW.0.15", "Bold eyebrows for expression"),
            ("MTEBA.0.2", "Arched eyebrows for engagement"),
            ("MTLO.0.1", "Fuller lips for speaking appeal"),
            ("MTLCV.0.15", "Natural smile curve for friendliness"),
            ("MTCB.0.15", "Defined cheekbones for camera appeal"),
            ("MTNW.-0.05", "Slightly refined nose"),
            ("MTCW.0.1", "Defined chin for streaming presence")
        ]
        
        for cmd, desc in enhanced_features:
            print(f"  {desc}...")
            if self.send_command(cmd):
                success_count += 1
            total_commands += 1
            time.sleep(0.2)
        
        print(f"🌟 Enhanced streaming features applied! ({success_count}/{total_commands})")
        return success_count == total_commands
    
    def apply_dynamic_streaming_effects(self) -> bool:
        """Apply dynamic effects perfect for streaming"""
        print("\n🎯 Applying Dynamic Streaming Effects...")
        print("=" * 50)
        
        # Randomize eye saturation for dynamic look
        dynamic_saturation = round(random.uniform(20000.0, 35000.0), 1)
        
        # Slight hair color variations for dynamic streaming look
        red_intensity = round(random.uniform(0.85, 0.95), 3)
        blue_intensity = round(random.uniform(0.75, 0.85), 3)
        
        dynamic_commands = [
            (f"ES.{dynamic_saturation}", f"Dynamic eye saturation: {dynamic_saturation}"),
            (f"HCR.{red_intensity}", f"Dynamic red hair intensity: {red_intensity}"),
            (f"HCB.{blue_intensity}", f"Dynamic blue hair intensity: {blue_intensity}")
        ]
        
        success_count = 0
        for cmd, desc in dynamic_commands:
            print(f"  {desc}...")
            if self.send_command(cmd):
                success_count += 1
            time.sleep(0.3)
        
        print(f"🎯 Dynamic effects applied! Perfect for streaming!")
        return success_count == len(dynamic_commands)
    
    def quick_streamer_test(self) -> bool:
        """Quick test to apply just the essential Streamer look"""
        print("⚡ Quick Streamer Test...")
        
        essential_commands = [
            "PRS.Fem",
            "HCR.0.9", "HCG.0.4", "HCB.0.8",  # Pink/purple hair
            "EC.0.8", "ES.25000",               # Bright violet eyes
            "OF.Pop Star",                      # Modern outfit
            "LVL.DJ"                           # Streaming environment
        ]
        
        success = True
        for cmd in essential_commands:
            if not self.send_command(cmd):
                success = False
            time.sleep(0.2)
        
        print(f"⚡ Quick test {'✅ Complete' if success else '❌ Failed'}!")
        return success
    
    def continuous_streaming_mode(self):
        """Continuous mode with subtle variations for live streaming"""
        print("\n🔴 Entering Live Streaming Mode...")
        print("Press Ctrl+C to stop")
        print("=" * 50)
        
        try:
            cycle = 0
            while True:
                cycle += 1
                print(f"\n🎬 Streaming Cycle #{cycle}")
                
                # Vary eye saturation for engaging look
                saturation = round(random.uniform(20000.0, 40000.0), 1)
                self.send_command(f"ES.{saturation}")
                
                # Subtle hair color variations (staying pink/purple)
                red_intensity = round(random.uniform(0.8, 1.0), 3)
                blue_intensity = round(random.uniform(0.7, 0.9), 3)
                
                self.send_command(f"HCR.{red_intensity}")
                self.send_command(f"HCB.{blue_intensity}")
                
                # Occasional dance animation
                if cycle % 3 == 0:
                    self.send_command("ANIM.Dance")
                    print("💃 Dance animation triggered!")
                
                print(f"✨ Streaming update: Eyes={saturation}, Hair=R{red_intensity}/B{blue_intensity}")
                time.sleep(5)  # 5-second intervals for streaming
                
        except KeyboardInterrupt:
            print("\n🛑 Live streaming mode stopped")

def apply_streamer_appearance(enhanced: bool = True, dynamic: bool = True) -> bool:
    """
    Main function to apply Streamer's visual appearance
    
    Args:
        enhanced: Whether to apply enhanced facial features
        dynamic: Whether to apply dynamic streaming effects
    
    Returns:
        True if setup completed successfully
    """
    setup = StreamerVisualSetup()
    
    # Apply basic setup
    basic_success = setup.apply_basic_streamer_setup()
    
    if not basic_success:
        logger.warning("⚠️ Basic setup had some failures")
    
    # Apply enhanced features if requested
    enhanced_success = True
    if enhanced:
        enhanced_success = setup.apply_enhanced_streamer_features()
    
    # Apply dynamic effects if requested
    dynamic_success = True
    if dynamic:
        dynamic_success = setup.apply_dynamic_streaming_effects()
    
    overall_success = basic_success and enhanced_success and dynamic_success
    
    if overall_success:
        logger.info("✅ Streamer visual setup completed successfully!")
    else:
        logger.warning("⚠️ Streamer visual setup completed with some issues")
    
    return overall_success

def main():
    """Interactive menu for Streamer visual setup"""
    print("🎬 STREAMER VISUAL SETUP TOOL 🎬")
    print(f"📡 Target: {HOST}:{PORT}")
    print("=" * 60)
    
    setup = StreamerVisualSetup()
    
    while True:
        print(f"\n{setup.character_name} Setup Options:")
        print("  1. 🎬 Apply Complete Streamer Setup")
        print("  2. 🌟 Apply Enhanced Streamer Setup")
        print("  3. 🎯 Apply Dynamic Streaming Effects")
        print("  4. ⚡ Quick Streamer Test")
        print("  5. 🔴 Live Streaming Mode (Continuous)")
        print("  6. 💖 Hair Only (Pink/Purple)")
        print("  7. ✨ Eyes Only (Bright Violet)")
        print("  8. 👗 Outfit Only (Pop Star)")
        print("  9. 🎵 Environment Only (DJ)")
        print("  0. 💃 Dance Animation")
        print("  q. Quit")
        
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == 'q':
            print("👋 Goodbye!")
            break
        elif choice == '1':
            setup.apply_basic_streamer_setup()
        elif choice == '2':
            setup.apply_basic_streamer_setup()
            setup.apply_enhanced_streamer_features()
        elif choice == '3':
            setup.apply_dynamic_streaming_effects()
        elif choice == '4':
            setup.quick_streamer_test()
        elif choice == '5':
            setup.apply_basic_streamer_setup()
            setup.continuous_streaming_mode()
        elif choice == '6':
            print("💖 Applying pink/purple hair...")
            setup.send_command("HCR.0.9")
            setup.send_command("HCG.0.4")
            setup.send_command("HCB.0.8")
            print("✅ Pink/purple hair applied!")
        elif choice == '7':
            print("✨ Applying bright violet eyes...")
            setup.send_command("EC.0.8")
            setup.send_command("ES.25000")
            print("✅ Bright violet eyes applied!")
        elif choice == '8':
            print("👗 Applying pop star outfit...")
            setup.send_command("OF.Pop Star")
            print("✅ Pop star outfit applied!")
        elif choice == '9':
            print("🎵 Applying DJ environment...")
            setup.send_command("LVL.DJ")
            print("✅ DJ environment applied!")
        elif choice == '0':
            print("💃 Triggering dance animation...")
            setup.send_command("ANIM.Dance")
            print("✅ Dance animation applied!")
        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    main() 