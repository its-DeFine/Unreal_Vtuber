# Documentation Structure

This directory contains all documentation for the autonomy project. The documentation has been reorganized into logical categories for easier navigation.

## Directory Structure

### `/api-reference`
Complete API documentation including:
- REST API endpoints for VTuber control
- AutoGen API references and functions
- Direct TCP command references for Unreal Engine
- Game control and NLP command references

### `/setup-guides`
Step-by-step guides for setting up and configuring the system:
- AutoGen configuration and deployment
- Local LLM setup (Ollama)
- Kokoro TTS integration
- V3 migration guides
- Authentication configuration

### `/system-architecture`
Comprehensive architectural documentation:
- System design and component interactions
- AutoGen orchestrator architecture
- NeuroSync system architecture
- Technical deep dives and Q&A

### `/troubleshooting`
Issue documentation and fixes:
- Bug reports and fix proposals
- Implementation fix summaries
- System status reports
- Build logs and error resolutions
- Test scripts and validation tools

### `/development`
Development guides and feature documentation:
- Feature implementation guides
- Character system documentation
- Development patterns and best practices
- Product requirements documents
- QA testing commands and scenarios

## Main Documentation Files

- [Claude Instructions](./CLAUDE.md) - Comprehensive project guidance for Claude Code
- [Tools Overview](./tools_README.md) - Available utility scripts and tools
- [AutoGen System Documentation](./system-architecture/AUTOGEN_SYSTEM_DOCUMENTATION.md) - Complete system overview

## Quick Start

1. **New Users**: Start with [V3 Quick Start Guide](./setup-guides/V3_QUICK_START.md)
2. **Developers**: Review [Development Patterns](./development/DEVELOPMENT_PATTERNS.md)
3. **API Integration**: See [API Control Reference](./api-reference/API_CONTROL_REFERENCE.md)
4. **Troubleshooting**: Check [Troubleshooting](./troubleshooting/) directory

## Contributing

When adding new documentation:
1. Place it in the appropriate category directory
2. Use descriptive filenames with UPPERCASE_WITH_UNDERSCORES.md format
3. Include a brief description at the top of each document
4. Update relevant index files if needed