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
