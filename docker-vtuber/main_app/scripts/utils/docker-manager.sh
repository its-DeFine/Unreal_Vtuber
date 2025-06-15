#!/bin/bash

# Docker Container Management Script
# Provides options to build, run, and test Docker containers

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BRIDGE_COMPOSE="docker-compose.bridge.yml"
BYOC_COMPOSE="docker-compose.byoc.yml"
AUTONOMOUS_COMPOSE="autonomous-starter/docker-compose.yml"
OLLAMA_COMPOSE="config/docker-compose.ollama.yml"
RTMP_COMPOSE="files_docker_rtmp/docker-compose.yml"
LOG_DIR="logs"
ENDPOINT_URL="http://localhost:5001/process_text"

# Function to detect GPU availability
detect_gpu() {
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
        return 0  # GPU available
    else
        return 1  # No GPU
    fi
}

# Function to create network if it doesn't exist
ensure_network() {
    local network_name="docker-vt_scb_bridge_net"
    if ! docker network ls | grep -q "$network_name"; then
        info "Creating network: $network_name"
        docker network create "$network_name"
    fi
}

# Auto-detect available compose files
detect_compose_files() {
    local available_files=()
    local available_descriptions=()
    
    if [ -f "$BRIDGE_COMPOSE" ]; then
        available_files+=("$BRIDGE_COMPOSE")
        available_descriptions+=("Bridge Services (neurosync, nginx-rtmp, redis)")
    fi
    
    if [ -f "$BYOC_COMPOSE" ]; then
        available_files+=("$BYOC_COMPOSE")
        available_descriptions+=("BYOC Services")
    fi
    
    if [ -f "$AUTONOMOUS_COMPOSE" ]; then
        available_files+=("$AUTONOMOUS_COMPOSE")
        available_descriptions+=("Autonomous Agent System (postgres, autonomous-agent)")
    fi
    
    if [ -f "$OLLAMA_COMPOSE" ]; then
        available_files+=("$OLLAMA_COMPOSE")
        available_descriptions+=("Ollama AI Service (GPU/CPU profiles)")
    fi
    
    if [ -f "$RTMP_COMPOSE" ]; then
        available_files+=("$RTMP_COMPOSE")
        available_descriptions+=("RTMP Streaming Service (nginx-rtmp)")
    fi
    
    if [ ${#available_files[@]} -eq 0 ]; then
        error "No Docker Compose files found!"
        error "Expected files: $BRIDGE_COMPOSE, $BYOC_COMPOSE, or $AUTONOMOUS_COMPOSE"
        exit 1
    fi
    
    echo "Available compose configurations:"
    for i in "${!available_files[@]}"; do
        info "$((i+1)). ${available_files[$i]} - ${available_descriptions[$i]}"
    done
    echo
}

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to show usage
show_help() {
    cat << EOF
Docker Container Management Script

Usage: $0 [OPTION]

OPTIONS:
    -h, --help              Show this help message
    -b, --build             Build containers only
    -r, --run               Run containers without building
    -br, --build-run        Build and run containers
    -s, --stop              Stop all containers
    -d, --down              Stop and remove containers
    -t, --test              Test the endpoint with curl
    -l, --logs              Show container logs
    -st, --status           Show container status
    --clean                 Clean up containers, images, and volumes
    --bridge-only           Use only bridge compose file
    --full-stack            Use both bridge and byoc compose files
    --autonomous            Use autonomous agent compose file
    --ollama-gpu            Use Ollama service with GPU support
    --ollama-cpu            Use Ollama service with CPU only
    --autonomous-full       Use autonomous agent + Ollama (auto-detect GPU/CPU)
    --rtmp                  Use RTMP streaming service

EXAMPLES:
    $0 --build              # Build containers
    $0 --build-run          # Build and run containers
    $0 --run --bridge-only  # Run only bridge services
    $0 --test               # Test the endpoint
    $0 --logs               # Show logs
    $0 --clean              # Clean up everything

SERVICES:
    Bridge services: neurosync, nginx-rtmp, redis
    Full stack: All services from both compose files
    Autonomous: postgres, autonomous-agent
    Ollama: ollama (GPU) or ollama-cpu (CPU only)
    Autonomous-full: autonomous + ollama with dependency management
    RTMP: nginx-rtmp streaming service
EOF
}

# Function to build containers
build_containers() {
    local compose_files="$1"
    local log_file="$LOG_DIR/build_$(date +%Y%m%d_%H%M%S).log"
    
    log "Building containers..."
    info "Compose files: $compose_files"
    info "Log file: $log_file"
    
    if docker compose $compose_files build --progress=plain > "$log_file" 2>&1; then
        log "Build completed successfully"
        info "Build logs saved to: $log_file"
    else
        error "Build failed! Check logs: $log_file"
        exit 1
    fi
}

# Function to run containers
run_containers() {
    local compose_files="$1"
    local services="$2"
    
    log "Starting containers..."
    info "Compose files: $compose_files"
    info "Services: ${services:-all services}"
    
    # Special handling for autonomous-full to run in correct order
    if [ "$AUTONOMOUS_FULL" = true ]; then
        log "Starting autonomous stack in correct order..."
        
        # First, start Ollama
        info "Starting Ollama service..."
        if detect_gpu; then
            docker compose -f "$OLLAMA_COMPOSE" --profile gpu up -d
        else
            docker compose -f "$OLLAMA_COMPOSE" --profile cpu up -d
        fi
        
        # Wait for Ollama to be ready
        info "Waiting for Ollama to be ready..."
        sleep 5
        
        # Then start autonomous agent from its directory
        info "Starting autonomous agent..."
        cd autonomous-starter
        docker compose up -d
        cd ..
        
        log "Autonomous full stack started successfully"
    else
        if [ -n "$services" ]; then
            docker compose $compose_files up -d $services
        else
            docker compose $compose_files up -d
        fi
        
        log "Containers started successfully"
    fi
}

# Function to build and run containers
build_and_run() {
    local compose_files="$1"
    local services="$2"
    
    log "Building and running containers..."
    info "Compose files: $compose_files"
    info "Services: ${services:-all services}"
    
    # Special handling for autonomous-full to build in correct order
    if [ "$AUTONOMOUS_FULL" = true ]; then
        log "Building autonomous stack in correct order..."
        
        # First, start Ollama
        info "Starting Ollama service..."
        if detect_gpu; then
            docker compose -f "$OLLAMA_COMPOSE" --profile gpu up -d
        else
            docker compose -f "$OLLAMA_COMPOSE" --profile cpu up -d
        fi
        
        # Wait for Ollama to be ready
        info "Waiting for Ollama to be ready..."
        sleep 5
        
        # Then build and start autonomous agent from its directory
        info "Building and starting autonomous agent..."
        cd autonomous-starter
        docker compose up --build -d
        cd ..
        
        log "Autonomous full stack started successfully"
    else
        if [ -n "$services" ]; then
            docker compose $compose_files up --build -d $services
        else
            docker compose $compose_files up --build -d
        fi
        
        log "Containers built and started successfully"
    fi
}

# Function to stop containers
stop_containers() {
    local compose_files="$1"
    
    log "Stopping containers..."
    docker compose $compose_files stop
    log "Containers stopped"
}

# Function to stop and remove containers
down_containers() {
    local compose_files="$1"
    
    log "Stopping and removing containers..."
    docker compose $compose_files down
    log "Containers stopped and removed"
}

# Function to test endpoint
test_endpoint() {
    local max_retries=5
    local retry_count=0
    
    # Determine endpoint based on configuration
    local test_url="$ENDPOINT_URL"
    if [ "$AUTONOMOUS_ONLY" = true ] || [ "$AUTONOMOUS_FULL" = true ]; then
        test_url="http://localhost:3001/"
        info "Testing autonomous agent web interface"
    elif [ "$OLLAMA_GPU" = true ] || [ "$OLLAMA_CPU" = true ]; then
        test_url="http://localhost:11434/api/tags"
        info "Testing Ollama API endpoint"
    elif [ "$RTMP_ONLY" = true ]; then
        test_url="http://localhost:8080/"
        info "Testing RTMP monitor page"
    fi
    
    log "Testing endpoint: $test_url"
    
    while [ $retry_count -lt $max_retries ]; do
        if [ "$AUTONOMOUS_ONLY" = true ] || [ "$AUTONOMOUS_FULL" = true ]; then
            # Test autonomous agent web interface
            if curl -s "$test_url" > /dev/null 2>&1; then
                log "Autonomous agent web interface test successful!"
                info "Web interface is accessible at: $test_url"
                return 0
            fi
        elif [ "$OLLAMA_GPU" = true ] || [ "$OLLAMA_CPU" = true ]; then
            # Test Ollama API
            if curl -s "$test_url" > /dev/null 2>&1; then
                log "Ollama API test successful!"
                info "API endpoint response:"
                curl -s "$test_url" 2>/dev/null | jq . || echo "Response received (not JSON)"
                return 0
            fi
        elif [ "$RTMP_ONLY" = true ]; then
            # Test RTMP monitor page
            if curl -s "$test_url" > /dev/null 2>&1; then
                log "RTMP monitor page test successful!"
                info "Monitor page is accessible at: $test_url"
                return 0
            fi
        else
            # Test VTuber processing endpoint
            if curl -s -X POST \
               -H "Content-Type: application/json" \
               -d '{"text":"Hello from docker-manager script"}' \
               "$test_url" > /dev/null 2>&1; then
                log "VTuber endpoint test successful!"
                
                # Show actual response
                info "Response:"
                curl -X POST \
                     -H "Content-Type: application/json" \
                     -d '{"text":"Hello from docker-manager script"}' \
                     "$test_url" 2>/dev/null | jq . || echo "Response received (not JSON)"
                return 0
            fi
        fi
        
        retry_count=$((retry_count + 1))
        warning "Attempt $retry_count failed. Retrying in 3 seconds..."
        sleep 3
    done
    
    error "Endpoint test failed after $max_retries attempts"
    error "Make sure containers are running and the service is ready"
    return 1
}

# Function to show logs
show_logs() {
    local compose_files="$1"
    
    log "Showing container logs..."
    docker compose $compose_files logs --tail=50 -f
}

# Function to show container status
show_status() {
    local compose_files="$1"
    
    log "Container status:"
    docker compose $compose_files ps
    
    echo
    info "System resources:"
    docker system df
}

# Function to clean up
cleanup() {
    local compose_files="$1"
    
    warning "This will remove all containers, images, and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Cleaning up..."
        docker compose $compose_files down -v --rmi all
        docker system prune -f
        log "Cleanup completed"
    else
        info "Cleanup cancelled"
    fi
}

# Parse command line arguments
BRIDGE_ONLY=false
FULL_STACK=false
AUTONOMOUS_ONLY=false
OLLAMA_GPU=false
OLLAMA_CPU=false
AUTONOMOUS_FULL=false
RTMP_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -b|--build)
            ACTION="build"
            shift
            ;;
        -r|--run)
            ACTION="run"
            shift
            ;;
        -br|--build-run)
            ACTION="build_run"
            shift
            ;;
        -s|--stop)
            ACTION="stop"
            shift
            ;;
        -d|--down)
            ACTION="down"
            shift
            ;;
        -t|--test)
            ACTION="test"
            shift
            ;;
        -l|--logs)
            ACTION="logs"
            shift
            ;;
        -st|--status)
            ACTION="status"
            shift
            ;;
        --clean)
            ACTION="clean"
            shift
            ;;
        --bridge-only)
            BRIDGE_ONLY=true
            shift
            ;;
        --full-stack)
            FULL_STACK=true
            shift
            ;;
        --autonomous)
            AUTONOMOUS_ONLY=true
            shift
            ;;
        --ollama-gpu)
            OLLAMA_GPU=true
            shift
            ;;
        --ollama-cpu)
            OLLAMA_CPU=true
            shift
            ;;
        --autonomous-full)
            AUTONOMOUS_FULL=true
            shift
            ;;
        --rtmp)
            RTMP_ONLY=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Show available compose files first
