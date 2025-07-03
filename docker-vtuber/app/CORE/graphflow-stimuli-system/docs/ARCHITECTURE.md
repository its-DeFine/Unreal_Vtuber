# GraphFlow External Stimuli System - Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           GraphFlow External Stimuli System                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────┐                            ┌────────────────────────┐         │
│  │  API Gateway     │                            │  WebSocket Gateway    │         │
│  │  (FastAPI)       │                            │  (Real-time)          │         │
│  └────────┬─────────┘                            └──────────┬─────────────┘         │
│           │                                                  │                       │
│           └──────────────────┬───────────────────────────────┘                       │
│                              │                                                       │
│                              ▼                                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐         │
│  │                    GraphFlow Gateway Agent                              │         │
│  │  ┌─────────────────────────────────────────────────────────────┐      │         │
│  │  │                  Request Context Manager                      │      │         │
│  │  │  • Concurrent request tracking                               │      │         │
│  │  │  • Rate limiting & throttling                                │      │         │
│  │  │  • Request validation                                        │      │         │
│  │  └─────────────────────────────────────────────────────────────┘      │         │
│  └────────────────────────────────┬──────────────────────────────────────┘         │
│                                   │                                                  │
│                                   ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐         │
│  │                        Stimuli Flow Manager                            │         │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │         │
│  │  │ Categorizer │───▶│  Analyzer   │───▶│  Context    │              │         │
│  │  │    Node     │    │    Node     │    │  Enricher   │              │         │
│  │  └─────────────┘    └─────────────┘    └─────────────┘              │         │
│  └────────────────────────────────┬──────────────────────────────────────┘         │
│                                   │                                                  │
│                                   ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐         │
│  │                        Decision Flow Manager                           │         │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │         │
│  │  │   Router    │───▶│  Decision   │───▶│  Executor   │              │         │
│  │  │    Node     │    │   Engine    │    │    Node     │              │         │
│  │  └─────────────┘    └─────────────┘    └─────────────┘              │         │
│  └────────────────────────────────┬──────────────────────────────────────┘         │
│                                   │                                                  │
│                                   ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐         │
│  │                         System Interfaces                              │         │
│  │  ┌─────────────────────┐              ┌─────────────────────┐        │         │
│  │  │  System1 Interface  │              │  System2 Interface  │        │         │
│  │  │  (Avatar/Speech)    │              │  (Multi-Agent)      │        │         │
│  │  └─────────────────────┘              └─────────────────────┘        │         │
│  └────────────────────────────────┬──────────────────────────────────────┘         │
│                                   │                                                  │
└───────────────────────────────────┼──────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
          ┌─────────────────┐             ┌─────────────────┐
          │ NeuroSync VTuber│             │ AutoGen Agents  │
          │     System      │             │    System       │
          └─────────────────┘             └─────────────────┘
```

## Component Relationships

### 1. API Layer
The system provides two main entry points for external stimuli:

- **REST API Gateway**: Traditional HTTP endpoints for synchronous submission
- **WebSocket Gateway**: Real-time bidirectional communication for streaming

Both gateways implement:
- API key authentication with permission-based access control
- Rate limiting per API key
- Request validation and sanitization
- Metrics collection for all requests

### 2. Core Processing Pipeline

#### GraphFlow Gateway Agent
The central orchestrator that manages the entire processing pipeline:
- Implements request context management for concurrent processing
- Coordinates flow managers and system interfaces
- Handles health monitoring and metrics aggregation
- Manages graceful shutdown and resource cleanup

#### Stimuli Flow Manager
Processes incoming stimuli through three stages:
1. **Categorizer Node**: Classifies stimuli using LLM and pattern matching
2. **Analyzer Node**: Performs deep contextual analysis
3. **Context Enricher**: Augments with historical and environmental context

#### Decision Flow Manager
Makes routing decisions and plans execution:
1. **Router Node**: Applies decision matrix rules
2. **Decision Engine**: Evaluates complex conditions
3. **Executor Node**: Coordinates system integration

### 3. Integration Layer

#### System1 Interface (Avatar/Speech)
- Connects to NeuroSync VTuber system
- Triggers immediate avatar responses
- Manages TTS and visual expressions
- Handles character state synchronization

#### System2 Interface (Multi-Agent)
- Integrates with AutoGen agent system
- Routes to specialized agents (cognitive, programmer, observer)
- Manages asynchronous analysis workflows
- Aggregates multi-agent responses

## Data Flow Diagrams

### Stimuli Processing Flow
```
External Stimuli
       │
       ▼
