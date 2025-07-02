# CLAUDE.md - Consolidated Project Instructions

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains two main projects:

1. **docker-vtuber**: An autonomous AI agent system with VTuber integration, built on Microsoft AutoGen framework with cognitive enhancement capabilities
2. **agent-net**: A separate GPU monitoring and orchestration system

## Common Development Commands

### Container Management (Primary Tool)
```bash
# From root directory
./scripts/docker/docker-manager.sh --build-run    # Build and run containers
./scripts/docker/docker-manager.sh --stop         # Stop all containers
./scripts/docker/docker-manager.sh --logs         # Show container logs
./scripts/docker/docker-manager.sh --test         # Test endpoints
./scripts/docker/docker-manager.sh --status       # Check container status

# Docker manager options
./scripts/docker/docker-manager.sh --autonomous   # Run autonomous agent only
./scripts/docker/docker-manager.sh --cognitive    # Run with Ollama LLM
./scripts/docker/docker-manager.sh --full-stack   # Run complete system
```

### Async Docker Builds
```bash
# Interactive mode
python3 docker-vtuber/main_app/scripts/utils/docker-build-monitor.py -f docker-vtuber/docker-compose.autogen-ollama.yml

# Auto mode
python3 docker-vtuber/main_app/scripts/utils/docker-build-monitor.py -f docker-vtuber/docker-compose.autogen-ollama.yml --auto

# The build monitor provides:
# - Async Docker Compose builds that don't block the terminal
# - Real-time log monitoring saved to docker-build.log
# - Build completion detection and status checking
# - Interactive commands: status, logs, stop, exit
```

### Testing
```bash
# Python tests
cd docker-vtuber
python test_enhanced_autogen_system.py
python test_goal_metrics_system_complete.py
pytest app/CORE/autogen-agent/tests/test_main.py

# Integration tests
python main_app/tests/integration/test_goal_system_integration.py
python test_intelligent_tool_selection.py

# Web app
cd docker-vtuber/app/BYOC/webapp
npm run dev      # Development server
npm run lint     # ESLint
npm run build    # Production build
```

### Monitoring & Debugging
```bash
# Monitor autonomous system
./scripts/monitoring/monitor_autonomous_system.sh

# Database investigation
./scripts/database/investigate_database.sh

# Health checks
curl http://localhost:3100/health    # Autonomous Agent
curl http://localhost:5001/health    # VTuber System
curl http://localhost:8000/health    # Cognee Memory
```

## High-Level Architecture

This is an experimental AI research platform built on containerized microservices. **Note: This is a research/development system, not production-ready.**

### docker-vtuber Project Structure

The system consists of multiple containerized services:

1. **AutoGen Cognitive Agent** (`docker-vtuber/app/CORE/autogen-agent/`)
   - Microsoft AutoGen framework with 3 specialized agents (cognitive_ai, programmer, observer)
   - Intelligent tool selection using context-aware scoring (NOT random)
   - Goal management with SMART framework
   - Darwin-Gödel self-improvement engine (experimental)
   - MCP server skeleton (NOT fully implemented)

2. **VTuber System** (`docker-vtuber/app/AVATAR/`)
   - NeuroSync Player for real-time avatar control
   - Audio-to-face mapping with LiveLink integration
   - Kokoro TTS support
   - Simple boolean activation control

3. **NeuroBridge Orchestration** (`docker-vtuber/app/AVATAR/NeuroBridge/`)
   - Autonomous orchestrator for human-like conversation
   - Priority-based interruption system
   - SCB integration for System 1/2 communication
   - Natural language game control

4. **Memory Services**
   - PostgreSQL with pgvector for embeddings (port 5434/5435)
   - Redis for state management (port 6379)
   - Optional Cognee for semantic memory (port 8000)

5. **BYOC WebApp** (`docker-vtuber/app/BYOC/webapp/`)
   - React/Vite frontend with TypeScript
   - Audio recording and Web3 wallet connectivity

### Service Communication

- Services communicate via HTTP APIs and shared PostgreSQL database
- AutoGen → Cognee: HTTP API calls (not MCP tools)
- AutoGen → VTuber: Simple on/off activation
- All services log to PostgreSQL analytics tables

### Key Ports
- Autonomous Agent: 3100 (or 8000/8200/8201)
- VTuber System: 5001
- SCB Bridge: 5000
- PostgreSQL: 5434/5435
- Redis: 6379
- Ollama LLM: 11434
- Cognee: 8000
- RTMP: 1935/8080

## Development Guidelines

### Container-First Development
Always execute commands inside containers, never on host:
```bash
# ✅ Correct
docker exec -it autonomous-agent npm install

# ❌ Wrong
npm install
```

### Docker Compose Configurations
- `docker-compose.autogen-ollama.yml`: Local LLM with Ollama, no external dependencies
- `docker-compose.cognitive.yml`: Full features with evolution engine
- `docker-compose.bridge.yml`: Complete stack with all services
- `docker-compose.neurobridge.yml`: NeuroBridge orchestration stack

### Environment Configuration
- Main config in `.env` file at project root
- Service URLs use container names (e.g., `http://cognee:8000`)
- API keys in `.env`, never in docker-compose files

### Plugin Development
When developing plugins:
- Place in `autonomous-starter/src/plugin-*` directories
- Follow action/service/provider/evaluator structure
- Use `runtime.getSetting()` for configuration
- Include comprehensive structured logging

### Database Schema
Core database schema with 13 tables plus analytics:
- memories, goals, relationships, participants
- logs, goals_memories, relationships_memories
- cache, accounts, transactions, trade_performances
- rooms, rooms_participants_relations
- knowledge, performance_logs, statistics

### Key Integration Points

1. **AutoGen ↔ Cognee**: HTTP API calls for memory (NOT MCP tools - those are placeholders)
2. **AutoGen ↔ VTuber**: Simple on/off activation via boolean flag
3. **AutoGen ↔ SCB/AgentNet**: State management via Redis (when configured)
4. **All Services**: Logging to PostgreSQL analytics tables

### Implementation Status

**✅ Working:**
- Multi-agent AutoGen conversations
- Intelligent tool selection with scoring
- Goal management system
- Basic VTuber integration
- PostgreSQL storage and analytics
- NeuroBridge orchestration
- Priority-based interruptions

**⚠️ Partial/Issues:**
- Cognee integration (authentication problems)
- MCP server (skeleton only)
- Error handling (basic only)
- Production monitoring (missing)

**❌ Not Implemented:**
- True 24/7 autonomous operation
- Complete MCP tool integration
- Sophisticated VTuber conditional logic
- Production-grade fault tolerance

### Testing Strategy
- Unit tests for individual components
- Integration tests for service communication
- Goal management system tests for autonomous behavior
- Always verify with monitoring scripts after changes

### Performance Targets (Aspirational)
- Decision cycle time: ~30 seconds (configurable via LOOP_INTERVAL)
- Memory query response: Depends on Cognee service performance
- Tool execution: Context-aware selection (implemented)
- System uptime: Research platform - not designed for 24/7 operation

## Important Notes

1. **This is a research platform**, not a production system
2. **Cognee runs as a service**, not an embedded library
3. **MCP integration is incomplete** - needs implementation for Cursor IDE
4. **Error handling is basic** - needs hardening for production use
5. **Monitoring is minimal** - add comprehensive observability for production
6. Always check container logs when debugging issues
7. Use the scripts/docker/docker-manager.sh script as the primary management tool