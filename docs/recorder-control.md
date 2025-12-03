# Recorder Control Sidecar

This sidecar runs alongside the Pixel Streaming stack to control the GStreamer copy-recorder without touching the signaling container entrypoint.

## Endpoints (port 8889 inside the stack)
- `POST /recordings/start` – body: `{ label?, duration?, streamer_id? }`
  - `streamer_id` optional; defaults to first streamer if omitted.
  - Spawns `gs_webrtc_recorder.py` in the sidecar with no re-encode; output lands in `/recordings/<label>_<epoch>.mkv`.
- `POST /recordings/stop` – stops the active recorder process.
- `GET /recordings/status` – reports running/not, pid, label, streamer_id, output path.
- `GET /recordings/{filename}` – download a specific MKV.
- `DELETE /recordings/{filename}` – remove a specific MKV from `/recordings`.

## Auth
- IP allowlist: `VTUBER_ALLOWED_ADDRESSES` (or `RECORDINGS_ALLOWED_IPS`). Requests from other IPs get 403. Default includes loopback + the Docker bridge.
- Optional token: set `RECORDINGS_API_TOKEN` to require Bearer auth; leave unset to rely on IP allowlist only.

## Compose (already wired)
`docker-compose.unreal.yml` includes:
```yaml
  recorder-control:
    build:
      context: ./tools/recorder
      dockerfile: Dockerfile
    depends_on: [unreal-signaling]
    env:
      RECORDER_CTRL_PORT=8889
      RECORDER_SIGNALING_URL=ws://unreal-signaling:80
      RECORDER_OUTPUT_DIR=/recordings
  PY_RECORDER_PATH=/opt/embody/recorder/gs_webrtc_recorder.py
  VTUBER_ALLOWED_ADDRESSES=... # set in .env (defaults to 127.0.0.1,::1,172.18.0.1)
  RECORDER_SIGNALING_URL=ws://unreal-signaling:80 # override if your streamer socket differs (e.g., 8888)
  RECORDINGS_API_TOKEN=... # optional bearer token; leave unset to rely on IP allowlist
    volumes:
      - /recordings:/recordings
    command: ["python3", "/opt/embody/recorder/control_server.py"]
    ports:
      - "8889:8889"
    networks: [vtuber_network]
```
Ensure `/recordings` is a host path/volume shared where you want outputs stored/pulled from.

## Usage
```
# start a 25s recording with label "sync_test"
curl -X POST http://<host>:8889/recordings/start \
  -H 'Content-Type: application/json' \
  -d '{"label":"sync_test","duration":25}'

# check status
curl http://<host>:8889/recordings/status

# stop early if needed
curl -X POST http://<host>:8889/recordings/stop
```

## Notes
- The recorder connects to signaling via `RECORDER_SIGNALING_URL` and writes MKVs to `/recordings` (no re-encode).
- Keep the sidecar on the same host/bridge as signaling for minimal latency; avoid TURN by staying local.
- Downloads are not exposed here; fetch files from `/recordings` via SSH/volume or add a private download endpoint if needed.
