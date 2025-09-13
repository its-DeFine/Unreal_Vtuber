#!/bin/bash

# LiveKit VTuber Agent Deployment Script

set -e

echo "==========================================

"
echo "LiveKit VTuber Agent Deployment"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${YELLOW}Warning: Running as root is not recommended${NC}"
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "Checking prerequisites..."

if ! command_exists docker; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Load environment variables
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    source .env
else
    echo -e "${YELLOW}No .env file found. Creating from template...${NC}"
    cat > .env << EOF
# LiveKit VTuber Agent Environment Variables

# Agent Configuration
AGENT_NAME=Luna
PERSONALITY="friendly energetic streamer"
LLM_MODEL=llama3.2

# Central Manager
MANAGER_URL=http://central-manager:8000
ORCHESTRATOR_ID=orchestrator-001
ORCHESTRATOR_AUTH_TOKEN=your_auth_token

# Twitch Integration (optional)
TWITCH_CLIENT_ID=
TWITCH_CLIENT_SECRET=
TWITCH_ACCESS_TOKEN=
TWITCH_CHANNEL=
TWITCH_BOT_NAME=VTuberBot

# YouTube Integration (optional)
YOUTUBE_API_KEY=
YOUTUBE_CHANNEL_ID=

# Livepeer (optional)
LIVEPEER_API_KEY=
LIVEPEER_API_SECRET=

# Behavior Settings
CHAT_RESPONSE_RATE=0.3
DONATION_THRESHOLD=5.00
MEMORY_CONSOLIDATION_INTERVAL=3600

# Paths
AUTONOMY_PATH=../../autonomy
EOF
    echo -e "${GREEN}Created .env file. Please edit it with your credentials.${NC}"
fi

# Function to deploy
deploy() {
    echo "Starting deployment..."
    
    # Build images
    echo "Building Docker images..."
    docker-compose -f docker/docker-compose.yml build
    
    # Pull required images
    echo "Pulling required images..."
    docker-compose -f docker/docker-compose.yml pull
    
    # Start services
    echo "Starting services..."
    docker-compose -f docker/docker-compose.yml up -d
    
    echo -e "${GREEN}✓ Deployment complete!${NC}"
    echo ""
    
    # Show status
    show_status
}

# Function to stop services
stop_services() {
    echo "Stopping services..."
    docker-compose -f docker/docker-compose.yml down
    echo -e "${GREEN}✓ Services stopped${NC}"
}

# Function to show status
show_status() {
    echo "Service Status:"
    echo "----------------------------------------"
    docker-compose -f docker/docker-compose.yml ps
    echo ""
    
    # Check LiveKit server
    if curl -s http://localhost:7881/health > /dev/null; then
        echo -e "LiveKit Server: ${GREEN}✓ Healthy${NC}"
    else
        echo -e "LiveKit Server: ${RED}✗ Not responding${NC}"
    fi
    
    # Check agent
    if docker ps | grep -q livekit_vtuber_agent; then
        echo -e "VTuber Agent: ${GREEN}✓ Running${NC}"
    else
        echo -e "VTuber Agent: ${RED}✗ Not running${NC}"
    fi
    
    # Check neurosync
    if docker ps | grep -q neurosync_s1; then
        echo -e "NeuroSync S1: ${GREEN}✓ Running${NC}"
    else
        echo -e "NeuroSync S1: ${RED}✗ Not running${NC}"
    fi
    
    echo ""
}

# Function to show logs
show_logs() {
    SERVICE=$1
    if [ -z "$SERVICE" ]; then
        docker-compose -f docker/docker-compose.yml logs -f
    else
        docker-compose -f docker/docker-compose.yml logs -f "$SERVICE"
    fi
}

# Function to test connection
test_connection() {
    echo "Testing connections..."
    echo ""
    
    # Test LiveKit
    echo -n "LiveKit Server: "
    if curl -s http://localhost:7881/health > /dev/null; then
        echo -e "${GREEN}Connected${NC}"
    else
        echo -e "${RED}Failed${NC}"
    fi
    
    # Test TCP
    echo -n "TCP Control (neurosync_s1): "
    if nc -zv localhost 5001 2>/dev/null; then
        echo -e "${GREEN}Connected${NC}"
    else
        echo -e "${RED}Failed${NC}"
    fi
    
    # Test Redis
    echo -n "Redis: "
    if docker exec redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}Connected${NC}"
    else
        echo -e "${RED}Failed${NC}"
    fi
    
    # Test Ollama
    echo -n "Ollama: "
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo -e "${GREEN}Connected${NC}"
    else
        echo -e "${RED}Failed${NC}"
    fi
    
    echo ""
}

# Function to load Ollama models
load_models() {
    echo "Loading Ollama models..."
    
    # Pull models
    docker exec ollama ollama pull llama3.2
    docker exec ollama ollama pull mistral
    
    echo -e "${GREEN}✓ Models loaded${NC}"
}

# Main menu
case "$1" in
    deploy|start)
        deploy
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        deploy
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    test)
        test_connection
        ;;
    models)
        load_models
        ;;
    clean)
        echo "Cleaning up..."
        docker-compose -f docker/docker-compose.yml down -v
        echo -e "${GREEN}✓ Cleanup complete${NC}"
        ;;
    *)
        echo "LiveKit VTuber Agent Deployment Script"
        echo ""
        echo "Usage: $0 {deploy|stop|restart|status|logs|test|models|clean}"
        echo ""
        echo "Commands:"
        echo "  deploy    - Build and start all services"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  status    - Show service status"
        echo "  logs      - Show logs (optional: service name)"
        echo "  test      - Test connections"
        echo "  models    - Load Ollama models"
        echo "  clean     - Stop and remove all containers and volumes"
        echo ""
        echo "Examples:"
        echo "  $0 deploy           # Deploy the system"
        echo "  $0 logs agent       # Show agent logs"
        echo "  $0 status           # Check status"
        echo ""
        exit 1
        ;;
esac