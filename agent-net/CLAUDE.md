# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a mock GPU uptime testing application for the Livepeer network that demonstrates client-side punishment logic based on GPU uptime. The project simulates different GPU uptime scenarios to test how job rates are adjusted based on agent performance.

**Latest Update (2025-01-15)**: Simplified to a minimal mock testing server with hardcoded GPU uptime data for testing client-side punishment logic.

## Essential Commands

### Build and Run
```bash
# Build GPU worker container
docker build -f Dockerfile.gpu -t byoc-worker .

# Create Docker network (required before first run)
docker network create byoc

# Start all services (including Caddy webserver)
docker-compose up -d

# Run server locally for development
./run_server_local.sh
```

### Testing
```bash
# Run the demo uptime testing script
python scripts/iam-using/demo_uptime_aware_testing.py

# Test with a specific agent (single orchestrator)
python scripts/iam-using/single_orchestrator_tester.py --agent agent-001 --rate 60

# Test multiple orchestrators
python scripts/iam-using/multi_orchestrator_tester.py \
  --orchestrators "orch1,http://localhost:8088,agent-001" \
                 "orch2,http://localhost:8089,agent-002"
```

## Architecture

### Service Architecture
- **Gateway** (port 9999): Livepeer gateway handling API requests
- **Orchestrator** (port 9995): Manages work distribution to workers
- **Worker** (port 9876): Mock FastAPI server returning hardcoded GPU uptime data
- **Webserver** (port 8088): Caddy reverse proxy routing requests

### Mock Server Implementation

The server (`server/server.py`) is a minimal FastAPI application with:

1. **Mock Agents** - Hardcoded uptime scenarios:
   - `agent-001`: 99.5% uptime → Full job rate (no punishment)
   - `agent-002`: 98.0% uptime → 50% job rate
   - `agent-003`: 92.0% uptime → 10% job rate
   - `agent-004`: 85.0% uptime → 0% job rate (full punishment)

2. **API Endpoints**:
   - `/health` - Basic health check
   - `/gpu-check` - Returns mock GPU data with uptime based on agent_id
   - `/text-to-image` - Echo endpoint that can route GPU check requests

### Client-Side Punishment Logic

The punishment strategy is implemented in the client scripts:
- 99%+ uptime: 100% job rate (base rate)
- 95-99% uptime: 50% job rate  
- 90-95% uptime: 10% job rate
- <90% uptime: 0% job rate (no jobs)

### Request Flow
1. Client → Caddy (8088) → Gateway (9999)
2. Gateway → Orchestrator (9995) → Worker (9876)
3. Worker returns mock GPU uptime data
4. Client applies punishment logic based on uptime

## Testing Scripts

All active scripts are in `scripts/iam-using/`:

1. **demo_uptime_aware_testing.py**
   - Main demo script
   - Tests all four agents sequentially
   - Shows how job rates adjust based on uptime

2. **single_orchestrator_tester.py**
   - Tests a single orchestrator/agent
   - Queries GPU status directly from worker
   - Implements client-side punishment logic
   - Configurable job rates and intervals

3. **multi_orchestrator_tester.py**
   - Tests multiple orchestrators simultaneously
   - Distributes jobs based on agent uptime
   - Provides per-orchestrator statistics

## Development Guidelines

1. **Mock Data**: All GPU uptime values are hardcoded in `MOCK_AGENTS` dictionary in server.py

2. **Dependencies**: Minimal requirements in `requirements-mock.txt`:
   - FastAPI
   - Uvicorn
   - Requests
   - Python-multipart

3. **No GPU Required**: This is a mock testing setup - no actual GPU is needed or checked

4. **Testing Different Scenarios**: Change the agent_id parameter to test different uptime scenarios

## Recent Changes (2025-01-15)

- Removed all complex monitoring systems (ping-based monitoring, GPU health tracking)
- Simplified server to only return mock data
- Removed unnecessary dependencies and modules
- Cleaned up scripts directory - only kept actively used scripts in `iam-using/`
- Enabled Caddy webserver for proper gateway routing
- Created multi-orchestrator testing capability