# GraphFlow External Stimuli System - Deployment Guide

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Production Considerations](#production-considerations)
5. [Monitoring Setup](#monitoring-setup)
6. [Scaling Strategies](#scaling-strategies)
7. [Backup and Recovery](#backup-and-recovery)
8. [Troubleshooting](#troubleshooting)

## Deployment Overview

The GraphFlow External Stimuli System is designed for containerized deployment with support for:

- **Docker**: Single-host deployment with docker-compose
- **Kubernetes**: Multi-host, scalable deployment
- **Cloud Providers**: AWS ECS, Google Cloud Run, Azure Container Instances

### System Requirements

- **CPU**: 4+ cores recommended
- **Memory**: 8GB minimum, 16GB recommended
- **Storage**: 50GB for logs and data
- **Network**: Low latency connection to integrated systems

## Docker Deployment

### Quick Start

```bash
# Clone repository
cd docker-vtuber/app/CORE/graphflow-stimuli-system

# Copy configuration files
cp config/production.env.example config/production.env
cp config/api_keys.json.example config/api_keys.json

# Edit configurations
nano config/production.env
nano config/api_keys.json

# Start all services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f graphflow-gateway
```

### Production Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  graphflow-gateway:
    build:
      context: .
      dockerfile: docker/Dockerfile
    image: graphflow-gateway:latest
    container_name: graphflow-gateway
    restart: unless-stopped
    ports:
      - "8080:8080"  # API port
      - "8081:8081"  # Metrics port
    environment:
      - GRAPHFLOW_ENV=production
    env_file:
      - config/production.env
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - graphflow-data:/app/data
    depends_on:
      - redis
      - postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - graphflow-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  redis:
    image: redis:7-alpine
    container_name: graphflow-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    networks:
      - graphflow-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres:
    image: postgres:15-alpine
    container_name: graphflow-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: graphflow
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./docker/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - graphflow-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  prometheus:
    image: prom/prometheus:latest
    container_name: graphflow-prometheus
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - graphflow-network

  grafana:
    image: grafana/grafana:latest
    container_name: graphflow-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    networks:
      - graphflow-network
    depends_on:
      - prometheus

  nginx:
    image: nginx:alpine
    container_name: graphflow-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - graphflow-gateway
    networks:
      - graphflow-network

volumes:
  graphflow-data:
  redis-data:
  postgres-data:
  prometheus-data:
  grafana-data:

networks:
  graphflow-network:
    driver: bridge
```

### Building and Pushing Images

```bash
# Build production image
docker build -t graphflow-gateway:latest -f docker/Dockerfile .

# Tag for registry
docker tag graphflow-gateway:latest your-registry/graphflow-gateway:latest

# Push to registry
docker push your-registry/graphflow-gateway:latest

# Deploy specific version
docker-compose up -d --no-deps graphflow-gateway
```

### Multi-Stage Dockerfile

```dockerfile
# docker/Dockerfile
FROM python:3.10-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ ./src/
COPY setup.py .
COPY pytest.ini .

# Install application
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 graphflow && \
    chown -R graphflow:graphflow /app

USER graphflow

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Run application
CMD ["python", "-m", "src.main"]
```

## Kubernetes Deployment

### Kubernetes Manifests

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: graphflow-system
```

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: graphflow-config
  namespace: graphflow-system
data:
  production.env: |
    GRAPHFLOW_LOG_LEVEL=INFO
    GRAPHFLOW_MAX_CONCURRENT_STIMULI=50
    GRAPHFLOW_LLM_PROVIDER=openai
    REDIS_URL=redis://redis-service:6379
    POSTGRES_URL=postgresql://postgres:password@postgres-service:5432/graphflow
```

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: graphflow-secrets
  namespace: graphflow-system
type: Opaque
stringData:
  api-keys.json: |
    {
      "api_keys": [
        {
          "key": "production-key-123",
          "name": "Production API Key",
          "permissions": ["read", "write"]
        }
      ]
    }
  GRAPHFLOW_LLM_API_KEY: "your-llm-api-key"
  POSTGRES_PASSWORD: "secure-password"
  REDIS_PASSWORD: "redis-password"
```

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: graphflow-gateway
  namespace: graphflow-system
  labels:
    app: graphflow-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: graphflow-gateway
  template:
    metadata:
      labels:
        app: graphflow-gateway
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8081"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: graphflow-gateway
        image: your-registry/graphflow-gateway:latest
        imagePullPolicy: Always
        ports:
        - name: api
          containerPort: 8080
        - name: metrics
          containerPort: 8081
        envFrom:
        - configMapRef:
            name: graphflow-config
        - secretRef:
            name: graphflow-secrets
        volumeMounts:
        - name: api-keys
          mountPath: /app/config/api_keys.json
          subPath: api-keys.json
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: api
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: api
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: api-keys
        secret:
          secretName: graphflow-secrets
          items:
          - key: api-keys.json
            path: api-keys.json
```

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: graphflow-service
  namespace: graphflow-system
  labels:
    app: graphflow-gateway
spec:
  type: ClusterIP
  ports:
  - name: api
    port: 8080
    targetPort: api
  - name: metrics
    port: 8081
    targetPort: metrics
  selector:
    app: graphflow-gateway
```

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: graphflow-hpa
  namespace: graphflow-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: graphflow-gateway
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
  - type: Pods
    pods:
      metric:
        name: graphflow_active_requests
      target:
        type: AverageValue
        averageValue: "30"
```

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: graphflow-ingress
  namespace: graphflow-system
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - graphflow.example.com
    secretName: graphflow-tls
  rules:
  - host: graphflow.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: graphflow-service
            port:
              name: api
```

### Helm Chart

```yaml
# helm/graphflow/Chart.yaml
apiVersion: v2
name: graphflow
description: GraphFlow External Stimuli System
type: application
version: 1.0.0
appVersion: "1.0.0"
```

```yaml
# helm/graphflow/values.yaml
replicaCount: 3

image:
  repository: your-registry/graphflow-gateway
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: 8080

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: graphflow.example.com
      paths:
        - path: /
          pathType: ImplementationSpecific
  tls:
    - secretName: graphflow-tls
      hosts:
        - graphflow.example.com

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

redis:
  enabled: true
  auth:
    enabled: true
    password: "redis-password"

postgresql:
  enabled: true
  auth:
    postgresPassword: "postgres-password"
    database: "graphflow"

monitoring:
  prometheus:
    enabled: true
  grafana:
    enabled: true
```

### Deploy with Helm

```bash
# Add helm repo (if using)
helm repo add graphflow https://charts.example.com

# Install
helm install graphflow ./helm/graphflow \
  --namespace graphflow-system \
  --create-namespace \
  --values custom-values.yaml

# Upgrade
helm upgrade graphflow ./helm/graphflow \
  --namespace graphflow-system \
  --values custom-values.yaml

# Check status
helm status graphflow -n graphflow-system
kubectl get pods -n graphflow-system
```

## Production Considerations

### Security Best Practices

1. **Network Security**
   ```yaml
   # Network Policy
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: graphflow-network-policy
     namespace: graphflow-system
   spec:
     podSelector:
       matchLabels:
         app: graphflow-gateway
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             name: ingress-nginx
       ports:
       - protocol: TCP
         port: 8080
     egress:
     - to:
       - namespaceSelector:
           matchLabels:
             name: graphflow-system
     - to:
       - namespaceSelector: {}
       ports:
       - protocol: TCP
         port: 443  # HTTPS
       - protocol: TCP
         port: 53   # DNS
   ```

2. **Secrets Management**
   ```bash
   # Use sealed secrets
   kubectl create secret generic graphflow-secrets \
     --from-file=api-keys.json \
     --dry-run=client -o yaml | \
     kubeseal -o yaml > sealed-secrets.yaml
   ```

3. **Pod Security Standards**
   ```yaml
   apiVersion: v1
   kind: Pod
   spec:
     securityContext:
       runAsNonRoot: true
       runAsUser: 1000
       fsGroup: 1000
     containers:
     - name: graphflow
       securityContext:
         allowPrivilegeEscalation: false
         readOnlyRootFilesystem: true
         capabilities:
           drop:
           - ALL
   ```

### Performance Optimization

1. **Resource Allocation**
   ```yaml
   resources:
     requests:
       cpu: "1"
       memory: "2Gi"
     limits:
       cpu: "4"
       memory: "8Gi"
   ```

2. **Connection Pooling**
   ```env
   # Database connections
   POSTGRES_POOL_SIZE=20
   POSTGRES_MAX_OVERFLOW=10
   REDIS_MAX_CONNECTIONS=50
   
   # HTTP connections
   SYSTEM1_CONNECTION_POOL_SIZE=20
   SYSTEM2_CONNECTION_POOL_SIZE=20
   ```

3. **Caching Strategy**
   ```yaml
   # Redis configuration
   redis:
     maxmemory: 2gb
     maxmemory-policy: allkeys-lru
     save: "900 1 300 10 60 10000"
   ```

### High Availability

1. **Multi-Region Deployment**
   ```yaml
   # Deploy across availability zones
   spec:
     affinity:
       podAntiAffinity:
         requiredDuringSchedulingIgnoredDuringExecution:
         - labelSelector:
             matchExpressions:
             - key: app
               operator: In
               values:
               - graphflow-gateway
           topologyKey: kubernetes.io/hostname
   ```

2. **Database Replication**
   ```yaml
   # PostgreSQL HA
   postgresql:
     replication:
       enabled: true
       slaveReplicas: 2
       synchronousCommit: "on"
   ```

## Monitoring Setup

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'graphflow-gateway'
    static_configs:
    - targets: ['graphflow-gateway:8081']
    metrics_path: '/metrics'
    
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
    - role: pod
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
      action: replace
      target_label: __metrics_path__
      regex: (.+)
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "GraphFlow System Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(graphflow_api_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Processing Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, graphflow_processing_time_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Active Requests",
        "targets": [
          {
            "expr": "graphflow_active_requests_current"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(graphflow_processing_errors_total[5m])"
          }
        ]
      }
    ]
  }
}
```

### Alerting Rules

```yaml
# monitoring/alerts.yml
groups:
- name: graphflow_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(graphflow_processing_errors_total[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"
      
  - alert: SlowProcessing
    expr: histogram_quantile(0.95, graphflow_processing_time_seconds_bucket) > 5
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Slow processing detected"
      description: "95th percentile latency is {{ $value }} seconds"
      
  - alert: PodMemoryUsage
    expr: container_memory_usage_bytes{pod=~"graphflow-.*"} / container_spec_memory_limit_bytes > 0.8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Pod {{ $labels.pod }} memory usage is {{ $value | humanizePercentage }}"
```

## Scaling Strategies

### Horizontal Scaling

```bash
# Manual scaling
kubectl scale deployment graphflow-gateway -n graphflow-system --replicas=5

# Update HPA limits
kubectl patch hpa graphflow-hpa -n graphflow-system \
  -p '{"spec":{"maxReplicas":20}}'
```

### Vertical Scaling

```yaml
# Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: graphflow-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: graphflow-gateway
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: graphflow-gateway
      maxAllowed:
        cpu: 4
        memory: 8Gi
```

### Load Testing

```bash
# Using k6
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 0 },
  ],
};

