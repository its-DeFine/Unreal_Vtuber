# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains two main projects:

1. **docker-vtuber**: An autonomous AI agent system with VTuber integration, built on Microsoft AutoGen framework with cognitive enhancement capabilities
2. **agent-net**: A separate GPU monitoring and orchestration system

## Common Development Commands

### Container Management (Primary Tool)
```bash
# Build and run containers
./docker-vtuber/main_app/scripts/utils/docker-manager.sh --build-run

# Stop all containers
./docker-vtuber/main_app/scripts/utils/docker-manager.sh --stop

# View logs
./docker-vtuber/main_app/scripts/utils/docker-manager.sh --logs

# Test endpoints
./docker-vtuber/main_app/scripts/utils/docker-manager.sh --test

# Check status
./docker-vtuber/main_app/scripts/utils/docker-manager.sh --status

# Service-specific options
./docker-vtuber/main_app/scripts/utils/docker-manager.sh --autonomous   # Autonomous agent only
./docker-vtuber/main_app/scripts/utils/docker-manager.sh --cognitive    # With Ollama LLM
./docker-vtuber/main_app/scripts/utils/docker-manager.sh --full-stack   # Complete system
```

### Async Docker Builds
```bash
# Interactive mode
python3 docker-vtuber/main_app/scripts/utils/docker-build-monitor.py -f docker-vtuber/docker-compose.autogen-ollama.yml

# Auto mode
python3 docker-vtuber/main_app/scripts/utils/docker-build-monitor.py -f docker-vtuber/docker-compose.autogen-ollama.yml --auto
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
./docker-vtuber/app/AVATAR/tools/monitoring/monitor_autonomous_system_fixed.sh

# Database investigation
./docker-vtuber/app/AVATAR/tools/database/investigate_database.sh

# Health checks
curl http://localhost:3100/health    # Autonomous Agent
curl http://localhost:5001/health    # VTuber System
curl http://localhost:8000/health    # Cognee Memory
```

## High-Level Architecture

### docker-vtuber Project Structure

The system consists of multiple containerized services:

1. **AutoGen Cognitive Agent** (`docker-vtuber/app/CORE/autogen-agent/`)
   - Microsoft AutoGen framework with 3 specialized agents (cognitive_ai, programmer, observer)
   - Intelligent tool selection using context-aware scoring
   - Goal management with SMART framework
   - Darwin-Gödel self-improvement engine (experimental)

2. **VTuber System** (`docker-vtuber/app/AVATAR/`)
   - NeuroSync Player for real-time avatar control
   - Audio-to-face mapping with LiveLink integration
   - Kokoro TTS support
   - Simple boolean activation control

3. **Memory Services**
   - PostgreSQL with pgvector for embeddings (port 5434/5435)
   - Redis for state management (port 6379)
   - Optional Cognee for semantic memory (port 8000)

4. **BYOC WebApp** (`docker-vtuber/app/BYOC/webapp/`)
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

## Important Notes

1. This is a research/experimental platform, not production-ready
2. Focus on autonomous AI agent development with VTuber integration
3. The system emphasizes intelligent decision-making and self-improvement
4. Current issues: Cognee authentication (401 errors), MCP server incomplete
5. Always check container logs when debugging issues
6. Use the docker-manager.sh script as the primary management tool