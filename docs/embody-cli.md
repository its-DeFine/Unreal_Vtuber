# Embody Orchestrator CLI (`scripts/embody_cli.sh`)

This repo ships a single entrypoint for onboarding and day-to-day operations: `./scripts/embody_cli.sh`.

## Recommended flow

1. Run the interactive dashboard:

```bash
./scripts/embody_cli.sh
```

## What you’ll see (interactive)

The CLI prints an overview dashboard, then prompts with a menu like:

```text
1) Start stack
2) Stop stack
3) Restart stack
4) Status
5) Logs
6) Health (quick)
7) TCP test (runner → game)
8) Config summary
9) GPU capacity
c) Cluster deploy (auto)
C) Cluster status
x) Cluster down
r) Rollout game image
u) Upgrade (pull/recreate containers)
v) Verify (end-to-end)
m) Payments status
p) Power (sleep/wake)
b) Optional RTMP broadcast
s) Setup / reconfigure
q) Quit
>
```

2. If you want a one-shot status view:

```bash
./scripts/embody_cli.sh overview
```

3. Run health + end-to-end checks:

```bash
./scripts/embody_cli.sh verify --fix
```

## Command reference

- `setup` – onboarding wizard (writes `.env` + `.env.turn`, pulls encrypted image, starts the stack)
  - Non-interactive example:
    ```bash
    ./scripts/embody_cli.sh setup --non-interactive \
      --orchestrator-id <id> \
      --orchestrator-address <0x...> \
      --invite-code <code>
    ```
- `overview` – compact dashboard (power state, containers, key config)
- `verify` – health + consistency checks (runner TCP + record/download smoke tests when awake)
  - `--fix` recreates runner/recorder if allowlist env drift is detected and auto-fixes common Payments allowlist gaps
  - Also checks outbound HTTPS (needed for presigned uploads) and warns if allowlists look misconfigured
- `payments` – Payments connectivity checks + viewer token helper (when a viewer token is available)
- `allowlists` – check/fix allowlists needed for Payments-driven workloads (`/power`, runner, recorder)
- `register` – register orchestrator in Payments (cached; skips when already registered)
- `license` / `license redeem` – view or redeem license token (invite code → token)
- `rollout` – load encrypted game image (wrapper for `tools/encrypted-game-image/rollout.sh`)
- `power` – sleep/wake the stack via `http://127.0.0.1:9090/power` (or a single compose project via `/power/projects/<project>`)
  - `power sleep|wake --project <compose_project>` targets one cluster instance (example: `vtuber-embody-0`)
  - `power wake --ttl <seconds>` sets an auto-sleep TTL on wake
- Day-to-day stack control:
  - `start`, `stop`, `restart`, `status`, `logs [service]`, `health`
- `broadcast` – manage the independent, opt-in WebRTC → RTMP bridge
  - `broadcast configure` – securely prompt for and store a destination outside the repo
  - `broadcast configure --url-file <path>` / `--url-stdin` – automation-safe destination input
  - `broadcast configure --test` – fake source/sink lifecycle mode (no account, game image, or GPU)
  - `broadcast start|stop|status|logs|recover` – operate and recover only the broadcast Compose project
  - `broadcast configure --disable` – stop it and remove the stored destination
  - `broadcast status --json` – sanitized machine-readable state
- `upgrade` – pull/recreate service containers (safe to run while sleeping; won’t wake the game)
  - Repo auto-updates to latest `origin/main` on CLI launch (ff-only, best-effort; skipped when the checkout is dirty or detached HEAD)
  - Opt-out of repo auto-update: `EMBODY_CLI_NO_AUTO_UPDATE=1 ./scripts/embody_cli.sh`
  - Opt-out of auto-upgrade-when-sleeping: `EMBODY_CLI_AUTO_UPGRADE_WHEN_SLEEPING=0 ./scripts/embody_cli.sh`