detect_compose_files

# Determine compose files to use
if [ "$BRIDGE_ONLY" = true ]; then
    if [ ! -f "$BRIDGE_COMPOSE" ]; then
        error "Bridge compose file not found: $BRIDGE_COMPOSE"
        exit 1
    fi
    COMPOSE_FILES="-f $BRIDGE_COMPOSE"
    SERVICES="neurosync nginx-rtmp redis"
    info "Using bridge-only configuration"
elif [ "$FULL_STACK" = true ]; then
    if [ ! -f "$BRIDGE_COMPOSE" ] || [ ! -f "$BYOC_COMPOSE" ]; then
        error "Full stack requires both: $BRIDGE_COMPOSE and $BYOC_COMPOSE"
        exit 1
    fi
    COMPOSE_FILES="-f $BRIDGE_COMPOSE -f $BYOC_COMPOSE"
    SERVICES=""
    info "Using full-stack configuration"
elif [ "$AUTONOMOUS_ONLY" = true ]; then
    if [ ! -f "$AUTONOMOUS_COMPOSE" ]; then
        error "Autonomous compose file not found: $AUTONOMOUS_COMPOSE"
        exit 1
    fi
    COMPOSE_FILES="-f $AUTONOMOUS_COMPOSE"
    SERVICES=""
    info "Using autonomous agent configuration"
