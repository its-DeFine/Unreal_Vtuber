# 🤖 Autonomous Agent Integration Guide

**Purpose**: Technical setup and integration guide for the Autonomous VTuber System  
**Last Updated**: May 28, 2025  
**Status**: Production Ready ✅

---

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (or other LLM provider)
- WSL2 with GPU support (optional, for advanced VTuber features)
- 16GB RAM minimum (32GB recommended)

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd docker-vt

# Copy environment template
cp .example.env .env

# Edit .env file with your API keys
nano .env
```

Required environment variables:
```env
# AI Provider
OPENAI_API_KEY=your_openai_api_key_here

# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autonomous_agent

# VTuber Integration
VTUBER_ENDPOINT_URL=http://neurosync:5001/process_text
NEUROSYNC_URL=http://neurosync:5000

# Autonomous Agent
AUTONOMOUS_LOOP_INTERVAL=30000
MEMORY_ARCHIVING_ENABLED=true
MEMORY_ACTIVE_LIMIT=200

# Monitoring
LOG_LEVEL=info
SCB_API_DEBUG=true
```

### 2. Start the System

```bash
# Start all services
docker-compose -f docker-compose.bridge.yml up --build -d

# Verify all containers are running
docker ps | grep -E "(autonomous|neurosync|postgres|redis)"

# Expected output: 4 containers running
# - autonomous_starter_s3 (AI agent)
# - neurosync_byoc (VTuber system)
# - autonomous_postgres_bridge (Database)
# - redis_scb (State management)
```

### 3. Verify System Health

```bash
# Check autonomous agent
curl http://localhost:3100/health

# Check VTuber system
curl http://localhost:5001/health

# Check database connectivity
docker exec autonomous_postgres_bridge pg_isready -U postgres

# Check Redis
docker exec redis_scb redis-cli ping
```

---

## 📊 Monitoring

### Enhanced Monitoring Script

```bash
# Start monitoring with default 30-minute duration
./monitor_autonomous_system_fixed.sh

# Monitor for custom duration
./monitor_autonomous_system_fixed.sh 60  # 60 minutes

# Monitor output includes:
# - Real-time dashboard
# - Full agent prompts
# - External stimuli (filtered)
# - VTuber I/O tracking
# - Memory statistics
```

### Log Structure

```
logs/autonomous_monitoring/session_TIMESTAMP/
├── structured/
│   ├── autonomous_iteration.jsonl    # Agent decisions
│   ├── tool_execution.jsonl         # Tool usage
│   ├── external_stimuli.jsonl       # User inputs
│   ├── vtuber_io.jsonl             # VTuber I/O
│   ├── memory_operation.jsonl       # Memory ops
│   └── scb_state_change.jsonl      # State changes
├── raw/
│   ├── autonomous_starter_s3.log    # Raw agent logs
│   └── neurosync_byoc.log          # Raw VTuber logs
└── ENHANCED_SUMMARY.md             # Session summary
```

---

## 🔧 Configuration

### Docker Compose Services

```yaml
# docker-compose.bridge.yml
services:
  autonomous_starter:
    container_name: autonomous_starter_s3
    ports:
      - "3100:3000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy

  neurosync:
    container_name: neurosync_byoc
    ports:
      - "5000:5000"  # API
      - "5001:5001"  # Player
    environment:
      - USE_REDIS_SCB=true
      - REDIS_URL=redis://redis:6379/0

  postgres:
    container_name: autonomous_postgres_bridge
    image: ankane/pgvector:latest
    environment:
      - POSTGRES_DB=autonomous_agent
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U postgres']
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    container_name: redis_scb
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Memory Management Configuration

```typescript
// Memory archiving configuration
const archivingConfig = {
  activeMemoryLimit: 200,           // Max active memories
  archiveThresholds: {
    timeBasedHours: 48,            // Archive after 48 hours
    importanceScore: 0.3,          // Archive if importance < 0.3
    accessFrequency: 14 * 24       // Archive if not accessed in 14 days
  },
  archivingBatchSize: 50,          // Process 50 memories per batch
  archivingIntervalMinutes: 30     // Run archiving every 30 minutes
};
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Agent Container Restarting
```bash
# Check logs
docker logs autonomous_starter_s3

