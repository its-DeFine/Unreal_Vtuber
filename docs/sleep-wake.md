# Sleep / Wake Control (Power API)

The orchestrator health service (port **9090**) exposes a power API to deliberately
stop/start the Pixel Streaming stack for power conservation. State is persisted in
`/var/lib/vtuber/power-state/power_state.json` and shared with the watchdog so it
skips recovery while sleeping.

## Endpoints
- `GET /power` – returns current state: `{"state":"awake|sleeping","reason":...,"awake_until":...}`
- `POST /power` – body:
  - `{"action":"sleep","reason":"maintenance"}` – stop all orchestrator containers (except `orchestrator-health`).
  - `{"action":"wake"}` – start all containers in dependency order.
  - `{"action":"wake","awake_seconds":3600}` – start all containers, then auto-sleep after `awake_seconds`.
- `GET /health` – continues to report service status; while sleeping, game shows as exited.

## Auth / allowlist
- `POWER_ALLOWED_IPS` governs which source IPs can access `/power`. If unset, it falls back to
  `VTUBER_ALLOWED_ADDRESSES`.
- `POWER_ALLOWED_IPS_FILE` (optional) points at a host-mounted file containing the same CSV allowlist.
  If present and non-empty, it overrides `POWER_ALLOWED_IPS` (useful when another service rotates edges).
- Requests from other IPs receive a 403.

## Behavior
- `sleep` writes state first, then stops every container in the compose project except itself (and any service
  listed in `POWER_KEEP_RUNNING_SERVICES`).
- `wake` flips state to `awake`, starts the stack in dependency order (TURN → signaling → game → runner/recorder/watchdog).
- If `awake_seconds` is provided on wake, the service schedules an automatic `sleep` after that TTL (best-effort).

## Compose wiring
`docker-compose.unreal.yml` already mounts the shared power-state file and passes the
allowlist to orchestrator-health/watchdog:
```
orchestrator-health:
  environment:
    - POWER_ALLOWED_IPS=${POWER_ALLOWED_IPS:-}
    - POWER_ALLOWED_IPS_FILE=${EDGE_POWER_ALLOWED_IPS_FILE-/var/lib/vtuber/power-state/power_allowed_ips.txt}
    - POWER_KEEP_RUNNING_SERVICES=${POWER_KEEP_RUNNING_SERVICES-orchestrator-edge-rotator}
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

# wake (until manually slept)
curl -X POST -H "Content-Type: application/json" \
  -d '{"action":"wake"}' \
  http://<host>:9090/power

# wake for 1 hour, then auto-sleep
curl -X POST -H "Content-Type: application/json" \
  -d '{"action":"wake","awake_seconds":3600,"reason":"session TTL"}' \
  http://<host>:9090/power
```
