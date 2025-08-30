#!/bin/bash
# Fix script for remote orchestrator deployment issues
# Created: 2025-08-30

set -e

echo "==========================================="
echo "Fixing Remote Orchestrator Deployment"
echo "==========================================="

# Function to apply fix locally
fix_local() {
    echo "Applying fix to local Unreal_Vtuber repository..."
    
    cd /home/geo/test/Unreal_Vtuber
    
    # Ensure entrypoint_bridge.sh is in the correct location and executable
    if [ -f "docker-vtuber/app/AVATAR/NeuroBridge/entrypoint_bridge.sh" ]; then
        echo "✓ entrypoint_bridge.sh found in correct location"
        chmod +x docker-vtuber/app/AVATAR/NeuroBridge/entrypoint_bridge.sh
        echo "✓ Made entrypoint_bridge.sh executable"
    else
        echo "✗ entrypoint_bridge.sh not found! Copying from scripts..."
        cp scripts/entrypoints/entrypoint_bridge.sh docker-vtuber/app/AVATAR/NeuroBridge/
        chmod +x docker-vtuber/app/AVATAR/NeuroBridge/entrypoint_bridge.sh
    fi
    
    # Create a rollback commit
    git add -A
    git diff --staged --quiet || git commit -m "fix: ensure entrypoint_bridge.sh is in correct location for build context"
    
    echo "✓ Local fix applied"
}

# Function to apply fix to remote
fix_remote() {
    REMOTE_HOST=$1
    REMOTE_USER=${2:-root}
    REMOTE_PATH=${3:-/root/Unreal_Vtuber}
    
    echo "Applying fix to remote orchestrator at $REMOTE_HOST..."
    
    # Copy the entrypoint file to remote
    echo "Copying entrypoint_bridge.sh to remote..."
    scp docker-vtuber/app/AVATAR/NeuroBridge/entrypoint_bridge.sh \
        ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/docker-vtuber/app/AVATAR/NeuroBridge/
    
    # SSH to remote and fix permissions
    ssh ${REMOTE_USER}@${REMOTE_HOST} << 'ENDSSH'
cd /root/Unreal_Vtuber

# Make entrypoint executable
chmod +x docker-vtuber/app/AVATAR/NeuroBridge/entrypoint_bridge.sh

# Stop and remove the problematic containers
echo "Stopping and removing problematic containers..."
docker-compose down

# Remove the failed containers
docker rm -f neurosync_s1 autogen_agent ollama_exporter scb_gateway || true

# Rebuild the images with fresh context
echo "Rebuilding images..."
docker-compose build --no-cache neurosync_s1

# Start the services
echo "Starting services..."
docker-compose up -d

# Check status
sleep 10
echo "Current container status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}"
ENDSSH
    
    echo "✓ Remote fix applied"
}

# Main execution
case "$1" in
    local)
        fix_local
        ;;
    remote)
        if [ -z "$2" ]; then
            echo "Usage: $0 remote <hostname> [username] [path]"
            echo "Example: $0 remote ServeurAI1 root /root/Unreal_Vtuber"
            exit 1
        fi
        fix_local  # Fix local first
        fix_remote "$2" "$3" "$4"
        ;;
    *)
        echo "Usage: $0 {local|remote}"
        echo "  local  - Fix local Unreal_Vtuber repository"
        echo "  remote - Fix remote orchestrator (requires hostname)"
        exit 1
        ;;
esac

echo "==========================================="
echo "Fix Complete!"
echo "==========================================="