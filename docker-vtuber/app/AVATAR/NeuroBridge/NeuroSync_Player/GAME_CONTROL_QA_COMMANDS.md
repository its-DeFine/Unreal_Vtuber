# Game Control QA Testing Commands

This document provides all available game control commands for direct testing via the `/game_control` API endpoint.

## 🎮 **Direct Game Control Endpoint**

**Base URL:** `POST http://localhost:5001/game_control`

## 📋 **Complete Command Reference**

### **LEVELS/SCENES**
```bash
# Cloud Environment (Default)
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["LVL.Home"]}'

# Medieval Castle Scene
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["LVL.Medieval"]}'

# DJ/Party Environment
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["LVL.DJ"]}'

# Cozy Lofi Scene
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["LVL.Lofi"]}'

# Split Screen Variants
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["LVL.Split"]}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["LVL.Split3"]}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["LVL.Split4"]}'
```

### **CHARACTER PRESETS**
```bash
# Feminine Build
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["PRS.Fem"]}'

# Masculine Build
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["PRS.Masc"]}'

# Feminine Variant
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["PRS.Fem1"]}'

# Masculine Variant
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["PRS.Masc1"]}'
```

### **OUTFITS**
```bash
# Default Outfit
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["OF.Default"]}'

# Maid Dress
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["OF.Maid Dress"]}'

# Pop Star Outfit
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["OF.Pop Star"]}'

# Kimono
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["OF.Kimono"]}'

# Black Dress
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["OF.Black Dress"]}'
```

### **HAIR STYLES**
```bash
# Default Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HS.Default"]}'

# Buzz Cut
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HS.Buzz"]}'

# Crop Style
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HS.Crop"]}'
```

### **HAIR COLORS (RGB 0.0-1.0)**
```bash
# Red Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HCR.0.9", "HCG.0.1", "HCB.0.1"]}'

# Blonde Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HCR.0.9", "HCG.0.8", "HCB.0.3"]}'

# Blue Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HCR.0.1", "HCG.0.3", "HCB.0.9"]}'

# Yellow Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HCR.0.9", "HCG.0.9", "HCB.0.2"]}'

# Purple Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HCR.0.7", "HCG.0.2", "HCB.0.9"]}'

# Green Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HCR.0.2", "HCG.0.8", "HCB.0.3"]}'

# Black Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HCR.0.1", "HCG.0.1", "HCB.0.1"]}'

# White Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["HCR.0.9", "HCG.0.9", "HCB.0.9"]}'
```

### **SKIN COLOR**
```bash
# Very Light Skin
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["SKC.0.3"]}'

# Light Skin
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["SKC.0.5"]}'

# Medium Skin (Default)
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["SKC.0.7"]}'

# Tan Skin
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["SKC.0.9"]}'

# Dark Skin
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["SKC.1.1"]}'
```

### **EYE COLOR**
```bash
# Blue Eyes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["EC.0.6", "ES.15000"]}'

# Green Eyes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["EC.0.3", "ES.15000"]}'

# Brown Eyes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["EC.0.1", "ES.15000"]}'

# Purple Eyes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["EC.0.8", "ES.15000"]}'

# Red Eyes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["EC.0.0", "ES.15000"]}'
```

### **BONE SCALING (Body Proportions)**
```bash
# Larger Head
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["BNH.1.3"]}'

# Smaller Head
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["BNH.0.8"]}'

# Larger Chest
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["BNC.1.2"]}'

# Smaller Chest
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["BNC.0.7"]}'

# Larger Arms
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["BNAR.1.3"]}'

# Longer Legs
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["BNL.1.2"]}'

# Larger Feet
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["BNF.1.2"]}'
```

### **FACIAL MORPH TARGETS (0.0-1.0)**
```bash
# Wider Nose
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["MTNW.0.8"]}'

# Narrower Nose
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["MTNW.0.3"]}'

# Wider Chin
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["MTCW.0.8"]}'

# Narrower Chin
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["MTCW.0.3"]}'

# Larger Eyes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["MTEYW.0.8"]}'

# Smaller Eyes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["MTEYW.0.3"]}'

# Taller Head
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["MTHT.0.7"]}'

# Wider Head Sides
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["MTHS.0.7"]}'
```

