# Architecture Truth Document

**Last Updated**: December 2024  
**Purpose**: Single source of truth for the actual system architecture

## ⚠️ Critical Notes for Future LLM Assistants

**READ THIS FIRST** before making any assumptions about the system:

1. **This is a RESEARCH PLATFORM**, not a production system
2. **Cognee is an EXTERNAL SERVICE**, not an embedded library
3. **MCP server is INCOMPLETE** - mostly placeholders
4. **Many features are PARTIALLY implemented**

## System Overview

This is an experimental AI research platform exploring autonomous agent capabilities using Microsoft AutoGen, with VTuber avatar integration and self-improvement features.

## What Actually Works

### ✅ Fully Functional Components

1. **Multi-Agent AutoGen System**
   - 3 agents: cognitive_ai_agent, programmer_agent, observer_agent
   - GroupChat manager for collaboration
   - Agents work together to make decisions

2. **Intelligent Tool Selection**
   - Context-aware scoring algorithm (NOT random)
   - Performance tracking and learning
   - Scoring weights: keyword (30%), performance (30%), recent (20%), diversity (10%), iteration (10%)

3. **Goal Management**
   - SMART goal framework implementation
   - Progress tracking with metrics
   - Natural language to structured goal conversion

4. **Basic VTuber Integration**
   - Simple on/off control via boolean flag
   - HTTP API to NeuroSync Player
   - Works when explicitly activated

5. **Darwin-Gödel Evolution Framework**
   - AST-based code analysis
   - Template-based modifications
   - Safety sandbox and approval gates

### ⚠️ Partially Working

1. **Cognee Memory Integration**
   - **Issue**: Authentication failures (401 errors)
   - **Reality**: External HTTP service, not embedded
   - **Fallback**: Uses PostgreSQL when Cognee fails
   - **Impact**: Semantic search often unavailable

2. **MCP Server**
   - **Status**: Skeleton implementation only
   - **Missing**: Tool registration, Cursor IDE integration
   - **Impact**: Cannot use with Cursor AI features

3. **Error Handling**
   - **Status**: Basic try/catch blocks only
   - **Missing**: Retry logic, circuit breakers, proper recovery
   - **Impact**: Not suitable for production use

### ❌ Not Implemented

1. **Production Monitoring**
   - No comprehensive observability
   - Missing distributed tracing
   - No alerting or metrics dashboards

2. **24/7 Autonomous Operation**
   - Not designed for continuous operation
   - No fault tolerance or self-healing
   - Research loops only

3. **Sophisticated VTuber Logic**
   - Just a boolean flag, not conditional
   - No complex activation scenarios
   - Basic integration only

## Architecture Diagrams

### Service Architecture
```
┌─────────────────────────────────────────┐
│         AutoGen Agent (Port 8200)        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │Cognitive│ │Programmer│ │Observer │   │
│  └────┬────┘ └────┬────┘ └────┬────┘   │
│       └───────────┴───────────┘         │
│              GroupChat Manager           │
└────────────────┬────────────────────────┘
                 │
     ┌───────────┴───────────┐
     │                       │
┌────▼─────┐          ┌─────▼──────┐
│PostgreSQL│          │   Cognee    │
│(Working) │          │(Auth Issues)│
└──────────┘          └────────────┘
```

### Data Flow
```
User Request 
    → AutoGen GroupChat 
    → Tool Selection (Intelligent Scoring)
    → Tool Execution
    → Memory Storage (PostgreSQL + Cognee attempt)
    → VTuber Output (if flag set)
```

## Deployment Configurations

1. **docker-compose.autogen-ollama.yml**
   - Local LLM with Ollama
   - No cloud dependencies
   - Good for development

2. **docker-compose.cognitive.yml**
   - Full features with Redis
   - Cognee service enabled
   - Research configuration

3. **docker-compose.bridge.yml**
   - Complete stack
   - All services integrated
   - Most complex setup

## Common Misconceptions to Avoid

1. **"Cognee is embedded"** - NO, it's an external HTTP service
2. **"MCP tools work"** - NO, just placeholders
3. **"Production ready"** - NO, research platform only
4. **"24/7 operation"** - NO, not designed for this
5. **"VTuber has AI logic"** - NO, just on/off flag

## Current Issues

1. **Cognee 401 Errors**: Authentication not working properly
2. **MCP Incomplete**: Cannot integrate with Cursor IDE
3. **Basic Error Handling**: Needs production-grade improvements
4. **No Monitoring**: Missing observability stack

## For Developers

When working on this codebase:

1. **Check implementation first** - Don't trust documentation claims
2. **Expect partial features** - Many things half-implemented
3. **This is research code** - Not production quality
4. **Test in containers** - All development must be containerized
5. **Cognee needs debugging** - Auth issues are blocking features

## Performance Characteristics

- **Decision cycles**: ~30 seconds (LOOP_INTERVAL)
- **Memory queries**: Depends on Cognee availability
- **Tool execution**: Context-aware selection works well
- **Uptime**: Not designed for continuous operation

## Summary

You have a sophisticated **research platform** that demonstrates advanced concepts:
- Multi-agent collaboration (working)
- Intelligent tool selection (working)
- Goal-driven behavior (working)
- Code self-modification (experimental)
- Semantic memory (broken - auth issues)

But it's **not** a production system. Think of it as a powerful prototype for exploring autonomous agent architectures.