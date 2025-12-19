# Unreal VTuber Pixel Streaming Stack

**Note:** This repo is under active development. Authorized orchestrators can deploy by following the quickstart below.

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

This repo assumes **encrypted game image distribution** (required):
- The proprietary **game** image is loaded from an encrypted artifact (ex: S3) via a Payments-issued lease.
- Orchestrators do **not** pull the game image from GHCR.
- The non-game service images (signaling/runner/recorder/etc.) can remain on GHCR and should be public.

### Admin setup (one-time)

Before an orchestrator can deploy, an admin/operator must:

1. Generate an `age` keypair (store the private identity securely; never commit it):
   ```bash
   age-keygen -o embody-ue-ps-enc-v1.agekey
   age-keygen -y embody-ue-ps-enc-v1.agekey    # prints the public recipient (age1...)
   ```
2. Register the decryption secret in Payments and grant orchestrator access:
   ```bash
   PAYMENTS_API_URL="http://<payments-ip>:8081"
   PAYMENTS_ADMIN_TOKEN="..." # X-Admin-Token
   IMAGE_REF="ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1"

   SECRET_B64="$(python3 - <<'PY'
import base64, pathlib
print(base64.b64encode(pathlib.Path("embody-ue-ps-enc-v1.agekey").read_bytes()).decode("ascii"))
PY
   )"

   # 1) Upsert image secret
   curl -sS -X PUT \
     -H "X-Admin-Token: $PAYMENTS_ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"image_ref\":\"$IMAGE_REF\",\"secret_b64\":\"$SECRET_B64\"}" \
     "$PAYMENTS_API_URL/api/licenses/images"

   # 2) Mint orchestrator token
   ORCH_ID="<orchestrator-id>"
   curl -sS -X POST \
     -H "X-Admin-Token: $PAYMENTS_ADMIN_TOKEN" \
     "$PAYMENTS_API_URL/api/licenses/orchestrators/$ORCH_ID/tokens"

   # 3) Grant access
   curl -sS -X POST \
     -H "X-Admin-Token: $PAYMENTS_ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"orchestrator_id\":\"$ORCH_ID\",\"image_ref\":\"$IMAGE_REF\"}" \
     "$PAYMENTS_API_URL/api/licenses/access/grant"
   ```
3. Publish encrypted artifacts (per game build):
   ```bash
   # On a trusted build machine with the game image available locally:
   ./tools/encrypted-game-image/produce.sh \
     --image ghcr.io/its-define/unreal_vtuber/embody-ue-ps:latest \
     --recipient "age1..." \
     --out /tmp/embody-ue-ps.tar.zst.age

   # Upload the artifact to S3 and produce a URL (public or presigned).
   # The orchestrator will receive that URL as --artifact-url.
   ```

### Orchestrator setup (one command)

Prereqs (admin provides):
- A Payments-issued orchestrator **license token**
- An encrypted artifact URL (public/presigned) for the desired game build

Store the license token on the host (recommended):
```bash
mkdir -p ~/.embody && chmod 700 ~/.embody
printf '%s' '<ORCH_TOKEN>' > ~/.embody/orch-license-token.txt
chmod 600 ~/.embody/orch-license-token.txt
```

One-liner (recommended, interactive wizard):
```bash
git clone https://github.com/its-DeFine/Unreal_Vtuber.git && cd Unreal_Vtuber && ./scripts/onboard_orchestrator.sh
```
The wizard will prompt you for the required inputs (choose a unique orchestrator ID + payout wallet, plus the admin-provided token + artifact URL) and can install missing dependencies on Ubuntu/Debian (Docker, NVIDIA driver, NVIDIA container toolkit). Optional settings (Payments URL, forwarder IP, host paths) default from `orchestrator.env.example`; run with `--advanced` to override them interactively.
For plain output: set `NO_COLOR=1` or pass `--no-color` (and `--no-fx` to disable transitions). If you don’t have the token/artifact yet, use `--config-only` and rerun later to load the encrypted build.

Non-interactive (for automation):
```bash
./scripts/onboard_orchestrator.sh --non-interactive \
  --orchestrator-id "<orchestrator-id>" \
  --orchestrator-address "0x1111111111111111111111111111111111111111" \
  --artifact-url "https://<public-or-presigned-url>" \
  --orch-token-file ~/.embody/orch-license-token.txt
```

