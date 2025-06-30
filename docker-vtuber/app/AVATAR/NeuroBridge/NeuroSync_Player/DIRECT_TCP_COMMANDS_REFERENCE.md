# 🔌 Direct TCP Commands Reference for Unreal Engine VTuber Control

**Complete reference for direct TCP communication with Unreal Engine on port 7777**

---

## 🎯 Overview

This document provides all available TCP commands for direct testing and control of the Unreal Engine VTuber application. These commands bypass the natural language processing layer and communicate directly with the game engine.

### 📡 **Connection Details**
- **Host:** `127.0.0.1` (localhost) or `host.docker.internal` (from Docker)
- **Port:** `7777`
- **Protocol:** TCP
- **Format:** Plain text commands ending with newline `\n`

---

## 🧪 **Direct TCP Testing Methods**

### **Method 1: Using `telnet`**
```bash
telnet 127.0.0.1 7777
# Then type commands directly, press Enter after each
LVL.Medieval
HCR.0.9
quit
```

### **Method 2: Using `nc` (netcat)**
```bash
# Single command
echo "LVL.Medieval" | nc 127.0.0.1 7777

# Multiple commands
(echo "HCR.0.9"; echo "HCG.0.1"; echo "HCB.0.1"; echo "LVL.Medieval") | nc 127.0.0.1 7777
```

### **Method 3: Using `printf` and `nc`**
```bash
# With explicit newlines
printf "LVL.Medieval\n" | nc 127.0.0.1 7777

# Multiple commands with timing
printf "HCR.0.9\nHCG.0.1\nHCB.0.1\nLVL.Medieval\n" | nc 127.0.0.1 7777
```

### **Method 4: From Docker Container**
```bash
# From inside the neurosync container
docker exec -it neurosync_s1 bash
echo "LVL.Medieval" | nc host.docker.internal 7777
```

---

## 📋 **Complete TCP Commands Reference**

### 🏰 **Level/Scene Commands**
```bash
LVL.Home          # Loads the main menu/cloud environment
LVL.Medieval      # Loads the medieval scene
LVL.DJ            # Loads the DJ scene
LVL.Lofi          # Loads the Lofi scene
LVL.Split         # Loads a dual split-screen level
LVL.Split3        # Loads a triple split-screen level
LVL.Split4        # Loads a quadruple split-screen level
```

**Test Example:**
```bash
echo "LVL.Medieval" | nc 127.0.0.1 7777
```

### 👤 **Character Preset Commands**
```bash
PRS.Masc          # Masculine, tall, and muscular preset
PRS.Fem           # Feminine, short, and underweight preset
PRS.Masc1         # Masculine, short, and underweight preset
PRS.Fem1          # Feminine, medium height, and average weight preset
```

**Test Example:**
```bash
echo "PRS.Fem" | nc 127.0.0.1 7777
```

### 👗 **Outfit Commands**
```bash
OF.Default        # Default outfit for any preset
OF.Maid Dress     # Maid dress (Fem or Fem1)
OF.Pop Star       # Pop star outfit (Fem or Fem1)
OF.Kimono         # Kimono outfit (Fem or Fem1)
OF.Black Dress    # Black dress outfit (Fem or Fem1)
```

**Test Example:**
```bash
echo "OF.Maid Dress" | nc 127.0.0.1 7777
```

### 💇 **Hair Style Commands**
```bash
HS.Default        # Default hairstyle
HS.Buzz           # Buzz cut hairstyle
HS.Crop           # Crop hairstyle
```

**Test Example:**
```bash
echo "HS.Crop" | nc 127.0.0.1 7777
```

### 🎨 **Hair Color Commands (RGB 0.0-1.0)**
```bash
HCR.0.9           # Red channel (0.0-1.0)
HCG.0.1           # Green channel (0.0-1.0)
HCB.0.1           # Blue channel (0.0-1.0)
```

**Common Hair Color Combinations:**
```bash
# Red Hair
printf "HCR.0.9\nHCG.0.1\nHCB.0.1\n" | nc 127.0.0.1 7777

# Blue Hair
printf "HCR.0.1\nHCG.0.3\nHCB.0.9\n" | nc 127.0.0.1 7777

# Yellow Hair
printf "HCR.0.9\nHCG.0.9\nHCB.0.2\n" | nc 127.0.0.1 7777

# Blonde Hair
printf "HCR.0.9\nHCG.0.8\nHCB.0.3\n" | nc 127.0.0.1 7777

# Purple Hair
printf "HCR.0.7\nHCG.0.2\nHCB.0.9\n" | nc 127.0.0.1 7777

# Green Hair
printf "HCR.0.2\nHCG.0.8\nHCB.0.3\n" | nc 127.0.0.1 7777

# Black Hair
printf "HCR.0.1\nHCG.0.1\nHCB.0.1\n" | nc 127.0.0.1 7777

# White Hair
printf "HCR.0.9\nHCG.0.9\nHCB.0.9\n" | nc 127.0.0.1 7777
```

