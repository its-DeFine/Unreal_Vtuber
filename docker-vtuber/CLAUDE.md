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

# Docker Build Monitor - For async builds with progress tracking
python3 scripts/utils/docker-build-monitor.py -f docker-compose.autogen-ollama.yml  # Interactive mode
python3 scripts/utils/docker-build-monitor.py -f docker-compose.autogen-ollama.yml --auto  # Auto mode

# The build monitor provides:
# - Async Docker Compose builds that don't block the terminal
# - Real-time log monitoring saved to docker-build.log
# - Build completion detection and status checking
# - Interactive commands: status, logs, stop, exit
# Use this when you need to run docker compose up -d --build and continue working
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

This is an experimental AI research platform built on containerized microservices. **Note: This is a research/development system, not production-ready.**

### Core Components

1. **AutoGen Cognitive Agent** (`app/CORE/autogen-agent/`)
   - Microsoft AutoGen framework with 3 specialized agents:
     - `cognitive_ai_agent`: Overall coordination and insights
     - `programmer_agent`: Code optimization and improvements  
     - `observer_agent`: Performance monitoring and analytics
   - Intelligent tool selection using context-aware scoring (NOT random)
   - Goal management with SMART goal creation and metrics tracking
   - Darwin-Gödel self-improvement capabilities (experimental)
   - MCP server skeleton (NOT fully implemented)

2. **VTuber System** (`app/AVATAR/`)
   - NeuroSync Player for real-time avatar control
   - Audio-to-face mapping and LiveLink integration
   - Local TTS with Kokoro support
   - Simple boolean activation flag (not sophisticated conditional logic)

3. **Cognee Service** (REMOVED - was in `app/CORE/cognee-service/`)
   - Now integrated as HTTP API calls from AutoGen
   - Runs as separate container service (when enabled)
   - NOT an embedded library - requires external service
   - Knowledge graph for semantic memory
   - Note: Authentication issues reported (401 errors)

4. **BYOC WebApp** (`app/BYOC/webapp/`)
   - React/Vite frontend with TypeScript
   - Audio recording and processing
   - Web3 wallet connectivity (mentioned but not verified)
   - Real-time system interaction

### Service Architecture
```
- Autonomous Agent → Port 3100 (or 8200/8201 depending on config)
- VTuber System → Port 5001
- SCB Bridge → Port 5000  
- Cognee Memory → Port 8000 (when running as separate service)
- PostgreSQL → Port 5434 (or 5435 in some configs)
- Redis → Port 6379
- Ollama LLM → Port 11434 (for local inference)
```

### Deployment Configurations

1. **autogen-ollama**: Local LLM with Ollama, no external dependencies
2. **cognitive**: Full features with evolution engine (experimental)
3. **bridge**: Complete stack with all services integrated

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

### Important Notes for Future Development

1. **This is a research platform**, not a production system
2. **Cognee runs as a service**, not an embedded library
3. **MCP integration is incomplete** - needs implementation for Cursor IDE
4. **Error handling is basic** - needs hardening for production use
5. **Monitoring is minimal** - add comprehensive observability for production