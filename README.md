# Unreal VTuber Orchestrator (Pixel Streaming)

Run Embody’s packaged Unreal Engine Pixel Streaming avatar on your own GPU host as an **authorized orchestrator**.

This repo contains the runtime Compose stack (TURN, signaling, game container, script-runner, recorder control, health/registration) plus a one-command onboarding wizard.

Key properties:
- ⚡ **Single-command onboarding** (interactive wizard)
- 🔒 **Encrypted game delivery** (no registry credentials on the orchestrator)
- ⏱️ **Short-lived decryption leases** issued by the Payments backend
- 🛡️ **Best-effort firewall automation** on EC2 (optional)

## Quickstart (one command)

You’ll need:
- `From your admin: a one-time invite code (bound to your payout wallet)` — Any Livepeer orchestrator can join the program; request a code at `george@atumera.com` or via Discord (`de_fi_ne`).
- From you: a **unique orchestrator ID** + a **payout wallet address** (`0x…`)
- A GPU host with an NVIDIA GPU (**at least 16GB VRAM required**) (Ubuntu 22.04 recommended)

Run:
```bash
git clone https://github.com/its-DeFine/Unreal_Vtuber.git && cd Unreal_Vtuber && sudo ./scripts/embody_cli.sh
```

Non-interactive (no prompts; useful for automation). Provide **all** required values:
```bash
sudo ./scripts/embody_cli.sh setup --non-interactive \
  --orchestrator-id "<orchestrator-id>" \
  --orchestrator-address "0x1111111111111111111111111111111111111111" \
  --invite-code "<ONE_TIME_INVITE_CODE>"
```

Tip: you can also omit `setup` — any `--flag` runs onboarding:
```bash
sudo ./scripts/embody_cli.sh --non-interactive --orchestrator-id "<id>" --orchestrator-address "0x..." --invite-code "<code>"
```

Recommended: pin to a release tag (avoids “main drift” and guarantees service images match the CLI version):
```bash
git fetch --tags
git checkout v1.3.1-beta.4
sudo ./scripts/embody_cli.sh
```

Day-to-day operations are also done via the CLI (no file edits needed):
- `./scripts/embody_cli.sh overview` – status dashboard (power, containers, registration)
- `./scripts/embody_cli.sh verify --fix` – health + end-to-end checks (runner TCP + record/download)
- `./scripts/embody_cli.sh power sleep|wake --ttl <seconds>` – stop/start the stack safely
- `./scripts/embody_cli.sh rollout --stage` – prefetch the next encrypted game image **without** stopping a live stack (writes “pending rollout” state)
- `./scripts/embody_cli.sh rollout --apply-staged` – apply a staged rollout during an idle window (after sleep, switches the next wake to the staged image)
- `./scripts/embody_cli.sh upgrade` – pull/recreate service containers (repo auto-updates on launch; recommended after updates)

Important: the Unreal game image is delivered **encrypted** (not anonymously pullable from GHCR).
If you see `denied` pulling `ghcr.io/.../embody-ue-ps:*`, run:
- `./scripts/embody_cli.sh rollout` (Payments lease → download/decrypt/load)

To reduce downtime for game image updates:
```bash
# 1) While users are live (no restart):
sudo ./scripts/embody_cli.sh rollout --stage

# 2) During an idle window:
sudo ./scripts/embody_cli.sh power sleep
sudo ./scripts/embody_cli.sh rollout --apply-staged
sudo ./scripts/embody_cli.sh power wake --ttl 3600
```

The wizard will:
- Preflight your host (and can install missing deps on Ubuntu/Debian)
- Write/update `.env`, generate `.env.turn`
- Redeem your invite code and store a license token (chmod 600)
- Fetch + decrypt + load the **encrypted** game image via a Payments lease (no artifact URLs to paste)
- Start `docker-compose.unreal.yml`, register your orchestrator, and verify registration best-effort
- Apply required inbound rules on UFW if active (best-effort; disable with `--no-apply-firewall`)
- EC2 security group auto-apply is opt-in: pass `--apply-aws-sg` (requires awscli + IAM role/creds)

Full guide: `docs/orchestrator-onboarding.md`