### 🎨 **Skin Color Commands**
```bash
SKC.0.2           # Very light skin (minimum realistic)
SKC.0.43          # Light skin
SKC.0.7           # Medium skin (default)
SKC.0.9           # Tan skin
SKC.1.2           # Dark skin (maximum realistic)
```

**Test Example:**
```bash
echo "SKC.0.43" | nc 127.0.0.1 7777
```

### 👁️ **Eye Color Commands**
```bash
EC.0.0            # Red eyes (hue)
EC.0.1            # Brown eyes
EC.0.3            # Green eyes
EC.0.6            # Blue eyes
EC.0.8            # Purple eyes
ES.15000          # Eye saturation (use values in 10,000s)
```

**Test Example:**
```bash
printf "EC.0.6\nES.15000\n" | nc 127.0.0.1 7777
```

### 🦴 **Bone Size Commands (Body Proportions)**
```bash
BNH.1.0           # Head bone size (default 1.0)
BNC.1.0           # Chest bone size
BNHD.1.0          # Hands bone size
BNA.1.0           # Abdomen bone size
BNAR.1.0          # Arms bone size
BNL.1.0           # Legs bone size
BNF.1.0           # Feet bone size
```

**Test Examples:**
```bash
echo "BNH.1.3" | nc 127.0.0.1 7777    # Larger head
echo "BNC.0.7" | nc 127.0.0.1 7777    # Smaller chest
echo "BNL.1.2" | nc 127.0.0.1 7777    # Longer legs
```

### 🎭 **Facial Morph Target Commands (0.0-1.0)**

#### **👂 Head & Neck**
```bash
MTHT.0.5          # Head Top: Crown height/bulge
MTHS.0.5          # Head Sides: Overall head width
MTHB.0.5          # Head Back: Rear skull protrusion
MTHBW.0.5         # Head Back Width: Side width at back
MTNFT.0.5         # Neck Front Top: Junction near clavicle
MTNF.0.5          # Neck Front: Forward throat area
MTNS.0.5          # Neck Sides: Width of neck sides
MTNBH.0.5         # Neck Back High: Upper rear neck
MTNBL.0.5         # Neck Back Low: Lower rear neck
MTND.0.5          # Neck Definition: Muscular definition
```

#### **👂 Ears** 
```bash
MTEW.0.5          # Ear Width
MTEP.0.5          # Ear Point: Pointiness of tips
MTEL.0.5          # Earlobe volume
MTERS.0.3         # Ear Size (0.0-0.5 range only!)
```

#### **🧠 Forehead & Temples**
```bash
MTFHC.0.5         # Forehead Center: Depth/flatness
MTFHCR.0.5        # Forehead Curvature: Side curve
MTFHS.0.5         # Forehead Sides: Lateral shaping
MTT.0.5           # Temples: Side skull hollow/bulge
```

#### **🤨 Eyebrows**
```bash
MTEBH.0.5         # Eyebrow Height
MTEBW.0.5         # Eyebrow Width
MTEBA.0.5         # Eyebrow Arch
```

#### **👁️ Eyes**
```bash
MTEC.0.5          # Eye Cavity: Socket depth
MTEYW.0.8         # Eye Width (commonly used for "bigger eyes")
MTEB.0.5          # Eye Bags
MTEYH.0.5         # Eye Height
```

#### **👃 Nose**
```bash
MTNB.0.5          # Nose Base: Lower width/flare
MTNL.0.5          # Nose Length
MTNW.0.8          # Nose Width (bridge/tip)
MTN.0.5           # Nostril size/flare
MTS.0.5           # Septum: Vertical structure
MTNCR.0.5         # Nose Crookedness: Asymmetry
```

#### **😊 Cheeks**
```bash
MTCB.0.5          # Cheek Bone: Zygomatic height/width
MTCT.0.5          # Cheek Tissue: Soft tissue volume
MTCD.0.5          # Cheek Definition: Angular vs soft
```

