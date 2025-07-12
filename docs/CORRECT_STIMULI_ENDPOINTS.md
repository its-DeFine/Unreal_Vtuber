# Correct Stimuli Endpoints for S1 and S2 Systems

## Overview

This document provides the definitive guide for sending stimuli to both S1 (NeuroSync Avatar) and S2 (AutoGen Teams) systems using the **actual endpoints that exist** in the codebase.

## ❌ What NOT to Do

**DO NOT** make up endpoints or call arbitrary URLs like:
- `/api/chat` (doesn't exist)
- `/api/speak` (doesn't exist) 
- `/api/teams/trigger` (doesn't exist)
- Random endpoints that aren't in the actual codebase

## ✅ Correct S1 (NeuroSync Avatar) Stimuli Endpoints

The S1 system runs on **two containers** with different purposes:

### 1. S1 NeuroSync API (Port 5000)
**Base URL:** `http://localhost:5000`

#### SCB Directive Endpoint
```http
POST http://localhost:5000/scb/directive
Content-Type: application/json

{
  "text": "Your stimuli message here",
  "actor": "external_system",
  "ttl": 30
}
```

**Purpose:** Send general stimuli via the Shared Cognitive Blackboard (SCB)

### 2. S1 Player API (Port 5001) 
**Base URL:** `http://localhost:5001`

#### Speech Generation Endpoint
```http
POST http://localhost:5001/process_text
Content-Type: application/json

{
  "text": "Text to be spoken by the avatar",
  "direct_speech": true,
  "autonomous_context": {
    "source": "external_system",
    "direct_speech": true
  }
}
```

**Purpose:** Generate speech/voice output from the avatar

#### Avatar Control Endpoint
```http
POST http://localhost:5001/game_control
Content-Type: application/json

{
  "prompt": "wave hello, smile, and nod",
  "autonomous_context": {
    "source": "external_system"
  }
}
```

**Purpose:** Control avatar animations and movements

#### Character Management Endpoints
```http
GET http://localhost:5001/character/list
GET http://localhost:5001/character/current
POST http://localhost:5001/character/switch
```

## ✅ Correct S2 (AutoGen Teams) Stimuli Endpoints

The S2 system runs on **one container**:

### S2 AutoGen API (Port 8200)
**Base URL:** `http://localhost:8200`

#### Main Stimuli Endpoint
```http
POST http://localhost:8200/api/stimuli/receive
Content-Type: application/json

{
  "stimuli_id": "unique_id_12345",
  "content": "Your request for team processing",
  "source": "external_system",
  "priority": "medium",
  "category": "optional_category",
  "metadata": {
    "team_preference": "trader|educator|streamer"
  }
}
```

**Purpose:** Main endpoint for triggering AutoGen team processing

#### Status and Control Endpoints
```http
GET http://localhost:8200/api/stimuli/status
GET http://localhost:8200/api/stimuli/tools
POST http://localhost:8200/api/stimuli/control/pause
POST http://localhost:8200/api/stimuli/control/resume
```

## 🎯 Complete Examples

### Trading Scenario
```python
import asyncio
import aiohttp

async def trading_scenario():
    async with aiohttp.ClientSession() as session:
        # 1. Send analysis request to S2
        s2_data = {
            "stimuli_id": f"trading_{int(time.time())}",
            "content": "Analyze Bitcoin and Ethereum trends with investment recommendations",
            "source": "external_system",
            "priority": "high",
            "metadata": {"team_preference": "trader"}
        }
        async with session.post("http://localhost:8200/api/stimuli/receive", json=s2_data) as resp:
            s2_result = await resp.json()
        
        # 2. Send speech to S1
        s1_speech_data = {
            "text": "Analyzing cryptocurrency market trends for investment opportunities",
            "direct_speech": True,
            "autonomous_context": {"source": "external_system", "direct_speech": True}
        }
        async with session.post("http://localhost:5001/process_text", json=s1_speech_data) as resp:
            s1_result = await resp.json()
        
        # 3. Send avatar gesture to S1
        s1_avatar_data = {
            "prompt": "lean forward thoughtfully, then nod confidently",
            "autonomous_context": {"source": "external_system"}
        }
        async with session.post("http://localhost:5001/game_control", json=s1_avatar_data) as resp:
            avatar_result = await resp.json()
```

### Education Scenario
```python
async def education_scenario():
    async with aiohttp.ClientSession() as session:
        # 1. Send education request to S2
        s2_data = {
            "stimuli_id": f"education_{int(time.time())}",
            "content": "Explain quantum computing principles with beginner-friendly examples",
            "source": "external_system",
            "priority": "medium", 
            "metadata": {"team_preference": "educator"}
        }
        await session.post("http://localhost:8200/api/stimuli/receive", json=s2_data)
        
        # 2. Send welcoming speech to S1
        s1_data = {
            "text": "Welcome to today's quantum computing lesson! Let's explore this fascinating field together.",
            "direct_speech": True,
            "autonomous_context": {"source": "external_system", "direct_speech": True}
        }
        await session.post("http://localhost:5001/process_text", json=s1_data)
        
        # 3. Send teaching gestures to S1
        avatar_data = {
            "prompt": "wave hello enthusiastically, then gesture as if explaining concepts",
            "autonomous_context": {"source": "external_system"}
        }
        await session.post("http://localhost:5001/game_control", json=avatar_data)
```

## 🔍 How These Endpoints Were Discovered

1. **Code Analysis:** Examined the actual source code in:
   - `/docker-vtuber/app/CORE/autogen-agent/autogen_agent/api/stimuli_api.py` (S2)
   - `/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Local_API/neurosync_local_api.py` (S1 port 5000)
   - `/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/llm_to_face.py` (S1 port 5001)

2. **Docker Compose Analysis:** Checked `docker-compose.all.yml` for actual port mappings

3. **Live Testing:** Used the investigation script to test actual endpoints and verify they work

## 📋 Port Summary

| System | Container | Port | Purpose |
|--------|-----------|------|---------|
| S1 | neurosync_s1 | 5000 | Neural processing, SCB |
| S1 | neurosync_s1 | 5001 | Player API, speech, avatar |
| S2 | autogen_agent | 8200 | AutoGen teams, stimuli processing |

## ⚠️ Important Notes

1. **Use the actual endpoints documented here** - they are tested and confirmed working
2. **Don't invent new endpoints** - the systems are designed with specific interfaces
3. **Follow the request formats shown** - the APIs expect specific JSON structures
4. **Both systems are designed to receive external stimuli** - this is their intended usage
5. **S1 has multiple endpoints for different purposes** (speech vs avatar vs SCB)
6. **S2 has a unified stimuli API** that routes to appropriate teams

## 🧪 Testing

Use the provided test scripts:
- `test_correct_stimuli_endpoints.py` - Investigates and verifies endpoints
- `correct_stimuli_examples.py` - Demonstrates proper usage patterns

Both scripts are located in the `/tests` directory and can be run with:
```bash
python3 test_correct_stimuli_endpoints.py
python3 correct_stimuli_examples.py
```