# Documentation Structure

This directory contains all project documentation organized by component and purpose.

## Directory Structure

### `/project/`
- **CLAUDE.md** - Consolidated instructions for Claude Code AI assistant
- **SYSTEM_STATUS_REPORT.md** - Current system status and issues
- General project-wide documentation

### `/architecture/`
- **ARCHITECTURE_DEEP_DIVE.md** - Comprehensive system architecture including NeuroBridge
- **ARCHITECTURE_QA.md** - Architecture Q&A and explanations
- System design and architectural decisions

### `/docker-vtuber/`
- **README.md** - Main docker-vtuber project documentation
- **build-logs/** - Build output logs and debug information
- Docker-specific setup and configuration

### `/neurosync/`
- **README.md** - NeuroSync Player main documentation
- **API_CONTROL_REFERENCE.md** - Complete API reference for VTuber control
- **AUTONOMOUS_ORCHESTRATOR_GUIDE.md** - Orchestration system guide
- **DIRECT_TCP_COMMANDS_REFERENCE.md** - TCP protocol reference
- **GAME_CONTROL_QA_COMMANDS.md** - Natural language game control testing
- **KOKORO_TTS_README.md** - Kokoro TTS integration
- **KOKORO_TTS_SETUP.md** - Kokoro TTS setup instructions
- **LOCAL_LLM_README.md** - Local LLM configuration
- **NLP_GAME_CONTROL_PROMPTS.md** - NLP to game command examples
- **TCP_COMMANDS_LIST.md** - TCP command reference
- **NEUROSYNC_LOCAL_API_README.md** - NeuroSync Local API documentation

### `/autogen/`
- **AUTOGEN_AGENT_README.md** - AutoGen agent documentation
- **AUTOGEN_API_REFERENCE.md** - AutoGen API endpoints
- **AUTOGEN_CAPABILITIES_ANALYSIS.md** - Capabilities analysis
- **AUTOGEN_CONFIGURATION_GUIDE.md** - Configuration guide
- **AUTOGEN_FUNCTIONS_REFERENCE.md** - Functions reference
- **AUTOGEN_SYSTEM_DOCUMENTATION.md** - System documentation
- **COGNEE_AUTHENTICATION.md** - Cognee authentication issues

### `/implementation/`
- **TEACHABLE_CODE_EXECUTION_COMPLETE.md** - Teachable agents implementation
- Implementation details and technical guides

### Other Documentation
- **GAME_CONTROL_README.md** - Game control system overview
- **LIPSYNC_SYNCHRONIZATION_ISSUE.md** - Known lipsync issues
- **NEUROSYNC_REORGANIZATION_PROPOSAL.md** - System reorganization proposal
- **NEUROSYNC_SYSTEM_ARCHITECTURE.md** - NeuroSync architecture details

## Quick Links

- [Architecture Overview](architecture/ARCHITECTURE_DEEP_DIVE.md)
- [Project Setup Instructions](project/CLAUDE.md)
- [API Reference](neurosync/API_CONTROL_REFERENCE.md)
- [System Status](project/SYSTEM_STATUS_REPORT.md)

## Documentation Standards

1. All documentation should be in Markdown format
2. Use clear headings and table of contents for long documents
3. Include code examples where appropriate
4. Keep documentation up-to-date with code changes
5. Place new documentation in the appropriate subdirectory

## Contributing

When adding new documentation:
1. Place it in the correct subdirectory based on its purpose
2. Update this README if adding a new category
3. Ensure filenames are descriptive and use UPPERCASE_WITH_UNDERSCORES
4. Include a brief description at the top of each document