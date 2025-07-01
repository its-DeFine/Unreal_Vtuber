# Game Control QA Testing Commands (Natural Language)

This document provides all available game control commands for direct testing via the `/game_control` API endpoint using **natural language prompts**.

## 🎮 **Direct Game Control Endpoint**

**Base URL:** `POST http://localhost:5001/game_control`

**Format:** The API uses natural language prompts that get converted to TCP commands automatically.

```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "NATURAL LANGUAGE DESCRIPTION"}'
```

## 📋 **QA Test Commands by Category**

### **LEVELS/SCENES**
```bash
# Cloud Environment (Default)
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "home environment"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "cloud scene"}'

# Medieval Castle Scene
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "medieval castle scene"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "fantasy medieval environment"}'

# DJ/Party Environment
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "DJ party environment"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "music party scene"}'

# Cozy Lofi Scene
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "cozy lofi scene"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "ambient cozy setting"}'
```

### **CHARACTER APPEARANCE**
```bash
# Character Build
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "feminine character build"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "masculine character build"}'

# Complete Appearance Changes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "feminine character with maid dress"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "masculine character with default outfit"}'
```

### **HAIR COLORS**
```bash
# Red Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "red hair"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "bright red hair color"}'

# Blonde Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "blonde hair"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "yellow blonde hair"}'

# Blue Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "blue hair"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "bright blue hair color"}'

# Purple Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "purple hair"}'

# Green Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "green hair"}'

# Black Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "black hair"}'

# White Hair
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "white hair"}'
```

### **OUTFITS & STYLES**
```bash
# Maid Dress
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "maid dress outfit"}'

# Pop Star Outfit
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "pop star outfit"}'

# Kimono
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "kimono outfit"}'

# Black Dress
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "black dress"}'

# Default Outfit
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "default outfit"}'
```

### **FACIAL FEATURES**
```bash
# Larger Eyes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "bigger eyes"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "large eyes"}'

# Nose Changes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "wider nose"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "narrow nose"}'

# Chin Changes
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "wider chin"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "narrow chin"}'
```

### **ENVIRONMENT LIGHTING**
```bash
# Day Time
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "day time bright lighting"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "bright sunny day"}'

# Night Time
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "night time"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "dark night scene"}'

# Sunset
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "sunset lighting"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "golden hour sunset"}'

# Stars
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "bright stars"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "starry night sky"}'
```

### **ANIMATIONS**
```bash
# Dance Animation
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "dance animation"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "start dancing"}'
```

## 🧪 **Comprehensive QA Test Scenarios**

### **Scenario 1: Complete Character Makeover**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "prompt": "feminine character with red hair, maid dress, larger eyes, medieval castle scene"
}'
```

### **Scenario 2: DJ Party Setup**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "prompt": "DJ party environment with blue hair, pop star outfit, dance animation, night time lighting"
}'
```

### **Scenario 3: Cozy Evening Scene**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "prompt": "cozy lofi scene with purple hair, kimono outfit, sunset lighting, bright stars"
}'
```

### **Scenario 4: Fantasy Adventure Look**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{
  "prompt": "medieval fantasy scene with blonde hair, black dress, feminine character, day time"
}'
```

### **Scenario 5: Natural Variations**
```bash
# Test different phrasings for same result
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "Change hair to red color"}'

curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "Make the hair red"}'

curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "Red hair please"}'
```

## 🔍 **Available TCP Commands (Generated Automatically)**

The system automatically converts natural language to these TCP commands:

### **Levels:** `LVL.Home`, `LVL.Medieval`, `LVL.DJ`, `LVL.Lofi`
### **Character Presets:** `PRS.Fem`, `PRS.Masc`, `PRS.Fem1`, `PRS.Masc1`  
### **Outfits:** `OF.Default`, `OF.Maid Dress`, `OF.Pop Star`, `OF.Kimono`, `OF.Black Dress`
### **Hair Colors:** `HCR.X`, `HCG.X`, `HCB.X` (RGB values 0.0-1.0)
### **Facial Morphs:** `MTEYW.X` (eyes), `MTNW.X` (nose), `MTCW.X` (chin)
### **Environment:** `SNH.X` (sun height), `STRB.X` (stars), `ANIM.Dance`

## 🎯 **Testing Specific Features**

### **Hair Color Variations**
```bash
# Test all major colors
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "red hair"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "blue hair"}'  
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "green hair"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "yellow hair"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "purple hair"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "white hair"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "black hair"}'
```

### **Scene Changes**
```bash
# Test all environments
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "home scene"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "medieval scene"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "DJ scene"}'
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "lofi scene"}'
```

### **Complex Combinations**
```bash
# Test multiple changes at once
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "red hair, medieval scene, maid dress, bigger eyes"}'

curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "blue hair, DJ environment, pop star outfit, dance"}'

curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "night time, bright stars, purple hair, kimono"}'
```

## 🔍 **System Monitoring Commands**

### **Health Check**
```bash
curl -s http://localhost:5001/game_control/health | jq .
```

### **Available Features**
```bash
curl -s http://localhost:5001/game_control/features | jq .
```

### **Test Basic Connectivity**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "test"}' | jq .
```

## 📝 **Response Format**

All commands return JSON with execution details:
```json
{
  "status": "completed",
  "prompt": "red hair, medieval scene",
  "commands_generated": 3,
  "commands_successful": 3,
  "commands_failed": 0,
  "tcp_host": "host.docker.internal", 
  "tcp_port": 7777,
  "orchestrator_enabled": true
}
```

## 🚨 **Important Testing Notes**

1. **Natural Language**: Use descriptive phrases, not technical commands
2. **Multiple Changes**: Combine multiple changes in one prompt for efficiency
3. **Validation**: Check `commands_successful` count in response
4. **TCP Connection**: System connects to Unreal Engine on port 7777
5. **Error Handling**: Failed commands are logged but don't stop others

## ⚠️ **Known Issues & Limitations**

- Some complex combinations may not work as expected
- Environment changes may occasionally cause game instability  
- TCP connection issues may cause silent failures
- Natural language parsing may misinterpret some requests
- Always test simple changes before complex combinations

## 🔄 **Reset to Default**
```bash
curl -X POST http://localhost:5001/game_control -H "Content-Type: application/json" -d '{"prompt": "reset to default appearance, home scene, feminine character"}'
```

Use these natural language commands for comprehensive QA testing of the VTuber system! 