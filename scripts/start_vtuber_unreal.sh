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
INSTANCE_ID=""
PORT_OFFSET=""
VTUBER_CONTAINER_PREFIX=""
VTUBER_NETWORK_NAME=""
TURN_ENV_FILE=""
SIGNALING_HTTP_HOST_PORT=""
SIGNALING_STREAMER_HOST_PORT=""
RECORDER_CTRL_HOST_PORT=""
ORCHESTRATOR_HEALTH_HOST_PORT=""
VTUBER_GAME_TCP_HOST_PORT=""
VTUBER_RUNNER_HOST_PORT=""
TURN_PORT=""
TURN_MIN_PORT=""
TURN_MAX_PORT=""
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
    echo "  --instance <id>           Run a separate stack instance (isolated containers + docker network)"
    echo "  --port-offset <n>         Offset host ports to avoid collisions (default derived from --instance)"
    echo ""
    echo "Examples:"
    echo "  $0 start -d                # Start in background"
    echo "  $0 start --gpu 0 -d         # Start using GPU 0"
    echo "  $0 start --instance 2 -d    # Start a second instance (auto port offsets)"
    echo "  $0 logs unreal-game         # Show game logs"
    echo "  $0 test                     # Trigger sample BYOB playback"
}

while [ $# -gt 0 ]; do
    case "$1" in
        -d|--detach)
            DETACHED="-d"
            shift
            ;;
        --instance)
            if [ -z "${2:-}" ]; then
                echo -e "${RED}Error: --instance requires a value (e.g. --instance 2).${NC}"
                exit 1
            fi
            INSTANCE_ID="$2"
            shift 2
            ;;
        --instance=*)
            INSTANCE_ID="${1#*=}"
            if [ -z "$INSTANCE_ID" ]; then
                echo -e "${RED}Error: --instance requires a value (e.g. --instance=2).${NC}"
                exit 1
            fi
            shift
            ;;
        --port-offset)
            if [ -z "${2:-}" ]; then
                echo -e "${RED}Error: --port-offset requires a numeric value (e.g. --port-offset 100).${NC}"
                exit 1
            fi
            PORT_OFFSET="$2"
            shift 2
            ;;
        --port-offset=*)
            PORT_OFFSET="${1#*=}"
            if [ -z "$PORT_OFFSET" ]; then
                echo -e "${RED}Error: --port-offset requires a numeric value (e.g. --port-offset=100).${NC}"
                exit 1
            fi
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

normalize_instance() {
    if [ -z "$INSTANCE_ID" ] || [ "$INSTANCE_ID" = "1" ]; then
        INSTANCE_ID=""
        return
    fi
    if ! echo "$INSTANCE_ID" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._-]*$'; then
        echo -e "${RED}Error: --instance must be alphanumeric (allowed: . _ -). Got: ${INSTANCE_ID}${NC}"
        exit 1
    fi
}

normalize_offset() {
    if [ -n "$PORT_OFFSET" ] && ! echo "$PORT_OFFSET" | grep -Eq '^[0-9]+$'; then
        echo -e "${RED}Error: --port-offset must be a non-negative integer. Got: ${PORT_OFFSET}${NC}"
        exit 1
    fi

    if [ -z "$PORT_OFFSET" ]; then
        if echo "${INSTANCE_ID:-}" | grep -Eq '^[0-9]+$'; then
            # Instance 2 -> +100, instance 3 -> +200, ...
            if [ "${INSTANCE_ID}" -ge 2 ]; then
                PORT_OFFSET=$(( (INSTANCE_ID - 1) * 100 ))
            else
                PORT_OFFSET=0
            fi
        elif [ -n "$INSTANCE_ID" ]; then
            PORT_OFFSET=100
        else
            PORT_OFFSET=0
        fi
    fi
}

derive_instance_env() {
    if [ -n "$INSTANCE_ID" ]; then
        VTUBER_CONTAINER_PREFIX="vtuber-${INSTANCE_ID}"
        VTUBER_NETWORK_NAME="vtuber_network_${INSTANCE_ID}"
        TURN_ENV_FILE=".env.turn.${INSTANCE_ID}"
    else
        VTUBER_CONTAINER_PREFIX=""
        VTUBER_NETWORK_NAME=""
        TURN_ENV_FILE=".env.turn"
    fi

    SIGNALING_HTTP_HOST_PORT=$((8080 + PORT_OFFSET))
    SIGNALING_STREAMER_HOST_PORT=$((8888 + PORT_OFFSET))
    RECORDER_CTRL_HOST_PORT=$((8889 + PORT_OFFSET))
    ORCHESTRATOR_HEALTH_HOST_PORT=$((9090 + PORT_OFFSET))
    VTUBER_GAME_TCP_HOST_PORT=$((7777 + PORT_OFFSET))
    VTUBER_RUNNER_HOST_PORT=$((9877 + PORT_OFFSET))
    TURN_PORT=$((3478 + PORT_OFFSET))

    # TURN uses a port range; shift it farther to avoid collisions when PORT_OFFSET is small.
    local turn_range_offset
    turn_range_offset=$((PORT_OFFSET * 10))
    TURN_MIN_PORT=$((49160 + turn_range_offset))
    TURN_MAX_PORT=$((49200 + turn_range_offset))

    if [ "$TURN_MAX_PORT" -gt 65535 ] || [ "$TURN_PORT" -gt 65535 ]; then
        echo -e "${RED}Error: derived TURN ports exceed 65535 (TURN_PORT=${TURN_PORT}, TURN_MAX_PORT=${TURN_MAX_PORT}). Use a smaller --port-offset.${NC}"
        exit 1
    fi
}

