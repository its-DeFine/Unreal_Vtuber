# Orchestrator Onboarding (Local Workstation)

Use this guide when you want to run the Unreal VTuber orchestrator on a local
GPU machine (physical workstation or on-prem server) without provisioning any
EC2 infrastructure. By the end you will have Pixel Streaming, the TURN/signaling
stack, and the script runner talking to the remote payments backend.

---

## 1. Requirements

- **Hardware / drivers**: NVIDIA GPU with the proprietary driver installed. The
  `unreal-game` container mounts host libraries, so keep the driver up to date.
- **Software**: Docker, Docker Compose plugin, `curl`, `python3`, and `bash`.
- **Payments backend access**: Ensure you can reach the payments API (default
  `http://3.141.111.200:8081`). If the backend restricts ingress, have the admin
  allow your public IP on port 8081.
- **Public IP**: Know the public IPv4 that WebRTC clients will use (for TURN and
  signaling). You can find it with `curl https://api.ipify.org`.

---

## 2. Prepare environment files

1. Copy the orchestrator sample env into place (Compose reads `.env` by default):
   ```bash
   cd autonomy
   cp orchestrator.env.example .env
   ```
2. Edit `.env` and fill in:
    - `PAYMENTS_API_URL` – URL of the payments backend (`http://IP:8081`).
    - `ORCHESTRATOR_ID` – unique identifier for this host (e.g. `orch-local-001`).
    - `ORCHESTRATOR_ADDRESS` – payout wallet (must be in the top Livepeer set if
      rank validation is on).
    - `PUBLIC_IP` – the IPv4 you want TURN/signaling to advertise.
    - `VTUBER_SESSION_DIR` – where to persist session assets on disk.
    - Optional: `ORCHESTRATOR_CONTACT_EMAIL`, `VTUBER_ALLOWED_ADDRESSES`, etc.
    - Recorder tuning (optional):
        - `VTUBER_RECORDER_ENDPOINT` – where the script runner posts recorder start/stop events (defaults to `http://recorder-manager:9001`).
        - `VTUBER_TCP_HOST` – TCP command target for the Unreal game (defaults to `127.0.0.1`).
        - `RECORDER_CAPTURE_DIR` – host directory mounted at `/captures` inside `recorder-manager` (defaults to `/home/ubuntu/Unreal_Vtuber/captures`).
        - `RECORDER_VIDEO_BITRATE_KBPS`, `RECORDER_AUDIO_BITRATE_KBPS`, `RECORDER_FRAME_RATE` – change encoder settings for transcode mode.
        - `RECORDER_SIGNALLING_URL`, `RECORDER_STREAMER_ID`, `RECORDER_MODE`, `RECORDER_RAW_REMUX_COMMAND` – advanced overrides for the recorder service.
        - `RECORDER_STORAGE_URL`, `RECORDER_STORAGE_TOKEN`, `RECORDER_UPLOAD_ORCHESTRATOR_ID` – enable automatic uploads to the storage service.
     
   > The **dedicated client IP** is only required when you expose Pixel
   > Streaming to remote viewers. For local-only recording, skip the public
   > allowlist and access the UI via SSH tunneling instead.

3. Generate TURN credentials (creates `.env.turn` used by the TURN container):
   ```bash
   ./scripts/generate_turn_credentials.sh
   ```
   The script respects `PUBLIC_IP` from `.env`; if unset it will auto-detect.

---

## 3. Start the orchestrator stack

1. Create the shared Docker network if it doesn’t exist yet:
   ```bash
   docker network create vtuber_network 2>/dev/null || true
   ```
2. Launch the services:
   ```bash
   docker compose -f docker-compose.unreal.yml up -d
   ```
   The compose file reads `.env` and `.env.turn` automatically.
3. Check container health:
   ```bash
   docker compose -f docker-compose.unreal.yml ps
   docker compose -f docker-compose.unreal.yml logs -f unreal-signaling
   ```

The `orchestrator-registration` container waits the configured
`ORCHESTRATOR_REGISTRATION_DELAY` (default 10 s) and then POSTs to the payments
backend so this host shows up in `/api/orchestrators`.

---

## 4. Verify connectivity

- **Pixel Streaming UI**: on the orchestrator, open `http://127.0.0.1:8080` (or
  forward the port over SSH) and confirm the page loads.
- **Runner API**: `curl http://127.0.0.1:9877/health` should return
  `{"status":"ok"}`.
- **Recorder manager**: `curl http://127.0.0.1:9001/health` confirms the auto
  recorder endpoint is reachable.
- **Payments backend**: `curl http://<PAYMENTS_IP>:8081/api/orchestrators`
  should list your `ORCHESTRATOR_ID` with `eligible_for_payments=true` once the
  health service reports healthy.
- **Audio/script test** (optional): from another terminal run
  ```bash
  cd autonomy/private_creator
  python3 generate_vtuber_program.py --prompt "Quick hello" --session-id local-test
  ```
  to send audio + commands to the orchestrator.
- **Firewall/ingress**: restrict inbound traffic to the orchestrator itself and
  the payments backend. External clients no longer need 8080/8888/8889 or the
  TURN relay range because captures are initiated from inside the host.

---

## 5. Updating registration

If the host’s public IP or metadata changes, rerun the registrar:
```bash
cd autonomy
PAYMENTS_API_URL=... ORCHESTRATOR_ID=... ORCHESTRATOR_ADDRESS=... \
python3 scripts/register_orchestrator.py --once
```
You can execute it on the orchestrator or from another machine (set the env vars
accordingly).

---

## 6. Maintenance & teardown

- Restart the stack with `docker compose -f docker-compose.unreal.yml restart`.
- Stop everything with `docker compose -f docker-compose.unreal.yml down`.
- Logs are stored under `/home/<user>/vtuber_sessions` (override via
  `VTUBER_SESSION_DIR` in `.env`).
- To clean the TURN credentials, delete `.env.turn` and regenerate when needed.

---

## 7. Next steps

- Review `docs/payments-deployment.md` for network port whitelists between the
  orchestrator and the payments backend.
- To provision remote AWS orchestrators instead, use
  `scripts/provision_orchestrator.py` with
  `scripts/provision_orchestrator.env.example`.
