#!/bin/bash

echo "🚀 Deploying Unified Monitoring System"
echo "====================================="
echo ""

# Stop existing Grafana and Prometheus if running
echo "📦 Stopping existing monitoring containers..."
docker stop graphflow-stimuli-system-prometheus-1 graphflow-stimuli-system-grafana-1 2>/dev/null || true
docker rm graphflow-stimuli-system-prometheus-1 graphflow-stimuli-system-grafana-1 2>/dev/null || true

# Create required directories
echo "📁 Creating monitoring directories..."
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/exporters

# Copy GraphFlow dashboard to unified monitoring
echo "📋 Copying dashboards..."
cp docker-vtuber/app/CORE/graphflow-stimuli-system/monitoring/grafana/dashboards/graphflow-dashboard.json monitoring/grafana/dashboards/ 2>/dev/null || true

# Update Grafana provisioning
echo "🔧 Configuring Grafana provisioning..."
cat > monitoring/grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    uid: prometheus
    jsonData:
      timeInterval: "15s"
EOF

cat > monitoring/grafana/provisioning/dashboards/dashboard.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'Default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

# Start unified monitoring
echo "🔄 Starting unified monitoring stack..."
docker-compose -f docker-compose.monitoring.yml up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo ""
echo "✅ Service Status:"
echo "=================="

check_service() {
    local name=$1
    local url=$2
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -qE "200|302"; then
        echo "✓ $name is running at $url"
    else
        echo "✗ $name is not responding at $url"
    fi
}

check_service "Grafana" "http://localhost:3000"
check_service "Prometheus" "http://localhost:9090"
check_service "Node Exporter" "http://localhost:9100/metrics"

echo ""
echo "📊 Grafana Access:"
echo "=================="
echo "URL: http://localhost:3000"
echo "Username: admin"
echo "Password: admin"
echo ""
echo "✨ Features:"
echo "- Auto-configured Prometheus datasource"
echo "- Pre-loaded dashboards:"
echo "  - Unified System Overview"
echo "  - GraphFlow Dashboard"
echo "  - Container metrics via cAdvisor"
echo "  - System metrics via Node Exporter"
echo ""
echo "📈 Monitored Services:"
echo "- GraphFlow Gateway"
echo "- VTuber S1"
echo "- AutoGen Agent"
echo "- Ollama"
echo "- Redis"
echo "- PostgreSQL"
echo "- All Docker containers"
echo ""
echo "🔗 Quick Links:"
echo "- Grafana: http://localhost:3000"
echo "- Prometheus: http://localhost:9090"
echo "- Prometheus Targets: http://localhost:9090/targets"
echo ""
echo "✅ Unified monitoring deployment complete!"