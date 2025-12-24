# Orchestrator Onboarding

This guide covers the fastest path to run an authorized Unreal VTuber orchestrator on a GPU host (EC2 or on-prem). The recommended flow is a single onboarding command that generates config, loads the encrypted game image via a Payments lease, and starts the stack.

## Requirements

- NVIDIA driver + NVIDIA Container Toolkit (the game container uses `runtime: nvidia`)
- Docker + Docker Compose plugin (or `docker-compose`)
- Outbound internet access to pull service images and reach the Payments API

Orchestrator provides:
- Choose a unique Orchestrator ID (`ORCHESTRATOR_ID`)
- Payout wallet (`ORCHESTRATOR_ADDRESS`)

Admin provides:
- A one-time invite code (recommended; bound to the payout wallet)

## Quickstart (single command)

Run the onboarding script (interactive wizard):
```bash
git clone https://github.com/its-DeFine/Unreal_Vtuber.git && cd Unreal_Vtuber && sudo ./scripts/embody_cli.sh
```

Notes:
- The script writes/updates `.env` and generates `.env.turn`.
- It will prompt for the required inputs (choose a unique orchestrator ID + payout wallet, then paste your invite code) and can install missing dependencies on Ubuntu/Debian (Docker, NVIDIA driver, NVIDIA container toolkit).
- On multi-GPU hosts, it will offer to pin Unreal to a specific GPU via `NVIDIA_VISIBLE_DEVICES` (you can also pass `--gpu-devices 0`).
- The wizard redeems the invite code, stores a license token (chmod 600), then requests a Payments lease which includes a fresh download URL for the encrypted build.
- It allowlists the primary Embody edge/gateway IP you provide (pass `--edge-ip`, or `--forwarder-ip` for backwards compatibility).
- TURN will advertise `--edge-ip` as `TURN_EXTERNAL_IP` (needed when the orchestrator is behind an edge/gateway DNAT).
- If you have multiple edge/gateway IPs, add them with `--allowed-ip <ip>` (repeatable) or `--allowed-ips <csv>`.
- Optional: enable automatic edge routing by passing `--edge-config-url <url>` (and optionally `--edge-config-token <tok>`). In Embody-managed environments, these values may be auto-provided during invite-code redemption or via `EMBODY_EDGE_CONFIG_URL_DEFAULT`. This config is used by the `orchestrator-edge-rotator` sidecar.
- To override storage paths: `--session-dir ...` and `--recordings-dir ...`.
- For plain output: set `NO_COLOR=1` or pass `--no-color` (and `--no-fx` to disable transitions).
- If you don’t have an invite code yet, abort and request one from your admin.

Tip:
- `sudo ./scripts/embody_cli.sh` runs `verify` automatically before showing the day-to-day menu (disable with `EMBODY_CLI_AUTO_VERIFY=0`).

Non-interactive (for automation):
```bash
sudo ./scripts/embody_cli.sh setup --non-interactive \
  --orchestrator-id "<orchestrator-id>" \
  --orchestrator-address "0x1111111111111111111111111111111111111111" \
  --invite-code "ABCD-EFGH-IJKL-MNOP-QRST"
```

## Firewall / ingress checklist

Ensure inbound allowlists / firewall rules are set:
- Your edge/gateway IP -> TCP `8080,8888,8889,9877` and UDP `3478,49160-49200`
- Payments backend -> TCP `9090` (health monitoring)

The onboarding wizard will apply these rules to UFW (best-effort) if UFW is active on the host. Disable with `--no-apply-firewall`.

On EC2, security group auto-apply is opt-in: pass `--apply-aws-sg` (requires `aws` CLI + permissions via instance profile/IAM role/credentials).

### Optional: automate edge rotation (no SSH / no AWS SG edits)
If your orchestrator host uses UFW/host firewall allowlists, enable the `orchestrator-edge-rotator` sidecar to:
- Poll a control plane for the desired edge assignment
- Update host firewall allowlists (via `iptables`)
- Rewrite `.env` `SIGNALING_MATCHMAKER_ARGS=...` and recreate signaling so it re-registers on the chosen edge

Minimum `.env`:
- `EDGE_CONFIG_URL=https://<control-plane>/orchestrator-edge`
- `EDGE_FIREWALL_EXTRA_CIDRS=<payments-ip>/32` (so Payments can still reach `:9090/health`)

## Verify

- Recommended (one command):
  ```bash
  sudo ./scripts/embody_cli.sh verify
  ```

- If it finds issues, run the auto-fix pass (restarts exited services and can enable edge routing):
  ```bash
  sudo ./scripts/embody_cli.sh verify --fix
  ```

- Signaling health: `curl http://127.0.0.1:8080/healthz`
- Runner health: `curl http://127.0.0.1:9877/health`
- Orchestrator health: `curl http://127.0.0.1:9090/health`

If the orchestrator doesn’t appear in Payments yet, rerun:
```bash
sudo ./scripts/embody_cli.sh register
```

## Post-onboarding verification (multi-edge)

In the current multi-edge setup, user traffic hits a regional **edge** (running `ps-gateway` + matchmaker + TURN DNAT),
and the edge routes/proxies to your **orchestrator** (this host).

Quick diagram:
```
browser/app.embody.zone -> edge-<id>.app.embody.zone (ps-gateway + matchmaker + TURN)
                           -> orchestrator (signaling + game + runner + recorder)
```

### 1) Verify TURN advertises the edge IP (DNAT)

On the orchestrator host:
```bash
grep -E '^(TURN_EXTERNAL_IP|TURN_SERVER)=' .env.turn
```

Expected:
- `TURN_EXTERNAL_IP=<EDGE_IP>`
- `TURN_SERVER=<EDGE_IP>:3478`

### 2) Verify the orchestrator is registered on the intended edge matchmaker

From anywhere with network access (including this host), check the edge status:
```bash
curl -fsS https://edge-<id>.app.embody.zone/api/status | jq
```

Look for your orchestrator address in `.servers[]` with `ready: true`.

If your orchestrator is missing:
- Ensure your signaling server is configured to register with the edge matchmaker:
  - In `.env` set:
    - `SIGNALING_MATCHMAKER_ARGS="--use_matchmaker --matchmaker_address <EDGE_IP> --matchmaker_port 8889"`
  - Restart: `docker compose -f docker-compose.unreal.yml up -d unreal-signaling`
- Check signaling logs for matchmaker connectivity:
  - `docker logs vtuber-unreal-signaling --tail 200 | grep -E "Matchmaker|Connected|register" || true`
- Confirm outbound TCP to the edge matchmaker port from the orchestrator host:
  - `nc -vz <EDGE_IP> 8889` (or `telnet <EDGE_IP> 8889`)

### 3) End-to-end allocation smoke test (admin)

Once the edge shows your orchestrator as `ready`, an admin can allocate a session via the front door and confirm it lands
on the same edge. See the ops runbook in the `infra-gating` repo for “allocate → run → record → download”.

## Updating (new game build)

To load a new encrypted artifact and restart the stack:
```bash
./tools/encrypted-game-image/rollout.sh \
  --payments-api-url http://<payments-ip>:8081 \
  --orch-token-file ~/.embody/orch-license-token.txt \
  --image-ref ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1
```
