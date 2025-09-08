#!/bin/bash
# Start script for Unreal Engine game with Pixel Streaming

echo "Starting Unreal Engine game with Pixel Streaming..."

# Wait for Xvfb to be ready
sleep 2

# Set environment variables
export DISPLAY=:99
export XDG_RUNTIME_DIR=/tmp/runtime-gameuser
mkdir -p $XDG_RUNTIME_DIR

# Pixel Streaming parameters
PS_PARAMS=(
    -PixelStreamingURL="ws://${SIGNALING_HOST}:${SIGNALING_PORT}"
    -PixelStreamingIP="${SIGNALING_HOST}"
    -PixelStreamingPort="${SIGNALING_PORT}"
    -RenderOffScreen
    -Windowed
    -ResX=1920
    -ResY=1080
    -ForceRes
    -AllowPixelStreamingCommands
    -PixelStreamingEncoderRateControl=VBR
    -PixelStreamingEncoderTargetBitrate=5000000
    -PixelStreamingEncoderMaxBitrate=10000000
    -PixelStreamingWebRTCFps=${FPS:-60}
    -PixelStreamingWebRTCDisableReceiveAudio
    -PixelStreamingWebRTCDisableTransmitAudio
)

# TCP Server parameters for VTuber control
TCP_PARAMS=(
    -TCPServerEnabled=true
    -TCPServerPort=7777
    -TCPServerBindAddress=0.0.0.0
)

# Graphics parameters
GRAPHICS_PARAMS=(
    -dx12
    -sm6
    -NoAudio
    -NoSound
    -NullRHI
)

# Check if game executable exists
GAME_PATH="/home/gameuser/Embody/Linux/Embody.sh"
if [ ! -f "$GAME_PATH" ]; then
    echo "Error: Game executable not found at $GAME_PATH"
    echo "Waiting for game files to be mounted..."
    sleep infinity
fi

# Make executable
chmod +x "$GAME_PATH"

# Start the game with all parameters
echo "Launching game with parameters:"
echo "  Pixel Streaming: ${PS_PARAMS[@]}"
echo "  TCP Server: ${TCP_PARAMS[@]}"
echo "  Graphics: ${GRAPHICS_PARAMS[@]}"

cd /home/gameuser/Embody/Linux

# Execute the game
exec ./Embody.sh \
    "${PS_PARAMS[@]}" \
    "${TCP_PARAMS[@]}" \
    "${GRAPHICS_PARAMS[@]}" \
    -game \
    -log \
    2>&1 | tee /var/log/supervisor/game_output.log