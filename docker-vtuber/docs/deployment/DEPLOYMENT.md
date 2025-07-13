# Deployment Guide - Autonomous VTuber System

## Overview

This guide provides comprehensive instructions for deploying the Autonomous VTuber System in various environments, from local development to production-scale deployments.

## System Requirements

### Minimum Requirements (Development)
- **CPU**: 4 cores (8 recommended)
- **Memory**: 8GB RAM (16GB recommended)
- **Storage**: 50GB free space
- **Network**: Broadband internet connection
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2

### Recommended Requirements (Production)
- **CPU**: 8+ cores with AVX2 support
- **Memory**: 32GB RAM (64GB for high-load scenarios)
- **Storage**: 200GB SSD + additional storage for Neo4j
- **Network**: High-bandwidth connection with low latency
- **GPU**: Optional NVIDIA GPU for enhanced LLM inference

### Container Runtime
- **Docker**: 20.10.0 or later
- **Docker Compose**: 2.0.0 or later
- **Available Ports**: 3000, 5000, 5001, 6379, 7687, 8000, 8200, 11434

## Quick Start Deployment

### Local Development Setup

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd docker-vtuber
   ```

2. **Environment Configuration**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit configuration
   nano .env
   ```

3. **Start Core Services**
   ```bash
   # Start the unified system
   cd app/CORE
   python unified_main.py --env development
   
   # Or using Docker (recommended)
   docker-compose up -d
   ```

4. **Verify Deployment**
   ```bash
   # Check system health
   curl http://localhost:8000/health
   
   # View API documentation
   open http://localhost:8000/docs
   ```

### Production Deployment

```bash
# Production deployment with scaling
export SYSTEM_MODE=production
docker-compose -f docker-compose.prod.yml up -d --scale autogen-agent=3

# Monitor deployment
docker-compose logs -f
```

## Docker Configuration

### Core System Dockerfile

**Location**: `/app/CORE/autogen-agent/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Copy application code
COPY autogen_agent ./autogen_agent
COPY static ./static
COPY requirements.txt ./requirements.txt

# Install dependencies
ENV PIP_DEFAULT_TIMEOUT=1000
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --timeout 1000 -r requirements.txt

# Start application
CMD ["python", "-m", "autogen_agent.simplified_main"]
```

### UI Service Dockerfile

**Location**: `/app/ui/Dockerfile`

```dockerfile
FROM node:18-alpine
WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm install

# Copy application code
COPY . .

# Build application
RUN npm run build

# Start application
EXPOSE 3000
CMD ["npm", "start"]
```

### NeuroSync Bridge Dockerfile

**Location**: `/app/AVATAR/NeuroBridge/dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Start NeuroSync Player
CMD ["python", "NeuroSync_Player/text_to_face.py"]
```

## Complete Docker Compose Configuration

### Development Environment

**File**: `docker-compose.dev.yml`