#### **💋 Lips**
```bash
MTLO.0.5          # Lips Outer: Pout/forward volume
MTLW.0.5          # Lips Width
MTLOV.0.5         # Lips Overlap: Top over bottom
MTLCV.0.5         # Lips Curve: Smile/frown arc
MTLD.0.5          # Lips Depth: Thickness
MTLU.0.5          # Lips Underlap: Bottom under top
```

#### **🗿 Chin & Jaw**
```bash
MTCL.0.5          # Chin Length
MTCP.0.5          # Chin Point: Round vs sharp
MTCW.0.7          # Chin Width (commonly used)
MTJL.0.5          # Jaw Lower: Droop/sharpness
MTJH.0.5          # Jaw Higher: Raises/lowers jawline
```

#### **👹 Fantasy Features**
```bash
MTH.0.3           # Horns: Fantasy horn morph (0.0-0.5 range only!)
```

**Test Examples:**
```bash
echo "MTEYW.0.8" | nc 127.0.0.1 7777    # Bigger eyes
echo "MTNW.0.3" | nc 127.0.0.1 7777     # Narrower nose
echo "MTCW.0.8" | nc 127.0.0.1 7777     # Wider chin
```

### 🎬 **Animation Commands**
```bash
ANIM.Dance        # Plays dance animation
```

**Test Example:**
```bash
echo "ANIM.Dance" | nc 127.0.0.1 7777
```

### 🌅 **Environment Commands**
```bash
CLDS.0.5          # Cloud speed (0.0 = static, 1.0 = fast)
CLDO.0.5          # Cloud opacity (0.0 = transparent, 1.0 = solid)
SNH.0.8           # Sun height (0.1 = night, 0.8 = day)
STRB.0.9          # Star brightness (0.0 = none, 1.0 = bright)
```

**Environment Combinations:**
```bash
# Day Time
printf "SNH.0.8\nSTRB.0.3\n" | nc 127.0.0.1 7777

# Night Time
printf "SNH.0.1\nSTRB.0.9\n" | nc 127.0.0.1 7777

# Sunset
printf "SNH.0.4\nSTRB.0.6\n" | nc 127.0.0.1 7777

# Fast Clouds
printf "CLDS.0.8\nCLDO.0.7\n" | nc 127.0.0.1 7777
```

### 💾 **Save/Load Commands**
```bash
NAME.AgentName    # Sets character name (required before saving)
BTN.Save          # Saves character settings
Load0.            # Loads save slot 0
Load1.            # Loads save slot 1
Load2.            # Loads save slot 2
Load3.            # Loads save slot 3
```

**Test Example:**
```bash
printf "NAME.TestCharacter\nBTN.Save\n" | nc 127.0.0.1 7777
```

### 🖥️ **Menu/System Commands**
```bash
MENU.             # Opens menu (for debugging)
CMENU.            # Closes menu
QUIT.             # Shuts down the game
```

**Test Example:**
```bash
echo "MENU." | nc 127.0.0.1 7777
```

---

## 🧪 **Complete Test Scenarios**

### **Scenario 1: Medieval Maid Setup**
```bash
(
echo "PRS.Fem"
echo "OF.Maid Dress"
echo "HS.Crop"
echo "HCR.0.9"
echo "HCG.0.1"
echo "HCB.0.1"
echo "MTEYW.0.8"
echo "SKC.0.5"
echo "LVL.Medieval"
) | nc 127.0.0.1 7777
```

### **Scenario 2: DJ Party Setup**
```bash
(
echo "PRS.Fem"
echo "OF.Pop Star"
echo "HS.Default"
echo "HCR.0.1"
echo "HCG.0.3"
echo "HCB.0.9"
echo "LVL.DJ"
echo "SNH.0.2"
echo "STRB.0.9"
echo "ANIM.Dance"
) | nc 127.0.0.1 7777
```

### **Scenario 3: Night Scene Setup**
```bash
(
echo "LVL.Lofi"
echo "OF.Kimono"
echo "HCR.0.7"
echo "HCG.0.2"
echo "HCB.0.9"
echo "SNH.0.1"
echo "STRB.0.9"
echo "CLDS.0.3"
echo "CLDO.0.8"
) | nc 127.0.0.1 7777
```