Multi-edge deployments:
- Manual mode: the edge/gateway IP you provide is used for allowlists and TURN DNAT (`TURN_EXTERNAL_IP`).
- Verify the orchestrator registers on the intended edge matchmaker after onboarding (see `docs/orchestrator-onboarding.md`).
- If needed, set `SIGNALING_MATCHMAKER_ARGS` in `.env` (example: `--use_matchmaker --matchmaker_address <EDGE_IP> --matchmaker_port 8889`).
- To rotate edges without SSH (recommended), enable control-plane mode (`EDGE_CONFIG_URL`) so the included `orchestrator-edge-rotator` sidecar can manage edge assignment (`docs/orchestrator-onboarding.md`).

## Cluster mode (multiple avatars on one GPU host)

Cluster mode runs multiple isolated Pixel Streaming stacks on one host (one compose project per avatar) so an edge can allocate multiple concurrent sessions.

One-command deploy (auto-configures based on GPU VRAM, then launches all instances):
```bash
sudo ./scripts/embody_cli.sh cluster deploy --auto --yes --pull missing
```

Cap the number of instances:
```bash
sudo ./scripts/embody_cli.sh cluster deploy --auto --yes --max-instances 12 --pull missing
```

Garbage collect stopped cluster projects (ex: after experiments):
```bash
sudo ./scripts/embody_cli.sh cluster gc --dry-run
sudo ./scripts/embody_cli.sh cluster gc --yes
```

Optional: lower per-instance GPU load (helps smaller GPUs run >1 instance):
- Set these env vars (shell or `.env`), then recreate the game containers.
```bash
# Balanced preset (720p @ 30fps):
export VTUBER_CONSOLE_VARIABLES_FILE=./pixel-streaming/config/ConsoleVariables.lowload.30fps.720p.ini
export VTUBER_GAME_USER_SETTINGS_FILE=./pixel-streaming/config/GameUserSettings.lowload.30fps.720p.ini
export EMBODY_EXTRA_ARGS="-ForceRes -ResX=1280 -ResY=720 -PixelStreamingAllowCodecNames=H264 -PixelStreamingDisableVP8 -PixelStreamingDisableVP9"

# To reduce render load further (tradeoff: blurrier video), keep the same preset but lower the stream resolution:
# - 480p:  -ResX=854  -ResY=480
# - 360p:  -ResX=640  -ResY=360
# - 240p:  -ResX=426  -ResY=240

# Ultra preset (720p @ 20fps, aggressive scalability cuts):
export VTUBER_CONSOLE_VARIABLES_FILE=./pixel-streaming/config/ConsoleVariables.lowload.20fps.720p.ini
export VTUBER_GAME_USER_SETTINGS_FILE=./pixel-streaming/config/GameUserSettings.lowload.20fps.720p.ini
export EMBODY_EXTRA_ARGS="-ForceRes -ResX=1280 -ResY=720 -PixelStreamingAllowCodecNames=H264 -PixelStreamingDisableVP8 -PixelStreamingDisableVP9"
```

## Per-avatar sleep/wake (cluster mode)

In cluster mode, each avatar is its own compose project (example: `vtuber-embody-0`). You can sleep/wake a single avatar locally:
```bash
./scripts/embody_cli.sh power sleep --project vtuber-embody-0
./scripts/embody_cli.sh power wake --ttl 3600 --project vtuber-embody-0
```

Remote automation (ex: Payments) can call:
- `POST http://<host>:9090/power/projects/<compose_project>`

Experimental remote spawn/delete (cluster instances):
- Enabled by default for new installs (in `orchestrator.env.example`). To disable: set `EXPERIMENTAL_REMOTE_CLUSTER_CONTROL=0` in `.env` and recreate `orchestrator-health`.
- `POST http://<host>:9090/cluster/deploy` with JSON `{ "avatar_id": "embody-0", "slot": 0, "gpu": "0" }`
- `POST http://<host>:9090/cluster/down` with JSON `{ "avatar_id": "embody-0" }` (or `{ "project": "vtuber-embody-0" }`)

