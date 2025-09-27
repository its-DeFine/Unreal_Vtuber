# Headless Pixel Streaming Recorder

This prototype records Pixel Streaming sessions without modifying the Unreal project. It connects to the signalling server, subscribes to the target streamer and stores a synchronized audio/video file.

## Requirements

- Python 3.10+
- `aiortc`, `aiohttp`, `numpy` (see `stream_recorder/requirements.txt`)
- Network access to the Pixel Streaming signalling server (default `ws://<host>:8888`)

Install dependencies locally:

```bash
cd stream_recorder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python stream_recorder/record_stream.py \
  --signalling-url ws://86.106.138.188:8080 \
  --output captures/session-001.webm \
  --duration 120 \
  --streamer orch-alpha

# Automatically upload to the storage service when complete:

python stream_recorder/record_stream.py \
  --signalling-url ws://86.106.138.188:8080 \
  --output captures/session-001.webm \
  --duration 120 \
  --session-id session-001 \
  --storage-url http://storage-unit:9000 \
  --upload-orchestrator-id orch-alpha \
  --storage-token supersecret
```

Arguments:

- `--signalling-url` – WebSocket endpoint of the Pixel Streaming signalling server.
- `--output` – Destination file (extension determines container format).
- `--duration` – Seconds to record (omit or set 0 to run until the stream ends).
- `--streamer` – Optional explicit streamer id (otherwise the first available stream is chosen).
- `--storage-url` + `--session-id` – When supplied together, the recorder automatically uploads the capture via `scripts/upload_capture.py`.
- `--upload-orchestrator-id` – Optional orchestrator identifier forwarded to the storage API during upload.
- `--storage-token` – Optional bearer token passed as `X-Storage-Token` when uploading.

The recorder automatically responds to signalling pings, exchanges SDP offer/answer, forwards ICE candidates, and writes the resulting media stream via `aiortc.MediaRecorder`.

If upload arguments are omitted you can still call `scripts/upload_capture.py` manually after recording.

> Running inside Docker on the orchestrator? Launch the container with `--network host` so the recorder can reach the local signalling server on `ws://127.0.0.1:8080`.
