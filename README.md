# Unreal VTuber Orchestrator (Pixel Streaming)

Run Embody/Atumera’s packaged Unreal Engine Pixel Streaming avatar on your own GPU host as an **authorized orchestrator**.

This repo contains the runtime Compose stack (TURN, signaling, game container, script-runner, recorder control, health/registration) plus a one-command onboarding wizard that gets a fresh machine online fast.

## Quickstart (one command)

You’ll need:
- From your admin: a **one-time invite code** (recommended) *or* an **orchestrator license token**, plus an **encrypted artifact URL** (`.tar.zst.age`)
- From you: a **unique orchestrator ID** + a **payout wallet address** (`0x…`)
- A GPU host with NVIDIA driver + Docker (Ubuntu 22.04 recommended)

1) If you were given a license token, save it on the host (recommended):
```bash
mkdir -p ~/.embody && chmod 700 ~/.embody
printf '%s' '<ORCH_LICENSE_TOKEN>' > ~/.embody/orch-license-token.txt
chmod 600 ~/.embody/orch-license-token.txt
```

2) Run the onboarding wizard:
```bash
git clone https://github.com/its-DeFine/Unreal_Vtuber.git && cd Unreal_Vtuber && ./scripts/onboard_orchestrator.sh
```

If you were given an invite code, the wizard will redeem it and store a license token for you.

The wizard will:
- Preflight your host (and can install missing deps on Ubuntu/Debian)
- Write/update `.env`, generate `.env.turn`
- Fetch + decrypt + load the **encrypted** game image via a Payments lease (no GHCR creds needed)
- Start `docker-compose.unreal.yml`, register your orchestrator, and verify registration best-effort
- Try to apply required inbound rules on EC2 best-effort (disable with `--no-apply-firewall`)

Full guide: `docs/orchestrator-onboarding.md`

## What’s inside

- `docker-compose.unreal.yml` – the Pixel Streaming + orchestration stack
- `scripts/onboard_orchestrator.sh` – one-command onboarding wizard
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
