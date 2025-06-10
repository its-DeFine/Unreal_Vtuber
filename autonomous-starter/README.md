# Autonomous Starter (Python)

This project provides a simple autonomous agent powered by the [Autogen](https://github.com/microsoft/autogen) framework. It replaces the previous TypeScript implementation.

## Quick Start

```bash
pip install -r requirements.txt
python autogen_orchestrator.py
```

The orchestrator initializes a group chat manager and starts a basic conversation. From this entrypoint you can integrate additional tools such as MCP or launch legacy ELIZA agents.
