# 🎮 Simple TCP Commands List for Windows Testing

**Direct TCP commands for Unreal Engine VTuber control on port 7777**

---

## 🔌 **Connection Info**
- **Port:** `7777`
- **Host:** `127.0.0.1` (if running locally on Windows)
- **Format:** Each command on a new line

---

## 🖥️ **Windows Testing Methods**

### **Method 1: Using Windows Telnet**
```cmd
telnet 127.0.0.1 7777
```
Then type commands one by one and press Enter.

### **Method 2: Using PowerShell**
```powershell
$tcpClient = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 7777)
$stream = $tcpClient.GetStream()
$writer = New-Object System.IO.StreamWriter($stream)
$writer.WriteLine("LVL.Medieval")
$writer.Flush()
$writer.Close()
$tcpClient.Close()
```

---

## 📋 **All Available TCP Commands**

### 🏰 **Level/Scene Commands**
```
LVL.Home
LVL.Medieval
LVL.DJ
LVL.Lofi
LVL.Split
LVL.Split3
LVL.Split4
```

### 👤 **Character Presets**
```
PRS.Masc
PRS.Fem
PRS.Masc1
PRS.Fem1
```

### 👗 **Outfits**
```
OF.Default
OF.Maid Dress
OF.Pop Star
OF.Kimono
OF.Black Dress
```

### 💇 **Hair Styles**
```
HS.Default
HS.Buzz
HS.Crop
```

### 🎨 **Hair Colors (RGB 0.0-1.0)**
**Red Hair:**
```
HCR.0.9
HCG.0.1
HCB.0.1
```

**Blue Hair:**
```
HCR.0.1
HCG.0.3
HCB.0.9
```

**Yellow Hair:**
```
HCR.0.9
HCG.0.9
HCB.0.2
```

**Blonde Hair:**
```
HCR.0.9
HCG.0.8
HCB.0.3
```

**Purple Hair:**
```
HCR.0.7
HCG.0.2
HCB.0.9
```

**Green Hair:**
```
HCR.0.2
HCG.0.8
HCB.0.3
```

**Black Hair:**
```
HCR.0.1
HCG.0.1
HCB.0.1
```

**White Hair:**
```
HCR.0.9
HCG.0.9
HCB.0.9
```

### 🎨 **Skin Colors**
```
SKC.0.2     (Very light)
SKC.0.43    (Light)
SKC.0.7     (Medium - default)
SKC.0.9     (Tan)
SKC.1.2     (Dark)
```

### 👁️ **Eye Colors**
**Blue Eyes:**
```
EC.0.6
ES.15000
```

**Green Eyes:**
```
EC.0.3
ES.15000
```

**Brown Eyes:**
```
EC.0.1
ES.15000
```

**Purple Eyes:**
```
EC.0.8
ES.15000
```

**Red Eyes:**
```
EC.0.0
ES.15000
```

### 🦴 **Body Proportions**
```
BNH.1.0     (Head size - default)
BNC.1.0     (Chest size)
BNHD.1.0    (Hands size)
BNA.1.0     (Abdomen size)
BNAR.1.0    (Arms size)
BNL.1.0     (Legs size)
BNF.1.0     (Feet size)
```

**Examples:**
```
BNH.1.3     (Larger head)
BNC.0.7     (Smaller chest)
BNL.1.2     (Longer legs)
```

### 🎭 **Facial Features (0.0-1.0)**

**Eyes:**
```
MTEYW.0.8   (Bigger eyes - commonly used)
MTEC.0.5    (Eye cavity depth)
MTEB.0.5    (Eye bags)
MTEYH.0.5   (Eye height)
```

**Nose:**
```
MTNW.0.8    (Nose width - commonly used)
MTNB.0.5    (Nose base)
MTNL.0.5    (Nose length)
MTN.0.5     (Nostril size)
MTS.0.5     (Septum)
MTNCR.0.5   (Nose crookedness)
```

**Chin & Jaw:**
```
MTCW.0.7    (Chin width - commonly used)
MTCL.0.5    (Chin length)
MTCP.0.5    (Chin point)
MTJL.0.5    (Jaw lower)
MTJH.0.5    (Jaw higher)
```

