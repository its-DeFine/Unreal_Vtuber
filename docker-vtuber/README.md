# 🤖 Docker VTuber - Autonomous Agent System

**An intelligent autonomous agent system for managing VTuber experiences through dynamic tool selection and contextual decision-making.**

[![Status](https://img.shields.io/badge/Status-Phase%201%20Complete-green)](./docs/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%2B%20pgvector-blue)](./docs/DATABASE_ANALYSIS.md)
[![Framework](https://img.shields.io/badge/Framework-AutoGen_Cognitive-blue)](./docs/prd/AUTOGEN_COGNITIVE_ENHANCEMENT_PRD.md)

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- PostgreSQL with pgvector extension
- **ElevenLabs API Key** (for TTS)
- **OpenAI API Key** (for LLM)
- Optional Cognee server (started via `docker-compose.bridge.yml`)

### 🔑 Environment Configuration
Before starting the system, create a `.env` file in the project root with the following required API keys:

```bash
# Required API Keys
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Additional AI Provider Keys
ANTHROPIC_API_KEY=your_anthropic_key_here
GROQ_API_KEY=your_groq_key_here

# VTuber System Configuration
VTUBER_PAYMENT_ENABLED=false
VTUBER_ENDPOINT_URL=http://neurosync:5001
```

### 🐳 Docker Initialization

#### Build NeuroSync VTuber System (System 1)
```bash
# Build the NeuroSync containers with clean cache
docker-compose -f docker-compose.neurobridge.yml build --no-cache

# Start the NeuroSync VTuber system
docker-compose -f docker-compose.neurobridge.yml up -d
```

#### Build AutoGen Cognitive System (System 2)
```bash
# Build and start the AutoGen autonomous agent
docker-compose -f docker-compose.bridge.yml build --no-cache
docker-compose -f docker-compose.bridge.yml up -d
```

#### Quick Start with Docker Management Script
```bash
# Build and run all containers
./docker-manager --build-run    # Build and run all containers
./docker-manager --test         # Test the system endpoint
./docker-manager --status       # Check system status
```

### 🗣️ VTuber Communication Methods

#### Direct API Calls to VTuber System
```bash
# Method 1: Direct HTTP POST to NeuroSync
curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test message for the VTuber to speak!", "autonomous_context": true}'

# Method 2: Using the orchestrator endpoint
curl -X POST http://localhost:3000/vtuber/speak \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from the orchestrator!", "emotion": "happy"}'
```

#### Environment Variables for VTuber Control
```bash
# Required environment variables for VTuber communication
VTUBER_ENDPOINT_URL=http://neurosync:5001    # NeuroSync service endpoint
VTUBER_PAYMENT_ENABLED=false                # Disable payment for continuous access
NEUROSYNC_TTS_PROVIDER=kokoro               # TTS provider (kokoro/elevenlabs)
NEUROSYNC_LLM_PROVIDER=openai               # LLM provider for responses
```

### Monitor & Test
```bash
# Monitor autonomous agent activity
./monitor_autonomous_system.sh 10

# Investigate current database state
./investigate_database.sh

# View container logs
./docker-manager --logs
```

---

## 🧠 Dual Cognitive Systems Architecture

This system implements a **dual-process cognitive architecture** inspired by human cognition, with two complementary systems working in harmony:

### 🎭 System 1: NeuroSync (Neural Bridge) - "Fast Thinking"
**Role**: Reactive, intuitive, immediate responses and character embodiment

**Characteristics**:
- **Speed**: Sub-second response times for natural conversation flow
- **Function**: Real-time TTS, facial animation, emotion expression
- **Processing**: Pattern-based, automated responses
- **Technology Stack**: 
  - KOKORO TTS for natural speech synthesis
  - Live Link facial animation system
  - Emotion-driven character control
  - Direct audio/visual output pipeline

**Key Features**:
- Immediate text-to-speech conversion
- Real-time facial expression generation
- Emotion-based animation blending
- Natural conversation timing and flow
- Character personality embodiment

### 🤖 System 2: AutoGen Cognitive - "Slow Thinking"
**Role**: Deliberative, analytical, strategic decision-making and learning

**Characteristics**:
- **Speed**: 30-45 second decision cycles for thoughtful responses
- **Function**: Complex reasoning, tool orchestration, memory management
- **Processing**: Multi-step analysis, pattern learning, strategic planning
- **Technology Stack**:
  - AutoGen orchestrator with MCP tools
  - Cognee knowledge graph memory
  - Darwin-Gödel self-improvement engine
  - Advanced tool selection algorithms

**Key Features**:
- Deep contextual understanding
- Long-term memory and learning
- Complex tool orchestration
- Strategic conversation planning
- Self-optimization and evolution

### 🔄 System Integration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DUAL COGNITIVE FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│  Input → System 2 (AutoGen) Analysis                           │
│    ↓                                                            │
│  Strategic Decision & Context Processing                        │
│    ↓                                                            │
│  System 1 (NeuroSync) Execution                               │
│    ↓                                                            │
│  Immediate TTS + Animation Output                              │
│    ↓                                                            │
│  System 2 Learning & Memory Update                            │
└─────────────────────────────────────────────────────────────────┘
```

**Benefits of Dual System Architecture**:
- **Natural Interaction**: System 1 provides immediate, natural responses
- **Intelligent Depth**: System 2 ensures thoughtful, contextual decision-making  
- **Continuous Learning**: Both systems learn from interactions to improve over time
- **Scalable Intelligence**: Can handle both reactive and complex cognitive tasks
- **Human-like Cognition**: Mirrors human fast/slow thinking processes

---

## 📚 Documentation

**Complete documentation is available in the [`docs/`](./docs/) folder:**

### 🎯 Core Documents
- **[Product Requirements Document](./docs/AUTONOMOUS_AGENT_PRD.md)** - Complete vision and technical specifications
- **[Database Analysis](./docs/DATABASE_ANALYSIS.md)** - Database schema for AutoGen with MCP integration
- **[Implementation Summary](./docs/IMPLEMENTATION_SUMMARY.md)** - What's done and what's next

### 📖 Quick Links
- [System Architecture](./docs/AUTONOMOUS_AGENT_PRD.md#system-architecture)
- [Current Database State](./docs/DATABASE_ANALYSIS.md#current-database-state)
- [Implementation Roadmap](./docs/IMPLEMENTATION_SUMMARY.md#implementation-roadmap)
- [Performance Metrics](./docs/AUTONOMOUS_AGENT_PRD.md#key-performance-indicators-kpis)

---

## 🏗️ System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                 AUTOGEN COGNITIVE ENHANCEMENT                 │
├─────────────────────────────────────────────────────────────────┤
│  🎯 AutoGen Orchestrator Agent                                 │
│  ├── Cognitive Decision Engine with Memory                     │
│  ├── Goal-Directed Autonomous Behavior                         │
│  ├── Darwin-Gödel Self-Improvement                            │
│  └── Advanced Tool Orchestration                               │
├─────────────────────────────────────────────────────────────────┤
│  🔧 MCP Tool Integration Layer                                 │
│  ├── Memory & Context MCP Tool                                 │
│  ├── Cognee Knowledge Graph MCP Tool                          │
│  ├── VTuber Integration MCP Tool                              │
│  └── Analytics & Monitoring MCP Tools                         │
├─────────────────────────────────────────────────────────────────┤
│  🧠 Cognee Knowledge Graph Memory                              │
│  ├── Semantic Relationship Storage                             │
│  ├── Multi-hop Reasoning (5+ degrees)                         │
│  ├── <100ms Complex Graph Queries                             │
│  └── Built-in Graph Storage (No Neo4j needed)                 │
├─────────────────────────────────────────────────────────────────┤
│  🔬 Darwin-Gödel Self-Improvement                              │
│  ├── Safe Code Evolution & Optimization                        │
│  ├── Performance Analysis & Bottleneck Detection              │
│  ├── Sandboxed Testing & Rollback                             │
│  └── 50-100% Performance Improvement Target                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Current Status

### ✅ Phase 1: Foundation Complete
- **Database Integration**: AutoGen with MCP tool for memory access
- **Analytics Enhancement**: Tool usage, decision patterns, context archival
- **System Monitoring**: Comprehensive logging and performance tracking
- **Documentation**: Complete PRD, database analysis, and implementation guide

### 🔄 Phase 2: Intelligent Decision Engine (In Progress)
- **Tool Selection Algorithm**: Multi-criteria decision making
- **Context Analysis**: Intelligent understanding of VTuber state
- **Pattern Learning**: Learn from successful tool combinations
- **Performance Optimization**: Real-time decision quality metrics

---

## 📊 Key Metrics

### Current Performance
- **Memory Storage**: 117 records (69 messages, 24 facts, 24 memories)
- **Decision Frequency**: 30-45 second autonomous cycles
- **Learning Focus**: VR features and innovation discussions
- **System Uptime**: 24/7 autonomous operation

### Target Goals
- **Decision Quality**: 90% intelligent tool selections
- **Response Time**: <30 second decision cycles
- **Memory Efficiency**: 500+ memories with intelligent archival
- **Tool Analytics**: 100% usage tracking and effectiveness scoring

---

## 🛠️ Tools & Scripts

### Container Management
- [`./docker-manager`](./docker-manager) - Unified Docker management script
- [`docs/DOCKER_MANAGEMENT.md`](./docs/DOCKER_MANAGEMENT.md) - Complete Docker management guide

### Database Management
- [`setup_analytics_tables.sql`](./setup_analytics_tables.sql) - Enhance database with analytics
- [`investigate_database.sh`](./investigate_database.sh) - Analyze current database state

### System Monitoring
- [`monitor_autonomous_system.sh`](./monitor_autonomous_system.sh) - Real-time system monitoring
- [`logs/autonomous_monitoring/`](./logs/autonomous_monitoring/) - Historical monitoring data

### Cognee Memory Integration
 - Set `COGNEE_URL` (e.g. `http://cognee:8000`) and `COGNEE_API_KEY` in `.env` to enable long-term memory via Cognee.
 - Configure Cognee as MCP tool in AutoGen agent configuration.

### Configuration
- [`docker-compose.bridge.yml`](./docker-compose.bridge.yml) - Container orchestration
- [`.env`](./.env) - Environment configuration

---

## 🔧 Development

### Architecture
- **Language**: TypeScript/JavaScript (Node.js)
- **Database**: PostgreSQL with pgvector extension
- **Framework**: AutoGen orchestrator with MCP tools
- **Containerization**: Docker & Docker Compose
- **State Management**: Redis for SCB bridge

### Key Components
1. **Autonomous Agent**: Decision-making and tool orchestration
2. **VTuber System**: Real-time character interaction and control
3. **SCB Bridge**: Shared contextual state management
4. **Analytics Engine**: Performance tracking and pattern learning

### Contributing
1. Review the [PRD](./docs/AUTONOMOUS_AGENT_PRD.md) for requirements
2. Check [Database Analysis](./docs/DATABASE_ANALYSIS.md) for current state
3. Follow [Implementation Summary](./docs/IMPLEMENTATION_SUMMARY.md) for next steps
4. Test changes with monitoring tools

---

## 📈 Roadmap

### Phase 2: Intelligent Decision Engine (Next 2 weeks)
- Advanced tool selection algorithm
- Multi-criteria decision making
- Tool dependency management
- Real-time performance metrics

### Phase 3: Enhanced Tool Ecosystem (Month 2)
- Social media management tools
- Analytics and performance tools
- Advanced VTuber control capabilities
- Community interaction management

### Phase 4: Advanced Intelligence (Month 3)
- Predictive decision making
- Multi-agent support
- Cross-session learning
- Self-optimizing algorithms

---

## 🤝 Support

### Documentation
- **Complete Docs**: [`docs/`](./docs/) folder
- **API Reference**: Coming in Phase 2
- **Troubleshooting**: See monitoring logs

### Community
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Contributing**: See development guidelines above

---

**Project Status**: Phase 1 Complete, Phase 2 In Progress 🚀  
**Last Updated**: May 27, 2025  
**Maintained by**: Autonomous Systems Team