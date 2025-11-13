#!/bin/sh

set -eu

log() {
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
}

WATCHDOG_COMPOSE_FILE="${WATCHDOG_COMPOSE_FILE:-/workspace/docker-compose.unreal.yml}"
WATCHDOG_RUNNER_SERVICE="${WATCHDOG_RUNNER_SERVICE:-vtuber-script-runner}"
WATCHDOG_GAME_CONTAINER="${WATCHDOG_GAME_CONTAINER:-vtuber-unreal-game}"
WATCHDOG_EVENT_RETRY_DELAY="${WATCHDOG_EVENT_RETRY_DELAY:-5}"
WATCHDOG_VERBOSE="${WATCHDOG_VERBOSE:-0}"

if [ ! -f "$WATCHDOG_COMPOSE_FILE" ]; then
  log "Compose file $WATCHDOG_COMPOSE_FILE not found; exiting."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  USE_COMPOSE_PLUGIN=1
else
  log "docker compose plugin is not available in this image; exiting."
  exit 1
fi

compose_cmd() {
  if [ "$USE_COMPOSE_PLUGIN" = "1" ]; then
    docker compose -f "$WATCHDOG_COMPOSE_FILE" "$@"
  fi
}

ensure_runner_namespace() {
  runner_id="$(compose_cmd ps -q "$WATCHDOG_RUNNER_SERVICE" | head -n 1 || true)"
  game_ns="$(docker inspect -f '{{.NetworkSettings.SandboxKey}}' "$WATCHDOG_GAME_CONTAINER" 2>/dev/null || true)"

  if [ -z "$game_ns" ]; then
    log "Game container $WATCHDOG_GAME_CONTAINER not running yet; skipping namespace check."
    return
  fi

  if [ -z "$runner_id" ]; then
    log "Runner container missing; recreating $WATCHDOG_RUNNER_SERVICE."
    compose_cmd up -d --force-recreate "$WATCHDOG_RUNNER_SERVICE"
    return
  fi

  runner_ns="$(docker inspect -f '{{.NetworkSettings.SandboxKey}}' "$runner_id" 2>/dev/null || true)"

  if [ "$runner_ns" != "$game_ns" ] || [ -z "$runner_ns" ]; then
    log "Sandbox mismatch detected (game=$game_ns runner=$runner_ns). Recreating runner."
    compose_cmd up -d --force-recreate "$WATCHDOG_RUNNER_SERVICE"
  elif [ "$WATCHDOG_VERBOSE" = "1" ]; then
    log "Runner namespace matches Unreal game."
  fi
}

watch_events() {
  while true; do
    log "Watching docker events for $WATCHDOG_GAME_CONTAINER..."
    docker events \
      --filter "container=$WATCHDOG_GAME_CONTAINER" \
      --filter "event=start" \
      --filter "event=restart" \
      --filter "event=die" \
      --format '{{.Status}} {{.Time}}' |
      while IFS= read -r event_line; do
        [ -z "$event_line" ] && continue
        log "Received event: $event_line"
        ensure_runner_namespace
      done

    log "Event stream ended, retrying in ${WATCHDOG_EVENT_RETRY_DELAY}s."
    sleep "$WATCHDOG_EVENT_RETRY_DELAY"
  done
}

log "Starting vtuber-script-runner watchdog (runner=$WATCHDOG_RUNNER_SERVICE, game=$WATCHDOG_GAME_CONTAINER)."
ensure_runner_namespace
watch_events
