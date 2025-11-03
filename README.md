# Unreal VTuber Pixel Streaming Stack

This repository now hosts the Unreal Engine Pixel Streaming runtime plus the
launcher scripts used to operate an orchestrator host. The Python payments
backend that previously lived in `backend/` was extracted to its own project so
it can be deployed and iterated on independently of the Unreal stack.

## Payments backend moved

- Clone the backend from `Embody-Inc/payments-backend` when payouts are needed.
- Run its Docker Compose stack separately (typically on a non-GPU host) and
  expose the API on a reachable address or join it to the shared
  `vtuber_network`.
- Set `PAYMENTS_API_URL`, `ORCHESTRATOR_ID`, and `ORCHESTRATOR_ADDRESS` in
  `.env` here so the orchestrator registration helper can contact the backend.

## Contents

- `docker-compose.unreal.yml` – TURN, signaling, packaged Unreal container, script runner, and orchestrator registration helper.
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
   Our test environment runs on AWS g5.xlarge: NVIDIA A10G (24 GB VRAM, ~158 TFLOPS FP16, 150 W TDP), 4 vCPUs, 16 GB RAM. Any GPU with comparable specs should deliver similar Pixel Streaming quality.
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
   ```
4. Open the firewall so the forwarder, your workstation, and the payments backend can reach this host.

   | Traffic source                     | Ports (TCP)                   | Ports (UDP)               |
   | --------------------------------- | ------------------------------ | ------------------------- |
   | Forwarder / client (3.150.172.153)| 8080, 8888, 8889, 9876, 9877   | 3478, 49160‑49200        |
   | Payments backend (set to your host)| 9090                          | –                        |

   **Example (UFW)**
   ```bash
   CLIENT_IP=3.150.172.153          # Forwarder public IP
   DIRECT_VIEWER_IP=86.106.138.188  # Optional: operator workstation
   PAYMENTS_IP=<payments-backend-ip>

   for PORT in 8080 8888 8889 9876 9877; do
     sudo ufw allow from $CLIENT_IP to any port $PORT proto tcp
   done
   sudo ufw allow from $CLIENT_IP to any port 3478 proto udp
   sudo ufw allow from $CLIENT_IP to any port 49160:49200 proto udp

   if [ -n "$DIRECT_VIEWER_IP" ]; then
     for PORT in 8080 8888 8889 9876 9877; do
       sudo ufw allow from $DIRECT_VIEWER_IP to any port $PORT proto tcp
     done
     sudo ufw allow from $DIRECT_VIEWER_IP to any port 3478 proto udp
     sudo ufw allow from $DIRECT_VIEWER_IP to any port 49160:49200 proto udp
   fi

   sudo ufw allow from $PAYMENTS_IP    to any port 9090 proto tcp
   sudo ufw reload
   ```
5. Launch the Pixel Streaming stack:
   ```bash
   docker network create vtuber_network 2>/dev/null || true
   docker compose -f docker-compose.unreal.yml up -d
   ```
6. Start the payments backend from the `Embody-Inc/payments-backend` repo (or
   point `PAYMENTS_API_URL` at an existing deployment).
7. Register with the payments backend (retries until it succeeds):
   ```bash
   PAYMENTS_API_URL=http://<payments-ip>:8081 \
   ORCHESTRATOR_ID=<your-id> \
   ORCHESTRATOR_ADDRESS=<your-wallet> \
   python3 scripts/register_orchestrator.py
   ```
8. Verify:
   - Pixel Streaming UI: `http://<PUBLIC_IP>:8080`
   - Runner health: `curl http://<PUBLIC_IP>:9877/health`
   - Registration: `curl http://<payments-ip>:8081/api/orchestrators`

## Upgrade from previous release

1. Update the repo:
   ```bash
   cd /home/ubuntu/Unreal_Vtuber
   git fetch origin
   git pull origin main         # or checkout the release tag/branch
   ```
2. Refresh containers: `docker compose -f docker-compose.unreal.yml pull`
   (or `build`) to pick up the latest signaling image.
3. Restart Unreal stack: `docker compose -f docker-compose.unreal.yml up -d unreal-signaling unreal-game vtuber-turn-server`.
4. Recreate the script runner (required after every game restart so it shares the network namespace):
   ```bash
   docker compose -f docker-compose.unreal.yml up -d --force-recreate vtuber-script-runner
   ```
5. Sanity check: ensure the UI loads (`:8080`), runner health responds (`:9877/health`), and payments registration still passes.
6. Update the standalone backend repo separately so payouts keep flowing with the latest code.

## Documentation

The `docs/` directory continues to cover onboarding, AWS automation, and
operations. Each guide now includes a reminder that the payments services are
maintained in `Embody-Inc/payments-backend`; consult that project for compose
files, environment variables, and data layout.
