#!/bin/bash
# Start VTuber with Unreal Engine Pixel Streaming
# Created: 2025-09-08

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}     VTuber + Unreal Engine Pixel Streaming Launcher${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Check if running from correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found!${NC}"
    echo "Please run this script from the autonomy directory"
    exit 1
fi

# Check if Unreal compose file exists
if [ ! -f "docker-compose.unreal.yml" ]; then
    echo -e "${RED}Error: docker-compose.unreal.yml not found!${NC}"
    echo "Unreal integration files are missing"
    exit 1
fi

# Check environment files
echo -e "${YELLOW}Checking environment configuration...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found, copying from .env.example${NC}"
    cp .env.example .env
fi

if [ ! -f ".env.unreal" ]; then
    echo -e "${RED}Error: .env.unreal file not found!${NC}"
    echo "Please configure Unreal settings:"
    echo "  1. Copy .env.unreal.example to .env.unreal"
    echo "  2. Edit .env.unreal with your game paths"
    exit 1
fi

# Parse command line arguments
COMMAND=${1:-up}
DETACHED=""
if [ "$2" == "-d" ] || [ "$1" == "-d" ]; then
    DETACHED="-d"
fi

# Function to check service health
check_health() {
    echo -e "\n${YELLOW}Checking service health...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.unreal.yml ps
}

# Function to show logs
show_logs() {
    SERVICE=$1
    if [ -z "$SERVICE" ]; then
        docker-compose -f docker-compose.yml -f docker-compose.unreal.yml logs --tail=50
    else
        docker-compose -f docker-compose.yml -f docker-compose.unreal.yml logs --tail=50 $SERVICE
    fi
}

# Main execution
case "$COMMAND" in
    up|start)
        echo -e "${GREEN}Starting VTuber with Unreal Engine...${NC}"
        
        # Create network if it doesn't exist
        docker network create vtuber_network 2>/dev/null || true
        
        # Load environment variables
        set -a
        source .env
        source .env.unreal
        set +a
        
        # Start services
        docker-compose -f docker-compose.yml -f docker-compose.unreal.yml up $DETACHED
        
        if [ "$DETACHED" == "-d" ]; then
            echo -e "\n${GREEN}Services started in background!${NC}"
            sleep 5
            check_health
            
            echo -e "\n${GREEN}Access points:${NC}"
            echo -e "  Web Interface: ${YELLOW}http://localhost:8080${NC}"
            echo -e "  VTuber API: ${YELLOW}http://localhost:5001${NC}"
            echo -e "  TCP Control: ${YELLOW}localhost:7777${NC}"
            echo -e "\n${GREEN}View logs with:${NC} $0 logs [service-name]"
        fi
        ;;
        
    down|stop)
        echo -e "${YELLOW}Stopping VTuber and Unreal Engine...${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.unreal.yml down
        echo -e "${GREEN}Services stopped!${NC}"
        ;;
        
    restart)
        echo -e "${YELLOW}Restarting services...${NC}"
        $0 stop
        sleep 2
        $0 start $DETACHED
        ;;
        
    logs)
        show_logs $2
        ;;
        
    ps|status)
        check_health
        ;;
        
    build)
        echo -e "${YELLOW}Building Docker images...${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.unreal.yml build
        echo -e "${GREEN}Build complete!${NC}"
        ;;
        
    test)
        echo -e "${YELLOW}Testing Unreal TCP connection...${NC}"
        docker exec neurosync_s1 python -c "
import socket
import sys
try:
    s = socket.socket()
    s.settimeout(5)
    s.connect(('unreal-game', 7777))
    s.send(b'TEST\\n')
    response = s.recv(1024)
    s.close()
    print('✅ TCP connection successful!')
    print(f'Response: {response.decode()}')
    sys.exit(0)
except Exception as e:
    print(f'❌ TCP connection failed: {e}')
    sys.exit(1)
" || echo -e "${RED}Connection test failed${NC}"
        ;;
        
    help|--help|-h)
        echo "Usage: $0 [COMMAND] [OPTIONS]"
        echo ""
        echo "Commands:"
        echo "  up, start     Start all services"
        echo "  down, stop    Stop all services"
        echo "  restart       Restart all services"
        echo "  logs [name]   Show logs (optionally for specific service)"
        echo "  ps, status    Show service status"
        echo "  build         Build Docker images"
        echo "  test          Test Unreal TCP connection"
        echo "  help          Show this help message"
        echo ""
        echo "Options:"
        echo "  -d            Run in detached mode (background)"
        echo ""
        echo "Examples:"
        echo "  $0 start -d              # Start in background"
        echo "  $0 logs unreal-game      # Show game logs"
        echo "  $0 test                  # Test TCP connection"
        ;;
        
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac