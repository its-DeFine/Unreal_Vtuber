# AutoGen Agent System Documentation

Welcome to the comprehensive documentation for the AutoGen Agent System - a sophisticated autonomous AI platform built on Microsoft's AutoGen framework with advanced self-improvement capabilities.

## 📋 Documentation Overview

This documentation suite provides complete coverage of the system architecture, APIs, configuration, and maintenance procedures. It's designed to enable easy future modifications and cross-referencing.

### 📚 Documentation Structure

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[System Documentation](AUTOGEN_SYSTEM_DOCUMENTATION.md)** | Complete system overview, architecture, and component relationships | Understanding the system, planning changes |
| **[Functions Reference](AUTOGEN_FUNCTIONS_REFERENCE.md)** | Detailed function-level documentation with parameters and examples | Development, debugging, API integration |
| **[Configuration Guide](AUTOGEN_CONFIGURATION_GUIDE.md)** | Environment setup, tuning, and deployment configurations | System setup, performance optimization |
| **[API Reference](AUTOGEN_API_REFERENCE.md)** | MCP endpoints, data structures, and troubleshooting | External integration, debugging |

---

## 🏗️ System Architecture Quick Start

### Core Components

```mermaid
graph TD
    A[Main Application] --> B[Multi-Agent Collaboration]
    A --> C[Tool Registry & Selection]
    A --> D[Memory & Learning System]
    A --> E[Darwin-Gödel Evolution]
    
    B --> F[AutoGen Agents]
    C --> G[Tool Execution Bridge]
    D --> H[Cognee Knowledge Graph]
    E --> I[Code Analysis & Generation]
    
    A --> J[External Integrations]
    J --> K[SCB - Shared Cognitive Blackboard]
    J --> L[VTuber System]
    J --> M[MCP Server]
```

### Key Features

- **🤖 Multi-Agent Reasoning** - Microsoft AutoGen with teachable agents
- **🧠 Intelligent Tool Selection** - Context-aware scoring algorithm (40% context, 30% performance, 20% recent success, 10% diversity)
- **💾 Semantic Memory** - Cognee knowledge graph for long-term learning
- **🧬 Self-Evolution** - Darwin-Gödel Machine for autonomous code improvement
- **📊 Comprehensive Analytics** - Performance tracking and optimization
- **🔌 Flexible Integration** - MCP, REST, WebSocket APIs

---

## 🚀 Quick Start Guide

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+ (optional, for SCB)
- Ollama (optional, for local LLM)

### Basic Setup

1. **Clone and Install**
   ```bash
   git clone <repository>
   cd autogen-agent
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   # Copy template
   cp .env.example .env
   
   # Edit configuration
   export DATABASE_URL=postgresql://user:pass@localhost:5432/autogen
   export USE_OLLAMA=true
   export OLLAMA_MODEL=llama3.1:8b
   ```

3. **Initialize Database**
   ```bash
   # Create database and tables
   python -m autogen_agent.setup_database
   ```

4. **Start the System**
   ```bash
   # Autonomous mode
   python -m autogen_agent.main --mode autonomous
   
   # MCP server mode
   python -m autogen_agent.main --mode mcp
   ```

### Docker Quick Start

```bash
# Using docker-compose
docker-compose up -d

# Check status
curl http://localhost:8080/health
```

---

## 📖 How to Use This Documentation

### For New Users

1. **Start with [System Documentation](AUTOGEN_SYSTEM_DOCUMENTATION.md)** - Get familiar with the architecture and components
2. **Review [Configuration Guide](AUTOGEN_CONFIGURATION_GUIDE.md)** - Set up your environment properly
3. **Check [API Reference](AUTOGEN_API_REFERENCE.md)** - Learn about integration options

### For Developers

1. **[Functions Reference](AUTOGEN_FUNCTIONS_REFERENCE.md)** - Detailed function documentation
2. **[System Documentation](AUTOGEN_SYSTEM_DOCUMENTATION.md)** - Integration patterns and cross-references
3. **[API Reference](AUTOGEN_API_REFERENCE.md)** - Data structures and error handling

### For System Administrators

1. **[Configuration Guide](AUTOGEN_CONFIGURATION_GUIDE.md)** - Production deployment and tuning
2. **[API Reference](AUTOGEN_API_REFERENCE.md)** - Monitoring and troubleshooting
3. **[System Documentation](AUTOGEN_SYSTEM_DOCUMENTATION.md)** - Maintenance procedures

---

## 🔄 System Operation Modes

