# 🤖 Docker VTuber - Autonomous Agent System

**An intelligent autonomous agent system for managing VTuber experiences through dynamic tool selection and contextual decision-making.**

[![Status](https://img.shields.io/badge/Status-Phase%201%20Complete-green)](./docs/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%2B%20pgvector-blue)](./docs/DATABASE_ANALYSIS.md)
[![Framework](https://img.shields.io/badge/Framework-ElizaOS-purple)](./docs/AUTONOMOUS_AGENT_PRD.md)

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- PostgreSQL with pgvector extension
- OpenAI API key
- Optional Cognee server (started via `docker-compose.bridge.yml`)

### Launch System
```bash
# Quick start with Docker management script
./docker-manager --build-run    # Build and run all containers
./docker-manager --test         # Test the system endpoint
./docker-manager --status       # Check system status

# Alternative: Manual commands
docker-compose -f docker-compose.bridge.yml up -d
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

## 📚 Documentation

**Complete documentation is available in the [`docs/`](./docs/) folder:**

### 🎯 Core Documents
- **[Product Requirements Document](./docs/AUTONOMOUS_AGENT_PRD.md)** - Complete vision and technical specifications
- **[Database Analysis](./docs/DATABASE_ANALYSIS.md)** - Current system state and ElizaOS integration
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
│                    AUTONOMOUS VTUBER SYSTEM                    │
├─────────────────────────────────────────────────────────────────┤
│  🧠 Autonomous Agent (Port 3100)                              │
│  ├── ElizaOS Framework Integration                            │
│  ├── 117 Active Memories (VR-focused learning)               │
│  ├── 4 Tool Arsenal (VTuber, Research, Context, SCB)         │
│  └── Enhanced Analytics (tool_usage, decision_patterns)       │
├─────────────────────────────────────────────────────────────────┤
│  🎭 VTuber System (Port 5001)                                 │
│  ├── NeuroSync Player                                         │
│  ├── Emotion & Behavior Control                              │
│  └── Real-time VTuber Interaction                            │
├─────────────────────────────────────────────────────────────────┤
│  🔗 SCB Bridge (Port 5000)                                    │
│  ├── Shared Contextual Bridge                                │
│  ├── Redis State Management                                  │
│  └── Real-time Mind-State Sync                               │
├─────────────────────────────────────────────────────────────────┤
│  🗄️ Database Layer                                            │
│  ├── PostgreSQL + pgvector (Port 5434)                       │
│  ├── ElizaOS Schema (13 tables)                              │
│  └── Analytics Enhancement (3 new tables)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Current Status

### ✅ Phase 1: Foundation Complete
- **Database Integration**: ElizaOS framework with 117 active memories
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
 - Include `@elizaos/plugin-cognee` in your runtime plugins list.

### Configuration
- [`docker-compose.bridge.yml`](./docker-compose.bridge.yml) - Container orchestration
- [`.env`](./.env) - Environment configuration

---

## 🔧 Development

### Architecture
- **Language**: TypeScript/JavaScript (Node.js)
- **Database**: PostgreSQL with pgvector extension
- **Framework**: ElizaOS for agent intelligence
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