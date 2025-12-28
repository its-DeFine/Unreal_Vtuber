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
- `POST /recordings/{filename}/upload` – upload an existing MKV to a presigned URL
  - body: `{ upload_url, delete_after? }`
  - returns: `{ uploaded, bytes, sha256, deleted_after_upload }`

## Auth
- IP allowlist: `VTUBER_ALLOWED_ADDRESSES` (or `RECORDINGS_ALLOWED_IPS`). Requests from other IPs get 403. Default includes loopback + the Docker bridge.
- Optional token: set `RECORDINGS_API_TOKEN` to require Bearer auth; leave unset to rely on IP allowlist only.

## Compose (already wired)
`docker-compose.unreal.yml` already exposes the sidecar on port `8889` and mounts a host recordings directory to `/recordings`:
```yaml
  recorder-control:
    image: ghcr.io/its-define/unreal_vtuber/recorder-control:${EMBODY_SERVICE_IMAGE_TAG:-latest}
    environment:
      - RECORDER_CTRL_PORT=8889
      - RECORDER_SIGNALING_URL=${RECORDER_SIGNALING_URL:-ws://vtuber-unreal-signaling:80}
      - RECORDER_OUTPUT_DIR=/recordings
      - PY_RECORDER_PATH=/opt/embody/recorder/gs_webrtc_recorder.py
      - VTUBER_ALLOWED_ADDRESSES=${VTUBER_ALLOWED_ADDRESSES:-127.0.0.1,::1,172.17.0.1,172.18.0.1}
      - RECORDINGS_API_TOKEN=${RECORDINGS_API_TOKEN:-}
    volumes:
      - ${VTUBER_RECORDINGS_DIR:-/recordings}:/recordings
    command: ["python3", "/opt/embody/recorder/control_server.py"]
    ports:
      - "8889:8889"
    networks: [vtuber_network]
```
Set `VTUBER_RECORDINGS_DIR` in `.env` to control where recordings are stored on the host (defaults to `/recordings`).

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
- For headless automation, prefer uploading to object storage via `/recordings/{filename}/upload` and serving downloads from there.
