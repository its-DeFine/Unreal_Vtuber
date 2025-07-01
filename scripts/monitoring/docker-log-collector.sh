#!/usr/bin/env bash
# -------------------------------------------------------------
# Docker Log Collector (lightweight)
# -------------------------------------------------------------
# Continuously tails docker logs for the specified containers and
# writes them to rotating log files inside ./logs/docker/
# Each container gets its own logfile: <container>.log
# Logs rotate daily (and on restart) with ISO timestamps appended.
#
# Usage (interactive):
#   ./scripts/monitoring/docker-log-collector.sh neurosync_s1 nginx-rtmp
#
# Usage (background / systemd):
#   nohup ./scripts/monitoring/docker-log-collector.sh neurosync_s1 nginx-rtmp &
#
# Env-vars:
#   LOG_DIR   Where to store the logs (default: ./logs/docker)
#   TS_FORMAT date format string (default: +"%Y-%m-%dT%H:%M:%S")
# -------------------------------------------------------------
set -euo pipefail

LOG_DIR=${LOG_DIR:-"$(pwd)/logs/docker"}
TS_FORMAT=${TS_FORMAT:-"%Y-%m-%dT%H:%M:%S"}

if [ $# -lt 1 ]; then
  echo "Usage: $0 <container_name1> [container_name2 ...]"
  exit 1
fi

mkdir -p "$LOG_DIR"

echo "📄 Writing docker logs to $LOG_DIR"

declare -a PIDS=()
trap 'echo "🛑 Stopping log collectors"; for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done' INT TERM EXIT

for container in "$@"; do
  logfile="$LOG_DIR/${container}-$(date +%Y%m%d-%H%M%S).log"
  echo "▶️  Tailing $container -> $logfile"
  # Use timestamps from docker (RFC3339) for consistency
  docker logs -f --since 0s --timestamps "$container" 2>&1 | tee -a "$logfile" &
  PIDS+=("$!")
  # Small delay to avoid overloading
  sleep 0.1
done

# Wait for all background tails
wait 