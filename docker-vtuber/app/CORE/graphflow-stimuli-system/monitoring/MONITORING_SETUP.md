# GraphFlow Monitoring Setup Guide

## 📊 Grafana Access

### Login Credentials
- **URL**: http://localhost:3001
- **Username**: `admin`
- **Password**: `admin`

> Note: Grafana will prompt you to change the password on first login. You can skip this if it's just for local development.

## 🔧 Setting Up Prometheus Data Source

### 1. Access Grafana
1. Open http://localhost:3001 in your browser
2. Login with `admin`/`admin`

### 2. Add Prometheus Data Source
1. Click the gear icon (⚙️) → **Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Configure:
   - **Name**: `GraphFlow-Prometheus`
   - **URL**: `http://prometheus:9090` (internal Docker network)
   - **Access**: `Server (default)`
5. Click **Save & Test**

## 📈 Creating GraphFlow Dashboard

### Quick Import Dashboard
1. Click the **+** icon → **Import**
2. Upload or paste the dashboard JSON from: `monitoring/grafana/dashboards/graphflow-dashboard.json`

### Manual Dashboard Creation
1. Click **+** → **Create** → **Dashboard**
2. Add panels for key metrics:

#### Panel 1: Stimuli Processing Rate
```promql
rate(graphflow_stimuli_submissions_total[5m])
```
- Title: "Stimuli Processing Rate"
- Visualization: Time series

#### Panel 2: Processing Time
```promql
histogram_quantile(0.95, rate(graphflow_processing_duration_seconds_bucket[5m]))
```
- Title: "95th Percentile Processing Time"
- Visualization: Gauge

#### Panel 3: System Status
```promql
up{job="graphflow-gateway"}
```
- Title: "System Status"
- Visualization: Stat

#### Panel 4: Active Requests
```promql
graphflow_active_requests
```
- Title: "Active Requests"
- Visualization: Stat

#### Panel 5: Total Processed by Category
```promql
sum by (category) (rate(graphflow_stimuli_submissions_total[5m]))
```
- Title: "Stimuli by Category"
- Visualization: Pie chart

#### Panel 6: API Request Rate
```promql
rate(graphflow_api_requests_total[5m])
```
- Title: "API Request Rate"
- Visualization: Time series
- Legend: {{method}} {{endpoint}}

#### Panel 7: WebSocket Connections
```promql
graphflow_active_websocket_connections
```
- Title: "Active WebSocket Connections"
- Visualization: Stat

#### Panel 8: Decision Distribution
```promql
sum by (decision) (rate(graphflow_routing_decisions_total[5m]))
```
- Title: "Routing Decisions"
- Visualization: Bar chart

## 🎯 Available Metrics

### GraphFlow Specific Metrics
- `graphflow_stimuli_submissions_total` - Total stimuli submitted (by source, priority)
- `graphflow_processing_duration_seconds` - Processing duration histogram
- `graphflow_routing_decisions_total` - Routing decisions made
- `graphflow_api_requests_total` - API requests (by method, endpoint, status)
- `graphflow_api_request_duration_seconds` - API request duration
- `graphflow_active_websocket_connections` - Active WebSocket connections
- `graphflow_active_requests` - Currently active requests
- `graphflow_system_health` - System health status

### System Metrics
- `up` - Target up/down status
- `process_cpu_seconds_total` - CPU usage
- `process_resident_memory_bytes` - Memory usage
- `python_gc_collections_total` - Python garbage collection

## 🚨 Setting Up Alerts

### Example Alert: High Processing Time
1. Go to **Alerting** → **Alert rules**
2. Click **New alert rule**
3. Configure:
   - **Rule name**: "High Stimuli Processing Time"
   - **Query**: 
     ```promql
     histogram_quantile(0.95, rate(graphflow_processing_duration_seconds_bucket[5m])) > 1
     ```
   - **Condition**: When query result is above 1 second
   - **For**: 5 minutes

### Example Alert: System Down
```promql
up{job="graphflow-gateway"} == 0
```

## 📝 Prometheus Configuration

The Prometheus configuration is located at:
`monitoring/prometheus.yml`

Current scrape targets:
- GraphFlow Gateway metrics: `http://graphflow-gateway:9090/metrics`

To add more targets, edit the prometheus.yml:
```yaml
scrape_configs:
  - job_name: 'graphflow-gateway'
    static_configs:
      - targets: ['graphflow-gateway:9090']
    
  # Add more services here
  - job_name: 'vtuber-system'
    static_configs:
      - targets: ['neurosync_s1:5001']
```

## 🔍 Useful PromQL Queries

### Performance Monitoring
```promql
# Average processing time
avg(rate(graphflow_processing_duration_seconds_sum[5m]) / rate(graphflow_processing_duration_seconds_count[5m]))

# Error rate
sum(rate(graphflow_api_requests_total{status=~"4..|5.."}[5m])) / sum(rate(graphflow_api_requests_total[5m]))

# Throughput by priority
sum by (priority) (rate(graphflow_stimuli_submissions_total[5m]))
```

### Capacity Planning
```promql
# Peak concurrent requests
max_over_time(graphflow_active_requests[1h])

# Memory usage trend
rate(process_resident_memory_bytes[5m])
```

## 🛠️ Troubleshooting

### Prometheus Not Scraping
1. Check Prometheus targets: http://localhost:9091/targets
2. Verify the endpoint is accessible:
   ```bash
   curl http://localhost:8081/metrics
   ```

### No Data in Grafana
1. Check data source connection test passes
2. Verify time range is correct (data might be recent)
3. Check Prometheus is receiving data: http://localhost:9091/graph

### Dashboard Not Loading
1. Ensure Prometheus data source is configured
2. Check browser console for errors
3. Verify panel queries are valid

## 📚 Resources
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [PromQL Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)