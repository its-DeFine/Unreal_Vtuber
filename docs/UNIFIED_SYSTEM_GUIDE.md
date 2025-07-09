# 🎯 Unified VTuber System Guide

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User/Admin Input                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GraphFlow Gateway (:8081)                     │
│                 (External Stimuli Processing)                    │
└────────────┬──────────────────────────────────┬─────────────────┘
             │                                  │
             ▼                                  ▼
┌────────────────────────────┐    ┌────────────────────────────────┐
│    NeuroSync S1 (:5001)    │    │   AutoGen Agent (:8200)       │
│    (VTuber Avatar System)  │    │   (Multi-Agent Intelligence)   │
└────────────┬───────────────┘    └──────────┬─────────────────────┘
             │                               │
             ├───────────────┬───────────────┤
             │               │               │
             ▼               ▼               ▼
┌─────────────────┐ ┌─────────────┐ ┌──────────────┐
│ Redis (:6379)   │ │ PostgreSQL  │ │ Neo4j (:7474)│
│ (Shared Context)│ │ (:5433/5434)│ │(Graph Store) │
└─────────────────┘ └─────────────┘ └──────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Ollama LLM (:11434)                          │
│                  (Local Language Model)                         │
└─────────────────────────────────────────────────────────────────┘

                        Monitoring Layer
┌─────────────────────────────────────────────────────────────────┐
│  Prometheus (:9090) → Grafana (:3000) → Dashboards & Alerts    │
│  Node Exporter (:9100) | cAdvisor (:8090) | Custom Exporters   │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Deploy Everything
```bash
./deploy-unified-system.sh
```

### 2. Access Points
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **GraphFlow API**: http://localhost:8081/api/docs
- **Prometheus**: http://localhost:9090
- **Neo4j Browser**: http://localhost:7474 (neo4j/password123)

## 📊 Monitoring Features

### Pre-configured Dashboards

1. **VTuber System Overview**
   - Real-time health status of all services
   - System resource usage (CPU, Memory)
   - Stimuli processing rates
   - Container performance metrics

2. **NeuroSync S1 Detailed**
   - Speech generation rate
   - Response time percentiles
   - Character switching activity
   - Error rates and active sessions

3. **GraphFlow Dashboard**
   - Stimuli categorization breakdown
   - Processing pipeline performance
   - Routing decisions analytics
   - API endpoint metrics

4. **AutoGen Performance**
   - Agent activity metrics
   - Task completion rates
   - Multi-agent coordination stats
   - Evolution cycle tracking

### Automated Alerts

The system includes pre-configured alerts for:
- Service downtime
- High error rates
- Performance degradation
- Resource exhaustion
- Database connectivity issues

## 🔧 Service Management

### View Logs
```bash
# All services
docker-compose -f docker-compose.unified.yml logs -f

# Specific service
docker-compose -f docker-compose.unified.yml logs -f neurosync
```

### Restart Services
```bash
# Single service
docker-compose -f docker-compose.unified.yml restart graphflow-gateway

# All services
docker-compose -f docker-compose.unified.yml restart
```

### Scale Services
```bash
# Scale AutoGen agents
docker-compose -f docker-compose.unified.yml up -d --scale autogen_agent=3
```

## 📈 Key Metrics

### NeuroSync S1
- `neurosync_speech_generated_total` - Total speeches generated
- `neurosync_processing_duration_seconds` - Response time histogram
- `neurosync_active_sessions` - Current active sessions
- `neurosync_character_switches_total` - Character changes

### GraphFlow
- `graphflow_stimuli_submissions_total` - Stimuli by source/priority
- `graphflow_processing_time_seconds` - Processing duration
- `graphflow_routing_decisions_total` - Routing decision distribution
- `graphflow_active_requests` - Current processing queue

### AutoGen
- `autogen_agent_tasks_total` - Tasks processed
- `autogen_evolution_cycles_total` - Self-improvement cycles
- `autogen_tool_executions_total` - Tool usage statistics
- `autogen_conversation_length` - Conversation metrics

### System
- `node_cpu_seconds_total` - CPU usage
- `node_memory_MemAvailable_bytes` - Available memory
- `container_cpu_usage_seconds_total` - Per-container CPU
- `container_memory_usage_bytes` - Per-container memory

## 🛠️ Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.unified.yml logs [service-name]

# Check port conflicts
netstat -tulpn | grep [port-number]
```

### Monitoring Not Working
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify metrics endpoint
curl http://[service]:[port]/metrics
```

### Performance Issues
1. Check Grafana dashboards for resource bottlenecks
2. Review container limits in docker-compose.unified.yml
3. Scale services if needed

## 🔐 Security Notes

- Change default passwords in production
- Configure firewall rules for exposed ports
- Use environment variables for sensitive data
- Enable SSL/TLS for external access

## 📦 Backup & Recovery

### Backup Data
```bash
# Backup all volumes
docker run --rm -v autonomy_redis_data:/data -v backup:/backup alpine tar czf /backup/redis-backup.tar.gz -C /data .
docker run --rm -v autonomy_autonomous_postgres_data:/data -v backup:/backup alpine tar czf /backup/postgres-backup.tar.gz -C /data .
```

### Restore Data
```bash
# Restore volumes
docker run --rm -v autonomy_redis_data:/data -v backup:/backup alpine tar xzf /backup/redis-backup.tar.gz -C /data
```

## 🎉 Features Summary

✅ **Unified Deployment** - Single command to deploy everything
✅ **Complete Monitoring** - All services monitored automatically
✅ **Pre-configured Dashboards** - Beautiful visualizations ready to use
✅ **Automated Alerts** - Proactive issue detection
✅ **Service Discovery** - New containers automatically monitored
✅ **Log Aggregation** - Centralized logging with Loki
✅ **Performance Metrics** - Detailed performance tracking
✅ **Resource Monitoring** - Container and system resource usage
✅ **Health Checks** - Automatic health monitoring
✅ **Scalability** - Easy horizontal scaling