normalize_instance
normalize_offset
derive_instance_env

compose() {
    local env_prefix=()

    env_prefix+=(TURN_ENV_FILE="$TURN_ENV_FILE")
    env_prefix+=(SIGNALING_HTTP_HOST_PORT="$SIGNALING_HTTP_HOST_PORT")
    env_prefix+=(SIGNALING_STREAMER_HOST_PORT="$SIGNALING_STREAMER_HOST_PORT")
    env_prefix+=(RECORDER_CTRL_HOST_PORT="$RECORDER_CTRL_HOST_PORT")
    env_prefix+=(ORCHESTRATOR_HEALTH_HOST_PORT="$ORCHESTRATOR_HEALTH_HOST_PORT")
    env_prefix+=(VTUBER_GAME_TCP_HOST_PORT="$VTUBER_GAME_TCP_HOST_PORT")
    env_prefix+=(VTUBER_RUNNER_HOST_PORT="$VTUBER_RUNNER_HOST_PORT")
    env_prefix+=(TURN_PORT="$TURN_PORT")
    env_prefix+=(TURN_MIN_PORT="$TURN_MIN_PORT")
    env_prefix+=(TURN_MAX_PORT="$TURN_MAX_PORT")

    if [ -n "$VTUBER_CONTAINER_PREFIX" ]; then
        env_prefix+=(VTUBER_CONTAINER_PREFIX="$VTUBER_CONTAINER_PREFIX")
    fi
    if [ -n "$VTUBER_NETWORK_NAME" ]; then
        env_prefix+=(VTUBER_NETWORK_NAME="$VTUBER_NETWORK_NAME")
        env_prefix+=(COMPOSE_PROJECT_NAME="unreal_vtuber_${INSTANCE_ID}")
    fi
    if [ -n "$GPU_SELECTION" ]; then
        env_prefix+=(NVIDIA_VISIBLE_DEVICES="$GPU_SELECTION")
    fi

    env "${env_prefix[@]}" docker compose -f docker-compose.unreal.yml "$@"
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

        docker network create "${VTUBER_NETWORK_NAME:-vtuber_network}" 2>/dev/null || true

        if [ ! -s "$TURN_ENV_FILE" ]; then
            echo -e "${YELLOW}TURN credentials missing; generating ${TURN_ENV_FILE}...${NC}"
            TURN_ENV_FILE="$TURN_ENV_FILE" \
              TURN_PORT="$TURN_PORT" \
              TURN_MIN_PORT="$TURN_MIN_PORT" \
              TURN_MAX_PORT="$TURN_MAX_PORT" \
              ./scripts/generate_turn_credentials.sh --output "$TURN_ENV_FILE"
        fi

        if [ -n "$GPU_SELECTION" ]; then
            echo -e "${YELLOW}Using NVIDIA_VISIBLE_DEVICES=${GPU_SELECTION}${NC}"
        fi
        if [ -n "$INSTANCE_ID" ]; then
            echo -e "${YELLOW}Instance: ${INSTANCE_ID} (project=unreal_vtuber_${INSTANCE_ID}, prefix=${VTUBER_CONTAINER_PREFIX}, ports=+${PORT_OFFSET})${NC}"
        fi

        compose up $DETACHED

        if [ "$DETACHED" == "-d" ]; then
            echo -e "\n${GREEN}Services started in background!${NC}"
            sleep 5
            check_health

            echo -e "\n${GREEN}Access points:${NC}"
            echo -e "  Signaling health: ${YELLOW}http://localhost:${SIGNALING_HTTP_HOST_PORT}/healthz${NC}"
            echo -e "  Runner health: ${YELLOW}http://localhost:${VTUBER_RUNNER_HOST_PORT}/health${NC}"
            echo -e "  Orchestrator health: ${YELLOW}http://localhost:${ORCHESTRATOR_HEALTH_HOST_PORT}/health${NC}"
            echo -e "  Unreal TCP (in-container): ${YELLOW}${VTUBER_CONTAINER_PREFIX:-vtuber}-unreal-game:7777${NC}"
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
        if [ -n "$INSTANCE_ID" ]; then
            echo -e "${YELLOW}Instance: ${INSTANCE_ID} (project=unreal_vtuber_${INSTANCE_ID}, prefix=${VTUBER_CONTAINER_PREFIX}, ports=+${PORT_OFFSET})${NC}"
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
        docker exec "${VTUBER_CONTAINER_PREFIX:-vtuber}-unreal-game" bash -lc 'printf "TTS_BYOB_/opt/embody/sample-15s.mp3\r\n" | nc -q 1 127.0.0.1 7777' \
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