### Autonomous Mode
Continuous operation with self-improvement capabilities
```bash
python -m autogen_agent.main --mode autonomous
```

### MCP Server Mode
Model Context Protocol server for development integration
```bash
python -m autogen_agent.main --mode mcp
```

### Test Mode
Development and testing mode with enhanced logging
```bash
python -m autogen_agent.main --mode test
```

---

## 🛠️ Key Configuration Options

### Essential Environment Variables

```bash
# Core System
LOOP_INTERVAL=60                    # Seconds between cycles
LOG_LEVEL=INFO                      # Logging verbosity
DATABASE_URL=postgresql://...       # Database connection

# LLM Configuration
USE_OLLAMA=true                     # Enable Ollama
OLLAMA_MODEL=llama3.1:8b           # Model selection
OLLAMA_URL=http://localhost:11434   # Ollama endpoint

# Integrations
AGENTNET_ENABLED=true               # Enable SCB publishing
REDIS_URL=redis://localhost:6379/0  # Redis for SCB
VTUBER_ENDPOINT=http://localhost:8000 # VTuber integration

# Safety Settings
DARWIN_GODEL_REAL_MODIFICATIONS=false  # Code modification safety
DARWIN_GODEL_REQUIRE_APPROVAL=true     # Human approval required
```

### Performance Tuning

```bash
# High-Performance Configuration
MAX_WORKER_THREADS=16
ASYNC_BATCH_SIZE=5
DB_POOL_SIZE=50
TOOL_CACHE_SIZE=2000
```

Refer to [Configuration Guide](AUTOGEN_CONFIGURATION_GUIDE.md) for complete options.

---

## 🔗 Integration Examples

### MCP Integration

```python
# Connect to AutoGen MCP server
from mcp.client.stdio import stdio_client

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        # Get system status
        result = await session.call_tool("get_cognitive_status", {})
        
        # Trigger decision cycle
        result = await session.call_tool("trigger_cognitive_decision", {
            "context": {"priority": "high"}
        })
```

### REST API Integration

```python
import requests

# Get system status
response = requests.get("http://localhost:8080/api/status")
status = response.json()

# Trigger evolution cycle
response = requests.post("http://localhost:8080/api/evolution", 
                        json={"safety_mode": True})
```

See [API Reference](AUTOGEN_API_REFERENCE.md) for complete integration examples.

---

## 📊 Monitoring & Health Checks

### Health Check Endpoints

```bash
# Basic health check
curl http://localhost:8080/health

# Detailed system status
curl http://localhost:8080/status | jq .

# Performance metrics
curl http://localhost:8080/metrics
```

### Key Metrics to Monitor

- **Success Rate** - Percentage of successful decision cycles
- **Decision Time** - Average time per cycle
- **Memory Usage** - System memory consumption
- **Tool Diversity** - Distribution of tool usage
- **Evolution Frequency** - Self-improvement cycles per period

---

## 🔧 Troubleshooting Quick Reference

### Common Issues

