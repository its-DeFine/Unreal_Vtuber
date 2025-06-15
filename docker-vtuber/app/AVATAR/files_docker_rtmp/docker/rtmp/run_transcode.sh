#!/bin/bash
# run_transcode.sh
# Usage: run_transcode.sh <stream_name>
# Called by nginx-rtmp 'exec' directive. Logs all output to /opt/data/ffmpeg-<stream_name>.log
set -euo pipefail

STREAM_NAME=$1
LOG_FILE="/opt/data/ffmpeg-${STREAM_NAME}.log"

/usr/local/bin/ffmpeg -loglevel verbose -i "rtmp://localhost:1935/live/${STREAM_NAME}" \
  -pix_fmt yuv420p \
  -c:a libfdk_aac -b:a 128k -c:v libx264 -b:v 2500k -f flv -g 30 -r 30 -s 1280x720 -preset superfast "rtmp://localhost:1935/hls/${STREAM_NAME}_720p2628kbs" \
  -c:a libfdk_aac -b:a 128k -c:v libx264 -b:v 1000k -f flv -g 30 -r 30 -s 854x480 -preset superfast "rtmp://localhost:1935/hls/${STREAM_NAME}_480p1128kbs" \
  -c:a libfdk_aac -b:a 128k -c:v libx264 -b:v 750k -f flv -g 30 -r 30 -s 640x360 -preset superfast "rtmp://localhost:1935/hls/${STREAM_NAME}_360p878kbs" \
  -c:a libfdk_aac -b:a 128k -c:v libx264 -b:v 400k -f flv -g 30 -r 30 -s 426x240 -preset superfast "rtmp://localhost:1935/hls/${STREAM_NAME}_240p528kbs" \
  -c:a libfdk_aac -b:a 64k -c:v libx264 -b:v 200k -f flv -g 15 -r 15 -s 426x240 -preset superfast "rtmp://localhost:1935/hls/${STREAM_NAME}_240p264kbs" \
  2>&1 | tee -a "$LOG_FILE" 