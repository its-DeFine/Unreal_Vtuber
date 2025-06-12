# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Container Management
```bash
# Primary tool for all Docker operations
./scripts/utils/docker-manager.sh --build-run    # Build and run containers
./scripts/utils/docker-manager.sh --stop         # Stop all containers
./scripts/utils/docker-manager.sh --logs         # Show container logs
./scripts/utils/docker-manager.sh --test         # Test endpoints
./scripts/utils/docker-manager.sh --status       # Check container status

# Service-specific options
./scripts/utils/docker-manager.sh --autonomous   # Run autonomous agent only
./scripts/utils/docker-manager.sh --cognitive    # Run with Ollama LLM
./scripts/utils/docker-manager.sh --full-stack   # Run complete system
```

### Testing
```bash
# Python tests
python test_enhanced_autogen_system.py
python test_goal_metrics_system_complete.py
pytest app/CORE/autogen-agent/tests/test_main.py

# Web app development
cd app/BYOC/webapp && npm run dev
cd app/BYOC/webapp && npm run lint
cd app/BYOC/webapp && npm run build
```

### Monitoring & Debugging
```bash
# Monitor autonomous system
./app/AVATAR/tools/monitoring/monitor_autonomous_system_fixed.sh

# Database investigation
./app/AVATAR/tools/database/investigate_database.sh

# Check service health
curl http://localhost:3100/health    # Autonomous Agent
curl http://localhost:5001/health    # VTuber System
curl http://localhost:8000/health    # Cognee Memory
```

## High-Level Architecture

This is a modular autonomous agent system built on containerized microservices:

### Core Components

1. **AutoGen Cognitive Agent** (`app/CORE/autogen-agent/`)
   - Microsoft AutoGen framework for multi-agent LLM conversations
   - MCP (Model Context Protocol) tool integration
   - Goal management with SMART goal creation and metrics tracking
   - Darwin-Gödel self-improvement capabilities
   - Autonomous decision-making with memory integration

2. **VTuber System** (`app/AVATAR/`)
   - NeuroSync Player for real-time avatar control
   - Audio-to-face mapping and LiveLink integration
   - Local TTS with Kokoro support
   - Conditional activation via tools

3. **Cognee Service** (`app/CORE/cognee-service/`)
   - Knowledge graph for long-term memory
   - Semantic relationship management
   - Multi-hop reasoning capabilities
   - Integration with AutoGen via MCP tools

4. **BYOC WebApp** (`app/BYOC/webapp/`)
   - React/Vite frontend with TypeScript
   - Audio recording and processing
   - Web3 wallet connectivity
   - Real-time system interaction

### Service Architecture
```
- Autonomous Agent → Port 3100
- VTuber System → Port 5001
- SCB Bridge → Port 5000
- Cognee Memory → Port 8000
- PostgreSQL → Port 5434
- Redis → Port 6379
```

### Critical Development Rules

1. **Container-First Development**: NEVER run npm/pip commands on host
   ```bash
   # ✅ Correct
   docker exec -it autonomous-agent npm install <package>
   
   # ❌ Wrong - breaks containerized development
   npm install <package>
   ```

2. **Environment Configuration**
   - Main config: `.env` file in project root
   - API keys and secrets in `.env`, never in docker-compose files
   - Service URLs use container names (e.g., `http://cognee:8000`)

3. **Plugin Development** (ElizaOS pattern)
   - Plugins in `autonomous-starter/src/plugin-*` directories
   - Follow action/service/provider/evaluator structure
   - Use runtime.getSetting() for configuration
   - Comprehensive logging with structured data

4. **Database Access**
   - PostgreSQL with pgvector extension
   - ElizaOS schema (13 core tables)
   - Connection: `postgresql://postgres:postgres@postgres:5432/autonomous_agent`
   - Enhanced analytics tables for decision tracking

### Key Integration Points

1. **AutoGen ↔ Cognee**: Memory storage and retrieval via MCP tools
2. **AutoGen ↔ VTuber**: Conditional activation and control
3. **AutoGen ↔ SCB/AgentNet**: State management via Redis
4. **All Services**: Comprehensive logging to PostgreSQL analytics tables

### Testing Strategy
- Unit tests for individual components
- Integration tests for service communication
- Goal management system tests for autonomous behavior
- Always verify with monitoring scripts after changes

### Performance Targets
- Decision cycle time: <30 seconds
- Memory query response: <100ms
- Tool execution: Context-aware selection
- System uptime: 24/7 autonomous operation