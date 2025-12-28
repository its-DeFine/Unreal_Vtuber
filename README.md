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

Day-to-day operations are also done via the CLI (no file edits needed):
- `./scripts/embody_cli.sh overview` – status dashboard (power, containers, registration)
- `./scripts/embody_cli.sh verify --fix` – health + end-to-end checks (runner TCP + record/download)
- `./scripts/embody_cli.sh power sleep|wake --ttl <seconds>` – stop/start the stack safely
- `./scripts/embody_cli.sh update` – fast-forward this repo to latest `origin/main`

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