### **ANIMATIONS**
```bash
# Dance Animation
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["ANIM.Dance"]}'
```

### **ENVIRONMENT LIGHTING**
```bash
# Day Time (High Sun)
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["SNH.0.8"]}'

# Sunset
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["SNH.0.4"]}'

# Night Time
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["SNH.0.1"]}'

# Bright Stars
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["STRB.0.9"]}'

# Dim Stars
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["STRB.0.3"]}'

# No Stars
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["STRB.0.0"]}'
```

### **CLOUD SETTINGS**
```bash
# Fast Clouds
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["CLDS.0.8"]}'

# Slow Clouds
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["CLDS.0.2"]}'

# Static Clouds
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["CLDS.0.0"]}'

# Dense Clouds
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["CLDO.0.9"]}'

# Light Clouds
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["CLDO.0.3"]}'
```

## 🧪 **QA Test Scenarios**

### **Scenario 1: Complete Character Makeover**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "commands": [
    "PRS.Fem",
    "OF.Maid Dress", 
    "HS.Crop",
    "HCR.0.9", "HCG.0.1", "HCB.0.1",
    "EC.0.6", "ES.15000",
    "SKC.0.5",
    "LVL.Medieval"
  ]
}'
```

### **Scenario 2: DJ Party Setup**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "commands": [
    "LVL.DJ",
    "OF.Pop Star",
    "HCR.0.1", "HCG.0.3", "HCB.0.9",
    "ANIM.Dance",
    "SNH.0.2",
    "STRB.0.9"
  ]
}'
```

### **Scenario 3: Cozy Evening Scene**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "commands": [
    "LVL.Lofi",
    "OF.Kimono",
    "HCR.0.7", "HCG.0.2", "HCB.0.9",
    "SNH.0.2",
    "STRB.0.8",
    "CLDS.0.3"
  ]
}'
```

### **Scenario 4: Fantasy Adventure Look**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "commands": [
    "LVL.Medieval",
    "PRS.Fem",
    "OF.Black Dress",
    "HS.Default",
    "HCR.0.9", "HCG.0.8", "HCB.0.3",
    "EC.0.3", "ES.15000",
    "SNH.0.6"
  ]
}'
```

### **Scenario 5: Natural Language Test**
```bash
# Test natural language processing
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "prompt": "Change to medieval scene with red hair, feminine character, and maid dress"
}'

curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "prompt": "Blue hair, DJ environment, pop star outfit, dance animation"
}'

curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "prompt": "Night time with bright stars and slow clouds"
}'
```

## 🔍 **Testing Commands**

### **Health Check**
```bash
curl -s http://localhost:5001/health | jq .
```

### **Check Last Game Control Result**
```bash
# (Game control responses include command success count)
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"commands": ["LVL.Home"]}' | jq .
```

### **Reset to Default**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "commands": [
    "PRS.Fem",
    "OF.Default", 
    "HS.Default",
    "HCR.0.9", "HCG.0.8", "HCB.0.3",
    "EC.0.3", "ES.15000",
    "SKC.0.7",
    "LVL.Home",
    "SNH.0.6",
    "STRB.0.5"
  ]
}'
```

## 📝 **Response Format**

All commands return JSON with success information:
```json
{
  "commands_sent": 3,
  "commands_successful": 3,
  "tcp_connection": "healthy",
  "message": "Commands executed successfully"
}
```

## ⚠️ **Important Notes**

1. **RGB Values**: Hair colors use RGB values from 0.0 to 1.0
2. **Bone Scaling**: Values typically range from 0.5 to 1.5
3. **Morph Targets**: Facial features use 0.0 to 1.0 range
4. **Environment**: Some combinations work better than others
5. **TCP Connection**: Commands are sent via TCP to Unreal Engine
6. **Error Handling**: Invalid commands are ignored, valid ones still execute

## 🚨 **Known Issues**

- Environment changes may occasionally crash the game (use with caution)
- Some command combinations may not work as expected
- TCP connection issues may cause commands to fail silently
- Always test individual commands before combining multiple ones

Use these commands for comprehensive QA testing of the VTuber appearance and environment system! 