Remote metadata + ops (experimental):
- `GET http://<host>:9090/meta` (git head + container image refs/ids, plus last `verify` + pending rollout state).
- Disabled by default. Enable with `./scripts/embody_cli.sh remote-updates enable` (or set `EXPERIMENTAL_REMOTE_OPS=1` in `.env`) and recreate `orchestrator-health`.
- Security: `/ops/*` always requires `POWER_ALLOWED_IPS` / `POWER_ALLOWED_IPS_FILE` allowlisting (otherwise returns 403).
- `POST http://<host>:9090/ops/upgrade` with JSON `{ "apply": true }` (git ff-only update; optionally pull/recreate host-level containers).
- `POST http://<host>:9090/ops/rollout`:
  - Stage only (prefetch while live): `{ "payments_api_url": "http://<payments>:8081", "image_ref": "ghcr.io/...:enc-v1", "stage_only": true, "min_free_gb": 15 }`
  - Apply staged (idle window): `{ "image_ref": "ghcr.io/...:enc-v1", "skip_download": true, "recreate_stopped": true }`
- `POST http://<host>:9090/ops/pull-image` with JSON `{ "image": "ghcr.io/<org>/<image>:<tag>" }` (unencrypted image pull; follow by redeploy/recreate).

## Auto updates (watchtower)

This stack includes `vtuber-auto-updater` (watchtower). It runs in label-enable mode and updates any container labeled:
- `com.centurylinklabs.watchtower.enable=true`

This includes both the single-instance stack and cluster-mode per-avatar containers, without touching unrelated containers on the host.

## Security / allowlists

This stack protects control endpoints (runner, recorder-control, power) with strict allowlists.

Default allowlisted IPs depend on setup mode:
- Always allow local access: `127.0.0.1`, `::1`, docker bridge gateways (`172.17.0.1`, `172.18.0.1`)
- Control-plane mode (`EDGE_CONFIG_URL` set): allowlists are managed by the `orchestrator-edge-rotator` sidecar
  - Assigned edge CIDRs/IPs are allowed automatically
  - If `PAYMENTS_API_URL` is an IPv4, `setup` also allowlists the Payments host so it can run remote jobs without SSH:
    - Host firewall ports: `EDGE_FIREWALL_EXTRA_CIDRS=<payments-ip>/32`
    - Power API: `EDGE_POWER_EXTRA_CIDRS=<payments-ip>/32`
    - Runner/recorder: `EDGE_LOCAL_ALLOWLIST=...,<payments-ip>`
- Manual mode: `VTUBER_ALLOWED_ADDRESSES` is written from your `--edge-ip` (plus any `--allowed-ip`) and also includes the Payments IPv4 host when available

## What’s inside

- `docker-compose.unreal.yml` – the Pixel Streaming + orchestration stack
- `scripts/embody_cli.sh` – onboarding + day-to-day CLI entrypoint
- `scripts/onboard_orchestrator.sh` – deprecated alias for onboarding (calls `embody_cli.sh setup`)
- `tools/encrypted-game-image/` – encrypted artifact consume/rollout helpers
- `orchestrator-health/` – host-visible health endpoint (`http://<host>:9090/health`)
- `docs/` – architecture + operational guides

## Orchestrator incentives program

Authorized orchestrators may be eligible for payouts based on program rules (uptime/usage/other factors). During onboarding you set `ORCHESTRATOR_ADDRESS` (your payout wallet) and the stack registers + reports health to the Payments backend, which tracks eligibility and payout scheduling.

Program terms, eligibility, and payout rules are governed by the legal docs below and any agreement you have with the administrator running the program.

## Docs

- Orchestrator onboarding: `docs/orchestrator-onboarding.md`
- CLI reference: `docs/embody-cli.md`
- Architecture: `docs/pixel-streaming-architecture.md`
- Recorder control: `docs/recorder-control.md`
- Staging environment: `docs/staging.md`
- Sleep/wake: `docs/sleep-wake.md`
- Unreal integration notes: `docs/unreal-integration.md`
- Admin (encrypted build distribution): `docs/admin-encrypted-game-image.md`

## Legal

- EULA: `legal/UNREAL_VTUBER_EULA.md`
- Terms: `legal/Terms and Conditions.pdf`
- Privacy: `legal/Privacy Policy.pdf`
