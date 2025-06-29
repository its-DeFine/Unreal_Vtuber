# AutoGen System - Configuration Guide

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [LLM Configuration](#llm-configuration)
3. [Database Configuration](#database-configuration)
4. [Integration Configuration](#integration-configuration)
5. [Performance Tuning](#performance-tuning)
6. [Security Configuration](#security-configuration)
7. [Development Configuration](#development-configuration)
8. [Troubleshooting](#troubleshooting)

---

## Environment Variables

### Core System Variables

#### `LOOP_INTERVAL`
- **Purpose:** Sleep interval between autonomous cycles
- **Type:** Integer (seconds)
- **Default:** `30`
- **Example:** `LOOP_INTERVAL=45`
- **Impact:** Higher values reduce system load but slow response time

#### `LOG_LEVEL`
- **Purpose:** Logging verbosity level
- **Type:** String
- **Default:** `INFO`
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Example:** `LOG_LEVEL=DEBUG`

#### `WORKING_DIR`
- **Purpose:** Base directory for system operations
- **Type:** String (path)
- **Default:** Current directory
- **Example:** `WORKING_DIR=/opt/autogen`

### AutoGen Agent Configuration

#### `USE_AUTOGEN_LLM`
- **Purpose:** Enable AutoGen's built-in LLM capabilities
- **Type:** Boolean
- **Default:** `true`
- **Example:** `USE_AUTOGEN_LLM=false`
- **Note:** Disabling may reduce functionality

#### `USE_OLLAMA`
- **Purpose:** Enable Ollama integration for local LLM
- **Type:** Boolean
- **Default:** `false`
- **Example:** `USE_OLLAMA=true`

#### `OLLAMA_MODEL`
- **Purpose:** Specify Ollama model to use
- **Type:** String
- **Default:** `llama3.2:3b`
- **Example:** `OLLAMA_MODEL=llama3.1:8b`
- **Note:** Model must be available in Ollama

#### `OLLAMA_URL`
- **Purpose:** Ollama server endpoint
- **Type:** String (URL)
- **Default:** `http://localhost:11434`
- **Example:** `OLLAMA_URL=http://ollama:11434`

---

## LLM Configuration

### Ollama Configuration

#### Environment Setup
```bash
# Enable Ollama
export USE_OLLAMA=true
export OLLAMA_MODEL=llama3.1:8b
export OLLAMA_URL=http://localhost:11434

# Cognee LLM integration
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3.1:8b
export EMBEDDING_PROVIDER=fastembed
```

#### Model Selection Guidelines

| Model | VRAM Required | Performance | Use Case |
|-------|---------------|-------------|----------|
| `llama3.2:3b` | 4GB | Fast | Development, testing |
| `llama3.1:8b` | 8GB | Good | Production, balanced |
| `llama3.1:70b` | 48GB+ | Excellent | High-performance scenarios |

#### Performance Optimization
```bash
# GPU acceleration
export CUDA_VISIBLE_DEVICES=0

# Memory optimization
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=1
```

### OpenAI Configuration

```bash
# OpenAI API setup
export OPENAI_API_KEY=your_api_key_here
export OPENAI_MODEL=gpt-4
export OPENAI_TEMPERATURE=0.7
```

### Azure OpenAI Configuration

```bash
# Azure OpenAI setup
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_API_KEY=your_api_key_here
export AZURE_OPENAI_DEPLOYMENT=gpt-4-deployment
export AZURE_OPENAI_API_VERSION=2023-12-01-preview
```

---

## Database Configuration

### PostgreSQL Configuration

#### Environment Variables
```bash
# PostgreSQL connection
export DATABASE_URL=postgresql://user:password@localhost:5432/autogen_db
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=autogen_db
export DB_USER=autogen_user
export DB_PASSWORD=secure_password
```

#### Connection Pool Settings
```bash
# Connection pool optimization
export DB_POOL_SIZE=10
export DB_MAX_OVERFLOW=20
export DB_POOL_TIMEOUT=30
export DB_POOL_RECYCLE=3600
```

#### Database Setup
```sql
-- Create database and user
CREATE DATABASE autogen_db;
CREATE USER autogen_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE autogen_db TO autogen_user;

-- Enable required extensions
\c autogen_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### Statistics Database Schema

The system automatically creates required tables:
- `cycle_statistics` - Performance metrics per cycle
- `tool_usage` - Tool selection and execution stats
- `evolution_actions` - Evolution cycle tracking
- `memory_entries` - Interaction memories
- `goals` - Goal management data

---

## Integration Configuration

### SCB (Shared Cognitive Blackboard) Configuration

#### Environment Variables
```bash
# Enable SCB integration
export AGENTNET_ENABLED=true
export REDIS_URL=redis://localhost:6379/0

# Redis configuration
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
export REDIS_PASSWORD=optional_password
```

#### Redis Setup
```bash
# Redis server configuration
redis-server --port 6379 --save 900 1 --save 300 10 --save 60 10000
```

#### SCB Message Format
```json
{
  "agent_id": "autogen_agent",
  "timestamp": 1234567890.123,
  "event_type": "decision_cycle",
  "data": {
    "iteration": 1,
    "success": true,
    "metrics": {}
  }
}
```

### VTuber Integration Configuration

#### Environment Variables
```bash
# VTuber endpoint
export VTUBER_ENDPOINT=http://localhost:8000
export VTUBER_ENABLED=true
```

#### VTuber Client Configuration
```bash
# Advanced VTuber settings
export VTUBER_TIMEOUT=30
export VTUBER_RETRY_COUNT=3
export VTUBER_BATCH_SIZE=1
```

### Cognee Knowledge Graph Configuration

#### Environment Variables
```bash
# Cognee API configuration
export COGNEE_URL=http://localhost:8080
export COGNEE_BEARER_TOKEN=your_cognee_token_here
export COGNEE_DATASET=autogen_knowledge

# Cognee LLM settings (for direct integration)
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3.1:8b
export EMBEDDING_PROVIDER=fastembed
```

#### Token Generation
```python
# Generate Cognee token
from autogen_agent.scripts.generate_cognee_token import generate_token
token = generate_token(username="autogen", password="secure_password")
```

---

## Performance Tuning

### Memory Management

#### Python Memory Settings
```bash
# Python memory optimization
export PYTHONMALLOC=malloc
export MALLOC_ARENA_MAX=2
export MALLOC_MMAP_THRESHOLD_=1048576
```

#### Evolution System Memory
```bash
# Darwin-Gödel memory limits
export DARWIN_GODEL_MAX_MEMORY_MB=1024
export DARWIN_GODEL_SANDBOX_TIMEOUT=300
```

### CPU and Concurrency

#### Threading Configuration
```bash
# Thread pool settings
export MAX_WORKER_THREADS=4
export TOOL_EXECUTION_TIMEOUT=120
export ASYNC_BATCH_SIZE=3
```

#### Evolution Concurrency
```bash
# Evolution system concurrency
export EVOLUTION_MAX_PARALLEL=2
export CODE_ANALYSIS_TIMEOUT=60
```

### Tool Selection Optimization

#### Performance Weights
```bash
# Tool selection algorithm weights
export CONTEXT_RELEVANCE_WEIGHT=0.4
export HISTORICAL_PERFORMANCE_WEIGHT=0.3
export RECENT_SUCCESS_WEIGHT=0.2
export DIVERSITY_BONUS_WEIGHT=0.1
```

#### Caching Configuration
```bash
# Tool performance caching
export TOOL_CACHE_SIZE=1000
export TOOL_CACHE_TTL=3600
export CONTEXT_CACHE_SIZE=500
```

---

## Security Configuration

### Authentication

#### API Keys Management
```bash
# Secure API key storage
export COGNEE_API_KEY_FILE=/secure/path/cognee.key
export OPENAI_API_KEY_FILE=/secure/path/openai.key
```

#### Database Security
```bash
# Database SSL configuration
export DB_SSL_MODE=require
export DB_SSL_CERT=/path/to/client-cert.pem
export DB_SSL_KEY=/path/to/client-key.pem
export DB_SSL_ROOT_CERT=/path/to/ca-cert.pem
```

### Evolution Safety

#### Code Modification Safety
```bash
# Darwin-Gödel safety settings
export DARWIN_GODEL_REAL_MODIFICATIONS=false  # Sandbox mode only
export DARWIN_GODEL_REQUIRE_APPROVAL=true     # Human approval required
export DARWIN_GODEL_BACKUP_DIR=/backup/path   # Backup location
export DARWIN_GODEL_MAX_CHANGES_PER_CYCLE=3   # Limit modifications
```

#### Sandbox Configuration
```bash
# Sandbox security
export SANDBOX_DIR=/tmp/autogen_sandbox
export SANDBOX_TIMEOUT=300
export SANDBOX_MEMORY_LIMIT=512MB
export SANDBOX_NETWORK_DISABLED=true
```

---

## Development Configuration

### Debug Settings

#### Verbose Logging
```bash
# Development logging
export LOG_LEVEL=DEBUG
export ENABLE_FUNCTION_TRACING=true
export LOG_SQL_QUERIES=true
export LOG_TOOL_SELECTION=true
```

#### Performance Profiling
```bash
# Performance monitoring
export ENABLE_PERFORMANCE_PROFILING=true
export PROFILE_EVERY_N_CYCLES=10
export PROFILE_OUTPUT_DIR=/tmp/profiles
```

### Testing Configuration

#### Test Environment
```bash
# Test-specific settings
export AUTOGEN_TEST_MODE=true
export TEST_DATABASE_URL=postgresql://test:test@localhost:5432/autogen_test
export MOCK_EXTERNAL_SERVICES=true
export FAST_CYCLE_INTERVAL=5
```

#### Integration Testing
```bash
# Integration test settings
export TEST_REDIS_URL=redis://localhost:6380/15
export TEST_VTUBER_ENDPOINT=http://localhost:8001
export TEST_COGNEE_URL=http://localhost:8081
```

---

## Production Configuration

### Recommended Production Settings

```bash
# Core system
export LOOP_INTERVAL=60
export LOG_LEVEL=INFO
export MAX_WORKER_THREADS=8

# Database
export DATABASE_URL=postgresql://autogen:secure_pass@db:5432/autogen_prod
export DB_POOL_SIZE=20
export DB_MAX_OVERFLOW=30

# LLM
export USE_OLLAMA=true
export OLLAMA_MODEL=llama3.1:8b
export OLLAMA_URL=http://ollama:11434

# Integrations
export AGENTNET_ENABLED=true
export REDIS_URL=redis://redis:6379/0
export VTUBER_ENDPOINT=http://vtuber:8000

# Safety
export DARWIN_GODEL_REAL_MODIFICATIONS=false
export DARWIN_GODEL_REQUIRE_APPROVAL=true
```

### High-Performance Configuration

```bash
# High-performance settings
export LOOP_INTERVAL=30
export MAX_WORKER_THREADS=16
export ASYNC_BATCH_SIZE=5
export TOOL_EXECUTION_TIMEOUT=60

# Memory optimization
export DB_POOL_SIZE=50
export TOOL_CACHE_SIZE=2000
export CONTEXT_CACHE_SIZE=1000

# Evolution settings
export EVOLUTION_MAX_PARALLEL=4
export DARWIN_GODEL_MAX_MEMORY_MB=2048
```

---

## Docker Configuration

### Docker Compose Example

```yaml
version: '3.8'
services:
  autogen:
    build: .
    environment:
      - DATABASE_URL=postgresql://autogen:password@postgres:5432/autogen
      - REDIS_URL=redis://redis:6379/0
      - OLLAMA_URL=http://ollama:11434
      - USE_OLLAMA=true
      - OLLAMA_MODEL=llama3.1:8b
      - AGENTNET_ENABLED=true
      - LOG_LEVEL=INFO
    depends_on:
      - postgres
      - redis
      - ollama

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=autogen
      - POSTGRES_USER=autogen
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - CUDA_VISIBLE_DEVICES=0

volumes:
  postgres_data:
  redis_data:
  ollama_data:
```

---

## Troubleshooting

### Common Configuration Issues

#### Database Connection Issues
```bash
# Test database connection
export DATABASE_URL=postgresql://user:pass@host:5432/db
python -c "import psycopg2; conn = psycopg2.connect('$DATABASE_URL'); print('OK')"
```

#### Redis Connection Issues
```bash
# Test Redis connection
redis-cli -u $REDIS_URL ping
```

#### Ollama Model Issues
```bash
# Check available models
curl http://localhost:11434/api/tags

# Pull required model
ollama pull llama3.1:8b
```

### Performance Issues

#### Memory Usage
```bash
# Monitor memory usage
ps aux | grep python
htop -p $(pgrep -f autogen)
```

#### Database Performance
```sql
-- Check slow queries
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

### Log Analysis

#### Key Log Patterns
```bash
# Check for errors
grep -i error /path/to/logs/autogen.log

# Monitor tool selection
grep "Tool selected" /path/to/logs/autogen.log

# Check evolution cycles
grep "Evolution cycle" /path/to/logs/autogen.log
```

---

## Configuration Templates

### Development Template (`.env.development`)
```bash
# Development Configuration
LOG_LEVEL=DEBUG
LOOP_INTERVAL=15
DATABASE_URL=postgresql://dev:dev@localhost:5432/autogen_dev
USE_OLLAMA=true
OLLAMA_MODEL=llama3.2:3b
AGENTNET_ENABLED=false
DARWIN_GODEL_REAL_MODIFICATIONS=false
ENABLE_PERFORMANCE_PROFILING=true
```

### Production Template (`.env.production`)
```bash
# Production Configuration
LOG_LEVEL=INFO
LOOP_INTERVAL=60
DATABASE_URL=postgresql://autogen:${DB_PASSWORD}@postgres:5432/autogen
USE_OLLAMA=true
OLLAMA_MODEL=llama3.1:8b
AGENTNET_ENABLED=true
REDIS_URL=redis://redis:6379/0
VTUBER_ENDPOINT=http://vtuber:8000
DARWIN_GODEL_REAL_MODIFICATIONS=false
DARWIN_GODEL_REQUIRE_APPROVAL=true
```

### Testing Template (`.env.testing`)
```bash
# Testing Configuration  
LOG_LEVEL=WARNING
AUTOGEN_TEST_MODE=true
DATABASE_URL=postgresql://test:test@localhost:5432/autogen_test
MOCK_EXTERNAL_SERVICES=true
FAST_CYCLE_INTERVAL=5
SKIP_EVOLUTION=true
```

---

## Version Information

- **Configuration Version:** 1.0.0
- **Last Updated:** Current Date
- **Maintainer:** AutoGen Documentation System

---

*Remember to restart the system after changing configuration to ensure all changes take effect.*