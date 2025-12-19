# Orchestrator Onboarding

This guide covers the fastest path to run an authorized Unreal VTuber orchestrator on a GPU host (EC2 or on-prem). The recommended flow is a single onboarding command that generates config, loads the encrypted game image via a Payments lease, and starts the stack.

## Requirements

- NVIDIA driver + NVIDIA Container Toolkit (the game container uses `runtime: nvidia`)
- Docker + Docker Compose plugin (or `docker-compose`)
- Outbound internet access to pull service images and reach the Payments API

Admin provides:
- Orchestrator ID (`ORCHESTRATOR_ID`) + payout wallet (`ORCHESTRATOR_ADDRESS`)
- A Payments-issued orchestrator license token
- An encrypted artifact URL (public/presigned) for the desired game build (`.tar.zst.age`)

## Quickstart (single command)

1) Store the license token on the host (recommended):
```bash
mkdir -p ~/.embody && chmod 700 ~/.embody
printf '%s' '<ORCH_TOKEN>' > ~/.embody/orch-license-token.txt
chmod 600 ~/.embody/orch-license-token.txt
```

2) Run the onboarding script (interactive wizard):
```bash
git clone https://github.com/its-DeFine/Unreal_Vtuber.git && cd Unreal_Vtuber && ./scripts/onboard_orchestrator.sh
```

Notes:
- The script writes/updates `.env` and generates `.env.turn`.
- It will prompt for the admin-provided inputs (orchestrator ID/address, token, artifact URL) and can install missing dependencies on Ubuntu/Debian.
- By default it allowlists the forwarder IP (`3.150.172.153`) for runner/recorder/power endpoints; override with `--forwarder-ip`.
- To override storage paths: `--session-dir ...` and `--recordings-dir ...`.

Non-interactive (for automation):
```bash
./scripts/onboard_orchestrator.sh --non-interactive \
  --orchestrator-id "<orchestrator-id>" \
  --orchestrator-address "0x0000000000000000000000000000000000000000" \
  --artifact-url "https://<public-or-presigned-url>" \
  --orch-token-file ~/.embody/orch-license-token.txt
```

## Firewall / ingress checklist

Ensure inbound allowlists / firewall rules are set:
- Forwarder `3.150.172.153` -> TCP `8080,8888,8889,9877` and UDP `3478,49160-49200`
- Payments backend -> TCP `9090` (health monitoring)

## Verify

- Signaling health: `curl http://127.0.0.1:8080/healthz`
- Runner health: `curl http://127.0.0.1:9877/health`
- Orchestrator health: `curl http://127.0.0.1:9090/health`

If the orchestrator doesn’t appear in Payments yet, rerun:
```bash
docker compose -f docker-compose.unreal.yml run --rm orchestrator-registration
```

## Updating (new game build)

To load a new encrypted artifact and restart the stack:
```bash
./tools/encrypted-game-image/rollout.sh \
  --payments-api-url http://<payments-ip>:8081 \
  --orch-token-file ~/.embody/orch-license-token.txt \
  --image-ref ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1 \
  --artifact-url "https://<public-or-presigned-url>"
```