The onboarding script will:
- Write/update `.env` (Payments URL, orchestrator ID/address, public IP, allowlists, storage paths).
- Generate `.env.turn` (TURN credentials).
- Load the encrypted game image via a Payments lease and start `docker-compose.unreal.yml`.
- Run orchestrator registration (best-effort).

### Manual setup (if you prefer)

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
5. Install dependencies required to load the encrypted game image (Ubuntu example):
   ```bash
   sudo apt-get update
   sudo apt-get install -y curl jq zstd age
   ```
6. Load the encrypted game image + start the stack (includes the health monitor service).

   Prereqs:
   - A Payments-issued orchestrator **license token** file (admin provides)
   - An encrypted artifact URL (public/presigned) for the desired game build (admin provides)

   ```bash
   docker network create vtuber_network 2>/dev/null || true

   # Store the license token on the host (recommended location/permissions)
   mkdir -p ~/.embody
   chmod 700 ~/.embody
   printf '%s' '<ORCH_TOKEN>' > ~/.embody/orch-license-token.txt
   chmod 600 ~/.embody/orch-license-token.txt

   ./tools/encrypted-game-image/rollout.sh \
     --payments-api-url http://<payments-ip>:8081 \
     --orch-token-file ~/.embody/orch-license-token.txt \
     --image-ref ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1 \
     --artifact-url "https://<public-or-presigned-url>"
   ```
7. Register with the payments backend (retries until it succeeds):
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
8. Verify:
   - Signaling health: `curl http://<PUBLIC_IP>:8080/healthz`
   - Runner health: `curl http://<PUBLIC_IP>:9877/health`
   - Orchestrator monitor: `curl http://<PUBLIC_IP>:9090/health`
   - Registration: `curl http://<payments-ip>:8081/api/orchestrators`

**Note on images/services**

- `ghcr.io/its-define/unreal_vtuber/embody-signaling:latest` is an “app bundle” image (it runs the SignallingWebServer plus a runner and recorder-control process under `supervisord`).
- The compose file still references the game image as `ghcr.io/its-define/unreal_vtuber/embody-ue-ps:latest`, but under the encrypted distribution flow this is just the **local tag** created by `docker load` (the game image is not pulled from GHCR).
- The default `docker-compose.unreal.yml` still runs `vtuber-script-runner` + `recorder-control` as separate containers because the Unreal command port binds to `127.0.0.1` inside `vtuber-unreal-game` and recordings need a mounted `/recordings` volume (configured via `VTUBER_RECORDINGS_DIR`, defaults to `/recordings`).
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
updates the non-game containers (`vtuber-unreal-signaling`, `vtuber-turn-server`, plus the
service containers like runner/recorder/health/watchdog). Every
`WATCHTOWER_INTERVAL` seconds (defaults to 900/15 minutes) it pulls the latest `:latest`
tags and issues `docker compose … up -d --force-recreate` so the refreshed containers come
up with the new images. Customize the cadence by exporting `WATCHTOWER_INTERVAL=<seconds>`
before running `docker compose up -d`. If you need to pause auto-updates entirely, stop
`vtuber-auto-updater` with `docker compose -f docker-compose.unreal.yml stop vtuber-auto-updater`.

The game container (`vtuber-unreal-game`) is intentionally excluded because it is loaded via the encrypted artifact flow (not pulled from GHCR).

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
3. **Refresh non-game container images**
   ```bash
   docker compose -f docker-compose.unreal.yml pull \
     turn-server unreal-signaling \
     vtuber-script-runner recorder-control \
     orchestrator-health vtuber-watchdog vtuber-auto-updater
   ```
4. **Regenerate TURN credentials and reload the game via the encrypted artifact**
   ```bash
   ./scripts/generate_turn_credentials.sh

   ./tools/encrypted-game-image/rollout.sh \
     --payments-api-url http://<payments-ip>:8081 \
     --orch-token-file ~/.embody/orch-license-token.txt \
     --image-ref ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1 \
     --artifact-url "https://<public-or-presigned-url>"
   ```
5. **(One-time) ensure helper services exist**
   ```bash
   docker compose -f docker-compose.unreal.yml up -d vtuber-watchdog vtuber-auto-updater
   ```
6. **Validate traffic + health**
    - Signaling health: `curl http://<PUBLIC_IP>:8080/healthz`
    - Runner health: `curl http://<PUBLIC_IP>:9877/health`

> Note: the Pixel Streaming web UI is no longer bundled in the signaling image; deploy it separately (typically from an edge/gateway) and connect to signaling over WebSocket.

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
