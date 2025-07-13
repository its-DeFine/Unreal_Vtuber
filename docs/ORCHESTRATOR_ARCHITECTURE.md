# 🎯 Orchestrator Architecture Design
*Created: 2025-07-13 15:30*

## Overview

The Orchestrator is a lightweight, single-agent container that routes stimuli between System 1 and System 2 based on intelligent decision-making. It maintains a registry of available APIs and personas, making routing decisions in under 10ms.

## Core Principles

1. **Simplicity First** - Single ollama agent, minimal dependencies
2. **API Registry** - Self-documenting API discovery
3. **Stateless Routing** - No complex state management
4. **Observable** - Clear logging for every decision

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator Container                │
│  ┌─────────────────────────────────────────────────┐   │
│  │          Ollama Orchestrator Agent              │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────┐ │   │
│  │  │ API Registry│  │Routing Engine│  │ Logger │ │   │
│  │  └─────────────┘  └──────────────┘  └────────┘ │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                    ▲                ▲
                    │                │
        ┌───────────┴────┐    ┌──────┴───────┐
        │   Stimuli In   │    │ API Requests │
        └────────────────┘    └──────────────┘
                    │                │
        ┌───────────▼────┐    ┌──────▼───────┐
        │  System 1 API  │    │ System 2 API │
        └────────────────┘    └──────────────┘
```

## API Registry Structure

```yaml
# /config/api_registry.yaml
apis:
  system1:
    endpoint: "http://autonomous_neuro_player:5000"
    capabilities:
      - real_time_response
      - streaming_output
      - persona_switching
    personas:
      - trader
      - educator
      - streamer
    
  system2:
    endpoint: "http://autogen:5000"
    capabilities:
      - deep_analysis
      - multi_agent_reasoning
      - tool_usage
    teams:
      trader:
        tools: ["market_data", "trading_analysis"]
        agents: ["trader", "analyst", "critic"]
      educator:
        tools: ["curriculum_builder", "knowledge_base"]
        agents: ["teacher", "assistant", "validator"]
      streamer:
        tools: ["content_generator", "audience_analyzer"]
        agents: ["entertainer", "moderator", "producer"]
```

## Routing Decision Logic

```python
# Pseudo-code for routing logic
class OrchestratorAgent:
    def route_stimulus(self, stimulus):
        # Quick classification (< 10ms target)
        intent = self.classify_intent(stimulus)
        
        if intent.requires_real_time:
            return RouteDecision(
                system="s1",
                persona=intent.persona,
                reason="Real-time response required"
            )
        
        elif intent.requires_deep_analysis:
            return RouteDecision(
                system="s2",
                team=intent.domain,
                reason="Complex analysis needed"
            )
        
        elif intent.is_hybrid:
            return RouteDecision(
                system="both",
                s1_persona=intent.persona,
                s2_team=intent.domain,
                coordination="s1_first_then_s2",
                reason="Immediate response with deep follow-up"
            )
```

## Stimuli Types & Routing Rules

| Stimulus Type | Example | Route | Reasoning |
|--------------|---------|-------|-----------|
| Market Query | "What's BTC price?" | S1 (trader) | Real-time data needed |
| Deep Analysis | "Analyze market trends" | S2 (trader team) | Complex reasoning required |
| Teaching Request | "Explain blockchain" | Both | S1 starts, S2 enriches |
| Entertainment | "Tell me a joke" | S1 (streamer) | Immediate response |
| Planning | "Create trading strategy" | S2 (trader team) | Multi-agent collaboration |

## Container Configuration

```yaml
# docker-compose.orchestrator.yml
services:
  orchestrator:
    build:
      context: ./orchestrator
      dockerfile: Dockerfile
    container_name: vtuber_orchestrator
    environment:
      - OLLAMA_MODEL=llama3.2:3b  # Lightweight, fast
      - API_REGISTRY_PATH=/config/api_registry.yaml
      - LOG_LEVEL=INFO
      - DECISION_TIMEOUT_MS=10
    volumes:
      - ./orchestrator/config:/config
      - ./logs/orchestrator:/logs
    ports:
      - "8080:8080"  # Orchestrator API
    networks:
      - vtuber_network
    depends_on:
      - autonomous_neuro_player
      - autogen
```

## AutoGen Integration

```python
# orchestrator/agent.py
from autogen import AssistantAgent, UserProxyAgent

class OrchestratorAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="orchestrator",
            system_message="""You are the VTuber Orchestrator.
            Your job is to route incoming stimuli to the appropriate system.
            
            Rules:
            1. Route to S1 for real-time responses
            2. Route to S2 for complex analysis
            3. Route to both for hybrid scenarios
            
            Always respond with: {system: "s1"|"s2"|"both", config: {...}}
            """,
            llm_config={
                "model": "ollama/llama3.2:3b",
                "temperature": 0.1,  # Consistent routing
                "timeout": 10,
            }
        )
```

## Monitoring & Observability

```python
# Log format for every routing decision
{
    "timestamp": "2025-07-13T15:30:00Z",
    "stimulus_id": "stim_123",
    "stimulus_preview": "What's the BTC price?",
    "classification": {
        "intent": "market_query",
        "urgency": "real_time",
        "complexity": "low"
    },
    "routing_decision": {
        "system": "s1",
        "persona": "trader",
        "latency_ms": 8
    },
    "reason": "Real-time market data query"
}
```

## Future-Proofing

1. **Plugin Architecture** - New systems register via API
2. **Learning Mode** - Track routing success/failure
3. **A/B Testing** - Compare routing strategies
4. **Fallback Logic** - Graceful degradation if systems unavailable

## Implementation Checklist

- [ ] Create orchestrator container structure
- [ ] Implement API registry with auto-discovery
- [ ] Build lightweight routing agent with ollama
- [ ] Add comprehensive logging
- [ ] Create integration tests
- [ ] Document API contracts
- [ ] Performance benchmark (< 10ms routing)