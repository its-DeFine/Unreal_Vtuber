#!/bin/bash

# Force Rebuild Script for Unreal VTuber
# This script forces a complete rebuild of all containers with no cache

set -e

echo "=================================================="
echo "Force Rebuild for Unreal VTuber Containers"
echo "=================================================="
echo ""

# Parse command line arguments
NO_CACHE=true
CLEAN_IMAGES=true
COMPOSE_FILE="docker-compose.byoc.yml"

while [[ $# -gt 0 ]]; do
    case $1 in
        --cache)
            NO_CACHE=false
            shift
            ;;
        --no-clean)
            CLEAN_IMAGES=false
            shift
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --cache       Allow Docker cache (default: no cache)"
            echo "  --no-clean    Don't clean old images (default: clean)"
            echo "  -f, --file    Specify docker-compose file (default: docker-compose.byoc.yml)"
            echo "  -h, --help    Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if docker-compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: Docker compose file '$COMPOSE_FILE' not found!"
    exit 1
fi

echo "Configuration:"
echo "  Compose file: $COMPOSE_FILE"
echo "  No cache: $NO_CACHE"
echo "  Clean images: $CLEAN_IMAGES"
echo ""

# Step 1: Stop existing containers
echo "Step 1: Stopping existing containers..."
docker-compose -f "$COMPOSE_FILE" down

# Step 2: Clean old images if requested
if [ "$CLEAN_IMAGES" = true ]; then
    echo ""
    echo "Step 2: Cleaning old images and volumes..."
    docker-compose -f "$COMPOSE_FILE" down --rmi local -v || true
    
    # Also prune dangling images
    docker image prune -f
else
    echo ""
    echo "Step 2: Skipping image cleanup (--no-clean specified)"
fi

# Step 3: Pull latest base images
echo ""
echo "Step 3: Pulling latest base images..."
docker-compose -f "$COMPOSE_FILE" pull --ignore-pull-failures || true

# Step 4: Build containers
echo ""
echo "Step 4: Building containers..."

if [ "$NO_CACHE" = true ]; then
    echo "Building with --no-cache flag..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache --parallel
else
    echo "Building with cache..."
    docker-compose -f "$COMPOSE_FILE" build --parallel
fi

# Step 5: Start containers
echo ""
echo "Step 5: Starting containers..."
docker-compose -f "$COMPOSE_FILE" up -d

# Step 6: Wait for services to be healthy
echo ""
echo "Step 6: Checking service health..."

# Function to check health
check_health() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "  Checking $service..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo " ✓ Healthy"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 2
        echo -n "."
    done
    
    echo " ✗ Failed"
    return 1
}

# Check each service
HEALTH_OK=true

# Check NeuroSync
if ! check_health "NeuroSync API" "http://localhost:5000/health"; then
    HEALTH_OK=false
fi

# Check BYOC Worker
if ! check_health "BYOC Worker" "http://localhost:9876/health"; then
    HEALTH_OK=false
fi

# Step 7: Show container status
echo ""
echo "Step 7: Container Status:"
docker-compose -f "$COMPOSE_FILE" ps

# Final status
echo ""
echo "=================================================="
if [ "$HEALTH_OK" = true ]; then
    echo "✓ Rebuild completed successfully!"
    echo ""
    echo "All services are running and healthy."
else
    echo "⚠ Rebuild completed with warnings"
    echo ""
    echo "Some services failed health checks. Check logs with:"
    echo "  docker-compose -f $COMPOSE_FILE logs"
fi
echo "=================================================="

# Show resource usage
echo ""
echo "Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "neurosync|byoc|worker" || true

exit 0