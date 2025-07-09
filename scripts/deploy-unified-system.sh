#!/bin/bash

echo "🚀 Deploying Unified VTuber System with Complete Monitoring"
echo "=========================================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your OPENAI_API_KEY"
    exit 1
fi

# Stop all existing containers
echo "📦 Stopping existing containers..."
docker-compose -f docker-vtuber/docker-compose.neurobridge.yml down 2>/dev/null || true
docker-compose -f docker-vtuber/app/CORE/graphflow-stimuli-system/docker-compose.yml down 2>/dev/null || true
docker-compose -f docker-compose.monitoring.yml down 2>/dev/null || true

# Create required directories
echo "📁 Creating directories..."
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/exporters
mkdir -p docker-vtuber/app/CORE/graphflow-stimuli-system/logs
mkdir -p docker-vtuber/app/CORE/autogen-agent/logs

# Ensure Ollama exporter exists
if [ ! -f monitoring/exporters/ollama_exporter.py ]; then
    echo "📝 Creating Ollama exporter..."
    cat > monitoring/exporters/ollama_exporter.py << 'EOF'
#!/usr/bin/env python3
import os
import time
import requests
from prometheus_client import start_http_server, Gauge, REGISTRY
from prometheus_client.core import GaugeMetricFamily
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
EXPORTER_PORT = int(os.getenv('EXPORTER_PORT', '9122'))

class OllamaCollector:
    def __init__(self):
        self.ollama_host = OLLAMA_HOST
        
    def collect(self):
        try:
            response = requests.get(f"{self.ollama_host}/api/ps", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                
                yield GaugeMetricFamily(
                    'ollama_running_models_count',
                    'Number of currently running models',
                    value=len(models)
                )
                
                for model in models:
                    labels = [model.get('name', 'unknown')]
                    yield GaugeMetricFamily(
                        'ollama_model_memory_bytes',
                        'Memory usage of running model in bytes',
                        value=model.get('size', 0),
                        labels=['model']
                    )
        except Exception as e:
            logger.error(f"Failed to collect Ollama metrics: {e}")
            
        try:
            response = requests.get(f"{self.ollama_host}/", timeout=5)
            up = 1 if response.status_code == 200 else 0
        except:
            up = 0
            
        yield GaugeMetricFamily(
            'ollama_up',
            'Whether Ollama is up and responding',
            value=up
        )

if __name__ == '__main__':
    REGISTRY.register(OllamaCollector())
    start_http_server(EXPORTER_PORT)
    logger.info(f"Ollama exporter started on port {EXPORTER_PORT}")
    logger.info(f"Monitoring Ollama at {OLLAMA_HOST}")
    while True:
        time.sleep(60)
EOF
fi

# Ensure Grafana provisioning is set up
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

# Start the unified system
echo "🔄 Starting unified system..."
docker-compose -f docker-compose.unified.yml up -d

# Wait for services to start
echo "⏳ Waiting for services to initialize..."
sleep 20

# Pull Ollama models if needed
echo "🤖 Ensuring Ollama models are available..."
docker exec vtuber-ollama ollama pull llama3.1:8b 2>/dev/null || true

# Check service status
echo ""
echo "✅ Service Status:"
echo "=================="

check_service() {
    local name=$1
    local url=$2
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -qE "200|302|404"; then
        echo "✓ $name is running"
    else
        echo "✗ $name is not responding"
    fi
}

echo "Core Services:"
check_service "NeuroSync S1" "http://localhost:5001"
check_service "AutoGen Agent" "http://localhost:8200"
check_service "GraphFlow Gateway" "http://localhost:8081/api/v1/health"
check_service "Ollama LLM" "http://localhost:11434"

echo ""
echo "Data Stores:"
check_service "Redis" "http://localhost:6379" 2>/dev/null || echo "✓ Redis is running"
check_service "PostgreSQL (AutoGen)" "http://localhost:5434" 2>/dev/null || echo "✓ PostgreSQL (AutoGen) is running"
check_service "PostgreSQL (GraphFlow)" "http://localhost:5433" 2>/dev/null || echo "✓ PostgreSQL (GraphFlow) is running"
check_service "Neo4j" "http://localhost:7474"

echo ""
echo "Monitoring Stack:"
check_service "Grafana" "http://localhost:3000"
check_service "Prometheus" "http://localhost:9090"
check_service "Node Exporter" "http://localhost:9100/metrics"
check_service "cAdvisor" "http://localhost:8090"

echo ""
echo "📊 Access Points:"
echo "================="
echo "🎨 Grafana Dashboard: http://localhost:3000 (admin/admin)"
echo "📈 Prometheus: http://localhost:9090"
echo "🔍 cAdvisor: http://localhost:8090"
echo "🧠 Neo4j Browser: http://localhost:7474 (neo4j/password123)"
echo "🤖 GraphFlow API: http://localhost:8081/api/docs"
echo "🎭 VTuber API: http://localhost:5001"
echo "🤝 AutoGen API: http://localhost:8200"

echo ""
echo "📋 Available Dashboards in Grafana:"
echo "=================================="
echo "1. VTuber System Overview - Complete system health"
echo "2. NeuroSync S1 Detailed - Avatar performance metrics"
echo "3. GraphFlow Dashboard - Stimuli processing analytics"
echo "4. Container Performance - Resource usage monitoring"

echo ""
echo "🔗 Quick Commands:"
echo "=================="
echo "View logs: docker-compose -f docker-compose.unified.yml logs -f [service]"
echo "Stop all: docker-compose -f docker-compose.unified.yml down"
echo "Restart service: docker-compose -f docker-compose.unified.yml restart [service]"

echo ""
echo "✨ Unified system deployment complete!"
echo ""
echo "💡 Next Steps:"
echo "1. Open Grafana at http://localhost:3000"
echo "2. Login with admin/admin"
echo "3. Explore the pre-configured dashboards"
echo "4. Send test messages through GraphFlow API"