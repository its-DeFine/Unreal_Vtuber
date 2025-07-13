# Data Flow Documentation

## Overview

This document describes the comprehensive data flow patterns within the Autonomous VTuber System, illustrating how information moves between components, systems, and services to deliver intelligent, context-aware responses.

## High-Level Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                              │
│              (API, WebUI, Voice, Chat)                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 UNIFIED CORE                                   │
│            (Request Processing & Routing)                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                STIMULI ROUTER                                  │
│         (Intelligent Content Analysis)                        │
└─────┬─────────────────────────────────────────────────┬───────┘
      │                                                 │
┌─────▼─────┐                                   ┌───────▼───────┐
│ S1 SYSTEM │                                   │   S2 SYSTEM   │
│ (Avatar)  │                                   │ (AutoGen)     │
└─────┬─────┘                                   └───────┬───────┘
      │                                                 │
┌─────▼─────┐                                   ┌───────▼───────┐
│    SCB    │◄──────────────────────────────────┤   REDIS       │
│ (Memory)  │                                   │  (Queue)      │
└─────┬─────┘                                   └───────┬───────┘
      │                                                 │
┌─────▼─────┐                                   ┌───────▼───────┐
│  Neo4j    │                                   │   Neo4j       │
│(Semantic) │                                   │ (Knowledge)   │
└───────────┘                                   └───────────────┘
```

## Detailed Data Flow Patterns

### 1. Request Ingestion Flow

#### API Request Processing
```
[Client Request] 
    ↓
[FastAPI Validation]
    ↓
[Request Object Creation]
    ↓ 
[Authentication & Rate Limiting]
    ↓
[Unified CORE Router]
```

**Data Structure - Incoming Request**:
```json
{
  "stimuli_id": "unique-identifier",
  "content": "user message or command",
  "source": "api|webhook|ui|voice",
  "priority": "low|medium|high|critical",
  "processing_mode": "auto|s1_only|s2_only|s1_and_s2",
  "metadata": {
    "user_id": "user-123",
    "session_id": "session-456",
    "timestamp": "2025-07-13T10:00:00Z",
    "context": "additional_context"
  }
}
```

#### Request Transformation
```python
# Raw request → Standardized StimuliRequest
StimuliRequest(
    id=request.stimuli_id,
    content=request.content,
    source=request.source,
    priority=request.priority,
    processing_mode=ProcessingMode(request.processing_mode),
    metadata=request.metadata,
    created_at=datetime.now()
)
```

### 2. Intelligent Routing Flow

#### Content Analysis Pipeline
```
[Raw Content]
    ↓
[Keyword Extraction]
    ↓
[Intent Classification]
    ↓
[Character Matching] 
    ↓
[System Assignment]
    ↓
[Processing Strategy Selection]
```

**Routing Decision Matrix**:
```python
routing_keywords = {
    ProcessingMode.S1_ONLY: [
        "avatar", "speak", "say", "voice", "immediate"
    ],
    ProcessingMode.S2_ONLY: [
        "analyze", "research", "calculate", "study", 
        "trading", "market", "education"
    ],
    ProcessingMode.S1_AND_S2: [
        "explain", "discuss", "tell", "show", "presentation"
    ]
}

team_keywords = {
    TeamType.TRADER: [
        "trading", "market", "stock", "crypto", "financial"
    ],
    TeamType.EDUCATOR: [
        "teach", "learn", "education", "lesson", "study"
    ],
    TeamType.STREAMER: [
        "stream", "content", "social", "entertainment"
    ]
}
```

#### Character-Based Routing
```python
# Character priority routing
s2_only_characters = {
    "dr._house_doctor_template",
    "trader",
    "financial_analyst"
}

character_team_mapping = {
    "gordon_trader_template": TeamType.TRADER,
    "emma_teacher_template": TeamType.EDUCATOR,
    "alex_streamer_template": TeamType.STREAMER
}
```

### 3. S1 System Data Flow

#### S1 Processing Pipeline
```
[Stimuli Request]
    ↓
[Character Selection]
    ↓
[NeuroSync Player API Call]
    ↓
[Speech Synthesis]
    ↓
[Avatar Animation]
    ↓
[SCB State Update]
    ↓
[Response Formation]
```

**S1 Data Transformation**:
```python
# Input Processing
s1_payload = {
    "text": request.content,
    "character": request.metadata.get("character_type"),
    "emotion": "neutral",
    "voice_settings": {
        "rate": 1.0,
        "pitch": 0.0,
        "volume": 0.8
    }
}

# NeuroSync Response
neurosync_response = {
    "audio_url": "http://neurosync/audio/abc123.wav",
    "animation_data": {
        "facial_keyframes": [...],
        "gesture_sequence": [...],
        "emotion_blend": "confident"
    },
    "processing_time": 1.2
}
```

#### SCB Integration Flow
```
[S1 Response]
    ↓
[SCB Context Extraction]
    ↓
[Redis State Update]
    ↓
