# AutoGen Python Agent

This is an experimental AI research platform built with Microsoft's [AutoGen](https://github.com/microsoft/autogen) framework. 

**⚠️ Important: This is a research/development system, not production-ready.**

## Architecture Overview

The system uses a multi-agent architecture with three specialized AutoGen agents:
- **cognitive_ai_agent**: Overall system coordination and insights
- **programmer_agent**: Code optimization and technical improvements  
- **observer_agent**: Performance monitoring and analytics

These agents collaborate through a GroupChat manager to make collective decisions.

## Key Features

### ✅ Implemented
- **Multi-agent collaboration** with AutoGen GroupChat
- **Intelligent tool selection** using context-aware scoring (NOT random)
- **Goal management** with SMART goal framework and progress tracking
- **Darwin-Gödel evolution** for self-improvement (experimental)
- **Dual memory system**: PostgreSQL for metrics + Cognee API for semantic memory
- **Basic VTuber integration** with simple on/off control

### ⚠️ Partially Implemented
- **Cognee integration**: Works but has authentication issues (401 errors)
- **MCP server**: Skeleton exists but not fully functional
- **Error handling**: Basic implementation, needs hardening

### ❌ Not Implemented  
- True 24/7 autonomous operation capability
- Production-grade monitoring and fault tolerance
- Complete MCP tool integration for Cursor IDE
- Sophisticated VTuber conditional activation

## Development
```bash
python -m autogen_agent.main
```

### Using Ollama with AutoGen

To try a simple chat powered by a local Ollama model, install the required
packages and run the demo script:

```bash
pip install -r requirements.txt autogen ollama fix-busted-json
python -m autogen_agent.ollama_demo
```

Set the `OLLAMA_MODEL` and `OLLAMA_API_ENDPOINT` environment variables to
control which model and server are used.
