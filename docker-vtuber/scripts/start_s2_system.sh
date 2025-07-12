#!/bin/bash
# Start S2 System with proper initialization

echo "🚀 Starting S2 Specialized Teams System"
echo "========================================"

# Navigate to docker-vtuber directory
cd "$(dirname "$0")/.." || exit 1

# Check if docker-compose file exists
if [ ! -f "docker-compose.all.yml" ]; then
    echo "❌ docker-compose.all.yml not found!"
    exit 1
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.all.yml down

# Create queue directory on host (for easier debugging)
echo "📁 Creating queue directory..."
sudo mkdir -p /tmp/s2_queue
sudo chmod 777 /tmp/s2_queue

# Start services
echo "🔄 Starting services..."
docker-compose -f docker-compose.all.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
python3 scripts/verify_s2_setup.py

echo ""
echo "✅ S2 System started!"
echo ""
echo "📋 Next steps:"
echo "1. Test all routing scenarios:"
echo "   python3 scripts/test_all_routing_scenarios.py"
echo ""
echo "2. Monitor queue processing:"
echo "   python3 scripts/monitor_s2_queue.py"
echo ""
echo "3. View logs:"
echo "   docker logs -f autogen_agent | grep -E 'QUEUE|S2|TEAM'"
echo ""
echo "4. Test specific scenarios:"
echo "   python3 scripts/test_s2_queue_system.py --test-characters"