### **Scenario 4: Custom Character Creation**
```bash
(
echo "PRS.Fem1"
echo "OF.Black Dress"
echo "HS.Buzz"
echo "HCR.0.9"
echo "HCG.0.8"
echo "HCB.0.3"
echo "MTEYW.0.6"
echo "MTNW.0.4"
echo "MTCW.0.7"
echo "SKC.0.7"
echo "EC.0.3"
echo "ES.15000"
echo "LVL.Home"
) | nc 127.0.0.1 7777
```

### **Scenario 5: Reset to Default**
```bash
(
echo "PRS.Fem"
echo "OF.Default"
echo "HS.Default"
echo "HCR.0.9"
echo "HCG.0.8"
echo "HCB.0.3"
echo "SKC.0.7"
echo "EC.0.3"
echo "ES.15000"
echo "LVL.Home"
echo "SNH.0.6"
echo "STRB.0.5"
) | nc 127.0.0.1 7777
```

---

## 🔍 **Testing & Debugging Commands**

### **Connection Test**
```bash
# Test if TCP port is open
nc -zv 127.0.0.1 7777

# Test with timeout
timeout 5 nc 127.0.0.1 7777 < /dev/null
```

### **Debug Menu Commands**
```bash
# Open debug menu
echo "MENU." | nc 127.0.0.1 7777

# Close debug menu  
echo "CMENU." | nc 127.0.0.1 7777
```

### **Graceful Testing**
```bash
# Open menu first (for safety)
echo "MENU." | nc 127.0.0.1 7777
sleep 1

# Run your commands
echo "LVL.Medieval" | nc 127.0.0.1 7777
sleep 1

# Close menu
echo "CMENU." | nc 127.0.0.1 7777
```

---

## ⚠️ **Important Value Ranges & Constraints**

### **Critical Constraints:**
- **MTERS** (Ear Size): `0.0 - 0.5` only (higher values crash)
- **MTH** (Horns): `0.0 - 0.5` only (higher values crash)
- **SKC** (Skin Color): `0.2 - 1.2` for realistic tones
- **ES** (Eye Saturation): Use values in 10,000s (e.g., 15000)
- **All RGB values**: `0.0 - 1.0` range
- **Most morph targets**: `0.0 - 1.0` range

### **Safe Testing Values:**
- **Hair Colors**: Use pre-defined combinations above
- **Bone Sizes**: `0.5 - 1.5` range is safe
- **Environment**: All values `0.0 - 1.0` are safe
- **Morph Targets**: `0.0 - 1.0` except for constrained ones

---

## 🚨 **Troubleshooting**

### **Connection Issues:**
```bash
# Check if Unreal Engine is running
ps aux | grep -i unreal

# Check if port 7777 is listening
netstat -an | grep 7777
ss -tulpn | grep 7777

# Test from different locations
echo "MENU." | nc 127.0.0.1 7777          # Local
echo "MENU." | nc host.docker.internal 7777  # Docker
```

### **Command Issues:**
```bash
# Commands must end with newline
printf "LVL.Medieval\n" | nc 127.0.0.1 7777

# Some commands need exact spacing
echo "OF.Maid Dress" | nc 127.0.0.1 7777  # Correct
echo "OF.MaidDress" | nc 127.0.0.1 7777   # Wrong
```

### **Game Stability:**
```bash
# If game becomes unresponsive
echo "MENU." | nc 127.0.0.1 7777
sleep 2
echo "CMENU." | nc 127.0.0.1 7777

# Emergency reset
echo "QUIT." | nc 127.0.0.1 7777
```

---

## 📝 **Quick Reference Card**

**Most Used Commands:**
```bash
# Character
PRS.Fem, PRS.Masc                    # Presets
OF.Default, OF.Maid Dress            # Outfits
HS.Default, HS.Crop                  # Hair

# Colors  
HCR.0.9 HCG.0.1 HCB.0.1             # Red hair
SKC.0.7                              # Skin color
EC.0.6 ES.15000                      # Blue eyes

# Scenes
LVL.Home, LVL.Medieval, LVL.DJ       # Environments
SNH.0.1 (night), SNH.0.8 (day)      # Lighting

# Features
MTEYW.0.8                            # Bigger eyes
MTNW.0.6                             # Nose width
MTCW.0.7                             # Chin width

# Animation
ANIM.Dance                           # Dance

# System
MENU., CMENU., QUIT.                 # Menu control
```

**Connection:**
```bash
Host: 127.0.0.1:7777
Test: echo "MENU." | nc 127.0.0.1 7777
```

Use this reference for comprehensive TCP testing of all VTuber features! 🎮✨ 