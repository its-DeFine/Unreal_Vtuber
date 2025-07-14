# Shared Contextual Bridge (SCB) Architecture

## Overview

The Shared Contextual Bridge (SCB) is a Redis-backed system that enables knowledge sharing between System 1 (S1/NeuroSync) and System 2 (S2/AutoGen) components. It implements a unidirectional data flow where S2 writes analytical insights and S1 reads them to enhance responses.

## Architecture Principles

### 1. Unidirectional Data Flow
- **S2 → SCB → S1**
- S2 agents write reasoning, tool calls, and insights
- S1 reads context to enhance prompts
- No bidirectional writes to prevent conflicts

### 2. Team Isolation
- Each team (trader, educator, streamer) has isolated SCB space
- Key format: `scb:team:{team_name}`
- Teams cannot access each other's data

### 3. Character Limit Enforcement
- Default: 1000 characters per team
- Configurable via `SCB_MAX_CHARS_<TEAM>` environment variables
- Automatic trimming of oldest events when limit exceeded

## Components

### 1. Redis Backend
- **Service**: `redis_scb` container
- **Port**: 6379
- **Database**: 0
- **Key Structure**:
  - `scb:team:trader` - Trader team events
  - `scb:team:educator` - Educator team events
  - `scb:team:streamer` - Streamer team events
  - `scb:global` - Global events (optional)

### 2. SCB Gateway Service
- **Service**: `scb_gateway` container
- **Port**: 8300
- **Technology**: FastAPI
- **Purpose**: HTTP API for SCB operations

#### API Endpoints:
- `GET /health` - Health check
- `GET /scb/team/{team}/slice` - Get team SCB data
- `POST /scb/team/{team}/write` - Write to team SCB
- `DELETE /scb/team/{team}` - Clear team SCB
- `GET /scb/stats` - Get SCB statistics

### 3. S2 Integration (Write-Only)

#### SCBv2Client
Location: `autogen_agent/clients/scb_v2_client.py`

```python
# Append event to team SCB
client.append_event("scb:team:trader", {
    "type": "reasoning",
    "content": "Market analysis complete",
    "timestamp": time.time()
})
```

#### scb_operations_tool
Location: `autogen_agent/tools/scb_operations_tool.py`

AutoGen agents use this tool to write to SCB:
```python
#assistant to=scb_operations
{"event_type": "reasoning", "text": "Analysis shows bullish trend"}
```

### 4. S1 Integration (Read-Only)

#### SCBv2MinimalClient
Location: `NeuroSync_Player/utils/scb/scb_v2_minimal.py`

```python
# Read team context
context = client.get_team_context(team="educator", max_events=5)
# Returns formatted string:
# [reasoning] Previous analysis...
# [tool_call] Executed market_data...
```

#### Integration in llm_to_face.py
S1 automatically injects SCB context into prompts:
```python
if _scb_v2_client:
    scb_context = _scb_v2_client.get_team_context(team=team)
    if scb_context:
        current_system_message += f"\n\n[Recent Team Context from S2]:\n{scb_context}"
```

## Data Format

### Event Structure
```json
{
    "type": "reasoning|tool_call|note",
    "content": "Event description",
    "timestamp": 1234567890.123,
    "source": "s2",
    "actor": "s2_agent"
}
```

### Storage Format
Events are stored as JSON arrays in Redis:
```json
[
    {"type": "reasoning", "content": "Analysis complete", ...},
    {"type": "tool_call", "content": "market_data executed", ...}
]
```

## Configuration

### Environment Variables

#### Redis Configuration
- `REDIS_SCB_URL` - Redis connection URL (default: `redis://redis_scb:6379/0`)

#### Character Limits
- `SCB_MAX_CHARS` - Default character limit (default: 1000)
- `SCB_MAX_CHARS_TRADER` - Trader team limit
- `SCB_MAX_CHARS_EDUCATOR` - Educator team limit
- `SCB_MAX_CHARS_STREAMER` - Streamer team limit

#### S2 Configuration
Add to autogen_agent service:
```yaml
environment:
  - REDIS_SCB_URL=redis://redis_scb:6379/0
```

#### S1 Configuration
Already configured in neurosync_s1 service.

## Usage Patterns

### S2 Writing Pattern
1. Agent performs analysis
2. Uses scb_operations tool to write insights
3. Events stored in team SCB
4. Character limit enforced automatically

### S1 Reading Pattern
1. User sends request to S1
2. S1 determines team based on character role
3. Reads last 5 events from team SCB
4. Injects context into system prompt
5. LLM generates response with enhanced context

## Benefits

1. **Knowledge Transfer** - S2's analytical insights enhance S1's responses
2. **Team Specialization** - Each team maintains specialized knowledge
3. **No Conflicts** - Unidirectional flow prevents write conflicts
4. **Scalability** - Easy to add new teams or adjust limits
5. **Persistence** - Redis provides reliable storage

## Monitoring

### Check SCB Contents
```bash
# View trader team SCB
docker exec redis_scb redis-cli get "scb:team:trader" | jq

# Check all SCB keys
docker exec redis_scb redis-cli keys "scb:*"
```

### SCB Gateway Stats
```bash
curl http://localhost:8300/scb/stats | jq
```

## Troubleshooting

### S2 Not Writing
1. Check queue consumer is running: `curl http://localhost:8200/api/status`
2. Restart queue: `curl -X POST http://localhost:8200/api/queue/restart`
3. Check Redis connectivity

### S1 Not Reading
1. Verify character role detection
2. Check Redis connectivity
3. Verify SCB client initialization

### Character Limit Issues
1. Adjust environment variables
2. Restart affected containers
3. Clear SCB if needed: `docker exec redis_scb redis-cli flushall` 