| Problem | Quick Fix | Documentation |
|---------|-----------|---------------|
| System won't start | Check DATABASE_URL and dependencies | [Configuration Guide](AUTOGEN_CONFIGURATION_GUIDE.md#troubleshooting) |
| No tool selection | Verify tools loaded with `grep "Tool loaded"` | [API Reference](AUTOGEN_API_REFERENCE.md#troubleshooting-guide) |
| High memory usage | Reduce batch sizes and pool settings | [Configuration Guide](AUTOGEN_CONFIGURATION_GUIDE.md#performance-tuning) |
| Evolution not working | Check safety settings and permissions | [API Reference](AUTOGEN_API_REFERENCE.md#evolution-not-working) |

### Log Analysis Commands

```bash
# Check for errors
grep -i error /path/to/logs/autogen.log

# Monitor tool selection
grep "Tool selected" /path/to/logs/autogen.log | tail -20

# Check evolution cycles
grep "Evolution cycle" /path/to/logs/autogen.log
```

---

## 🧪 Development & Testing

### Development Setup

```bash
# Development environment
cp .env.development .env
export LOG_LEVEL=DEBUG
export ENABLE_PERFORMANCE_PROFILING=true

# Install development dependencies
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Unit tests
python -m pytest tests/

# Integration tests
python -m pytest tests/integration/

# Performance tests
python -m pytest tests/performance/
```

### Adding New Components

1. **New Tools** - See [Maintenance Guide](AUTOGEN_SYSTEM_DOCUMENTATION.md#adding-new-tools)
2. **New Services** - See [Maintenance Guide](AUTOGEN_SYSTEM_DOCUMENTATION.md#adding-new-services)
3. **Evolution Logic** - See [Maintenance Guide](AUTOGEN_SYSTEM_DOCUMENTATION.md#modifying-evolution-logic)

---

## 📈 Performance Benchmarks

### Typical Performance Metrics

| Metric | Development | Production | High-Performance |
|--------|-------------|------------|------------------|
| Decision Time | 1-3 seconds | 2-5 seconds | 1-2 seconds |
| Tool Selection | 100-500ms | 200-800ms | 100-300ms |
| Memory Usage | 500MB-1GB | 1-2GB | 2-4GB |
| Success Rate | >85% | >90% | >95% |

### Optimization Recommendations

- **CPU-bound workloads** - Increase `MAX_WORKER_THREADS`
- **Memory constraints** - Use smaller LLM models, optimize caching
- **Database performance** - Tune connection pools, add indexes
- **Network latency** - Use local Ollama deployment

---

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Use secure database connections (SSL)
- [ ] Store API keys in secure files, not environment variables
- [ ] Enable evolution safety settings (`DARWIN_GODEL_REQUIRE_APPROVAL=true`)
- [ ] Configure sandbox security for code modifications
- [ ] Implement proper authentication for API endpoints
- [ ] Regular security updates for dependencies

### Safety Settings

```bash
# Maximum security configuration
DARWIN_GODEL_REAL_MODIFICATIONS=false
DARWIN_GODEL_REQUIRE_APPROVAL=true
SANDBOX_NETWORK_DISABLED=true
EVOLUTION_MAX_PARALLEL=1
```

---

## 🤝 Contributing & Maintenance

### Documentation Maintenance

When making code changes, update the relevant documentation sections:

- **Function signatures** → [Functions Reference](AUTOGEN_FUNCTIONS_REFERENCE.md)
- **Configuration options** → [Configuration Guide](AUTOGEN_CONFIGURATION_GUIDE.md)
- **API endpoints** → [API Reference](AUTOGEN_API_REFERENCE.md)
- **Architecture changes** → [System Documentation](AUTOGEN_SYSTEM_DOCUMENTATION.md)

### Maintenance Checklist

- [ ] Update function documentation if signatures change
- [ ] Update logic flow diagrams if control flow changes
- [ ] Update integration patterns if new patterns emerge
- [ ] Update cross-reference guide if dependencies change
- [ ] Update configuration guide if new environment variables added

---

## 📞 Support & Resources

### Getting Help

1. **Check [Troubleshooting Guide](AUTOGEN_API_REFERENCE.md#troubleshooting-guide)** first
2. **Review [Configuration Guide](AUTOGEN_CONFIGURATION_GUIDE.md)** for setup issues
3. **Consult [Functions Reference](AUTOGEN_FUNCTIONS_REFERENCE.md)** for development questions
4. **Check system logs** with provided log analysis commands

### Useful Resources

- **Microsoft AutoGen Documentation** - https://microsoft.github.io/autogen/
- **Cognee Documentation** - https://cognee.ai/docs
- **Ollama Models** - https://ollama.ai/library
- **PostgreSQL Documentation** - https://www.postgresql.org/docs/

---

## 📋 Version Information

- **Documentation Version:** 1.0.0
- **System Version:** Current as of documentation date
- **Last Updated:** [Current Date]
- **Maintainer:** AutoGen Documentation System

---

## 🎯 Next Steps

### For New Users
1. Read [System Documentation](AUTOGEN_SYSTEM_DOCUMENTATION.md) overview
2. Set up development environment using [Configuration Guide](AUTOGEN_CONFIGURATION_GUIDE.md)
3. Try MCP integration examples from [API Reference](AUTOGEN_API_REFERENCE.md)

### For Developers
1. Study [Functions Reference](AUTOGEN_FUNCTIONS_REFERENCE.md) for detailed APIs
2. Review integration patterns in [System Documentation](AUTOGEN_SYSTEM_DOCUMENTATION.md)
3. Implement custom tools following the maintenance guide

### For Administrators
1. Review production settings in [Configuration Guide](AUTOGEN_CONFIGURATION_GUIDE.md)
2. Set up monitoring using [API Reference](AUTOGEN_API_REFERENCE.md) endpoints
3. Plan maintenance procedures from [System Documentation](AUTOGEN_SYSTEM_DOCUMENTATION.md)

---

*This documentation is designed to grow with the system. Please keep it updated as the codebase evolves.* 