elif [ "$OLLAMA_GPU" = true ]; then
    if [ ! -f "$OLLAMA_COMPOSE" ]; then
        error "Ollama compose file not found: $OLLAMA_COMPOSE"
        exit 1
    fi
    ensure_network
    COMPOSE_FILES="-f $OLLAMA_COMPOSE --profile gpu"
    SERVICES=""
    info "Using Ollama with GPU support"
elif [ "$OLLAMA_CPU" = true ]; then
    if [ ! -f "$OLLAMA_COMPOSE" ]; then
        error "Ollama compose file not found: $OLLAMA_COMPOSE"
        exit 1
    fi
    ensure_network
    COMPOSE_FILES="-f $OLLAMA_COMPOSE --profile cpu"
    SERVICES=""
    info "Using Ollama with CPU only"
elif [ "$AUTONOMOUS_FULL" = true ]; then
    if [ ! -f "$AUTONOMOUS_COMPOSE" ] || [ ! -f "$OLLAMA_COMPOSE" ]; then
        error "Autonomous full requires both: $AUTONOMOUS_COMPOSE and $OLLAMA_COMPOSE"
        exit 1
    fi
    ensure_network
    
    # Auto-detect GPU for Ollama profile
    if detect_gpu; then
        info "GPU detected, using Ollama with GPU support"
        COMPOSE_FILES="-f $OLLAMA_COMPOSE --profile gpu -f $AUTONOMOUS_COMPOSE"
    else
        info "No GPU detected, using Ollama with CPU only"
        COMPOSE_FILES="-f $OLLAMA_COMPOSE --profile cpu -f $AUTONOMOUS_COMPOSE"
    fi
    SERVICES=""
    info "Using autonomous agent with Ollama (full stack)"
