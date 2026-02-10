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
WATCHDOG_PROJECT_NAME="${WATCHDOG_PROJECT_NAME:-}"
WATCHDOG_POWER_STATE_FILE="${WATCHDOG_POWER_STATE_FILE:-/var/lib/vtuber/power-state/power_state.json}"

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
  if [ "$USE_COMPOSE_PLUGIN" != "1" ]; then
    return 1
  fi

  if [ -n "$WATCHDOG_PROJECT_NAME" ]; then
    docker compose -p "$WATCHDOG_PROJECT_NAME" -f "$WATCHDOG_COMPOSE_FILE" "$@"
  else
    docker compose -f "$WATCHDOG_COMPOSE_FILE" "$@"
  fi
}

power_state_sleeping() {
  state_file="$WATCHDOG_POWER_STATE_FILE"
  if [ -z "$state_file" ] || [ ! -f "$state_file" ]; then
    return 1
  fi

  # Cheap JSON parsing: find "state": "sleeping"
  state_value="$(grep -oE '\"state\"[[:space:]]*:[[:space:]]*\"[^\"]+\"' "$state_file" 2>/dev/null | head -n 1 | cut -d '\"' -f4 || true)"
  [ "$state_value" = "sleeping" ]
}

ensure_runner_namespace() {
  if power_state_sleeping; then
    [ "$WATCHDOG_VERBOSE" = "1" ] && log "Sleep mode active; skipping runner namespace check."
    return
  fi

  runner_id="$(compose_cmd ps -q "$WATCHDOG_RUNNER_SERVICE" | head -n 1 || true)"
  game_id="$(docker inspect -f '{{.Id}}' "$WATCHDOG_GAME_CONTAINER" 2>/dev/null || true)"
  game_status="$(docker inspect -f '{{.State.Status}}' "$WATCHDOG_GAME_CONTAINER" 2>/dev/null || true)"

  if [ -z "$game_id" ]; then
    log "Game container $WATCHDOG_GAME_CONTAINER not available yet; skipping namespace check."
    return
  fi
  if [ "$game_status" != "running" ]; then
    log "Game container $WATCHDOG_GAME_CONTAINER status=$game_status (expected running); skipping runner namespace check."
    return
  fi

  if [ -z "$runner_id" ]; then
    log "Runner container missing; recreating $WATCHDOG_RUNNER_SERVICE."
    if ! compose_cmd up -d --no-deps --force-recreate "$WATCHDOG_RUNNER_SERVICE"; then
      log "Runner recreate failed (game may be offline/starting); will retry on next game event."
    fi
    return
  fi

  expected_mode="container:${game_id}"
  runner_mode="$(docker inspect -f '{{.HostConfig.NetworkMode}}' "$runner_id" 2>/dev/null || true)"

  if [ -z "$runner_mode" ] || [ "$runner_mode" != "$expected_mode" ]; then
    log "Network namespace mismatch detected (expected=$expected_mode runner=$runner_mode). Recreating runner."
    if ! compose_cmd up -d --no-deps --force-recreate "$WATCHDOG_RUNNER_SERVICE"; then
      log "Runner recreate failed (game may be offline/starting); will retry on next game event."
    fi
  elif [ "$WATCHDOG_VERBOSE" = "1" ]; then
    log "Runner network namespace matches Unreal game."
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
        if power_state_sleeping; then
          [ "$WATCHDOG_VERBOSE" = "1" ] && log "Sleep mode active; ignoring event."
          continue
        fi
        ensure_runner_namespace
      done

    log "Event stream ended, retrying in ${WATCHDOG_EVENT_RETRY_DELAY}s."
    sleep "$WATCHDOG_EVENT_RETRY_DELAY"
  done
}

log "Starting vtuber-script-runner watchdog (runner=$WATCHDOG_RUNNER_SERVICE, game=$WATCHDOG_GAME_CONTAINER, project=${WATCHDOG_PROJECT_NAME:-<default>})."
ensure_runner_namespace
watch_events
