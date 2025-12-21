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

if [ ! -f "docker-compose.unreal.yml" ]; then
    echo -e "${RED}Error: docker-compose.unreal.yml not found!${NC}"
    exit 1
fi

COMMAND="up"
DETACHED=""
GPU_SELECTION=""
LOG_SERVICE=""

print_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS] [ARGS]"
    echo ""
    echo "Commands:"
    echo "  up, start     Start all services"
    echo "  down, stop    Stop all services"
    echo "  restart       Restart all services"
    echo "  logs [name]   Show logs (optionally for specific service)"
    echo "  ps, status    Show service status"
    echo "  pull          Pull Docker images"
    echo "  build         (alias for pull)"
    echo "  test          Send sample BYOB TTS command"
    echo "  help          Show this help message"
    echo ""
    echo "Options:"
    echo "  -d, --detach              Run in detached mode (background)"
    echo "  --gpu <id|all|none>       Select which NVIDIA GPU to expose (sets NVIDIA_VISIBLE_DEVICES)"
    echo ""
    echo "Examples:"
    echo "  $0 start -d                # Start in background"
    echo "  $0 start --gpu 0 -d         # Start using GPU 0"
    echo "  $0 logs unreal-game         # Show game logs"
    echo "  $0 test                     # Trigger sample BYOB playback"
}

while [ $# -gt 0 ]; do
    case "$1" in
        -d|--detach)
            DETACHED="-d"
            shift
            ;;
        --gpu)
            if [ -z "${2:-}" ]; then
                echo -e "${RED}Error: --gpu requires a value (e.g. --gpu 0, --gpu all).${NC}"
                exit 1
            fi
            GPU_SELECTION="$2"
            shift 2
            ;;
        --gpu=*)
            GPU_SELECTION="${1#*=}"
            if [ -z "$GPU_SELECTION" ]; then
                echo -e "${RED}Error: --gpu requires a value (e.g. --gpu=0).${NC}"
                exit 1
            fi
            shift
            ;;
        help|--help|-h)
            COMMAND="help"
            shift
            ;;
        up|start|down|stop|restart|logs|ps|status|pull|build|test)
            COMMAND="$1"
            shift
            ;;
        *)
            if [ "$COMMAND" = "logs" ] && [ -z "$LOG_SERVICE" ]; then
                LOG_SERVICE="$1"
                shift
            else
                echo -e "${RED}Unknown argument: $1${NC}"
                echo "Run '$0 help' for usage information"
                exit 1
            fi
            ;;
    esac
done

compose() {
    if [ -n "$GPU_SELECTION" ]; then
        NVIDIA_VISIBLE_DEVICES="$GPU_SELECTION" docker compose -f docker-compose.unreal.yml "$@"
    else
        docker compose -f docker-compose.unreal.yml "$@"
    fi
}

ensure_env() {
    if [ ! -f ".env" ]; then
        echo -e "${RED}Error: .env file not found!${NC}"
        echo "Copy orchestrator.env.example to .env and update your settings."
        exit 1
    fi
}

echo -e "${YELLOW}Checking environment configuration...${NC}"

check_health() {
    echo -e "\n${YELLOW}Checking service health...${NC}"
    compose ps
}

show_logs() {
    local SERVICE=$1
    if [ -z "$SERVICE" ]; then
        compose logs --tail=50
    else
        compose logs --tail=50 "$SERVICE"
    fi
}

case "$COMMAND" in
    up|start)
        ensure_env
        echo -e "${YELLOW}Reminder: start the payments backend from its separate repository if payouts are required.${NC}"

        echo -e "${GREEN}Starting VTuber with Unreal Engine...${NC}"

        docker network create vtuber_network 2>/dev/null || true

        if [ ! -s ".env.turn" ]; then
            echo -e "${YELLOW}TURN credentials missing; generating .env.turn...${NC}"
            ./scripts/generate_turn_credentials.sh
        fi

        if [ -n "$GPU_SELECTION" ]; then
            echo -e "${YELLOW}Using NVIDIA_VISIBLE_DEVICES=${GPU_SELECTION}${NC}"
        fi

        compose up $DETACHED

        if [ "$DETACHED" == "-d" ]; then
            echo -e "\n${GREEN}Services started in background!${NC}"
            sleep 5
            check_health

            echo -e "\n${GREEN}Access points:${NC}"
            echo -e "  Signaling health: ${YELLOW}http://localhost:8080/healthz${NC}"
            echo -e "  Runner health: ${YELLOW}http://localhost:9877/health${NC}"
            echo -e "  Orchestrator health: ${YELLOW}http://localhost:9090/health${NC}"
            echo -e "  Unreal TCP (in-container): ${YELLOW}vtuber-unreal-game:7777${NC}"
            echo -e "  Sample TTS trigger:${YELLOW} $0 test${NC}"
            echo -e "\n${GREEN}View logs with:${NC} $0 logs [service-name]"
        fi
        ;;

    down|stop)
        echo -e "${YELLOW}Stopping VTuber and Unreal Engine...${NC}"
        compose down
        echo -e "${GREEN}Services stopped!${NC}"
        ;;

    restart)
        ensure_env
        echo -e "${YELLOW}Reminder: start the payments backend from its separate repository if payouts are required.${NC}"

        echo -e "${YELLOW}Restarting services...${NC}"
        compose down
        sleep 2
        if [ -n "$GPU_SELECTION" ]; then
            echo -e "${YELLOW}Using NVIDIA_VISIBLE_DEVICES=${GPU_SELECTION}${NC}"
        fi
        compose up $DETACHED
        ;;

    logs)
        show_logs "$LOG_SERVICE"
        ;;

    ps|status)
        check_health
        ;;

    pull)
        ensure_env
        echo -e "${YELLOW}Pulling Docker images...${NC}"
        compose pull \
          turn-server unreal-signaling \
          vtuber-script-runner recorder-control \
          orchestrator-health vtuber-watchdog vtuber-auto-updater \
          orchestrator-registration
        echo -e "${GREEN}Pull complete!${NC}"
        ;;

    build)
        ensure_env
        echo -e "${YELLOW}No local builds are required; pulling images instead...${NC}"
        compose pull \
          turn-server unreal-signaling \
          vtuber-script-runner recorder-control \
          orchestrator-health vtuber-watchdog vtuber-auto-updater \
          orchestrator-registration
        echo -e "${GREEN}Pull complete!${NC}"
        ;;

    test)
        echo -e "${YELLOW}Sending sample BYOB TTS command...${NC}"
        docker exec vtuber-unreal-game bash -lc 'printf "TTS_BYOB_/opt/embody/sample-15s.mp3\r\n" | nc -q 1 127.0.0.1 7777' \
          && echo -e "${GREEN}Sample command sent. Listen for playback in the stream.${NC}" \
          || echo -e "${RED}Failed to reach Unreal TCP endpoint${NC}"
        ;;

    help|--help|-h)
        print_help
        ;;

    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;

esac