elif [ "$RTMP_ONLY" = true ]; then
    if [ ! -f "$RTMP_COMPOSE" ]; then
        error "RTMP compose file not found: $RTMP_COMPOSE"
        exit 1
    fi
    COMPOSE_FILES="-f $RTMP_COMPOSE"
    SERVICES=""
    info "Using RTMP streaming service"
else
    # Default to first available compose file
    if [ -f "$AUTONOMOUS_COMPOSE" ]; then
        COMPOSE_FILES="-f $AUTONOMOUS_COMPOSE"
        SERVICES=""
        info "Using default autonomous agent configuration"
    elif [ -f "$BRIDGE_COMPOSE" ]; then
        COMPOSE_FILES="-f $BRIDGE_COMPOSE"
        SERVICES="neurosync nginx-rtmp redis"
        info "Using default bridge configuration"
    else
        error "No compose files available for default configuration"
        exit 1
    fi
fi

# Execute the requested action
case $ACTION in
    build)
        build_containers "$COMPOSE_FILES"
        ;;
    run)
        run_containers "$COMPOSE_FILES" "$SERVICES"
        ;;
    build_run)
        build_and_run "$COMPOSE_FILES" "$SERVICES"
        ;;
    stop)
        stop_containers "$COMPOSE_FILES"
        ;;
    down)
        down_containers "$COMPOSE_FILES"
        ;;
    test)
        test_endpoint
        ;;
    logs)
        show_logs "$COMPOSE_FILES"
        ;;
    status)
        show_status "$COMPOSE_FILES"
        ;;
    clean)
        cleanup "$COMPOSE_FILES"
        ;;
    *)
        error "No action specified"
        show_help
        exit 1
        ;;
esac 