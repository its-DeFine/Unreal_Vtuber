# 🎯 Unified Monitoring System Guide

## 🚀 Overview
We've deployed a comprehensive monitoring system that tracks ALL your containers and services in one place!

## 📊 Access Points

### Grafana (Main UI)
- **URL**: http://localhost:3002
- **Username**: `admin`
- **Password**: `admin`
- **Features**: 
  - ✅ Auto-configured Prometheus datasource
  - ✅ Pre-loaded dashboards
  - ✅ Real-time metrics from all services

### Prometheus (Metrics)
- **URL**: http://localhost:9090
- **Targets Status**: http://localhost:9090/targets
- **Query Interface**: http://localhost:9090/graph

### cAdvisor (Container Metrics)
- **URL**: http://localhost:8090
- **Shows**: Detailed container resource usage

## 📈 What's Being Monitored

### Services
1. **GraphFlow Gateway** - External stimuli processing
2. **VTuber S1** - Avatar system
3. **AutoGen Agent** - Multi-agent system
4. **Ollama** - LLM service
5. **Redis** - Caching
6. **PostgreSQL** - Database
7. **All Docker Containers** - Via cAdvisor

### Metrics Available
- **System Metrics**: CPU, Memory, Disk, Network (via Node Exporter)
- **Container Metrics**: Per-container CPU, Memory, Network I/O
- **GraphFlow Metrics**: Stimuli processing rate, API requests, routing decisions
- **Service Health**: Up/Down status for all services
- **Custom Metrics**: Ollama models, Redis operations, PostgreSQL queries

## 🎨 Pre-configured Dashboards

### 1. Unified System Overview
Shows all services status at a glance:
- Service health indicators
- System CPU/Memory gauges
- Container resource usage over time
- GraphFlow activity metrics

### 2. GraphFlow Dashboard
Detailed GraphFlow metrics:
- Stimuli processing rate by source
- Processing time percentiles
- API request rates
- Routing decisions

### 3. Container Dashboard (via cAdvisor)
- Per-container resource usage
- Container lifecycle events
- Network I/O statistics

## 🔍 Useful Queries

### Check Service Health
```promql
up{job=~"graphflow-gateway|vtuber-s1|autogen-agent|ollama"}
```

### Container Memory Usage
```promql
container_memory_usage_bytes{name=~".*graphflow.*|.*vtuber.*|.*autogen.*"}
```

### GraphFlow Processing Rate
```promql
rate(graphflow_stimuli_submissions_total[5m])
```

### System Load Average
```promql
node_load1
```

## 🛠️ Management Commands

### View All Metrics
```bash
# GraphFlow metrics
curl http://localhost:8081/metrics

# Node metrics
curl http://localhost:9100/metrics

# Container metrics
curl http://localhost:8090/metrics
```

### Restart Monitoring
```bash
docker-compose -f docker-compose.monitoring.yml restart
```

### View Logs
```bash
# Prometheus logs
docker logs unified_prometheus

# Grafana logs
docker logs unified_grafana
```

## 🚨 Setting Up Alerts

1. In Grafana, go to **Alerting** → **Alert rules**
2. Create alerts for:
   - Service down: `up == 0`
   - High CPU: `rate(container_cpu_usage_seconds_total[5m]) > 0.8`
   - High Memory: `container_memory_usage_bytes > 1000000000`
   - Processing errors: `rate(graphflow_processing_errors_total[5m]) > 0`

## 📦 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Grafana (Port 3002)                  │
│                  (Visualization & Alerts)                │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                 Prometheus (Port 9090)                   │
│                  (Metrics Collection)                    │
└──┬──────┬─────────┬─────────┬─────────┬────────┬───────┘
   │      │         │         │         │        │
   ▼      ▼         ▼         ▼         ▼        ▼
┌──────┐┌────────┐┌────────┐┌──────┐┌──────┐┌────────┐
│Node  ││cAdvisor││GraphFlow││VTuber││AutoGen││ Redis │
│Exp.  ││        ││Gateway  ││  S1  ││ Agent ││Postgres│
│:9100 ││ :8090  ││  :9090  ││:5001 ││ :8000 ││Ollama  │
└──────┘└────────┘└────────┘└──────┘└──────┘└────────┘
```

## 🔄 Automatic Features

1. **Service Discovery**: Prometheus automatically discovers and monitors all containers
2. **Dashboard Provisioning**: Dashboards are automatically loaded on Grafana startup
3. **Datasource Configuration**: Prometheus is pre-configured in Grafana
4. **Metric Retention**: 30 days of historical data

## 💡 Tips

1. **Custom Dashboards**: Create your own by clicking **+** → **Dashboard** in Grafana
2. **Metric Explorer**: Use Prometheus's graph page to explore available metrics
3. **Container Details**: Click on any container in cAdvisor for detailed stats
4. **Export/Import**: Export dashboards as JSON for backup or sharing

## 🆘 Troubleshooting

### Service Not Appearing in Prometheus
1. Check if container is in the correct network:
   ```bash
   docker inspect <container_name> | grep NetworkMode
   ```
2. Verify metrics endpoint:
   ```bash
   curl http://<container>:<port>/metrics
   ```

### Grafana Can't Connect to Prometheus
1. Check Prometheus is running: `docker ps | grep prometheus`
2. Verify datasource URL in Grafana settings

### High Memory Usage
1. Check Prometheus retention: Reduce if needed in `prometheus.yml`
2. Monitor container limits with cAdvisor

## 🎉 Summary

You now have a fully automated, unified monitoring system that:
- ✅ Monitors all your services automatically
- ✅ Requires NO manual configuration
- ✅ Provides beautiful dashboards out of the box
- ✅ Scales with your system
- ✅ Retains 30 days of metrics history

Access Grafana at http://localhost:3002 and start exploring your metrics!