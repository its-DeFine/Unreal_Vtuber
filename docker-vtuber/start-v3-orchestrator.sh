#!/bin/bash
# Start script for AutoGen V3 Orchestrator
# This script ensures the V3 orchestrator is used by default

echo "🚀 Starting VTuber System with AutoGen V3 Orchestrator"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "💡 Creating .env from template..."
    cp .env.v3.example .env
    echo "✅ Created .env file. Please configure your settings and run again."
    exit 1
fi

# Check current orchestrator version
CURRENT_VERSION=$(grep "^ORCHESTRATOR_VERSION=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")

if [ -z "$CURRENT_VERSION" ]; then
    echo "⚠️ ORCHESTRATOR_VERSION not set in .env"
    echo "🔧 Adding ORCHESTRATOR_VERSION=v3 to .env..."
    echo "" >> .env
    echo "# AutoGen V3 Orchestrator (default)" >> .env
    echo "ORCHESTRATOR_VERSION=v3" >> .env
    CURRENT_VERSION="v3"
fi

if [ "$CURRENT_VERSION" = "v2" ]; then
    echo "⚠️ WARNING: You are using the deprecated V2 orchestrator!"
    echo "🔄 V2 is deprecated and will be removed in future releases."
    echo ""
    echo "To migrate to V3, either:"
    echo "1. Run: sed -i 's/ORCHESTRATOR_VERSION=v2/ORCHESTRATOR_VERSION=v3/' .env"
    echo "2. Or manually edit .env and change ORCHESTRATOR_VERSION to v3"
    echo ""
    read -p "Do you want to automatically upgrade to V3 now? (recommended) [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        sed -i 's/ORCHESTRATOR_VERSION=v2/ORCHESTRATOR_VERSION=v3/' .env
        echo "✅ Upgraded to V3 orchestrator!"
        CURRENT_VERSION="v3"
    else
        echo "⚠️ Continuing with deprecated V2 orchestrator..."
    fi
fi

echo "📌 Using Orchestrator Version: $CURRENT_VERSION"
echo ""

# Ensure V3 configuration is present
if [ "$CURRENT_VERSION" = "v3" ]; then
    # Check for V3 specific configs
    if ! grep -q "AUTOGEN_ORCHESTRATOR_ENABLED" .env; then
        echo "🔧 Adding V3 configuration to .env..."
        cat >> .env << 'EOF'

# AutoGen V3 Configuration
AUTOGEN_ORCHESTRATOR_ENABLED=true
ORCHESTRATOR_PERSONA=interactive_streamer
AUTONOMOUS_CONTENT_ENABLED=true
GROUP_CHAT_ENABLED=true
SCB_INTEGRATION_ENABLED=true
EOF
        echo "✅ V3 configuration added!"
    fi
fi

# Determine which docker-compose file to use
if [ -f "docker-compose.yml" ]; then
    COMPOSE_FILE="docker-compose.yml"
elif [ -f "docker-compose.autogen.yml" ]; then
    COMPOSE_FILE="docker-compose.autogen.yml"
elif [ -f "docker-compose.neurobridge.yml" ]; then
    COMPOSE_FILE="docker-compose.neurobridge.yml"
else
    echo "❌ Error: No docker-compose file found!"
    exit 1
fi

echo "🐳 Using compose file: $COMPOSE_FILE"
echo ""

# Build and start containers
echo "🔨 Building containers..."
docker-compose -f $COMPOSE_FILE build

echo ""
echo "🚀 Starting containers..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Check orchestrator status
echo ""
echo "🔍 Checking orchestrator status..."

# Try V3 endpoint first
if curl -s http://localhost:5001/orchestrator/v3/health > /dev/null 2>&1; then
    echo "✅ V3 Orchestrator is running!"
    echo ""
    echo "📊 V3 Status:"
    curl -s http://localhost:5001/orchestrator/v3/agents/status | python3 -m json.tool 2>/dev/null || echo "Status endpoint not ready yet"
elif curl -s http://localhost:5001/orchestrator/status > /dev/null 2>&1; then
    echo "✅ Orchestrator is running (V2 compatibility mode)"
else
    echo "⚠️ Orchestrator not responding yet. Check logs with:"
    echo "   docker-compose -f $COMPOSE_FILE logs neurosync"
fi

echo ""
echo "=================================================="
echo "✅ VTuber System Started!"
echo ""
echo "🌐 Available Endpoints:"
echo "   - Process Text: http://localhost:5001/process_text"
echo "   - Game Control: http://localhost:5001/game_control"
if [ "$CURRENT_VERSION" = "v3" ]; then
    echo "   - V3 Status: http://localhost:5001/orchestrator/v3/agents/status"
    echo "   - V3 Process: http://localhost:5001/orchestrator/v3/process"
    echo "   - V3 Persona: http://localhost:5001/orchestrator/v3/persona"
else
    echo "   - Orchestrator Status: http://localhost:5001/orchestrator/status"
fi
echo ""
echo "📝 Logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "🛑 Stop: docker-compose -f $COMPOSE_FILE down"
echo "=================================================="