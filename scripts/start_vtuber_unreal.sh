#!/bin/bash
# Start VTuber with Unreal Engine Pixel Streaming
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.unreal.yml"
ENV_FILE="${REPO_ROOT}/.env"
TURN_ENV_FILE="${REPO_ROOT}/.env.turn"

cd "${REPO_ROOT}"

echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}     VTuber + Unreal Engine Pixel Streaming Launcher${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""

if [ ! -f "${COMPOSE_FILE}" ]; then
    echo -e "${RED}Error: docker-compose.unreal.yml not found!${NC}"
    echo "Expected at: ${COMPOSE_FILE}"
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
    echo "  $0 start                   # Start in background"
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

if [ "$COMMAND" = "start" ] && [ -z "$DETACHED" ]; then
    DETACHED="-d"
fi

compose() {
    if [ -n "$GPU_SELECTION" ]; then
        NVIDIA_VISIBLE_DEVICES="$GPU_SELECTION" docker compose -f "${COMPOSE_FILE}" "$@"
    else
        docker compose -f "${COMPOSE_FILE}" "$@"
    fi
}

ensure_env() {
    if [ ! -f "${ENV_FILE}" ]; then
        echo -e "${RED}Error: .env file not found!${NC}"
        echo "Copy orchestrator.env.example to .env and update your settings."
        exit 1
    fi
}

trim_whitespace() {
    local s="$1"
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    printf '%s' "$s"
}

strip_wrapping_quotes() {
    local s="$1"
    if [[ "$s" == \"*\" && "$s" == *\" ]]; then
        s="${s#\"}"
        s="${s%\"}"
    fi
    if [[ "$s" == \'*\' && "$s" == *\' ]]; then
        s="${s#\'}"
        s="${s%\'}"
    fi
    printf '%s' "$s"
}

read_env_value() {
    local key="$1"
    local line value
    line="$(grep -E "^[[:space:]]*${key}=" "$ENV_FILE" 2>/dev/null | tail -n 1 || true)"
    if [ -z "$line" ]; then
        printf ''
        return 0
    fi
    value="${line#*=}"
    value="${value%%#*}"
    value="$(trim_whitespace "$value")"
    value="$(strip_wrapping_quotes "$value")"
    printf '%s' "$value"
}

extract_host_from_url() {
    local url="$1"
    url="${url#*://}"
    url="${url%%/*}"
    url="${url##*@}"
    url="${url%%:*}"
    printf '%s' "$url"
}

is_ipv4() {
    local ip="$1"
    [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

csv_has_token() {
    local csv="$1"
    local token="$2"
    csv="${csv//[[:space:]]/}"
    case ",${csv}," in
        *",${token},"*) return 0 ;;
        *) return 1 ;;
    esac
}

check_payments_allowlist() {
    local payments_url payments_host payments_ip want_cidr allow_file power_allow
    payments_url="$(read_env_value "PAYMENTS_API_URL")"
    if [ -z "$payments_url" ]; then
        payments_url="http://3.141.111.200:8081"
    fi
    payments_host="$(extract_host_from_url "$payments_url")"
    if ! is_ipv4 "$payments_host"; then
        echo -e "${YELLOW}WARN: cannot parse IPv4 from PAYMENTS_API_URL (${payments_url}); skipping allowlist test.${NC}"
        return 2
    fi
    payments_ip="$payments_host"
    want_cidr="${payments_ip}/32"

    allow_file="$(read_env_value "EDGE_POWER_ALLOWED_IPS_FILE")"
    if [ -z "$allow_file" ]; then
        allow_file="/var/lib/vtuber/power-state/power_allowed_ips.txt"
    fi

    if [ -f "$allow_file" ]; then
        if grep -qF "$want_cidr" "$allow_file" 2>/dev/null || grep -qF "$payments_ip" "$allow_file" 2>/dev/null; then
            echo -e "${GREEN}Payments allowlist: OK (${payments_ip})${NC}"
            return 0
        fi
        echo -e "${YELLOW}Payments allowlist: WARN (missing ${want_cidr} in ${allow_file})${NC}"
        echo -e "${YELLOW}Fix: ./scripts/embody_cli.sh allowlists fix${NC}"
        return 1
    fi

    power_allow="$(read_env_value "POWER_ALLOWED_IPS")"
    power_allow="$(trim_whitespace "${power_allow:-}")"
    if [ -z "$power_allow" ]; then
        echo -e "${YELLOW}Payments allowlist: WARN (missing allowlist file ${allow_file} and POWER_ALLOWED_IPS is unset)${NC}"
        echo -e "${YELLOW}Fix: ./scripts/embody_cli.sh allowlists fix${NC}"
        return 1
    fi
    if csv_has_token "$power_allow" "$want_cidr" || csv_has_token "$power_allow" "$payments_ip"; then
        echo -e "${GREEN}Payments allowlist: OK (${payments_ip})${NC}"
        return 0
    fi
    echo -e "${YELLOW}Payments allowlist: WARN (missing ${want_cidr} in POWER_ALLOWED_IPS)${NC}"
    echo -e "${YELLOW}Fix: ./scripts/embody_cli.sh allowlists fix${NC}"
    return 1
}

detect_game_image_from_compose() {
    awk '
        /^[[:space:]]*unreal-game:[[:space:]]*$/ { in_game=1; next }
        in_game && /^[[:space:]]*image:[[:space:]]*/ {
            sub(/^[[:space:]]*image:[[:space:]]*/, "", $0)
            gsub(/[[:space:]]+$/, "", $0)
            print $0
            exit
        }
        in_game && /^[^[:space:]]/ { in_game=0 }
    ' "$1"
}

ensure_game_image() {
    local GAME_IMAGE=""
    GAME_IMAGE="$(detect_game_image_from_compose "${COMPOSE_FILE}" 2>/dev/null || true)"
    if [ -z "$GAME_IMAGE" ]; then
        echo -e "${YELLOW}Warning: could not detect unreal-game image from compose; skipping preflight.${NC}"
        return 0
    fi
    if ! docker image inspect "$GAME_IMAGE" >/dev/null 2>&1; then
        echo -e "${RED}Error: game image not present locally: ${GAME_IMAGE}${NC}"
        echo -e "${YELLOW}Next step: run ./scripts/embody_cli.sh rollout (Payments lease → download/decrypt/load).${NC}"
        echo -e "${YELLOW}Docs: docs/admin-encrypted-game-image.md${NC}"
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

        if [ ! -s "${TURN_ENV_FILE}" ]; then
            echo -e "${YELLOW}TURN credentials missing; generating .env.turn...${NC}"
            ./scripts/generate_turn_credentials.sh
        fi

        ensure_game_image

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

        ensure_game_image

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
          orchestrator-edge-rotator orchestrator-health vtuber-watchdog vtuber-auto-updater \
          orchestrator-registration
        echo -e "${GREEN}Pull complete!${NC}"
        ;;

    build)
        ensure_env
        echo -e "${YELLOW}No local builds are required; pulling images instead...${NC}"
        compose pull \
          turn-server unreal-signaling \
          vtuber-script-runner recorder-control \
          orchestrator-edge-rotator orchestrator-health vtuber-watchdog vtuber-auto-updater \
          orchestrator-registration
        echo -e "${GREEN}Pull complete!${NC}"
        ;;

    test)
        ensure_env
        allowlist_rc="0"
        check_payments_allowlist || allowlist_rc="$?"

        echo -e "${YELLOW}Sending sample BYOB TTS command...${NC}"
        if docker exec vtuber-unreal-game bash -lc 'printf "TTS_BYOB_/opt/embody/sample-15s.mp3\r\n" | nc -q 1 127.0.0.1 7777'; then
            echo -e "${GREEN}Sample command sent. Listen for playback in the stream.${NC}"
            tts_rc="0"
        else
            echo -e "${RED}Failed to reach Unreal TCP endpoint${NC}"
            tts_rc="1"
        fi

        if [ "$tts_rc" != "0" ] || [ "$allowlist_rc" = "1" ]; then
            exit 1
        fi
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
