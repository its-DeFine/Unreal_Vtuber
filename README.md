# Unreal VTuber Orchestrator (Pixel Streaming)

Run Embody’s packaged Unreal Engine Pixel Streaming avatar on your own GPU host as an **authorized orchestrator**.

This repo contains the runtime Compose stack (TURN, signaling, game container, script-runner, recorder control, health/registration) plus a one-command onboarding wizard.

Key properties:
- **Single-command onboarding** (interactive wizard)
- **Encrypted game delivery** (no registry credentials on the orchestrator)
- **Short-lived decryption leases** issued by the Payments backend
- **Best-effort firewall automation** on EC2 (optional)

## Quickstart (one command)

You’ll need:
- From your admin: a **one-time invite code** (bound to your payout wallet)
- From you: a **unique orchestrator ID** + a **payout wallet address** (`0x…`)
- A GPU host with an NVIDIA GPU (Ubuntu 22.04 recommended)

Run:
```bash
git clone https://github.com/its-DeFine/Unreal_Vtuber.git && cd Unreal_Vtuber && sudo ./scripts/embody_cli.sh
```

The wizard will:
- Preflight your host (and can install missing deps on Ubuntu/Debian)
- Write/update `.env`, generate `.env.turn`
- Redeem your invite code and store a license token (chmod 600)
- Fetch + decrypt + load the **encrypted** game image via a Payments lease (no artifact URLs to paste)
- Start `docker-compose.unreal.yml`, register your orchestrator, and verify registration best-effort
- Apply required inbound rules on UFW if active (best-effort; disable with `--no-apply-firewall`)
- EC2 security group auto-apply is opt-in: pass `--apply-aws-sg` (requires awscli + IAM role/creds)

After onboarding (or anytime), run:
```bash
sudo ./scripts/embody_cli.sh verify
```

If it finds issues, run the auto-fix pass:
```bash
sudo ./scripts/embody_cli.sh verify --fix
```

Full guide: `docs/orchestrator-onboarding.md`

Tip:
- `sudo ./scripts/embody_cli.sh` will run `verify` automatically before showing the day-to-day menu (disable with `EMBODY_CLI_AUTO_VERIFY=0`).

Multi-edge deployments:
- The edge/gateway IP you provide is used for allowlists and TURN DNAT (`TURN_EXTERNAL_IP`).
- Verify the orchestrator registers on the intended edge matchmaker after onboarding (see `docs/orchestrator-onboarding.md`).
- If needed, set matchmaker flags in `.env` (example: `SIGNALING_EXTRA_ARGS="--use_matchmaker --matchmaker_address <EDGE_HOST> --matchmaker_port 8889 --public_port 8080"`).
- To rotate edges without SSH, configure the optional `orchestrator-edge-rotator` sidecar (`docs/orchestrator-onboarding.md`).

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
- Architecture: `docs/pixel-streaming-architecture.md`
- Recorder control: `docs/recorder-control.md`
- Sleep/wake: `docs/sleep-wake.md`
- Unreal integration notes: `docs/unreal-integration.md`
- Admin (encrypted build distribution): `docs/admin-encrypted-game-image.md`

## Legal

- EULA: `legal/UNREAL_VTUBER_EULA.md`
- Terms: `legal/Terms and Conditions.pdf`
- Privacy: `legal/Privacy Policy.pdf`
