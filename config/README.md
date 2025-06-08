# Configuration Directory

This directory contains Docker Compose configurations for different deployment scenarios:

## Files

- `docker-compose.bridge.yml` - Bridge configuration for the autonomous VTuber system
- `docker-compose.byoc.yml` - Bring Your Own Client configuration
- `docker-compose.ollama.yml` - Ollama local LLM configuration

## Usage

Use these compose files with Docker Compose to start different service configurations:

```bash
# Bridge configuration
docker-compose -f config/docker-compose.bridge.yml up

# BYOC configuration  
docker-compose -f config/docker-compose.byoc.yml up

# Ollama configuration
docker-compose -f config/docker-compose.ollama.yml up
```