┌─────────────┐
│  Validate   │
│  & Enrich   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│ Categorize  │────▶│ Cache Check  │
└──────┬──────┘     └──────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│   Analyze   │────▶│Context Store │
└──────┬──────┘     └──────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐
│Make Decision│────▶│Decision Matrix│
└──────┬──────┘     └──────────────┘
       │
       ├─────────────┬──────────────┐
       ▼             ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│Option A:    │ │Option B:    │ │Option C:    │
│Avatar+Agent │ │Agent Only   │ │Log Only     │
└─────────────┘ └─────────────┘ └─────────────┘
```

### Decision Routing Flow
```
Analyzed Stimuli
       │
       ▼
┌─────────────────┐
│ Load Decision   │
│    Matrix       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Check Emergency │──Yes──▶ Emergency Override
│    Rules        │
└────────┬────────┘
         │No
         ▼
┌─────────────────┐
│ Evaluate User   │
│   Context       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Apply Category  │
│  Specific Rules │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Generate Routing │
│   Decision      │
└─────────────────┘
```

## Integration Points

### 1. External Systems

#### NeuroSync VTuber System
- **Endpoint**: `http://neurosync:5001`
- **Protocol**: REST API with JSON
- **Functions**:
  - Trigger speech synthesis
  - Update avatar expressions
  - Query character state
  - Control streaming status

#### AutoGen Multi-Agent System
- **Endpoint**: `http://autogen-agent:3100`
- **Protocol**: REST API with JSON/WebSocket
- **Functions**:
  - Submit analysis tasks
  - Query agent status
  - Retrieve analysis results
  - Manage agent lifecycle

### 2. Infrastructure Services

#### Redis Cache
- **Purpose**: High-speed caching and state management
- **Usage**:
  - Categorization cache
  - Session state storage
  - Rate limiting counters
  - Real-time metrics

#### PostgreSQL Database
- **Purpose**: Persistent storage and analytics
- **Schema**:
  - Stimuli history
  - Processing results
  - Decision audit log
  - Context accumulation

#### Prometheus/Grafana
- **Purpose**: Metrics collection and visualization
- **Metrics**:
  - Processing latency
  - Throughput rates
  - Error rates
  - System resource usage

### 3. Configuration Services

#### Decision Matrix
- **Location**: `config/decision_matrix.json`
- **Hot-reload**: Supported via file watcher
- **Validation**: Schema-based validation

#### Emergency Override
- **Location**: `config/emergency_override.py`
- **Purpose**: Runtime rule injection
- **Security**: Admin-only access

## Security Architecture

### Authentication & Authorization
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  API Key    │────▶│ Permission  │────▶│  Resource   │
│  Validation │     │   Check     │     │   Access    │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Data Flow Security
- **Encryption**: TLS 1.3 for all external communication
- **Validation**: Input sanitization at entry points
- **Isolation**: Container-based service isolation
- **Audit**: Comprehensive logging of all decisions

## Scalability Design

### Horizontal Scaling
- **API Gateway**: Load balancer with multiple instances
- **Processing Nodes**: Stateless design for easy scaling
- **Queue Management**: Redis-based work distribution

### Performance Optimization
- **Caching Strategy**: Multi-level caching (memory, Redis)
- **Batch Processing**: Aggregation of similar requests
- **Connection Pooling**: Reusable connections to external systems

### Resource Management
- **Concurrent Limits**: Configurable per-node limits
- **Circuit Breakers**: Automatic degradation on failures
- **Backpressure**: Queue-based flow control