export default function() {
  let response = http.post(
    'https://graphflow.example.com/api/v1/stimuli/submit',
    JSON.stringify({
      content: 'Load test message',
      source: 'k6-test',
      priority: 'medium'
    }),
    {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-key'
      }
    }
  );
  
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
  });
}
```

## Backup and Recovery

### Database Backup

```bash
# PostgreSQL backup
#!/bin/bash
BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/graphflow_${TIMESTAMP}.sql"

# Create backup
kubectl exec -n graphflow-system postgres-0 -- \
  pg_dump -U postgres graphflow > ${BACKUP_FILE}

# Compress
gzip ${BACKUP_FILE}

# Upload to S3
aws s3 cp ${BACKUP_FILE}.gz s3://graphflow-backups/postgres/

# Clean old backups
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +7 -delete
```

### Redis Backup

```bash
# Redis backup
kubectl exec -n graphflow-system redis-master-0 -- \
  redis-cli --rdb /data/dump.rdb BGSAVE

# Copy backup
kubectl cp graphflow-system/redis-master-0:/data/dump.rdb \
  ./backups/redis/dump_$(date +%Y%m%d_%H%M%S).rdb
```

### Disaster Recovery

```yaml
# Velero backup configuration
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: graphflow-backup
  namespace: velero
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  template:
    includedNamespaces:
    - graphflow-system
    storageLocation: default
    volumeSnapshotLocations:
    - default
    ttl: 720h  # 30 days retention
