# Unreal VTuber Pixel Streaming Stack

**ATTENTION:** Under active development, do not try to setup at this time.

This repository now hosts the Unreal Engine Pixel Streaming runtime plus the
launcher scripts used to operate an orchestrator host. The registration helper
still talks to the remote payments API, but the backend itself lives in a
separate repository.

## Contents

- `docker-compose.unreal.yml` – TURN, signaling, packaged Unreal container, script runner, orchestrator registration helper, and local health monitor.
- `orchestrator-health/` – lightweight FastAPI service that exposes container health at `http://<host>:9090/health`.
- `pixel-streaming/` – Pixel Streaming configuration overrides shipped with the Unreal build.
- `tools/encrypted-game-image/` – helper scripts to distribute the proprietary game image as an encrypted artifact (no GHCR creds needed on the orchestrator).
- `tools/recorder/` – recorder-control sidecar (see `docs/recorder-control.md`).
- `scripts/` – utilities for onboarding and orchestration (`start_vtuber_unreal.sh`, `register_orchestrator.py`, etc.).
- `docs/` – deployment, integration, and operations guides (each doc now calls out where to pull the payments backend).

## New deployment

You can run the stack in two ways:

- **Direct image pull** (requires registry access to the game image), or
- **Encrypted game image distribution** (recommended): the **game** image is loaded from an encrypted artifact (ex: S3) via a Payments-issued lease, so orchestrators do **not** need registry credentials for the game payload.

1. Clone the repo and enter it:
   ```bash
   git clone https://github.com/its-DeFine/Unreal_Vtuber.git
   cd Unreal_Vtuber
   ```
   :::note GPU reference
Our test environment runs on AWS g4dn.xlarge: NVIDIA T4 (16 GB VRAM, ~65 TFLOPS FP16, 70 W TDP), 4 vCPUs, 16 GB RAM. Any GPU with comparable specs should deliver similar Pixel Streaming quality while keeping costs in check.
   :::
2. Generate TURN credentials (writes `.env.turn`):
   ```bash
   ./scripts/generate_turn_credentials.sh
   ```
3. Copy and edit the orchestrator env:
   ```bash
   cp orchestrator.env.example .env
   # edit .env with PAYMENTS_API_URL (point at the standalone backend),
   # ORCHESTRATOR_ID/ADDRESS, PUBLIC_IP, and ORCHESTRATOR_HEALTH_URL
   # include VTUBER_ALLOWED_ADDRESSES=3.150.172.153 so the script runner accepts commands from the forwarder
   ```
4. Open the firewall so the forwarder (3.150.172.153) and payments backend (3.141.111.200) can reach this host.

| Traffic source                     | Ports (TCP)                       | Ports (UDP)               |
| --------------------------------- | ---------------------------------- | ------------------------- |
| Forwarder / client (3.150.172.153) | 8080, 8888, 8889, 9877 | 3478, 49160‑49200 |
| Payments backend (3.141.111.200) | 9090                          | –                |

   **Example (UFW)**
   ```bash
   CLIENT_IP=3.150.172.153          # Forwarder public IP
   PAYMENTS_IP=3.141.111.200        # Payments backend public IP

   for PORT in 8080 8888 8889 9877; do
     sudo ufw allow from $CLIENT_IP to any port $PORT proto tcp
   done
   sudo ufw allow from $CLIENT_IP to any port 3478 proto udp
   sudo ufw allow from $CLIENT_IP to any port 49160:49200 proto udp

   sudo ufw allow from $PAYMENTS_IP to any port 9090 proto tcp

   sudo ufw reload
   ```
5. Launch the Pixel Streaming stack (includes the health monitor service).

   **Option A: encrypted game image distribution (recommended)**

   You need (a) an orchestrator license token file and (b) an encrypted artifact URL (public/presigned).
   The host also needs `age`, `zstd`, `jq`, and `curl` installed (the script will error if missing).

   ```bash
   docker network create vtuber_network 2>/dev/null || true
   ./tools/encrypted-game-image/rollout.sh \
     --payments-api-url http://<payments-ip>:8081 \
     --orch-token-file /path/to/orchestrator-license-token.txt \
     --image-ref ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1 \
     --artifact-url "https://<public-or-presigned-url>"
   ```

   **Option B: direct image pull**

   Double-check `.env` still contains `VTUBER_ALLOWED_ADDRESSES=3.150.172.153` before running compose:
   ```bash
   docker network create vtuber_network 2>/dev/null || true
   docker compose -f docker-compose.unreal.yml up -d
   ```
6. Register with the payments backend (retries until it succeeds):
   ```bash
   docker compose -f docker-compose.unreal.yml run --rm orchestrator-registration
   ```
   Or, if you prefer to run it on the host:
   ```bash
   PAYMENTS_API_URL=http://<payments-ip>:8081 \
   ORCHESTRATOR_ID=<your-id> \
   ORCHESTRATOR_ADDRESS=<your-wallet> \
   python3 scripts/register_orchestrator.py
   ```
7. Verify:
   - Signaling health: `curl http://<PUBLIC_IP>:8080/healthz`
   - Runner health: `curl http://<PUBLIC_IP>:9877/health`
   - Orchestrator monitor: `curl http://<PUBLIC_IP>:9090/health`
   - Registration: `curl http://<payments-ip>:8081/api/orchestrators`

**Note on images/services**

