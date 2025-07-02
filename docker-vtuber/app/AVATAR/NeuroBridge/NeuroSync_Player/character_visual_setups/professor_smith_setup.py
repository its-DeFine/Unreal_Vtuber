#!/usr/bin/env python3
"""
Professor Smith Visual Setup Script
Automatically configures the visual appearance for the Professor Smith character
- Blue hair and blue eyes for a distinguished academic look
- Professional feminine preset
- Academic/educational environment
"""

import socket
import time
import logging
import sys
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

class ProfessorSmithVisualSetup:
    """Visual setup controller for Professor Smith character"""
    
    def __init__(self):
        self.character_name = "Professor Smith"
        self.character_id = "demo_teacher"
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
    
    def apply_basic_professor_setup(self) -> bool:
        """Apply Professor Smith's signature academic look"""
        print(f"🎓 Applying {self.character_name} Visual Setup...")
        print("=" * 60)
        
        success_count = 0
        total_commands = 0
        
        # 1. Set Feminine Preset for Professional Look
        print("👩‍🏫 Setting professional feminine preset...")
        if self.send_command("PRS.Fem"):
            success_count += 1
        total_commands += 1
        time.sleep(0.5)
        
        # 2. Apply Distinguished Blue Hair
        print("💙 Setting distinguished blue hair color...")
        commands = [
            ("HCR.0.2", "Low red for blue hair"),      # Minimal red
            ("HCG.0.3", "Moderate green for depth"),   # Some green for depth  
            ("HCB.0.9", "High blue for vibrant color") # Strong blue
        ]
        
        for cmd, desc in commands:
            print(f"  {desc}...")
            if self.send_command(cmd):
                success_count += 1
            total_commands += 1
            time.sleep(0.3)
        
        # 3. Apply Intelligent Blue Eyes
        print("👁️ Setting intelligent blue eyes...")
        eye_commands = [
            ("EC.0.6", "Blue hue for eyes"),           # Blue eye color
            ("ES.15000", "Moderate saturation")        # Professional saturation
        ]
        
        for cmd, desc in eye_commands:
            print(f"  {desc}...")
            if self.send_command(cmd):
                success_count += 1
            total_commands += 1
            time.sleep(0.3)
        
        # 4. Apply Professional Outfit
        print("📚 Setting professional academic outfit...")
        if self.send_command("OF.Kimono"):  # Elegant and professional
            success_count += 1
        total_commands += 1
        time.sleep(0.5)
        
        # 5. Set Academic Environment
        print("🏛️ Setting academic environment...")
        if self.send_command("LVL.Medieval"):  # Classical academic setting
            success_count += 1
        total_commands += 1
        time.sleep(0.5)
        
        print("\n" + "=" * 60)
        print(f"🎓 PROFESSOR SMITH SETUP COMPLETE! ✨")
        print(f"👩‍🏫 Character: {self.character_name}")
        print("💙 Hair: Distinguished blue")
        print("👁️ Eyes: Intelligent blue")
        print("📚 Outfit: Professional Kimono")
        print("🏛️ Environment: Academic Medieval")
        print(f"📊 Success Rate: {success_count}/{total_commands} commands")
        print("=" * 60)
        
        return success_count == total_commands
    
    def apply_enhanced_professor_features(self) -> bool:
        """Apply enhanced facial features for a wise, approachable professor look"""
        print("\n🌟 Applying Enhanced Professor Features...")
        print("=" * 50)
        
        success_count = 0
        total_commands = 0
        
        # Enhanced facial features for wisdom and approachability
        enhanced_features = [
            ("MTEYW.0.1", "Slightly wider eyes for wisdom"),
            ("MTEYH.0.05", "Gentle eye height adjustment"),
            ("MTEBW.0.1", "Defined eyebrows for intelligence"),
            ("MTEBA.0.15", "Slightly arched eyebrows"),
            ("MTLO.0.05", "Gentle lip enhancement"),
            ("MTCB.0.1", "Subtle cheekbone definition"),
            ("MTNW.0.0", "Natural nose width"),
            ("MTCW.0.05", "Slight chin refinement")
        ]
        
        for cmd, desc in enhanced_features:
            print(f"  {desc}...")
            if self.send_command(cmd):
                success_count += 1
            total_commands += 1
            time.sleep(0.2)
        
        print(f"🌟 Enhanced features applied! ({success_count}/{total_commands})")
        return success_count == total_commands
    
    def quick_professor_test(self) -> bool:
        """Quick test to apply just the essential Professor Smith look"""
        print("⚡ Quick Professor Smith Test...")
        
        essential_commands = [
            "PRS.Fem",
            "HCR.0.2", "HCG.0.3", "HCB.0.9",  # Blue hair
            "EC.0.6", "ES.15000",               # Blue eyes
            "OF.Kimono"                         # Professional outfit
        ]
        
        success = True
        for cmd in essential_commands:
            if not self.send_command(cmd):
                success = False
            time.sleep(0.2)
        
        print(f"⚡ Quick test {'✅ Complete' if success else '❌ Failed'}!")
        return success

def apply_professor_smith_appearance(enhanced: bool = True) -> bool:
    """
    Main function to apply Professor Smith's visual appearance
    
    Args:
        enhanced: Whether to apply enhanced facial features
    
    Returns:
        True if setup completed successfully
    """
    setup = ProfessorSmithVisualSetup()
    
    # Apply basic setup
    basic_success = setup.apply_basic_professor_setup()
    
    if not basic_success:
        logger.warning("⚠️ Basic setup had some failures")
    
    # Apply enhanced features if requested
    enhanced_success = True
    if enhanced:
        enhanced_success = setup.apply_enhanced_professor_features()
    
    overall_success = basic_success and enhanced_success
    
    if overall_success:
        logger.info("✅ Professor Smith visual setup completed successfully!")
    else:
        logger.warning("⚠️ Professor Smith visual setup completed with some issues")
    
    return overall_success

def main():
    """Interactive menu for Professor Smith visual setup"""
    print("🎓 PROFESSOR SMITH VISUAL SETUP TOOL 🎓")
    print(f"📡 Target: {HOST}:{PORT}")
    print("=" * 60)
    
    setup = ProfessorSmithVisualSetup()
    
    while True:
        print(f"\n{setup.character_name} Setup Options:")
        print("  1. 🎓 Apply Complete Professor Setup")
        print("  2. 🌟 Apply Enhanced Professor Setup")
        print("  3. ⚡ Quick Professor Test")
        print("  4. 💙 Hair Only (Blue)")
        print("  5. 👁️ Eyes Only (Blue)")
        print("  6. 📚 Outfit Only (Professional)")
        print("  7. 🏛️ Environment Only (Academic)")
        print("  q. Quit")
        
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == 'q':
            print("👋 Goodbye!")
            break
        elif choice == '1':
            setup.apply_basic_professor_setup()
        elif choice == '2':
            setup.apply_basic_professor_setup()
            setup.apply_enhanced_professor_features()
        elif choice == '3':
            setup.quick_professor_test()
        elif choice == '4':
            print("💙 Applying blue hair...")
            setup.send_command("HCR.0.2")
            setup.send_command("HCG.0.3")
            setup.send_command("HCB.0.9")
            print("✅ Blue hair applied!")
        elif choice == '5':
            print("👁️ Applying blue eyes...")
            setup.send_command("EC.0.6")
            setup.send_command("ES.15000")
            print("✅ Blue eyes applied!")
        elif choice == '6':
            print("📚 Applying professional outfit...")
            setup.send_command("OF.Kimono")
            print("✅ Professional outfit applied!")
        elif choice == '7':
            print("🏛️ Applying academic environment...")
            setup.send_command("LVL.Medieval")
            print("✅ Academic environment applied!")
        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    main() 