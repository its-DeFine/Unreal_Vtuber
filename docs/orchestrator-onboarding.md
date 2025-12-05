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
        - `VTUBER_TCP_HOST` – TCP command target for the Unreal game (defaults to `unreal-game`).
        - `VTUBER_ALLOWED_ADDRESSES` – optional comma-separated IPs allowed to send TCP commands.
        - `RECORDER_VIDEO_BITRATE_KBPS`, `RECORDER_AUDIO_BITRATE_KBPS`, `RECORDER_FRAME_RATE` – change encoder settings for transcode mode.
        - `RECORDER_SIGNALLING_URL`, `RECORDER_STREAMER_ID`, `RECORDER_MODE`, `RECORDER_RAW_REMUX_COMMAND` – overrides used when you invoke the recorder script manually.
        - `RECORDER_ANSWER_START_BITRATE_KBPS`, `RECORDER_ANSWER_MAX_BITRATE_KBPS` – tweak the SDP bitrate hints advertised to the streamer.
        - `RECORDER_ENCODER_MIN_QP`, `RECORDER_ENCODER_MAX_QP`, `RECORDER_ENCODER_MIN_BITRATE`, `RECORDER_ENCODER_TARGET_BITRATE`, `RECORDER_ENCODER_MAX_BITRATE` – values pushed via the data channel to clamp Unreal’s encoder quality.
        - `RECORDER_WEBRTC_MIN_BITRATE`, `RECORDER_WEBRTC_START_BITRATE`, `RECORDER_WEBRTC_MAX_BITRATE` – WebRTC congestion-control hints (in bps) mirroring the Epic browser client.
     
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
   It also mounts `pixel-streaming/config/ConsoleVariables.ini` into the Unreal
   container so high-quality Pixel Streaming CVars are applied at boot. Adjust
   that file if you need different defaults.
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
- For cloud-hosted orchestrators, follow the AWS onboarding guide in
  `docs/aws-onboarding.md` (launch GPU instance, install Docker/NVIDIA, then run
  the same compose stack with your `.env` settings).
