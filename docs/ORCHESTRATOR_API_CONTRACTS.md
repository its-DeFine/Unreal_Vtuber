# 📄 Orchestrator API Contracts
*Created: 2025-07-13 15:45*

## Overview

This document defines the API contracts between the Orchestrator and Systems 1 & 2, ensuring clean interfaces and predictable behavior.

## Orchestrator API

### Base URL
```
http://orchestrator:8080
```

### Endpoints

#### 1. Route Stimulus
**POST** `/route`

Decides where to route an incoming stimulus.

**Request:**
```json
{
  "stimulus_id": "stim_12345",
  "text": "What's the current BTC price?",
  "context": {
    "user_id": "user_123",
    "session_id": "session_456",
    "previous_persona": "trader"
  },
  "priority": "normal"
}
```

**Response:**
```json
{
  "stimulus_id": "stim_12345",
  "system": "s1",
  "config": {
    "persona": "trader"
  },
  "confidence": 0.95,
  "reasoning": "Real-time market query requiring immediate response",
  "latency_ms": 8,
  "timestamp": "2025-07-13T15:45:00Z"
}
```

**Response Codes:**
- `200`: Successful routing decision
- `400`: Invalid request format
- `500`: Internal routing error

#### 2. Execute Routing
**POST** `/execute`

Executes a routing decision by calling the appropriate system APIs.

**Request:**
```json
{
  "stimulus_id": "stim_12345",
  "system": "both",
  "config": {
    "persona": "trader",
    "team": "trader",
    "coordination": "s1_then_s2"
  },
  "confidence": 0.85,
  "reasoning": "Market analysis requiring immediate response and deep analysis"
}
```

**Response:**
```json
{
  "stimulus_id": "stim_12345",
  "results": {
    "s1": {
      "response": "BTC is currently trading at $65,432",
      "audio_url": "/audio/response_123.wav",
      "latency_ms": 850
    },
    "s2": {
      "analysis": "Based on technical indicators...",
      "recommendations": ["Hold", "Set stop-loss at $64,000"],
      "latency_ms": 1200
    }
  },
  "total_latency_ms": 2050,
  "success": true
}
```

#### 3. Health Check
**GET** `/health`

**Response:**
```json
{
  "status": "healthy",
  "apis": {
    "system1": "healthy",
    "system2": "healthy"
  }
}
```

#### 4. Metrics
**GET** `/metrics`

Returns Prometheus-formatted metrics.

## System 1 API Contract

### Expected by Orchestrator

#### Process Text
**POST** `http://autonomous_neuro_player:5000/process_text`

**Request:**
```json
{
  "text": "What's the current BTC price?",
  "persona": "trader",
  "stream": false
}
```

**Response:**
```json
{
  "response": "BTC is currently trading at $65,432",
  "audio_url": "/audio/response_123.wav",
  "persona_used": "trader",
  "processing_time_ms": 850,
  "timestamp": "2025-07-13T15:45:00Z"
}
```

## System 2 API Contract

### Expected by Orchestrator

#### Process Complex Query
**POST** `http://autogen:5000/process`

**Request:**
```json
{
  "prompt": "Analyze the current BTC market trends",
  "team": "trader",
  "context": {
    "timeframe": "24h",
    "include_technical_analysis": true
  }
}
```

**Response:**
```json
{
  "team_used": "trader",
  "agents_involved": ["trader", "analyst", "critic"],
  "analysis": {
    "summary": "BTC showing bullish momentum...",
    "technical_indicators": {
      "rsi": 65,
      "macd": "bullish_cross"
    },
    "recommendations": ["Hold", "Set stop-loss at $64,000"]
  },
  "tools_used": ["market_data", "trading_analysis"],
  "processing_time_ms": 1200,
  "timestamp": "2025-07-13T15:45:00Z"
}
```

## Stimuli Classification Rules

### Quick Reference

| Stimulus Pattern | System | Configuration |
|-----------------|--------|---------------|
| "price", "current", "now" | S1 | persona: trader |
| "explain", "teach me" | S1 | persona: educator |
| "analyze", "deep dive" | S2 | team: contextual |
| "tell me about X quickly then analyze" | Both | s1_then_s2 |

### Detailed Routing Logic

```python
# Pseudo-code for routing logic
def classify_stimulus(text: str) -> RoutingDecision:
    # 1. Check for urgency markers
    urgency_words = ["now", "quick", "current", "fast"]
    has_urgency = any(word in text.lower() for word in urgency_words)
    
    # 2. Check for complexity markers
    complexity_words = ["analyze", "research", "compare", "strategy"]
    has_complexity = any(word in text.lower() for word in complexity_words)
    
    # 3. Check for hybrid patterns
    if has_urgency and has_complexity:
        return RoutingDecision(system="both", coordination="s1_then_s2")
    elif has_urgency:
        return RoutingDecision(system="s1")
    elif has_complexity:
        return RoutingDecision(system="s2")
    else:
        # Default to S1 for general queries
        return RoutingDecision(system="s1")
```

## Error Handling

### Fallback Strategy

1. **Primary System Unavailable**: Route to alternate system
2. **Both Systems Down**: Return cached response if available
3. **Routing Timeout**: Default to S1 with generic persona

### Error Response Format

```json
{
  "error": {
    "code": "ROUTING_ERROR",
    "message": "Failed to route stimulus",
    "details": {
      "stimulus_id": "stim_12345",
      "attempted_system": "s2",
      "fallback_system": "s1"
    }
  },
  "timestamp": "2025-07-13T15:45:00Z"
}
```

## Integration Testing

### Test Scenarios

1. **Simple S1 Query**
   - Input: "What time is it?"
   - Expected: Route to S1 (streamer)

2. **Complex S2 Analysis**
   - Input: "Create a comprehensive trading strategy for BTC"
   - Expected: Route to S2 (trader team)

3. **Hybrid Query**
   - Input: "Tell me the BTC price and analyze the trend"
   - Expected: Route to both (s1_then_s2)

4. **Failover Test**
   - Scenario: S2 unavailable
   - Expected: Route to S1 with explanation

## Performance SLAs

| Metric | Target | Critical |
|--------|--------|----------|
| Routing Decision | < 10ms | < 50ms |
| S1 Full Response | < 1s | < 2s |
| S2 Full Response | < 2s | < 5s |
| Health Check | < 100ms | < 500ms |

## Versioning

All APIs should include version in headers:
```
X-API-Version: 1.0.0
```

Future versions will maintain backward compatibility or provide migration path.