- `ghcr.io/its-define/unreal_vtuber/embody-signaling:latest` is an “app bundle” image (it runs the SignallingWebServer plus a runner and recorder-control process under `supervisord`).
- The default `docker-compose.unreal.yml` still runs `vtuber-script-runner` + `recorder-control` as separate containers because the Unreal command port binds to `127.0.0.1` inside `vtuber-unreal-game` and recordings need a mounted `/recordings` volume.
- Service images (`vtuber-script-runner`, `recorder-control`, `orchestrator-health`, `vtuber-watchdog`, `orchestrator-registration`) are published under GHCR with `:latest` and `:sha-<gitsha>` tags; set `EMBODY_SERVICE_IMAGE_TAG=sha-…` in `.env` to pin them.

### Automatic script-runner recovery

The compose stack now includes `vtuber-watchdog`, a lightweight service that
listens to Docker events for `vtuber-unreal-game`. Whenever the game container
restarts or crashes, the watchdog automatically runs
`docker compose -f docker-compose.unreal.yml up -d --force-recreate vtuber-script-runner`
so the runner always reattaches to the game’s network namespace. You can still
run the same command manually if you need to bounce the runner immediately, but
routine crashes no longer require an operator on-call.

> The watchdog uses the same Compose project name as the rest of the stack
> (`COMPOSE_PROJECT_NAME`, defaults to `unreal_vtuber`). If you override the
> project name when deploying, Compose automatically propagates it to the
> watchdog container so it recreates the correct runner.

### Sleep / wake control

The orchestrator health service on port **9090** now exposes a small power API
so you can intentionally stop/start the Unreal game without the watchdog
undoing it. The state is persisted at `/var/lib/vtuber/power-state/power_state.json`
and shared with the watchdog so it skips recovery while sleeping.

- Check state: `curl http://<PUBLIC_IP>:9090/power`
- Sleep: `curl -X POST -H "Content-Type: application/json" -d '{"action":"sleep","reason":"maintenance"}' http://<PUBLIC_IP>:9090/power`
- Wake: `curl -X POST -H "Content-Type: application/json" -d '{"action":"wake"}' http://<PUBLIC_IP>:9090/power`

Notes:
- Access is limited by source IP (`POWER_ALLOWED_IPS`, comma-separated). Default is
  the forwarder IP `3.150.172.153`; update the env var if your forwarder changes.
- Sleep writes state first, then stops the game (and stops the runner if
  `POWER_STOP_RUNNER_ON_SLEEP` is left at its default). The watchdog ignores game
  events while the state is `sleeping`.
- Wake flips state to `awake`, starts the game, waits for it to be running, and
  restarts the runner to reattach to the game namespace. The watchdog resumes normal
  enforcement once awake.

### Automatic image updates

`vtuber-auto-updater` (backed by [containrrr/watchtower](https://containrrr.dev/watchtower/))
watches `vtuber-unreal-game`, `vtuber-unreal-signaling`, `vtuber-turn-server`, plus the
service containers (runner/recorder/health/watchdog). Every
`WATCHTOWER_INTERVAL` seconds (defaults to 900/15 minutes) it pulls the latest `:latest`
tags and issues `docker compose … up -d --force-recreate` so the refreshed containers come
up with the new images. Customize the cadence by exporting `WATCHTOWER_INTERVAL=<seconds>`
before running `docker compose up -d`. If you need to pause auto-updates entirely, stop
`vtuber-auto-updater` with `docker compose -f docker-compose.unreal.yml stop vtuber-auto-updater`.

**If you use encrypted game image distribution:** watchtower should not manage `vtuber-unreal-game`,
otherwise it will try to pull the game image from the registry. Either stop the auto-updater, or
remove `vtuber-unreal-game` from the watchtower container list in `docker-compose.unreal.yml`.

## Documentation

The `docs/` directory continues to cover onboarding, AWS automation, and
operations. Each guide now notes that the payments services are maintained in
a standalone repository; consult that project for compose files, environment
variables, and data layout.

## Upgrade / migrate from an older release

Repo and container images are public now—no GitHub auth or PAT needed to update.

1. **Pull the latest codebase**
   ```bash
   cd /home/ubuntu/Unreal_Vtuber
   git fetch origin
   git pull origin main         # or checkout the release tag/branch
   ```
2. **Make sure allowlists match the new deployment**
   - Repeat the firewall steps from “New deployment” so the forwarder and payments backend can still reach the host.
   - If the orchestrator’s public IP changed, refresh the allowlist and update `.env` (`PUBLIC_IP`, `ORCHESTRATOR_HEALTH_URL`).
3. **Refresh container images**  
   ```bash
   docker compose -f docker-compose.unreal.yml pull
   ```
4. **Regenerate TURN credentials and restart the stack**  
   ```bash
   ./scripts/generate_turn_credentials.sh
   docker compose -f docker-compose.unreal.yml down
   docker compose -f docker-compose.unreal.yml up -d
   ```
5. **(One-time) ensure helper services exist**
   ```bash
   docker compose -f docker-compose.unreal.yml up -d vtuber-watchdog vtuber-auto-updater
   ```
6. **Validate traffic + health**
    - Pixel UI: `http://<PUBLIC_IP>:8080`
    - Runner: `curl http://<PUBLIC_IP>:9877/health`

## License and allowed use

The Unreal VTuber Pixel Streaming stack, including the packaged Unreal game
container and pixel streaming containers, is proprietary to **Atumera LLC** and
licensed for use only by authorized orchestrators under Atumera’s terms.

- You may not reverse engineer, decompile, redistribute, or repurpose the game
  or pixel streaming containers outside of the orchestrator context Atumera
  authorizes.
- Use of the stack is governed by `legal/UNREAL_VTUBER_EULA.md` in this
  repository, in addition to any third‑party licenses that apply to Unreal
  Engine, Epic’s Pixel Streaming tooling, and other dependencies.