[Cross-System Notification]
```

**SCB Data Structure**:
```json
{
  "stimuli_id": "unique-id",
  "system": "s1",
  "character": "gordon_trader_template",
  "content": "original stimuli",
  "response": "generated response",
  "context": {
    "conversation_turn": 5,
    "emotional_state": "confident",
    "topic": "market_analysis"
  },
  "timestamp": "2025-07-13T10:00:00Z"
}
```

### 4. S2 System Data Flow

#### S2 Team Processing Pipeline
```
[Stimuli Request]
    ↓
[Team Selection]
    ↓
[Queue Placement]
    ↓
[AutoGen Team Initialization]
    ↓
[Multi-Agent Conversation]
    ↓
[Insight Extraction]
    ↓
[Neo4j Storage]
    ↓
[Response Aggregation]
```

#### Team Assignment Flow
```python
# Team selection logic
def select_team(content: str, character_hint: str = None) -> TeamType:
    if character_hint in trader_characters:
        return TeamType.TRADER
    
    # Content analysis
    scores = {
        team: sum(1 for keyword in keywords 
                 if keyword in content.lower())
        for team, keywords in team_keywords.items()
    }
    
    return max(scores, key=scores.get) or TeamType.GENERAL
```

#### AutoGen Conversation Flow
```
[Team Initialization]
    ↓
[Group Chat Creation]
    ↓
[Coordinator Agent Starts]
    ↓
[Specialized Agents Contribute]
    ↓
[Memory Agent Learns]
    ↓
[Conversation Termination]
    ↓
[Result Extraction]
```

**AutoGen Message Structure**:
```json
{
  "name": "trader_coordinator",
  "content": "Based on the market data, I recommend...",
  "role": "assistant",
  "metadata": {
    "agent_type": "coordinator",
    "team": "trader",
    "turn": 3,
    "tools_used": ["market_data", "risk_assessment"]
  }
}
```

#### Tool Integration Flow
```
[Agent Decision]
    ↓
[Tool Selection]
    ↓
[Tool Execution]
    ↓
[Result Processing]
    ↓
[Team Discussion]
```

**Tool Execution Data**:
```python
# Market data tool example
tool_request = {
    "tool": "market_data",
    "parameters": {
        "symbol": "BTC-USD",
        "timeframe": "1d",
        "period_days": 30
    },
    "context": {
        "requesting_agent": "market_analyst",
        "conversation_id": "conv-123"
    }
}

tool_response = {
    "success": True,
    "result": {
        "symbol": "BTC-USD",
        "current_price": 45000,
        "price_change_24h": 2.5,
        "technical_analysis": {...}
    },
    "execution_time": 0.5,
    "metadata": {
        "data_source": "simulated",
        "timestamp": "2025-07-13T10:00:00Z"
    }
}
```

### 5. Memory and Knowledge Flow

#### Neo4j Semantic Storage Flow
```
[Team Insights]
    ↓
[Semantic Node Creation]
    ↓
[Embedding Generation]
    ↓
[Graph Relationship Mapping]
    ↓
[Knowledge Persistence]
```

**Semantic Node Structure**:
```python
SemanticNode(
    id="insight-abc123",
    content="Bitcoin shows bullish momentum with RSI at 65",
    context=SemanticContext.TRADING,
    node_type="market_insight",
    timestamp=1625184000.0,
    metadata={
        "team": "trader",
        "confidence": 0.87,
        "source_agents": ["analyst", "strategist"]
    },
    embedding=[0.1, 0.2, 0.3, ...],  # 384-dimensional vector
    initiating_agent="market_analyst",
    agent_category="s2_team",
    action_chain=["analyze_data", "calculate_indicators", "assess_trend"]
)
```

#### Knowledge Retrieval Flow
```
[Query Request]
    ↓
[Embedding Generation]
    ↓
[Semantic Search]
    ↓
[Context Filtering]
    ↓
[Relevance Ranking]
    ↓
[Result Assembly]
```

#### SCB Memory Bridge Flow
```
[S1 Conversation Context]
    ↓
[SCB State Extraction]
    ↓
[S2 Context Injection]
    ↓
[Enhanced Team Processing]
    ↓
[S2 Insights to SCB]
    ↓
[S1 Context Enhancement]
```

### 6. Response Aggregation Flow

#### Single System Response
```
[Processing Result]
    ↓
[Success Validation]
    ↓
[Response Formatting]
    ↓
[Metadata Addition]
    ↓
[Client Response]
```

#### Dual System Response (S1 + S2)
```
[Parallel Processing]
    ↓
[S1 Response] + [S2 Response]
    ↓
[Response Correlation]
    ↓
[Conflict Resolution]
    ↓