```yaml
version: '3.8'

services:
  # Core unified system
  unified-core:
    build:
      context: ./app/CORE
      dockerfile: Dockerfile
    container_name: unified-core
    ports:
      - "8000:8000"
    environment:
      - SYSTEM_MODE=simplified
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - REDIS_URL=redis://redis:6379
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password123
      - OLLAMA_HOST=http://ollama:11434
      - USE_OLLAMA=true
    depends_on:
      - redis
      - neo4j
      - ollama
    restart: unless-stopped
    volumes:
      - ./app/CORE:/app
      - unified_logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # S2 AutoGen Agent (can be scaled)
  autogen-agent:
    build:
      context: ./app/CORE/autogen-agent
      dockerfile: Dockerfile
    container_name: autogen-agent
    ports:
      - "8200:8000"
    environment:
      - USE_OLLAMA=true
      - OLLAMA_HOST=http://ollama:11434
      - OLLAMA_MODEL=llama3.1:8b
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password123
      - REDIS_URL=redis://redis:6379
      - S2_QUEUE_FILE=/tmp/s2_queue/s2_processing_queue.json
    depends_on:
      - redis
      - neo4j
      - ollama
    restart: unless-stopped
    volumes:
      - s2_queue:/tmp/s2_queue
      - autogen_logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 45s
      timeout: 15s
      retries: 3

  # S1 NeuroSync System
  neurosync-player:
    build:
      context: ./app/AVATAR/NeuroBridge
      dockerfile: dockerfile
    container_name: neurosync-player
    ports:
      - "5001:5001"
    environment:
      - NEUROSYNC_HOST=0.0.0.0
      - NEUROSYNC_PORT=5001
      - REDIS_URL=redis://redis:6379
      - CHARACTER_PATH=/app/characters
      - UNREAL_ENGINE_HOST=host.docker.internal
    depends_on:
      - redis
    restart: unless-stopped
    volumes:
      - ./app/AVATAR/NeuroBridge/NeuroSync_Player:/app
      - neurosync_data:/app/generated
      - character_data:/app/characters
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # NeuroSync Local API
  neurosync-local:
    build:
      context: ./app/AVATAR/NeuroBridge
      dockerfile: dockerfile
    container_name: neurosync-local
    ports:
      - "5000:5000"
    environment:
      - NEUROSYNC_LOCAL_HOST=0.0.0.0
      - NEUROSYNC_LOCAL_PORT=5000
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped
    volumes:
      - ./app/AVATAR/NeuroBridge/NeuroSync_Local_API:/app
    command: ["python", "neurosync_local_api.py"]

  # Web UI
  autonomy-ui:
    build:
      context: ./app/ui
      dockerfile: Dockerfile
    container_name: autonomy-ui
    ports:
      - "3000:3000"
    environment:
      - UI_HOST=0.0.0.0
      - UI_PORT=3000
      - UNIFIED_CORE_URL=http://unified-core:8000
      - AUTOGEN_URL=http://autogen-agent:8000
      - NEUROSYNC_URL=http://neurosync-player:5001
      - NEUROSYNC_LOCAL_URL=http://neurosync-local:5000
      - API_TIMEOUT=30
      - DEBUG=true
    depends_on:
      - unified-core
      - autogen-agent
    restart: unless-stopped
    volumes:
      - ./app/ui:/app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Infrastructure Services
  redis:
    image: redis:7-alpine
    container_name: vtuber-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --requirepass redis_password
    restart: unless-stopped
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  neo4j:
    image: neo4j:5.13-community
    container_name: vtuber-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password123
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=2G
    restart: unless-stopped
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "password123", "RETURN 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    container_name: vtuber-ollama
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0
    restart: unless-stopped
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/version"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
  neo4j_data:
  neo4j_logs:
  ollama_data:
  s2_queue:
  unified_logs:
  autogen_logs:
  neurosync_data:
  character_data:

networks:
  default:
    name: vtuber-network
    driver: bridge
```

### Production Environment

**File**: `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  # Production services with enhanced configuration
  unified-core:
    extends:
      file: docker-compose.dev.yml
      service: unified-core
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    environment:
      - SYSTEM_MODE=production
      - DEBUG=false
      - LOG_LEVEL=INFO

  autogen-agent:
    extends:
      file: docker-compose.dev.yml
      service: autogen-agent
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G

  # Production Redis with clustering
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --appendonly yes
      --requirepass ${REDIS_PASSWORD:-redis_secure_password}
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_prod_data:/data
    restart: always

  # Production Neo4j with enterprise features
  neo4j:
    image: neo4j:5.13-enterprise
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-neo4j_secure_password}
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      - NEO4J_dbms_memory_heap_max__size=8G
      - NEO4J_dbms_memory_pagecache_size=4G
    volumes:
      - neo4j_prod_data:/data
      - neo4j_prod_logs:/logs
      - ./backups:/backups
    restart: always

  # Load balancer
  nginx:
    image: nginx:alpine
    container_name: vtuber-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/ssl/certs
    depends_on:
      - unified-core
      - autonomy-ui
    restart: always

volumes:
  redis_prod_data:
  neo4j_prod_data:
  neo4j_prod_logs:
```

## Environment Configuration

### Development Environment Variables

```bash
# .env.development
SYSTEM_MODE=simplified
DEBUG=true
LOG_LEVEL=DEBUG

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# Database Configuration
REDIS_URL=redis://localhost:6379
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# LLM Configuration
USE_OLLAMA=true
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Service URLs
S1_CHARACTER_SYNC_ENDPOINT=http://localhost:5001
NEUROSYNC_PLAYER_URL=http://localhost:5001
NEUROSYNC_LOCAL_URL=http://localhost:5000

# Feature Flags
AGENTNET_ENABLED=true
S2_TEAMS_ENABLED=true
NEO4J_ENABLED=true
```

### Production Environment Variables

