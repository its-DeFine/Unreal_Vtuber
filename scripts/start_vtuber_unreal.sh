#!/bin/bash
# Start VTuber with Unreal Engine Pixel Streaming
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}     VTuber + Unreal Engine Pixel Streaming Launcher${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""

BACKEND_COMPOSE="backend/docker-compose.yml"

if [ ! -f "$BACKEND_COMPOSE" ]; then
    echo -e "${RED}Error: $BACKEND_COMPOSE not found!${NC}"
    echo "Please run this script from the repo root"
    exit 1
fi

if [ ! -f "docker-compose.unreal.yml" ]; then
    echo -e "${RED}Error: docker-compose.unreal.yml not found!${NC}"
    exit 1
fi

echo -e "${YELLOW}Checking environment configuration...${NC}"

if [ ! -f "backend/.env" ] && [ -f "backend/.env.example" ]; then
    echo -e "${YELLOW}Warning: backend/.env file not found, copying from backend/.env.example${NC}"
    cp backend/.env.example backend/.env
fi

if [ ! -f ".env.unreal" ]; then
    echo -e "${RED}Error: .env.unreal file not found!${NC}"
    echo "Copy .env.unreal.example to .env.unreal and update your game paths."
    exit 1
fi

COMMAND=${1:-up}
DETACHED=""
if [ "$2" == "-d" ] || [ "$1" == "-d" ]; then
    DETACHED="-d"
fi

check_health() {
    echo -e "\n${YELLOW}Checking service health...${NC}"
    docker compose -f "$BACKEND_COMPOSE" -f docker-compose.unreal.yml ps
}

show_logs() {
    local SERVICE=$1
    if [ -z "$SERVICE" ]; then
        docker compose -f "$BACKEND_COMPOSE" -f docker-compose.unreal.yml logs --tail=50
    else
        docker compose -f "$BACKEND_COMPOSE" -f docker-compose.unreal.yml logs --tail=50 "$SERVICE"
    fi
}

case "$COMMAND" in
    up|start)
        echo -e "${GREEN}Starting VTuber with Unreal Engine...${NC}"

        docker network create vtuber_network 2>/dev/null || true

        set -a
        source .env
        source .env.unreal
        set +a

        docker compose -f "$BACKEND_COMPOSE" -f docker-compose.unreal.yml up $DETACHED

        if [ "$DETACHED" == "-d" ]; then
            echo -e "\n${GREEN}Services started in background!${NC}"
            sleep 5
            check_health

            echo -e "\n${GREEN}Access points:${NC}"
            echo -e "  Pixel Streaming UI: ${YELLOW}http://localhost:8080${NC}"
            echo -e "  Unreal TCP (in-container): ${YELLOW}vtuber-unreal-game:7777${NC}"
            echo -e "  Sample TTS trigger:${YELLOW} $0 test${NC}"
            echo -e "\n${GREEN}View logs with:${NC} $0 logs [service-name]"
        fi
        ;;

    down|stop)
        echo -e "${YELLOW}Stopping VTuber and Unreal Engine...${NC}"
        docker compose -f "$BACKEND_COMPOSE" -f docker-compose.unreal.yml down
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
        docker compose -f "$BACKEND_COMPOSE" -f docker-compose.unreal.yml build
        echo -e "${GREEN}Build complete!${NC}"
        ;;

    test)
        echo -e "${YELLOW}Sending sample BYOB TTS command...${NC}"
        docker exec vtuber-unreal-game bash -lc 'printf "TTS_BYOB_/opt/embody/sample-15s.mp3\r\n" | nc -q 1 127.0.0.1 7777' \
          && echo -e "${GREEN}Sample command sent. Listen for playback in the stream.${NC}" \
          || echo -e "${RED}Failed to reach Unreal TCP endpoint${NC}"
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
        echo "  test          Send sample BYOB TTS command"
        echo "  help          Show this help message"
        echo ""
        echo "Options:"
        echo "  -d            Run in detached mode (background)"
        echo ""
        echo "Examples:"
        echo "  $0 start -d              # Start in background"
        echo "  $0 logs unreal-game      # Show game logs"
        echo "  $0 test                  # Trigger sample BYOB playback"
        ;;

    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;

esac
