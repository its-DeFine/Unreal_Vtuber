import socket
import time
import random

HOST, PORT = "127.0.0.1", 7777

def send(cmd):
    """Send command to the TCP server"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((HOST, PORT))
            s.sendall((cmd + "\n").encode())
            print(f"✅ {cmd}")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def actress_1_emerald_maid():
    """
    🎭 Actress 1: "Emerald Elegance" - Classic Maid with Green Theme
    PRS.Fem + Maid Dress + Green Hair + Emerald Eyes
    """
    print("🎭 Setting up Actress 1: 'Emerald Elegance'")
    print("="*60)
    
    # Petite feminine preset
    send("PRS.Fem")
    time.sleep(0.2)
    
    # Classic maid dress
    send("OF.MaidDress")
    time.sleep(0.2)
    
    # Emerald green hair
    send("HCR.0.1")    # Low red
    send("HCG.0.9")    # High green
    send("HCB.0.2")    # Slight blue
    time.sleep(0.2)
    
    # Default elegant hair
    send("HS.Default")
    time.sleep(0.2)
    
    # Mesmerizing emerald eyes
    send("EC.0.33")    # Green hue
    saturation = round(random.uniform(28000.0, 45000.0), 1)
    send(f"ES.{saturation}")
    
    print(f"✨ Emerald Elegance Complete!")
    print(f"👗 Maid Dress | 🧍 PRS.Fem | 💚 Emerald Hair | 💇 Default Style | 👁️ Green Eyes ({saturation})")
    print("="*60)

def actress_2_ruby_popstar():
    """
    🎭 Actress 2: "Ruby Sensation" - Pop Star with Red Theme  
    PRS.Fem + Pop Star + Red Hair + Ruby Eyes
    """
    print("🎭 Setting up Actress 2: 'Ruby Sensation'")
    print("="*60)
    
    # Petite feminine preset
    send("PRS.Fem")
    time.sleep(0.2)
    
    # Pop star outfit
    send("OF.PopStar")
    time.sleep(0.2)
    
    # Ruby red hair
    send("HCR.0.95")   # High red
    send("HCG.0.1")    # Low green
    send("HCB.0.15")   # Slight blue for depth
    time.sleep(0.2)
    
    # Edgy buzz cut
    send("HS.Buzz")
    time.sleep(0.2)
    
    # Mesmerizing ruby eyes
    send("EC.0.0")     # Red hue
    saturation = round(random.uniform(30000.0, 50000.0), 1)
    send(f"ES.{saturation}")
    
    print(f"✨ Ruby Sensation Complete!")
    print(f"👗 Pop Star | 🧍 PRS.Fem | ❤️ Ruby Hair | 💇 Buzz Cut | 👁️ Red Eyes ({saturation})")
    print("="*60)

def actress_3_sapphire_kimono():
    """
    🎭 Actress 3: "Sapphire Serenity" - Kimono with Blue Theme
    PRS.Fem + Kimono + Blue Hair + Sapphire Eyes  
    """
    print("🎭 Setting up Actress 3: 'Sapphire Serenity'")
    print("="*60)
    
    # Petite feminine preset
    send("PRS.Fem")
    time.sleep(0.2)
    
    # Traditional kimono
    send("OF.Kimono")
    time.sleep(0.2)
    
    # Sapphire blue hair
    send("HCR.0.1")    # Low red
    send("HCG.0.3")    # Medium green
    send("HCB.0.95")   # High blue
    time.sleep(0.2)
    
    # Sophisticated crop
    send("HS.Crop")
    time.sleep(0.2)
    
    # Mesmerizing sapphire eyes
    send("EC.0.67")    # Blue hue
    saturation = round(random.uniform(25000.0, 42000.0), 1)
    send(f"ES.{saturation}")
    
    print(f"✨ Sapphire Serenity Complete!")
    print(f"👗 Kimono | 🧍 PRS.Fem | 💙 Sapphire Hair | 💇 Crop Style | 👁️ Blue Eyes ({saturation})")
    print("="*60)

def actress_4_amethyst_noir():
    """
    🎭 Actress 4: "Amethyst Noir" - Black Dress with Purple Theme
    PRS.Fem1 + Black Dress + Purple Hair + Amethyst Eyes
    """
    print("🎭 Setting up Actress 4: 'Amethyst Noir'")
    print("="*60)
    
    # Medium feminine preset
    send("PRS.Fem1")
    time.sleep(0.2)
    
    # Elegant black dress
    send("OF.BlackDress")
    time.sleep(0.2)
    
    # Amethyst purple hair
    send("HCR.0.7")    # High red
    send("HCG.0.2")    # Low green
    send("HCB.0.85")   # High blue (creates purple)
    time.sleep(0.2)
    
    # Classic default style
    send("HS.Default")
    time.sleep(0.2)
    
    # Mesmerizing amethyst eyes
    send("EC.0.75")    # Purple hue
    saturation = round(random.uniform(32000.0, 48000.0), 1)
    send(f"ES.{saturation}")
    
    print(f"✨ Amethyst Noir Complete!")
    print(f"👗 Black Dress | 🧍 PRS.Fem1 | 💜 Amethyst Hair | 💇 Default Style | 👁️ Purple Eyes ({saturation})")
    print("="*60)

def actress_5_golden_default():
    """
    🎭 Actress 5: "Golden Goddess" - Default with Gold Theme
    PRS.Fem1 + Default + Golden Hair + Amber Eyes
    """
    print("🎭 Setting up Actress 5: 'Golden Goddess'")
    print("="*60)
    
    # Medium feminine preset
    send("PRS.Fem1")
    time.sleep(0.2)
    
    # Classic default outfit
    send("OF.Default")
    time.sleep(0.2)
    
    # Golden blonde hair
    send("HCR.0.9")    # High red
    send("HCG.0.8")    # High green (creates gold)
    send("HCB.0.2")    # Low blue
    time.sleep(0.2)
    
    # Trendy buzz cut
    send("HS.Buzz")
    time.sleep(0.2)
    
    # Mesmerizing amber eyes
    send("EC.0.12")    # Orange/amber hue
    saturation = round(random.uniform(27000.0, 44000.0), 1)
    send(f"ES.{saturation}")
    
    print(f"✨ Golden Goddess Complete!")
    print(f"👗 Default | 🧍 PRS.Fem1 | 💛 Golden Hair | 💇 Buzz Cut | 👁️ Amber Eyes ({saturation})")
    print("="*60)

def actress_6_silver_starlet():
    """
    🎭 Actress 6: "Silver Starlet" - Pop Star with Silver Theme
    PRS.Fem1 + Pop Star + Silver Hair + Ice Blue Eyes
    """
    print("🎭 Setting up Actress 6: 'Silver Starlet'")
    print("="*60)
    
    # Medium feminine preset
    send("PRS.Fem1")
    time.sleep(0.2)
    
    # Pop star outfit
    send("OF.PopStar")
    time.sleep(0.2)
    
    # Silver platinum hair
    send("HCR.0.85")   # High red
    send("HCG.0.85")   # High green
    send("HCB.0.9")    # High blue (creates silver)
    time.sleep(0.2)
    
    # Chic crop style
    send("HS.Crop")
    time.sleep(0.2)
    
    # Mesmerizing ice blue eyes
    send("EC.0.55")    # Cyan/ice blue hue
    saturation = round(random.uniform(29000.0, 46000.0), 1)
    send(f"ES.{saturation}")
    
    print(f"✨ Silver Starlet Complete!")
    print(f"👗 Pop Star | 🧍 PRS.Fem1 | 🤍 Silver Hair | 💇 Crop Style | 👁️ Ice Blue Eyes ({saturation})")
    print("="*60)

def main():
    """Actress Gallery Selection Menu"""
    actresses = {
        "1": ("🟢 Emerald Elegance", "Petite maid with emerald green theme", actress_1_emerald_maid),
        "2": ("❤️ Ruby Sensation", "Petite pop star with ruby red theme", actress_2_ruby_popstar), 
        "3": ("💙 Sapphire Serenity", "Petite kimono with sapphire blue theme", actress_3_sapphire_kimono),
        "4": ("💜 Amethyst Noir", "Medium black dress with purple theme", actress_4_amethyst_noir),
        "5": ("💛 Golden Goddess", "Medium default with golden theme", actress_5_golden_default),
        "6": ("🤍 Silver Starlet", "Medium pop star with silver theme", actress_6_silver_starlet)
    }
    
    print("✨ FEMININE ACTRESS GALLERY ✨")
    print(f"📡 Target: {HOST}:{PORT}")
    print("="*70)
    print("🎭 6 Gorgeous Actress Characters Available:")
    print()
    
    # Display preset distribution
    print("📊 Preset Distribution:")
    print("   PRS.Fem (Petite):  Actresses 1, 2, 3")
    print("   PRS.Fem1 (Medium): Actresses 4, 5, 6")
    print()
    
    while True:
        print("Choose your actress:")
        for key, (name, desc, _) in actresses.items():
            print(f"  {key}. {name}")
            print(f"     └─ {desc}")
        print()
        print("  7. 🎬 Showcase All Actresses (auto-cycle)")
        print("  q. Quit")
        
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == 'q':
            print("🎭 Thank you for visiting the Actress Gallery! 👋")
            break
        elif choice in actresses:
            name, desc, func = actresses[choice]
            print(f"\n🎬 Casting: {name}")
            func()
            print("🎭 Actress ready for her scene! ✨")
        elif choice == '7':
            print("🎬 SHOWCASE MODE: All Actresses")
            print("="*70)
            for i, (key, (name, desc, func)) in enumerate(actresses.items(), 1):
                print(f"\n🎭 Now featuring: {name}")
                func()
                if i < len(actresses):  # Don't wait after the last actress
                    print("⏳ Next actress in 4 seconds...")
                    time.sleep(4)
            print("\n🎬 Showcase complete! All actresses have graced the stage! ✨")
        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    main() 