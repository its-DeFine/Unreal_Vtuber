#!/bin/bash

# entrypoint_bridge.sh - Starts both NeuroSync Local API and Player services

set -e

echo "Starting NeuroSync Bridge Services..."

# Print environment variables for debugging
echo "Environment variables:"
echo "FLASK_HOST=${FLASK_HOST}"
echo "PLAYER_PORT=${PLAYER_PORT}"
echo "AUTONOMOUS_ORCHESTRATION_ENABLED=${AUTONOMOUS_ORCHESTRATION_ENABLED}"
echo "ORCHESTRATOR_VERSION=${ORCHESTRATOR_VERSION}"

# Set default values
FLASK_HOST=${FLASK_HOST:-"0.0.0.0"}
PLAYER_PORT=${PLAYER_PORT:-"5001"}

# Function to start the Flask API
start_flask_api() {
    echo "Starting NeuroSync Local API (Flask) on port 5000..."
    cd /app/NeuroBridge/NeuroSync_Local_API
    python3 neurosync_local_api.py &
    FLASK_PID=$!
    echo "Flask API started with PID: $FLASK_PID"
}

# Function to start the Player service
start_player() {
    echo "Starting NeuroSync Player service on port $PLAYER_PORT..."
    cd /app/NeuroBridge/NeuroSync_Player
    
    # Always start the main LLM to face service 
    # The orchestrator version is handled internally by the llm_to_face.py
    echo "Starting LLM to face service with orchestrator version: $ORCHESTRATOR_VERSION"
    python3 llm_to_face.py &
    
    PLAYER_PID=$!
    echo "Player service started with PID: $PLAYER_PID"
}

# Function to handle shutdown
shutdown() {
    echo "Shutting down services..."
    if [ ! -z "$FLASK_PID" ]; then
        kill $FLASK_PID 2>/dev/null || true
    fi
    if [ ! -z "$PLAYER_PID" ]; then
        kill $PLAYER_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap shutdown SIGTERM SIGINT

# Start services
start_flask_api
sleep 2
start_player

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 5

# Keep the container running and monitor services
echo "Services started successfully. Monitoring..."
while true; do
    # Check if Flask API is still running
    if ! kill -0 $FLASK_PID 2>/dev/null; then
        echo "Flask API process died. Restarting..."
        start_flask_api
    fi
    
    # Check if Player service is still running
    if ! kill -0 $PLAYER_PID 2>/dev/null; then
        echo "Player service process died. Restarting..."
        start_player
    fi
    
    sleep 10
done