```bash
# .env.production
SYSTEM_MODE=production
DEBUG=false
LOG_LEVEL=INFO

# Security
API_KEY_REQUIRED=true
RATE_LIMIT_ENABLED=true
CORS_ORIGINS=https://yourdomain.com

# High-performance settings
API_WORKERS=4
REDIS_MAX_CONNECTIONS=100
NEO4J_MAX_POOL_SIZE=50

# Monitoring
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30
ERROR_TRACKING_ENABLED=true

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_INTERVAL=6h
BACKUP_RETENTION_DAYS=30
```

## Nginx Load Balancer Configuration

### nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream unified_core {
        least_conn;
        server unified-core-1:8000;
        server unified-core-2:8000;
    }

    upstream autogen_agents {
        least_conn;
        server autogen-agent-1:8000;
        server autogen-agent-2:8000;
        server autogen-agent-3:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=stimuli:10m rate=5r/s;

    server {
        listen 80;
        server_name your-domain.com;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/ssl/certs/cert.pem;
        ssl_certificate_key /etc/ssl/certs/key.pem;

        # Main API routes
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://unified_core;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Stimuli processing (special rate limiting)
        location /api/stimuli/ {
            limit_req zone=stimuli burst=10 nodelay;
            proxy_pass http://unified_core;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # S2 AutoGen direct access
        location /s2/ {
            proxy_pass http://autogen_agents/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Web UI
        location / {
            proxy_pass http://autonomy-ui:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # WebSocket support (future)
        location /ws/ {
            proxy_pass http://unified_core;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }

        # Health checks
        location /health {
            access_log off;
            proxy_pass http://unified_core/health;
        }
    }
}
```

## Kubernetes Deployment (Advanced)

### Namespace and Base Resources

```yaml
# k8s/namespace.yml
apiVersion: v1
kind: Namespace
metadata:
  name: vtuber-system
---
# k8s/configmap.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vtuber-config
  namespace: vtuber-system
data:
  SYSTEM_MODE: "production"
  USE_OLLAMA: "true"
  REDIS_URL: "redis://redis-service:6379"
  NEO4J_URI: "bolt://neo4j-service:7687"
```

### Unified Core Deployment

```yaml
# k8s/unified-core.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: unified-core
  namespace: vtuber-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: unified-core
  template:
    metadata:
      labels:
        app: unified-core
    spec:
      containers:
      - name: unified-core
        image: vtuber/unified-core:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: vtuber-config
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: unified-core-service
  namespace: vtuber-system
spec:
  selector:
    app: unified-core
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### AutoGen Agent Deployment

```yaml
# k8s/autogen-agent.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: autogen-agent
  namespace: vtuber-system
spec:
  replicas: 5
  selector:
    matchLabels:
      app: autogen-agent
  template:
    metadata:
      labels:
        app: autogen-agent
    spec:
      containers:
      - name: autogen-agent
        image: vtuber/autogen-agent:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: vtuber-config
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
```

## Monitoring and Logging

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'vtuber-unified-core'
    static_configs:
      - targets: ['unified-core:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'vtuber-autogen'
    static_configs:
      - targets: ['autogen-agent:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:7474']
```

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "VTuber System Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(vtuber_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "S2 Team Processing",
        "type": "graph", 
        "targets": [
          {
            "expr": "vtuber_s2_processing_duration_seconds",
            "legendFormat": "Processing Time"
          }
        ]
      },
      {
        "title": "Character Utilization",
        "type": "heatmap",
        "targets": [
          {
            "expr": "vtuber_character_active_sessions",
            "legendFormat": "{{character}}"
          }
        ]
      }
    ]
  }
}
```

## Backup and Recovery

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

set -e

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Starting VTuber system backup..."

# Backup Redis data
echo "Backing up Redis data..."
docker exec vtuber-redis redis-cli --rdb "$BACKUP_DIR/redis.rdb" BGSAVE

# Backup Neo4j data
echo "Backing up Neo4j data..."
docker exec vtuber-neo4j neo4j-admin dump \
  --database=neo4j \
  --to="/backups/neo4j_$(date +%Y%m%d_%H%M%S).dump"

# Backup configuration
echo "Backing up configuration..."
cp -r ./config "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"

# Backup character templates
echo "Backing up character templates..."
cp -r ./app/AVATAR/NeuroBridge/NeuroSync_Player/characters "$BACKUP_DIR/"

# Create archive
echo "Creating backup archive..."
tar -czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_DIR" .
rm -rf "$BACKUP_DIR"

echo "Backup completed: $BACKUP_DIR.tar.gz"

# Cleanup old backups (keep last 30 days)
find /backups -name "*.tar.gz" -mtime +30 -delete

echo "Backup cleanup completed"
```

### Recovery Procedure

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file.tar.gz>"
  exit 1
fi

echo "Starting VTuber system recovery..."

# Stop services
docker-compose down

# Extract backup
RESTORE_DIR="/tmp/restore_$(date +%s)"
mkdir -p "$RESTORE_DIR"
tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

# Restore Redis data
echo "Restoring Redis data..."
cp "$RESTORE_DIR/redis.rdb" ./redis_data/dump.rdb

# Restore Neo4j data
echo "Restoring Neo4j data..."
docker run --rm -v neo4j_data:/data -v "$RESTORE_DIR:/backup" \
  neo4j:5.13 neo4j-admin load --from=/backup/neo4j.dump --force

# Restore configuration
echo "Restoring configuration..."
cp "$RESTORE_DIR/.env" .
cp -r "$RESTORE_DIR/config" ./

# Restore character templates
echo "Restoring character templates..."
cp -r "$RESTORE_DIR/characters" ./app/AVATAR/NeuroBridge/NeuroSync_Player/

# Start services
docker-compose up -d

# Verify recovery
sleep 30
curl -f http://localhost:8000/health || {
  echo "Health check failed after recovery"
  exit 1
}

echo "Recovery completed successfully"

# Cleanup
rm -rf "$RESTORE_DIR"
```

## Scaling Strategies

### Horizontal Scaling

```bash
# Scale AutoGen agents for increased S2 processing
docker-compose up -d --scale autogen-agent=5

# Scale unified core for higher API throughput
docker-compose up -d --scale unified-core=3
```

### Vertical Scaling

```yaml
# docker-compose.scale.yml
services:
  autogen-agent:
    deploy:
      resources:
        limits:
          cpus: '8.0'
          memory: 16G
        reservations:
          cpus: '4.0'
          memory: 8G
```

### Auto-scaling (Kubernetes)

```yaml
# k8s/hpa.yml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: autogen-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: autogen-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Security Hardening

### Docker Security

```bash
# Run containers as non-root user
RUN groupadd -r vtuber && useradd -r -g vtuber vtuber
USER vtuber

# Remove unnecessary packages
RUN apt-get purge -y wget curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Use read-only filesystem where possible
docker run --read-only --tmpfs /tmp vtuber/unified-core
```

### Network Security

```yaml
# docker-compose.security.yml
networks:
  frontend:
    driver: bridge
    internal: false
  backend:
    driver: bridge
    internal: true

services:
  unified-core:
    networks:
      - frontend
      - backend
  
  autogen-agent:
    networks:
      - backend
  
  redis:
    networks:
      - backend
```

## Troubleshooting

### Common Issues

1. **Service Not Starting**
   ```bash
   # Check logs
   docker-compose logs service-name
   
   # Check resource usage
   docker stats
   
   # Verify network connectivity
   docker-compose exec service-name ping redis
   ```

2. **High Memory Usage**
   ```bash
   # Monitor memory usage
   docker exec autogen-agent top
   
   # Adjust memory limits
   docker-compose up -d --scale autogen-agent=2
   ```

3. **Database Connection Issues**
   ```bash
   # Test Redis connection
   docker exec vtuber-redis redis-cli ping
   
   # Test Neo4j connection
   docker exec vtuber-neo4j cypher-shell -u neo4j -p password123 "RETURN 1"
   ```

### Performance Optimization

1. **Ollama Model Optimization**
   ```bash
   # Pull optimized models
   docker exec vtuber-ollama ollama pull llama3.1:8b-instruct-q4_K_M
   
   # Monitor GPU usage
   nvidia-smi
   ```

2. **Database Tuning**
   ```bash
   # Neo4j memory optimization
   echo "dbms.memory.heap.max_size=8G" >> neo4j.conf
   echo "dbms.memory.pagecache.size=4G" >> neo4j.conf
   
   # Redis optimization
   echo "maxmemory 2gb" >> redis.conf
   echo "maxmemory-policy allkeys-lru" >> redis.conf
   ```

---

This deployment guide provides comprehensive instructions for setting up the Autonomous VTuber System across different environments and scales. Follow the appropriate section based on your deployment requirements and infrastructure capabilities.