# 🧠 AutoGen Python Agent - Product Requirements Document (PRD)

**Version**: 1.0
**Date**: June 11, 2025
**Status**: Draft
**Team**: Autonomous Systems

---

## 📋 Executive Summary

The AutoGen Python Agent will introduce a new autonomous agent built with the [AutoGen](https://github.com/microsoft/autogen) framework. It will replace the existing HardNet agent with a lightweight, Python-based implementation focused on modular tool integration and streamlined decision loops. The agent will reside in a new top-level folder and interact with existing VTuber, SCB, and database components.

## 🎯 Product Vision

**"A modular Python agent that uses AutoGen to autonomously manage VTuber interactions and bridge data across the system."**

### Core Principles
- **Simplicity**: Pure Python implementation for easier experimentation
- **Extensibility**: Pluggable actions using AutoGen agents and tools
- **Compatibility**: Seamless integration with current PostgreSQL, Redis, and VTuber endpoints
- **Replaceability**: Fully replaces the HardNet TypeScript agent once feature parity is achieved

---

## 🏗️ System Architecture Overview

```text
┌────────────────────────────────────────┐
│            AUTOGEN PYTHON AGENT        │
├────────────────────────────────────────┤
│  🔄 Decision Loop (async)             │
│  🛠️ Tool Registry (Python modules)    │
│  🧠 Memory Manager (pgvector)          │
│  🔗 SCB & VTuber API Clients          │
└────────────────────────────────────────┘
```

### Key Components
1. **Decision Loop** – Periodic evaluation of context and tool invocation
2. **Tool Registry** – Python modules implementing AutoGen tool interfaces
3. **Memory Manager** – Vector store using pgvector for context retrieval
4. **Integration Clients** – Connectors to SCB Redis, VTuber API, and database

---

## 🎯 Core Requirements

1. **Python First**
   - Use Python 3.11+
   - Built on the AutoGen framework with asynchronous flows
2. **Pluggable Tools**
   - Each tool is a Python module exposing `run()` and metadata
   - Tools configurable via YAML/JSON
3. **Context Storage**
   - Interface with existing PostgreSQL schema (memories table)
   - Use embeddings for retrieval with pgvector
4. **SCB & VTuber Integration**
   - REST/Redis clients for communication
   - Support existing endpoints defined in the current agent
5. **Deployment**
   - Dockerfile for the new agent container
   - Compose entry in `docker-compose.bridge.yml`

---

## 🚀 Milestones

| Phase | Goal | Target Date |
|-------|------|-------------|
| 1 | Setup AutoGen base project and tool registry | Week 1 |
| 2 | Implement memory manager and SCB/VTuber clients | Week 2 |
| 3 | Achieve feature parity with HardNet | Week 3 |
| 4 | Migrate production workloads and deprecate HardNet | Week 4 |

---

## 📊 Success Metrics
- **Decision Cycle Time** < 20 seconds
- **Tool Execution Success Rate** > 95%
- **Memory Retrieval Accuracy** > 90%
- **Deployment Simplicity**: single container replacing HardNet

---

## 🤝 Stakeholders
- Product Management
- Autonomous Systems Team
- VTuber Platform Team
- Community Moderation Team