[Unified Response]
```

**Response Structure**:
```json
{
  "stimuli_id": "unique-id",
  "status": "success",
  "processing_mode": "s1_and_s2",
  "results": [
    {
      "system": "s1",
      "character": "gordon_trader_template",
      "response": "I see strong bullish signals in Bitcoin",
      "processing_time": 1.2,
      "metadata": {
        "audio_url": "http://neurosync/audio/response.wav",
        "animation_sequence": "confident_analysis"
      }
    },
    {
      "system": "s2", 
      "team": "trader",
      "insights": {
        "patterns": ["bullish_momentum", "volume_increase"],
        "strategies": ["buy_on_dip", "set_stop_loss_at_42k"],
        "risk_assessment": "medium_risk_high_reward"
      },
      "processing_time": 25.8,
      "metadata": {
        "agents_involved": 4,
        "conversation_rounds": 6,
        "tools_used": ["market_data", "technical_analysis"]
      }
    }
  ],
  "aggregated_insights": {
    "confidence": 0.89,
    "recommendation": "bullish_outlook",
    "action_items": ["monitor_support_levels", "prepare_entry_strategy"]
  }
}
```

## Error Handling and Recovery Flow

### Error Detection Flow
```
[Processing Error]
    ↓
[Error Classification]
    ↓
[Recovery Strategy Selection]
    ↓
[Fallback Execution]
    ↓
[Error Logging]
    ↓
[Circuit Breaker Update]
```

### Error Data Structure
```json
{
  "error_id": "err-123",
  "stimuli_id": "original-request",
  "error_type": "llm_timeout",
  "component": "s2_trader_team",
  "error_message": "AutoGen conversation exceeded timeout",
  "stack_trace": "...",
  "recovery_action": "fallback_to_simple_response",
  "timestamp": "2025-07-13T10:00:00Z",
  "metadata": {
    "processing_time": 60.0,
    "retry_count": 2,
    "circuit_breaker_state": "half_open"
  }
}
```

## Performance Monitoring Data Flow

### Metrics Collection Flow
```
[Component Activity]
    ↓
[Metric Extraction]
    ↓
[Aggregation]
    ↓
[Storage]
    ↓
[Dashboard Update]
```

### Performance Metrics Structure
```json
{
  "timestamp": "2025-07-13T10:00:00Z",
  "metrics": {
    "requests_per_minute": 25,
    "average_response_time": 18.5,
    "s1_processing_time": 2.1,
    "s2_processing_time": 24.8,
    "queue_depth": {
      "s2_trader": 3,
      "s2_educator": 1,
      "s2_streamer": 0
    },
    "character_utilization": {
      "gordon_trader_template": 0.75,
      "emma_teacher_template": 0.45,
      "alex_streamer_template": 0.30
    },
    "error_rates": {
      "total": 0.02,
      "by_component": {
        "s1_system": 0.01,
        "s2_system": 0.03,
        "neo4j": 0.005,
        "redis": 0.001
      }
    }
  }
}
```

## Data Security and Privacy Flow

### PII Scrubbing Flow
```
[Raw Input]
    ↓
[PII Detection]
    ↓
[Data Sanitization]
    ↓
[Safe Processing]
    ↓
[Audit Logging]
```

### Data Encryption Flow
```
[Sensitive Data]
    ↓
[Encryption at Rest]
    ↓
[Secure Transmission]
    ↓
[Authorized Access]
    ↓
[Decryption for Processing]
    ↓
[Re-encryption for Storage]
```

## Real-time Data Streaming

### WebSocket Data Flow (Future Enhancement)
```
[Client Connection]
    ↓
[Processing Started Event]
    ↓
[Progress Updates]
    ↓
[Partial Results]
    ↓
[Final Response]
    ↓
[Connection Close]
```

### Event Stream Structure
```json
{
  "event_type": "processing_update",
  "stimuli_id": "unique-id",
  "timestamp": "2025-07-13T10:00:00Z",
  "data": {
    "progress": 0.65,
    "current_stage": "s2_team_discussion",
    "estimated_completion": "15s",
    "partial_insights": ["market_trend_identified"]
  }
}
```

## Data Backup and Recovery Flow

### Backup Strategy Flow
```
[Real-time Operations]
    ↓
[Continuous SCB Backup]
    ↓
[Daily Neo4j Snapshot]
    ↓
[Configuration Backup]
    ↓
[Off-site Storage]
```

### Recovery Flow
```
[Failure Detection]
    ↓
[Service Isolation]
    ↓
[Data Recovery]
    ↓
[Service Restart]
    ↓
[State Restoration]
    ↓
[Health Verification]
```

## Integration Points and APIs

### External System Integration
```
[External API Call]
    ↓
[Authentication]
    ↓
[Rate Limit Check]
    ↓
[Data Translation]
    ↓
[Internal Processing]
    ↓
[Response Translation]
    ↓
[External Response]
```

### Webhook Data Flow
```
[External Event]
    ↓
[Webhook Trigger]
    ↓
[Event Validation]
    ↓
[Stimuli Generation]
    ↓
[Normal Processing Flow]
    ↓
[Callback Response]
```

---

This comprehensive data flow documentation illustrates how information moves through the Autonomous VTuber System, enabling developers to understand the system's data pathways, optimize performance, and debug issues effectively. The modular design ensures that data flows remain clean and traceable across all system components.