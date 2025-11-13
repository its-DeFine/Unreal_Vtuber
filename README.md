# Unreal VTuber Pixel Streaming Stack

This repository now hosts the Unreal Engine Pixel Streaming runtime plus the
launcher scripts used to operate an orchestrator host. The registration helper
still talks to the remote payments API, but the backend itself lives in a
separate repository.

## Contents

- `docker-compose.unreal.yml` – TURN, signaling, packaged Unreal container, script runner, orchestrator registration helper, and local health monitor.
- `orchestrator-health/` – lightweight FastAPI service that exposes container health at `http://<host>:9090/health`.
- `pixel-streaming/` – Pixel Streaming configuration overrides shipped with the Unreal build.
- `scripts/` – utilities for onboarding and orchestration (`start_vtuber_unreal.sh`, `register_orchestrator.py`, etc.).
- `docs/` – deployment, integration, and operations guides (each doc now calls out where to pull the payments backend).

## New deployment

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
| Forwarder / client (3.150.172.153) | 8080, 8888, 8889, 9876, 9877 | 3478, 49160‑49200 |
| Payments backend (3.141.111.200) | 9090                          | –                |

   **Example (UFW)**
   ```bash
   CLIENT_IP=3.150.172.153          # Forwarder public IP
   PAYMENTS_IP=3.141.111.200        # Payments backend public IP

   for PORT in 8080 8888 8889 9876 9877; do
     sudo ufw allow from $CLIENT_IP to any port $PORT proto tcp
   done
   sudo ufw allow from $CLIENT_IP to any port 3478 proto udp
   sudo ufw allow from $CLIENT_IP to any port 49160:49200 proto udp

   sudo ufw allow from $PAYMENTS_IP to any port 9090 proto tcp

   sudo ufw reload
   ```
5. Launch the Pixel Streaming stack (includes the health monitor service). Double-check `.env` still contains `VTUBER_ALLOWED_ADDRESSES=3.150.172.153` before running compose:
   ```bash
   docker network create vtuber_network 2>/dev/null || true
   docker compose -f docker-compose.unreal.yml up -d
   ```
6. Register with the payments backend (retries until it succeeds):
   ```bash
   PAYMENTS_API_URL=http://<payments-ip>:8081 \
   ORCHESTRATOR_ID=<your-id> \
   ORCHESTRATOR_ADDRESS=<your-wallet> \
   python3 scripts/register_orchestrator.py
   ```
7. Verify:
   - Pixel Streaming UI: `http://<PUBLIC_IP>:8080`
   - Runner health: `curl http://<PUBLIC_IP>:9877/health`
   - Orchestrator monitor: `curl http://<PUBLIC_IP>:9090/health`
   - Registration: `curl http://<payments-ip>:8081/api/orchestrators`

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

## Upgrade / migrate from an older release

1. **Pull the latest codebase**
   ```bash
   cd /home/ubuntu/Unreal_Vtuber
   git fetch origin
   git pull origin main         # or checkout the release tag/branch
   ```
2. **Make sure allowlists match the new deployment**
   - Repeat the same firewall steps outlined in the “New deployment” section (Step 4) so the forwarder and payments backend can still reach the host, and prune any stale entries.
   - If the orchestrator’s public IP changed (new Elastic IP or subnet), refresh the allowlist in your security group and update `.env` (`PUBLIC_IP`, `ORCHESTRATOR_HEALTH_URL`) so registration advertises the correct IP.
3. **Refresh container images**
   ```bash
   docker compose -f docker-compose.unreal.yml pull
   ```
4. **Recreate TURN + Unreal + signaling services with the new images** (ensure `.env` still lists `VTUBER_ALLOWED_ADDRESSES=3.150.172.153` before restarting)
   ```bash
   docker compose -f docker-compose.unreal.yml up -d unreal-signaling unreal-game turn-server
   ```
5. **Rebuild the runner so it picks up the latest config**
   ```bash
   docker compose -f docker-compose.unreal.yml up -d --force-recreate vtuber-script-runner
   ```
6. **Validate traffic + health**
   - Pixel UI: `http://<PUBLIC_IP>:8080`
   - Runner: `curl http://<PUBLIC_IP>:9877/health`

## Documentation

The `docs/` directory continues to cover onboarding, AWS automation, and
operations. Each guide now notes that the payments services are maintained in
a standalone repository; consult that project for compose files, environment
variables, and data layout.
