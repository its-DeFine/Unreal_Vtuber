# Stimuli Flow Analysis - Current System

## Overview

This document traces the complete stimuli request flow through the current autonomy system without making assumptions. Based on examination of the actual codebase, here's how stimuli requests are processed from initial reception to final response.

## System Architecture

The current system has three main entry points for stimuli:

1. **Unified CORE System** (`/home/geo/directories/autonomy/docker-vtuber/app/CORE/unified_main.py`) - Port 8000
2. **S1 NeuroSync System** (Avatar/Speech) - Port 5000/5001 
3. **S2 AutoGen System** (Multi-Agent Teams) - Port 8200
4. **GraphFlow Gateway** - Port 8081

## Complete Stimuli Flow Trace

### 1. Initial Request Reception

#### Unified CORE Entry Point
- **Endpoint**: `POST /api/stimuli/receive`
- **Port**: 8000 (not exposed in docker-compose)
- **Request Format**:
```json
{
  "stimuli_id": "string",
  "content": "string", 
  "source": "string",
  "priority": "medium",
  "processing_mode": "auto",
  "team_preference": "optional",
  "character_type": "optional",
  "metadata": {}
}
```

### 2. Routing Decision Process

The `StimuliProcessor` in `/home/geo/directories/autonomy/docker-vtuber/app/CORE/shared/processing/stimuli_processor.py` makes routing decisions:

#### Routing Priority:
1. **Explicit mode** - If `processing_mode` is not "auto", use that mode
2. **Character-based routing** - S2-only characters: `dr._house_doctor_template`, `trader`, `financial_analyst`
3. **Content analysis** - Keyword matching:
   - **S1_ONLY**: "avatar", "speak", "say", "voice", "immediate", "urgent_speech"
   - **S2_ONLY**: "analyze", "research", "calculate", "study", "investigate", "trading", "market", "financial", "education", "learning"
   - **S1_AND_S2**: "explain", "discuss", "tell", "show", "presentation"
4. **Priority fallback**:
   - Critical/Emergency → S1_AND_S2
   - High → S2_ONLY  
   - Default → S1_AND_S2

#### Team Selection for S2:
- **TRADER**: "trading", "market", "stock", "crypto", "financial", etc.
- **EDUCATOR**: "teach", "learn", "education", "lesson", "curriculum", etc.
- **STREAMER**: "stream", "content", "social", "community", "entertainment", etc.
- **Default**: GENERAL team

### 3. Processing Strategies

#### S1 Processing Strategy
- **Target**: NeuroSync S1 container at `http://localhost:5001`
- **Endpoints Attempted**:
  1. `POST /process_text` - Primary text processing endpoint
  2. `POST /scb/directive` - Fallback SCB directive endpoint at `http://localhost:5000`
  3. `GET /health` - Health check if others fail

#### S2 Processing Strategy  
- **Target**: AutoGen Agent container at `http://localhost:8200`
- **Endpoints**:
  1. `POST /api/stimuli/receive` - Direct API call
  2. **Fallback**: Redis queue `s2_{team_type}` if direct call fails

### 4. Actual Container Endpoints

#### S1 NeuroSync Container (neurosync_s1)
**Port 5000** (NeuroSync Local API):
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /scb/ping` - SCB health probe
- `GET /scb/slice` - Get SCB summary/window
- `POST /scb/event` - Append event to SCB
- `POST /scb/directive` - Append directive to SCB
- `POST /audio_to_blendshapes` - Audio processing

**Port 5001** (NeuroSync Player):
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics  
- `POST /process_text` - **Main text processing endpoint**
- `POST /game_control` - Game control commands
- `GET /game_control/health` - Game control health
- `GET /game_control/features` - Supported features
- `GET /character/list` - List available characters
- `GET /character/current` - Get current character
- `POST /character/switch` - Switch character
- `POST /character/create` - Create new character

#### S2 AutoGen Container (autogen_agent)
**Port 8200**:
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /api/status` - Detailed system status
- `POST /api/test/process` - Test stimuli processing
- `POST /api/stimuli/receive` - **Main stimuli endpoint**
- `GET /api/admin/control-panel` - Admin control panel
- `GET /api/stimuli/status` - Orchestrator status
- `POST /api/stimuli/control/pause` - Pause autonomous mode
- `POST /api/stimuli/control/resume` - Resume autonomous mode
- `GET /api/stimuli/tools` - Available tools

