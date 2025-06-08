#!/bin/bash

# Build script for Single Container RTMP Server
# Usage: ./build.sh [options]

set -e

# Configuration
IMAGE_NAME="rtmp-voice-server"
CONTAINER_NAME="rtmp-voice-server"
VERSION="latest"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to show usage
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  build       Build the Docker image"
    echo "  run         Run the container (with docker-compose)"
    echo "  stop        Stop the container"
    echo "  restart     Restart the container"
    echo "  logs        Show container logs"
    echo "  shell       Access container shell"
    echo "  clean       Clean up images and containers"
    echo "  test        Test the RTMP server"
    echo ""
}

# Build Docker image
build_image() {
    log "🔨 Building RTMP Server Docker image..."
    
    # Ensure we're in the right directory
    if [ ! -f "Dockerfile" ]; then
        log "❌ Dockerfile not found. Make sure you're in the rtmp-server directory."
        exit 1
    fi
    
    docker build -t $IMAGE_NAME:$VERSION .
    
    if [ $? -eq 0 ]; then
        log "✅ Docker image built successfully: $IMAGE_NAME:$VERSION"
        
        # Show image size
        size=$(docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep $IMAGE_NAME | head -1)
        log "📦 Image size: $size"
    else
        log "❌ Docker build failed"
        exit 1
    fi
}

# Run container
run_container() {
    log "🚀 Starting RTMP Server container..."
    
    # Create recordings directory if it doesn't exist
    mkdir -p ./recordings
    
    # Use docker-compose for easier management
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
        
        if [ $? -eq 0 ]; then
            log "✅ Container started successfully"
            log "🎥 RTMP Server available at: rtmp://localhost:1935"
            log "🌐 Web Interface available at: http://localhost:8080"
            log "📊 Statistics available at: http://localhost:8080/stats"
        else
            log "❌ Failed to start container"
            exit 1
        fi
    else
        log "⚠️  docker-compose not found, using docker run instead"
        
        # Stop existing container if running
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true
        
        # Run with docker
        docker run -d \
            --name $CONTAINER_NAME \
            -p 1935:1935 \
            -p 8080:8080 \
            -v $(pwd)/recordings:/var/recordings \
            --restart unless-stopped \
            $IMAGE_NAME:$VERSION
            
        if [ $? -eq 0 ]; then
            log "✅ Container started successfully"
            log "🎥 RTMP Server available at: rtmp://localhost:1935"
            log "🌐 Web Interface available at: http://localhost:8080"
        else
            log "❌ Failed to start container"
            exit 1
        fi
    fi
}

# Stop container
stop_container() {
    log "🛑 Stopping RTMP Server container..."
    
    if command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
        docker-compose down
    else
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true
    fi
    
    log "✅ Container stopped"
}

# Show logs
show_logs() {
    log "📋 Showing container logs..."
    
    if command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
        docker-compose logs -f
    else
        docker logs -f $CONTAINER_NAME
    fi
}

# Access shell
access_shell() {
    log "🔧 Accessing container shell..."
    
    if command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
        docker-compose exec rtmp-server /bin/bash
    else
        docker exec -it $CONTAINER_NAME /bin/bash
    fi
}

# Clean up
cleanup() {
    log "🧹 Cleaning up Docker images and containers..."
    
    # Stop and remove container
    stop_container
    
    # Remove images
    docker rmi $IMAGE_NAME:$VERSION 2>/dev/null || true
    docker system prune -f
    
    log "✅ Cleanup completed"
}

# Test RTMP server
test_server() {
    log "🧪 Testing RTMP Server..."
    
    # Check if container is running
    if ! docker ps | grep -q $CONTAINER_NAME; then
        log "❌ Container is not running. Start it first with: $0 run"
        exit 1
    fi
    
    # Test health endpoint
    log "🔍 Testing health endpoint..."
    health_response=$(curl -s http://localhost:8080/health || echo "FAILED")
    
    if [ "$health_response" = "healthy" ]; then
        log "✅ Health check passed"
    else
        log "❌ Health check failed: $health_response"
    fi
    
    # Test stats endpoint
    log "🔍 Testing statistics endpoint..."
    stats_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/stats)
    
    if [ "$stats_response" = "200" ]; then
        log "✅ Statistics endpoint accessible"
    else
        log "❌ Statistics endpoint failed with code: $stats_response"
    fi
    
    # Test RTMP port
    log "🔍 Testing RTMP port..."
    if nc -z localhost 1935 2>/dev/null; then
        log "✅ RTMP port 1935 is accessible"
    else
        log "❌ RTMP port 1935 is not accessible"
    fi
    
    log "🎯 RTMP Server test completed"
    log "📖 To stream to the server, use: rtmp://localhost:1935/live/your_stream_name"
    log "🌐 Open web interface: http://localhost:8080"
}

# Main script logic
case "${1:-help}" in
    build)
        build_image
        ;;
    run)
        run_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        stop_container
        sleep 2
        run_container
        ;;
    logs)
        show_logs
        ;;
    shell)
        access_shell
        ;;
    clean)
        cleanup
        ;;
    test)
        test_server
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        log "❌ Unknown command: $1"
        usage
        exit 1
        ;;
esac 