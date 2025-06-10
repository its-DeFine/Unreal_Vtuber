# 🧩 AutoGen Python Agent - Functional Requirements Document (FRD)

**Version**: 1.0
**Date**: June 11, 2025
**Status**: Draft

---

## 📋 Purpose
This document details the functional requirements for the new AutoGen Python Agent. The goal is to deliver a fully autonomous agent built with Python that can replicate and enhance the features of the current HardNet agent.

## 🔍 Functional Overview
1. **Startup Configuration**
   - Read environment variables for database, Redis, and VTuber endpoints
   - Load tool modules from a configurable folder
2. **Decision Loop**
   - Execute every 20–30 seconds
   - Retrieve recent context from PostgreSQL
   - Select and run tools using AutoGen agents
   - Persist new memories back to the database
3. **Tool Interface**
   - Each tool exposes:
     ```python
     def run(context: dict) -> dict:
         ...
     ```
   - Metadata defines name, description, and parameters
4. **Memory Management**
   - Store conversation history with embeddings
   - Provide retrieval helpers for similarity search
5. **SCB & VTuber API Clients**
   - Redis-based SCB client for real-time state updates
   - HTTP client for sending prompts to the VTuber system
6. **Logging & Monitoring**
   - Structured logs with timestamps and loop metrics
   - Optional integration with existing monitoring scripts
7. **Deployment**
   - Dockerfile building from a slim Python image
   - `docker-compose.bridge.yml` entry for `autogen_agent`
   - Health endpoint at `/api/health`

## ✅ Acceptance Criteria
- Agent runs in Docker and connects to PostgreSQL, Redis, and VTuber services
- Decision loop successfully triggers tools and stores results
- Health check returns `200 OK`
- Logs show tool usage and loop duration

---

## 🗂️ Folder Structure (Proposed)
```
autogen-agent/
├── Dockerfile
├── README.md
├── autogen_agent/
│   ├── __init__.py
│   ├── main.py
│   ├── tool_registry.py
│   ├── memory_manager.py
│   ├── clients/
│   │   ├── scb_client.py
│   │   └── vtuber_client.py
│   └── tools/
│       └── example_tool.py
└── tests/
    └── test_main.py
```

---

## ⏳ Future Enhancements
- Parallel tool execution using asyncio tasks
- Plugin system for third-party tool packages
- Optional UI dashboard for real-time monitoring

