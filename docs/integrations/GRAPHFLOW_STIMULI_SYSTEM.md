# GraphFlow Stimuli System Integration

## Overview

The GraphFlow Stimuli System is a sophisticated event-driven architecture component that handles external stimuli processing and routing within the autonomy system.

## System Location

The complete GraphFlow Stimuli System documentation and implementation is located at:
```
docker-vtuber/app/CORE/graphflow-stimuli-system/
```

## Product Requirements
- **[GRAPHFLOW_SYSTEM_PRD.md](./GRAPHFLOW_SYSTEM_PRD.md)** - Product requirements document
- **[GRAPHFLOW_SYSTEM_FRD.md](./GRAPHFLOW_SYSTEM_FRD.md)** - Functional requirements document

## Documentation Structure

### Main Documentation
- **README.md** - Comprehensive system overview and quick start
- **docs/ARCHITECTURE.md** - System architecture documentation
- **docs/API.md** - API reference and endpoints
- **docs/DEVELOPER_GUIDE.md** - Development guide and patterns

### Implementation Guides
- **docs/ANALYZER_NODE_IMPLEMENTATION.md** - Analyzer node implementation details
- **docs/CODE_WALKTHROUGH.md** - Code structure walkthrough
- **docs/MAIN_ENTRY_POINT.md** - System entry point documentation

### Operations
- **docs/CONFIGURATION.md** - Configuration guide
- **docs/DEPLOYMENT.md** - Deployment instructions
- **docs/CONTAINER_TESTING_GUIDE.md** - Container testing procedures

### Compliance & Security
- **COMPLIANCE_REPORT.md** - Compliance documentation
- **SECURITY_AUDIT_REPORT.md** - Security audit findings
- **VERIFICATION_REPORT.md** - System verification report
- **PIPELINE_FLOW_ANALYSIS.md** - Pipeline flow analysis

## Integration Points

The GraphFlow system integrates with:
- **AutoGen Agents** - via System1/System2 interfaces
- **VTuber System** - via TTS and orchestration clients
- **Cognee Memory** - via cognitive integration
- **PostgreSQL** - for data persistence

## Quick Start

To work with the GraphFlow system, navigate to its directory:
```bash
cd docker-vtuber/app/CORE/graphflow-stimuli-system/
```

Refer to the comprehensive README.md file in that directory for setup and usage instructions.

## Development

For development work on the GraphFlow system, consult:
1. `docs/DEVELOPER_GUIDE.md` for development patterns
2. `docs/CONFIGURATION.md` for configuration options
3. `docs/CONTAINER_TESTING_GUIDE.md` for testing procedures

The GraphFlow system maintains its own comprehensive documentation structure and should be referenced directly for detailed implementation work.