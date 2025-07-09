# AutoGen Agent - Refactored Structure

## Overview

The AutoGen Agent module has been refactored for better organization and maintainability. The new structure follows Python best practices with clear separation of concerns.

## Directory Structure

```
autogen_agent/
├── __init__.py           # Main package initialization
├── main.py              # Application entry point
├── api/                 # REST API endpoints
│   ├── __init__.py
│   └── stimuli_api.py   # Stimuli processing endpoints
├── clients/             # External service clients
│   ├── __init__.py
│   ├── scb_client.py    # Shared Context Blackboard client
│   ├── scb_client_enhanced.py
│   └── vtuber_client.py # VTuber system client
├── config/              # Configuration modules
│   ├── __init__.py
│   └── autonomy_config.py # Graduated autonomy system
├── core/                # Core business logic
│   ├── __init__.py
│   ├── agent_tool_bridge.py
│   ├── objective_bridge.py
│   ├── stimuli_autogen_team.py
│   ├── stimuli_orchestrator.py
│   └── tool_registry.py # Enhanced tool registry
├── evolution/           # Darwin-Gödel evolution system
│   ├── cognitive_evolution_engine.py
│   ├── darwin_godel_engine.py
│   └── llm_code_generator.py
├── services/            # Service layer
│   ├── conversation_storage_service.py
│   ├── evolution_service.py
│   ├── goal_management_service.py
│   ├── graph_consolidation_service.py
│   ├── neo4j_semantic_storage.py
│   └── stimuli_graph_connector.py
├── tools/               # Tool implementations
│   ├── __init__.py
│   ├── scb_operations_tool.py # NEW: SCB operations
│   ├── tool_management.py     # NEW: Tool management meta-tool
│   └── [other tools...]
└── utils/               # Utility modules
    ├── __init__.py
    ├── async_utils.py
    ├── capacity_monitor.py
    └── statistics_collector.py
```

## Key Changes in Refactoring

### 1. Module Organization
- **api/**: All REST API endpoints
- **clients/**: External service integrations
- **config/**: Configuration and settings
- **core/**: Core business logic and orchestration
- **services/**: Service layer for data management
- **tools/**: All tool implementations
- **utils/**: Shared utilities

### 2. Import Structure
All imports now use the full module path:
```python
from autogen_agent.core import ToolRegistry
from autogen_agent.config import get_autonomy_manager
from autogen_agent.tools.scb_operations_tool import run
```

### 3. Enhanced Capabilities
- **SCB Operations Tool**: Direct blackboard access for agents
- **Dynamic Tool Registration**: Runtime tool creation with safety validation
- **Graduated Autonomy**: 5-level system (OBSERVER → AUTONOMOUS)
- **Tool Management**: Meta-tool for tool lifecycle management

### 4. Test Organization
Tests have been moved to `/docker-vtuber/tests/autogen-agent/` with proper setup:
- `test_setup.py`: Common test configuration
- Enhanced capabilities tests achieving 100% pass rate
- Proper pytest integration with asyncio support

## Running the System

### Development
```bash
cd /home/geo/directories/autonomy/docker-vtuber/app/CORE/autogen-agent
python -m autogen_agent.main
```

### Testing
```bash
cd /home/geo/directories/autonomy/docker-vtuber/tests/autogen-agent
python3 -m pytest test_enhanced_capabilities.py -v
```

## Documentation

All documentation has been moved to the main docs folder:
- `/home/geo/directories/autonomy/docs/autogen-agent/`

Key documents:
- `autonomous_team_architecture.md`: System architecture
- `autonomous_team_capabilities_guide.md`: What the team can/cannot do
- `autonomous_team_scb_integration.md`: SCB integration details
- `enhanced_capabilities_implementation.md`: New features summary

## Migration Notes

### For Developers
1. Update all imports to use `autogen_agent.` prefix
2. Use the provided `update_imports.py` script for bulk updates
3. Ensure test files import from the correct paths

### Removed/Deprecated
- Cognee integration (replaced by Neo4j)
- Old lib folder (functionality integrated into main modules)
- Backup files and outdated code

## Future Improvements
1. Complete integration of all tests
2. Add more comprehensive error handling
3. Implement full Darwin-Gödel self-improvement
4. Enhance tool safety validation