# Sleep / Wake Control (Power API)

The orchestrator health service (port **9090**) exposes a power API to deliberately
stop/start the Unreal game without the watchdog undoing it. State is persisted in
`/var/lib/vtuber/power-state/power_state.json` and shared with the watchdog so it
skips recovery while sleeping.

## Endpoints
- `GET /power` – returns current state: `{"state":"awake|sleeping","reason":...}`
- `POST /power` – body:
  - `{"action":"sleep","reason":"maintenance"}` – stop the game (and runner if default).
  - `{"action":"wake"}` – start the game, wait for running, restart runner.
- `GET /health` – continues to report service status; while sleeping, game shows as exited.

## Auth / allowlist
- `POWER_ALLOWED_IPS` governs which source IPs can access `/power`. Set it in `.env`,
  e.g. `POWER_ALLOWED_IPS=127.0.0.1,::1,<edge-ip>`.
- Requests from other IPs receive a 403.

## Behavior
- `sleep` writes state first, then stops the game (and runner if
  `POWER_STOP_RUNNER_ON_SLEEP` is default). Watchdog ignores game events while sleeping.
- `wake` flips state to `awake`, starts the game, waits for running, and restarts the
  runner to reattach to the game namespace.

## Compose wiring
`docker-compose.unreal.yml` already mounts the shared power-state file and passes the
allowlist to orchestrator-health/watchdog:
```
orchestrator-health:
  environment:
    - POWER_ALLOWED_IPS=${POWER_ALLOWED_IPS:-}
  volumes:
    - /var/lib/vtuber/power-state:/var/lib/vtuber/power-state
...
vtuber-watchdog:
  volumes:
    - /var/lib/vtuber/power-state:/var/lib/vtuber/power-state:ro
```

## Usage examples
```
# check state
curl http://<host>:9090/power

# sleep
curl -X POST -H "Content-Type: application/json" \
  -d '{"action":"sleep","reason":"maintenance"}' \
  http://<host>:9090/power

# wake
curl -X POST -H "Content-Type: application/json" \
  -d '{"action":"wake"}' \
  http://<host>:9090/power
```
