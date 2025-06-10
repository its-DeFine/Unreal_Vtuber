# AutoGen Python Agent

This package provides a minimal autonomous agent built with the
[AutoGen](https://github.com/microsoft/autogen) framework. It aims to
replace the existing HardNet TypeScript agent with a lightweight Python
implementation.

## Features
- Tool registry that loads `run(context)` functions
- Simple memory manager placeholder
- SCB and VTuber API clients
- Decision loop with configurable interval

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