```

## Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**
   ```bash
   # Check logs
   kubectl logs -n graphflow-system graphflow-gateway-xxx -p
   
   # Check events
   kubectl describe pod -n graphflow-system graphflow-gateway-xxx
   
   # Common causes:
   # - Missing environment variables
   # - Database connection issues
   # - Insufficient resources
   ```

2. **High Memory Usage**
   ```bash
   # Check memory usage
   kubectl top pods -n graphflow-system
   
   # Get heap dump
   kubectl exec -n graphflow-system graphflow-gateway-xxx -- \
     python -m pyheapdump dump.hprof
   ```

3. **Slow Response Times**
   ```bash
   # Check metrics
   curl http://graphflow-service:8081/metrics | grep latency
   
   # Enable debug logging
   kubectl set env deployment/graphflow-gateway \
     GRAPHFLOW_LOG_LEVEL=DEBUG -n graphflow-system
   ```

### Debug Commands

```bash
# Port forward for local debugging
kubectl port-forward -n graphflow-system \
  svc/graphflow-service 8080:8080

# Execute commands in pod
kubectl exec -it -n graphflow-system \
  graphflow-gateway-xxx -- /bin/bash

# Check connectivity
kubectl run -it --rm debug \
  --image=nicolaka/netshoot \
  --restart=Never -- /bin/bash

# View real-time logs
kubectl logs -f -n graphflow-system \
  -l app=graphflow-gateway --tail=100
```

### Performance Profiling

```python
# Enable profiling endpoint
import cProfile
import pstats
from io import StringIO

@app.get("/debug/profile")
async def profile_endpoint():
    pr = cProfile.Profile()
    pr.enable()
    
    # Run some operations
    await process_test_stimuli()
    
    pr.disable()
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    
    return {"profile": s.getvalue()}
```