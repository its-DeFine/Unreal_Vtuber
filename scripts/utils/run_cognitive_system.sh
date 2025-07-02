#!/bin/bash

# 🧠 Advanced Cognitive System Startup & Monitoring Script
# Starts the complete autonomous VTuber system with cognitive capabilities

set -e

echo "🧠 ═══════════════════════════════════════════════"
echo "🧠   ADVANCED COGNITIVE SYSTEM STARTUP"
echo "🧠 ═══════════════════════════════════════════════"
echo "📅 $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Function to print colored output
print_status() {
    echo "🔧 $1"
}

print_success() {
    echo "✅ $1"
}

print_error() {
    echo "❌ $1"
}

print_info() {
    echo "📋 $1"
}

# Check if Docker is running
print_status "Checking Docker daemon..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi
print_success "Docker daemon is running"

# Check if docker-compose is available
print_status "Checking docker-compose availability..."
if ! command -v docker-compose > /dev/null 2>&1; then
    print_error "docker-compose is not installed or not in PATH"
    exit 1
fi
print_success "docker-compose is available"

# Navigate to correct directory
print_status "Navigating to project root..."
cd "$(dirname "$0")/.."
print_success "In directory: $(pwd)"

# Clean up any existing containers (optional)
print_status "Stopping any existing cognitive system containers..."
docker-compose -f config/docker-compose.bridge.yml down > /dev/null 2>&1 || true
print_success "Existing containers stopped"

echo ""
print_info "🚀 Starting Cognitive System Services..."
print_info "   • PostgreSQL + pgvector (Analytics database)"
print_info "   • Redis (SCB state management)"  
print_info "   • Cognee (Knowledge graph - NO Neo4j needed!)"
print_info "   • NeuroSync (VTuber + SCB bridge)"
print_info "   • Autonomous Agent (Enhanced with cognitive plugins)"
echo ""

# Start the complete system
print_status "Building and starting all services..."
docker-compose -f config/docker-compose.bridge.yml up --build -d

# Wait for services to be ready
print_status "Waiting for services to initialize..."

# Check PostgreSQL health
print_info "🗄️ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker exec autonomous_postgres_bridge pg_isready -U postgres -d autonomous_agent > /dev/null 2>&1; then
        print_success "PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "PostgreSQL failed to start after 30 attempts"
        exit 1
    fi
    sleep 1
done

# Check Redis
print_info "📡 Waiting for Redis to be ready..."
for i in {1..10}; do
    if docker exec redis_scb redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is ready"
        break
    fi
    if [ $i -eq 10 ]; then
        print_error "Redis failed to start after 10 attempts"
        exit 1
    fi
    sleep 1
done

# Check Cognee
print_info "🧠 Waiting for Cognee knowledge graph service..."
for i in {1..20}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Cognee knowledge graph service is ready"
        break
    fi
    if [ $i -eq 20 ]; then
        print_error "Cognee failed to start after 20 attempts"
        exit 1
    fi
    sleep 2
done

# Check NeuroSync VTuber system
print_info "🎭 Waiting for NeuroSync VTuber system..."
for i in {1..15}; do
    if curl -s http://localhost:5001/health > /dev/null 2>&1; then
        print_success "NeuroSync VTuber system is ready"
        break
    fi
    if [ $i -eq 15 ]; then
        print_error "NeuroSync failed to start after 15 attempts"
        exit 1
    fi
    sleep 2
done

# Check Autonomous Agent
print_info "🤖 Waiting for Autonomous Agent with cognitive plugins..."
for i in {1..25}; do
    if curl -s http://localhost:3100/health > /dev/null 2>&1; then
        print_success "Autonomous Agent with cognitive capabilities is ready"
        break
    fi
    if [ $i -eq 25 ]; then
        print_error "Autonomous Agent failed to start after 25 attempts"
        exit 1
    fi
    sleep 3
done

echo ""
print_success "🧠 COGNITIVE SYSTEM FULLY OPERATIONAL! 🚀"
echo ""

print_info "📋 Service Status:"
print_info "   🗄️ PostgreSQL + Analytics: http://localhost:5434"
print_info "   📡 Redis SCB Bridge: localhost:6379"
print_info "   🧠 Cognee Knowledge Graph: http://localhost:8000"
print_info "   🎭 NeuroSync VTuber: http://localhost:5001"
print_info "   🤖 Autonomous Agent: http://localhost:3100"
print_info "   📊 SCB Bridge API: http://localhost:5000"

echo ""
print_info "🧠 Key Cognitive Features Active:"
print_info "   ✅ Knowledge Graph Memory (90% answer relevancy)"
print_info "   ✅ Autonomous Work Execution & Evaluation"
print_info "   ✅ Multi-dimensional Quality Scoring"
print_info "   ✅ Task Manager with Real Work Artifacts"
print_info "   ✅ Enhanced Decision Making with Semantic Search"
print_info "   ✅ Plugin Architecture Integration"

echo ""
print_info "🔧 Testing Options:"
print_info "   📋 Run tests: python3 tests/test_cognitive_system.py"
print_info "   📊 Monitor logs: ./scripts/monitor_logs.sh"
print_info "   🧪 Test Cognee: curl -X POST http://localhost:8000/api/v1/add -H 'Content-Type: application/json' -d '{\"data\": [\"Test memory\"], \"dataset_name\": \"test\"}'"

echo ""
print_info "📈 Monitoring Commands:"
print_info "   🔍 All logs: docker-compose -f config/docker-compose.bridge.yml logs -f"
print_info "   🧠 Cognee logs: docker logs cognee_server -f"
print_info "   🤖 Agent logs: docker logs autonomous_starter_s3 -f"
print_info "   🎭 VTuber logs: docker logs neurosync_s1 -f"

echo ""
if [ "$1" = "--monitor" ]; then
    print_info "🔍 Starting log monitoring (Ctrl+C to exit)..."
    echo ""
    docker-compose -f config/docker-compose.bridge.yml logs -f
else
    print_info "💡 Use './scripts/run_cognitive_system.sh --monitor' to watch logs in real-time"
    print_info "💡 Use './scripts/stop_cognitive_system.sh' to stop all services"
fi

echo ""
print_success "🧠 Cognitive System Ready for Advanced AI Operations! 🎯" 