### 5. Request Flow Examples

#### Example 1: S1-Only Processing
```
Request: "Please say hello to everyone"
↓
1. Unified CORE receives at /api/stimuli/receive
2. StimuliRouter detects "say" keyword → ProcessingMode.S1_ONLY
3. S1ProcessingStrategy calls NeuroSync Player:
   POST http://localhost:5001/process_text
   {
     "text": "Please say hello to everyone"
   }
4. NeuroSync Player processes text through LLM and speech
5. Response returned with speech generation result
```

#### Example 2: S2-Only Processing
```
Request: "Analyze the current market trends for Bitcoin"
↓
1. Unified CORE receives at /api/stimuli/receive
2. StimuliRouter detects "analyze", "market" keywords → ProcessingMode.S2_ONLY
3. Team selection detects "market", "Bitcoin" → TeamType.TRADER
4. S2ProcessingStrategy calls AutoGen Agent:
   POST http://localhost:8200/api/stimuli/receive
   {
     "stimuli_id": "...",
     "content": "Analyze the current market trends for Bitcoin",
     "team_preference": "trader"
   }
5. AutoGen orchestrator processes with trader team
6. Response returned with analysis results
```

#### Example 3: S1+S2 Processing
```
Request: "Explain blockchain technology to our audience"
↓
1. Unified CORE receives at /api/stimuli/receive  
2. StimuliRouter detects "explain" keyword → ProcessingMode.S1_AND_S2
3. Both strategies execute in parallel:
   - S1: POST http://localhost:5001/process_text
   - S2: POST http://localhost:8200/api/stimuli/receive (team: educator)
4. Both systems process simultaneously
5. Both responses returned in array
```

### 6. Current Integration Points

#### GraphFlow Gateway
- **Container**: `graphflow_gateway` (Port 8081)
- **Function**: External stimuli reception from admin interfaces
- **Targets**: 
  - S1: `http://neurosync_s1:5001`
  - S2: `http://autogen_agent:8000` (Note: Should be 8200)

#### Redis Integration
- **Container**: `redis_scb` (Port 6379)
- **Usage**: 
  - SCB (Shared Context Blackboard) for S1 system
  - Fallback queue for S2 processing
  - Cross-system communication

### 7. Response Formats

#### Unified CORE Response
```json
{
  "stimuli_id": "request_id",
  "status": "success|failed", 
  "processing_mode": "s1_only|s2_only|s1_and_s2",
  "team_type": "trader|educator|streamer|general",
  "processing_time": 1.234,
  "queued": false,
  "message_id": "optional_queue_id",
  "error": "optional_error_message"
}
```

#### S1 NeuroSync Response (/process_text)
```json
{
  "status": "processing",
  "message": "Input processed.", 
  "llm_provider": "ollama|openai",
  "s1_system": true
}
```

#### S2 AutoGen Response (/api/stimuli/receive)
```json
{
  "success": true,
  "stimuli_id": "request_id",
  "processing_time": 2.345,
  "tools_triggered": ["tool1", "tool2"],
  "agent_decision": "decision_description",
  "response_content": "agent_response",
  "timestamp": "2025-07-12T..."
}
```

## Current Issues Identified

1. **Port Mismatch**: GraphFlow targets `autogen_agent:8000` but container exposes `8200`
2. **Unified CORE Not Exposed**: Main orchestration system not accessible externally  
3. **GraphFlow Integration**: May bypass unified routing logic
4. **Fallback Reliability**: S2 queue fallback relies on Redis but direct calls should work

## Testing Recommendations

As advised, test stimuli processing in this order:

1. **S1 Only**: Direct call to `POST http://localhost:5001/process_text`
2. **S2 Only**: Direct call to `POST http://localhost:8200/api/stimuli/receive`
3. **Unified Flow**: Call through unified CORE system (when exposed)
4. **Both Systems**: Test S1+S2 parallel processing

This will help verify each integration point works as expected and identify any communication issues.