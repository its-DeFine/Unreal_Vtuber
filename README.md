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

✅ **Step 1 — Run the onboarding wizard:**
```bash
git clone https://github.com/its-DeFine/Unreal_Vtuber.git && cd Unreal_Vtuber && sudo ./scripts/embody_cli.sh
```

✅ **Step 2 — Verify everything works (recommended):**
```bash
./scripts/embody_cli.sh verify --fix
```

✅ **Step 3 — Save GPU when idle (recommended):**
```bash
./scripts/embody_cli.sh power sleep
```

Tip: running `sudo ./scripts/embody_cli.sh` with no args will:
- run onboarding (`setup`) if you haven’t configured the host yet, otherwise
- open the interactive dashboard menu (it does not auto-run tests or auto-sleep).

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

Recommended: pin to a release tag (avoids “main drift”; CLI auto-update is skipped when pinned to a tag):
```bash
git fetch --tags
git checkout v1.3.1-beta.4
sudo ./scripts/embody_cli.sh
```

If you also want the **service containers** pinned to the same release, set `EMBODY_SERVICE_IMAGE_TAG=v1.3.1-beta.4` in `.env` and run `sudo ./scripts/embody_cli.sh upgrade` once to pull/recreate services.

Day-to-day operations are also done via the CLI (no file edits needed):
- `./scripts/embody_cli.sh overview` – status dashboard (power, containers, registration)
- `./scripts/embody_cli.sh verify --fix` – health + end-to-end checks (runner TCP + record/download)
- `./scripts/embody_cli.sh power sleep|wake --ttl <seconds>` – stop/start the stack safely
- `./scripts/embody_cli.sh rollout` – update the encrypted game image (supports low-downtime stage/apply; see `docs/game-image-updates.md`)
- `./scripts/embody_cli.sh upgrade` – pull/recreate service containers (repo auto-updates on launch; recommended after updates)

Important: the Unreal game image is delivered **encrypted** (not anonymously pullable from GHCR).
If you see `denied` pulling `ghcr.io/.../embody-ue-ps:*`, run:
- `./scripts/embody_cli.sh rollout` (Payments lease → download/decrypt/load)

## Updates (what auto-updates, what doesn’t)

There are three separate “update” paths:

- **Repo (CLI scripts)**: the CLI best-effort fast-forwards to `origin/main` on launch (skipped when the repo is dirty or pinned to a tag). Opt-out: `EMBODY_CLI_NO_AUTO_UPDATE=1 ./scripts/embody_cli.sh`
- **Service containers**: `vtuber-auto-updater` (watchtower) periodically updates labeled containers (TURN/signaling/runner/recorder/health, etc.). This updates container images, not the git repo.
- **Encrypted game image**: the Unreal game image is updated via `rollout` (Payments lease → download/decrypt/load). Low-downtime stage/apply is documented in `docs/game-image-updates.md`.
- **Remote automation (no SSH)**: the `orchestrator-health` service exposes control endpoints on `:9090` (`/power`, `/meta`, `/ops/*`). Details: `docs/embody-cli.md`.

The wizard will:
- Preflight your host (and can install missing deps on Ubuntu/Debian)
- Write/update `.env`, generate `.env.turn`
- Redeem your invite code and store a license token (chmod 600)
- Fetch + decrypt + load the **encrypted** game image via a Payments lease (no artifact URLs to paste)
- Start `docker-compose.unreal.yml`, register your orchestrator, and verify registration best-effort
- Apply required inbound rules on UFW if active (best-effort; disable with `--no-apply-firewall`)
- EC2 security group auto-apply is opt-in: pass `--apply-aws-sg` (requires awscli + IAM role/creds)

Full guide: `docs/orchestrator-onboarding.md`

Edge assignment (advanced): the recommended/default setup uses control-plane mode (`EDGE_CONFIG_URL`) so the `orchestrator-edge-rotator` sidecar can manage edge assignment + allowlists. See `docs/orchestrator-onboarding.md`.

## Cluster mode (multiple avatars on one GPU host)

Cluster mode runs multiple isolated Pixel Streaming stacks on one host (one compose project per avatar) so an edge can allocate multiple concurrent sessions.
It is **optional** and is only enabled when you explicitly run `cluster ...` commands (it does not auto-start/stop on CLI launch).

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

## Auto updates (watchtower)

This stack includes `vtuber-auto-updater` (watchtower). It runs in label-enable mode and updates any container labeled:
- `com.centurylinklabs.watchtower.enable=true`

This includes both the single-instance stack and cluster-mode per-avatar containers, without touching unrelated containers on the host.

Note: this does not replace the encrypted game-image `rollout` flow; the Unreal game image is updated via `rollout` (see `docs/game-image-updates.md`).

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
- Game image updates (encrypted): `docs/game-image-updates.md`
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
