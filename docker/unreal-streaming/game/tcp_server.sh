#!/bin/bash
# TCP Server relay for VTuber commands
# This script listens on port 7777 and forwards commands to the Unreal Engine game

echo "Starting TCP server on port 7777 for VTuber commands..."

# Create a named pipe for communication
PIPE=/tmp/vtuber_commands
rm -f $PIPE
mkfifo $PIPE

# Function to handle incoming connections
handle_client() {
    while true; do
        # Listen for incoming connections
        nc -l -p 7777 | while read -r command; do
            echo "Received command: $command"
            
            # Log the command
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] $command" >> /var/log/supervisor/tcp_commands.log
            
            # Forward to Unreal Engine if it's running
            # The game will handle these commands internally
            echo "$command" > $PIPE &
            
            # Send acknowledgment
            echo "ACK: $command"
        done
    done
}

# Start the TCP server
handle_client