# Common fixes:
# - Verify OPENAI_API_KEY is set correctly
# - Check database connectivity
# - Ensure sufficient memory (16GB+)
```

#### 2. Database Connection Failed
```bash
# Test database
docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "SELECT 1"

# Reset database if needed
docker-compose down -v
docker-compose up -d
```

#### 3. VTuber Not Responding
```bash
# Check VTuber logs
docker logs neurosync_byoc

# Test endpoint
curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world!"}'
```

#### 4. Memory Issues
```bash
# Check memory usage
docker stats

# If high memory usage:
# 1. Check memory archiving is enabled
# 2. Reduce MEMORY_ACTIVE_LIMIT
# 3. Increase archiving frequency
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=debug
docker-compose up --build -d

# View debug logs
docker logs -f autonomous_starter_s3 | grep DEBUG
```

---

## 📈 Performance Optimization

### Resource Allocation

```yaml
# Add to docker-compose.bridge.yml
services:
  autonomous_starter:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### Database Optimization

```sql
-- Run these on the PostgreSQL container
docker exec -it autonomous_postgres_bridge psql -U postgres -d autonomous_agent

-- Optimize for autonomous agent workload
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
```

### Monitoring Performance

```bash
# Real-time performance metrics
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Database performance
docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent \
  -c "SELECT COUNT(*) as memories, 
      pg_size_pretty(pg_database_size('autonomous_agent')) as db_size 
      FROM memories;"
```

---

## 🔄 Maintenance

### Regular Tasks

1. **Monitor Memory Growth**
   ```bash
   # Check memory count
   docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent \
     -c "SELECT COUNT(*) FROM memories WHERE \"agentId\" = 
         (SELECT id FROM agents LIMIT 1);"
   ```

2. **Archive Old Memories**
   ```bash
   # Manual archiving if needed
   docker exec autonomous_starter_s3 npm run archive-memories
   ```

3. **Backup Database**
   ```bash
   # Backup
   docker exec autonomous_postgres_bridge pg_dump -U postgres autonomous_agent \
     > backup_$(date +%Y%m%d).sql
   
   # Restore
   docker exec -i autonomous_postgres_bridge psql -U postgres autonomous_agent \
     < backup_20250528.sql
   ```

4. **Update System**
   ```bash
   # Pull latest changes
   git pull
   
   # Rebuild containers
   docker-compose -f docker-compose.bridge.yml build --no-cache
   docker-compose -f docker-compose.bridge.yml up -d
   ```

---

## 🚀 Advanced Configuration

### Multi-Environment Setup

```bash
# Development
docker-compose -f docker-compose.bridge.yml -f docker-compose.dev.yml up

# Production
docker-compose -f docker-compose.bridge.yml -f docker-compose.prod.yml up

# With BYOC scaling
docker-compose -f docker-compose.bridge.yml -f docker-compose.byoc.yml up
```

### Custom Agent Configuration

```typescript
// autonomous-starter/src/index.ts
const character = {
  name: 'YourVTuberName',
  settings: {
    voice: { model: 'en-US-Neural2-F' },
    personality: 'friendly and energetic',
    topics: ['gaming', 'technology', 'anime'],
    autonomousLoopInterval: 30000
  }
};
```

### API Integration

```bash
# External API to trigger agent actions
curl -X POST http://localhost:3100/api/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "action": "sendToVTuber",
    "params": {
      "prompt": "React excitedly to the new game announcement!"
    }
  }'
```

---

## 📚 Additional Resources

- [System Architecture](./AUTONOMOUS_VTUBER_IO_ARCHITECTURE.md)
- [Product Requirements](./AUTONOMOUS_AGENT_PRD.md)
- [Memory Archiving](./MEMORY_ARCHIVING_IMPLEMENTATION_PLAN.md)
- [Monitoring Guide](../MONITORING_GUIDE.md)

---

**Support**: For issues, check the troubleshooting section or open a GitHub issue  
**License**: See LICENSE file in repository root 