**Lips:**
```
MTLO.0.5    (Lips outer)
MTLW.0.5    (Lips width)
MTLOV.0.5   (Lips overlap)
MTLCV.0.5   (Lips curve)
MTLD.0.5    (Lips depth)
MTLU.0.5    (Lips underlap)
```

**Cheeks:**
```
MTCB.0.5    (Cheek bone)
MTCT.0.5    (Cheek tissue)
MTCD.0.5    (Cheek definition)
```

**Eyebrows:**
```
MTEBH.0.5   (Eyebrow height)
MTEBW.0.5   (Eyebrow width)
MTEBA.0.5   (Eyebrow arch)
```

**Head & Neck:**
```
MTHT.0.5    (Head top)
MTHS.0.5    (Head sides)
MTHB.0.5    (Head back)
MTHBW.0.5   (Head back width)
MTNFT.0.5   (Neck front top)
MTNF.0.5    (Neck front)
MTNS.0.5    (Neck sides)
MTNBH.0.5   (Neck back high)
MTNBL.0.5   (Neck back low)
MTND.0.5    (Neck definition)
```

**Forehead & Temples:**
```
MTFHC.0.5   (Forehead center)
MTFHCR.0.5  (Forehead curvature)
MTFHS.0.5   (Forehead sides)
MTT.0.5     (Temples)
```

**Ears:**
```
MTEW.0.5    (Ear width)
MTEP.0.5    (Ear point)
MTEL.0.5    (Earlobe)
MTERS.0.3   (Ear size - MAX 0.5!)
```

**Fantasy:**
```
MTH.0.3     (Horns - MAX 0.5!)
```

### 🎬 **Animations**
```
ANIM.Dance
```

### 🌅 **Environment**
**Day/Night:**
```
SNH.0.8     (Day time)
SNH.0.4     (Sunset)
SNH.0.1     (Night time)
```

**Stars:**
```
STRB.0.9    (Bright stars)
STRB.0.5    (Medium stars)
STRB.0.0    (No stars)
```

**Clouds:**
```
CLDS.0.8    (Fast clouds)
CLDS.0.2    (Slow clouds)
CLDS.0.0    (Static clouds)
CLDO.0.9    (Dense clouds)
CLDO.0.3    (Light clouds)
```

### 💾 **Save/Load**
```
NAME.TestCharacter
BTN.Save
Load0.
Load1.
Load2.
Load3.
```

### 🖥️ **System Commands**
```
MENU.       (Open menu)
CMENU.      (Close menu)
QUIT.       (Quit game)
```

---

## 🧪 **Quick Test Sequences**

### **Test 1: Basic Character**
```
PRS.Fem
OF.Default
HS.Default
LVL.Home
```

### **Test 2: Medieval Maid**
```
PRS.Fem
OF.Maid Dress
HS.Crop
HCR.0.9
HCG.0.1
HCB.0.1
MTEYW.0.8
LVL.Medieval
```

### **Test 3: DJ Party**
```
PRS.Fem
OF.Pop Star
HCR.0.1
HCG.0.3
HCB.0.9
LVL.DJ
SNH.0.2
STRB.0.9
ANIM.Dance
```

### **Test 4: Night Scene**
```
LVL.Lofi
OF.Kimono
HCR.0.7
HCG.0.2
HCB.0.9
SNH.0.1
STRB.0.9
```

---

## ⚠️ **Important Notes**

- Each command must be on its own line
- Use exact spacing (e.g., "OF.Maid Dress" not "OF.MaidDress")
- **MTERS** (ear size) and **MTH** (horns): Maximum 0.5 or game crashes!
- **SKC** (skin): Keep between 0.2-1.2 for realistic tones
- **ES** (eye saturation): Use values like 15000 (in thousands)
- RGB values: 0.0 to 1.0 range

---

## 🔧 **Windows Telnet Setup**

If telnet isn't available:
```cmd
dism /online /Enable-Feature /FeatureName:TelnetClient
```

Then use:
```cmd
telnet 127.0.0.1 7777
```

Type commands one by one, press Enter after each.

---

**Copy and paste these commands directly into your TCP client!** 🎮 