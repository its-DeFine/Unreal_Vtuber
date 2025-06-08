#!/bin/bash
set -e

# Entrypoint script for nginx-rtmp server
# Handles initialization and startup

echo "🎥 [RTMP Server] Starting nginx-rtmp server..."

# Set up logging
mkdir -p /var/log/nginx
touch /var/log/nginx/access.log
touch /var/log/nginx/error.log

# Create required directories if they don't exist
mkdir -p /var/recordings/voice
mkdir -p /tmp/hls/voice
mkdir -p /tmp/hls/test
mkdir -p /tmp/dash
mkdir -p /var/www/html

# Set correct permissions
chown -R nginx:nginx /var/recordings /tmp/hls /tmp/dash /var/www /var/log/nginx

# Ensure GStreamer is available
if ! command -v gst-launch-1.0 &> /dev/null; then
    echo "❌ [RTMP Server] GStreamer not found"
    exit 1
fi

# Ensure FFmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ [RTMP Server] FFmpeg not found"
    exit 1
fi

# Test nginx configuration
echo "🔧 [RTMP Server] Testing nginx configuration..."
nginx -t

if [ $? -ne 0 ]; then
    echo "❌ [RTMP Server] nginx configuration test failed"
    exit 1
fi

# Log environment information
echo "🔍 [RTMP Server] Environment Information:"
echo "  - nginx version: $(nginx -v 2>&1)"
echo "  - GStreamer version: $(gst-launch-1.0 --version | head -1)"
echo "  - FFmpeg version: $(ffmpeg -version | head -1)"
echo "  - Python version: $(python3 --version)"
echo "  - Current user: $(whoami)"
echo "  - Working directory: $(pwd)"

# Start background processes if needed
echo "🚀 [RTMP Server] Starting background processes..."

# Start audio processing daemon
if [ -f "/usr/local/bin/audio_processor.py" ]; then
    python3 /usr/local/bin/audio_processor.py --daemon &
    echo "✅ [RTMP Server] Audio processor daemon started"
fi

# Start stream manager daemon
if [ -f "/usr/local/bin/stream_manager.py" ]; then
    python3 /usr/local/bin/stream_manager.py --daemon &
    echo "✅ [RTMP Server] Stream manager daemon started"
fi

# Handle signals for graceful shutdown
trap 'echo "🛑 [RTMP Server] Received shutdown signal, stopping..."; pkill -TERM nginx; exit 0' TERM INT

echo "✅ [RTMP Server] Initialization complete"
echo "🎯 [RTMP Server] RTMP server will listen on port 1935"
echo "🌐 [RTMP Server] HTTP server will listen on port 8080"
echo "📊 [RTMP Server] Statistics available at: http://localhost:8080/stats"
echo "💾 [RTMP Server] Recordings will be saved to: /var/recordings"
echo "📺 [RTMP Server] HLS streams available at: http://localhost:8080/hls/"

# Execute the main command
exec "$@" 