- `cluster` – multi-instance “cluster mode” (multiple concurrent avatars on one host)
  - Config: `~/.embody/cluster.json` (override with `EMBODY_CLUSTER_FILE=/path/to/cluster.json`)
  - Commands: `cluster plan`, `cluster list`, `cluster up`, `cluster deploy`, `cluster down`, `cluster status`, `cluster logs`
    - `cluster deploy` is a convenience wrapper: `pull` + `cluster up --recreate` (disable pieces with `--no-pull`, `--no-recreate`)
    - If you’re pinned to a release tag (detached HEAD), auto-update is skipped and `cluster deploy` won’t switch branches.
  - Port map (slot-based, deterministic):
    - Signaling public port: `8080 + slot`
    - Runner port: `9877 + slot`
    - Recorder-control port: `8889 + slot`
  - Per-instance isolation:
    - Docker compose projects + per-instance networks
    - Sessions: `${VTUBER_SESSION_DIR}/<avatar>`
    - Recordings: `${VTUBER_RECORDINGS_DIR}/<avatar>`
    - Deterministic per-slot Docker subnet: `172.30.<slot>.0/24` (gateway `172.30.<slot>.1` is auto-added to `VTUBER_ALLOWED_ADDRESSES` so host → runner/recorder calls work)
  - Note: `cluster up` enforces a conservative VRAM estimate (8GiB/instance); pass `--force` to bypass.

## Network / allowlists

The orchestrator uses allowlists to protect control endpoints:

- Script runner (9877): strict IP string match via `VTUBER_ALLOWED_ADDRESSES`
- Recorder control (8889): strict IP string match via `VTUBER_ALLOWED_ADDRESSES` (and optional `RECORDINGS_API_TOKEN`)
- Power API (9090): CIDR-aware allowlist via `POWER_ALLOWED_IPS` or `POWER_ALLOWED_IPS_FILE`

If `EDGE_CONFIG_URL` is configured, the `orchestrator-edge-rotator` sidecar manages allowlists automatically and can also add extra “always allowed” CIDRs/IPs:

- `EDGE_FIREWALL_EXTRA_CIDRS` – additional CIDRs to allow through host firewall (ex: Payments host for `/health`)
- `EDGE_POWER_EXTRA_CIDRS` – additional CIDRs allowed to call `/power` (ex: Payments host for wake/sleep)
- `EDGE_LOCAL_ALLOWLIST` – IPs prepended to `VTUBER_ALLOWED_ADDRESSES` (ex: Payments host for runner/recorder)

CLI helper:

- `./scripts/embody_cli.sh allowlists status`
- `./scripts/embody_cli.sh allowlists fix`

## Remote workloads (record → upload)

If you use Payments-driven recording jobs:

- The orchestrator must allowlist the Payments host IP for `/power`, runner, and recorder.
- The orchestrator must have **outbound HTTPS** access so it can `PUT` to presigned URLs.

See also:
- Optional RTMP broadcast: `docs/broadcast.md`
- Recorder control docs: `docs/recorder-control.md`
- Onboarding guide: `docs/orchestrator-onboarding.md`

## Remote metadata + ops (experimental)

The `orchestrator-health` service exposes remote metadata and a small remote-control API on `:9090`:

- `GET http://<host>:9090/meta` – git head + service images/ids + last `verify` + rollout state
- `POST http://<host>:9090/ops/upgrade` – ff-only git update; optional pull/recreate host services
- `POST http://<host>:9090/ops/rollout` – stage/apply encrypted game image via a Payments lease
- `POST http://<host>:9090/ops/pull-image` – `docker pull` for unencrypted images

### Defaults and what changes require

- Enabled by default. To disable: set `EXPERIMENTAL_REMOTE_OPS=0` in `.env` and recreate `orchestrator-health`.
- Always protected by the Power allowlist. If `POWER_ALLOWED_IPS` / `POWER_ALLOWED_IPS_FILE` is not configured, `/ops/*` returns `403`.
- Most `orchestrator-health` env vars (including `EXPERIMENTAL_REMOTE_OPS` and `EXPERIMENTAL_REMOTE_CLUSTER_CONTROL`) are read at process startup, so changes require a recreate/restart.

Recreate `orchestrator-health` (from the repo root):

```bash
# Default host project name used by the CLI is `vtuber-host`:
docker compose -p vtuber-host -f docker-compose.unreal.yml --env-file .env up -d --force-recreate orchestrator-health
```

If your host stack uses a different compose project name, replace `vtuber-host`. You can discover it from the running container:

```bash
docker inspect vtuber-orchestrator-health --format '{{ index .Config.Labels "com.docker.compose.project" }}'
```

Note: if you only changed allowlist file contents at `/var/lib/vtuber/power-state/power_allowed_ips.txt`, no recreate is needed (it’s read on each request).
