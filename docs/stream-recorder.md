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
  --signalling-url ws://86.106.138.188:8888 \
  --output captures/session-001.webm \
  --duration 120 \
  --streamer orch-alpha
```

Arguments:

- `--signalling-url` – WebSocket endpoint of the Pixel Streaming signalling server.
- `--output` – Destination file (extension determines container format).
- `--duration` – Seconds to record (omit or set 0 to run until the stream ends).
- `--streamer` – Optional explicit streamer id (otherwise the first available stream is chosen).

The recorder automatically responds to signalling pings, exchanges SDP offer/answer, forwards ICE candidates, and writes the resulting media stream via `aiortc.MediaRecorder`.

Once the file is written, reuse `scripts/upload_capture.py` to push the recording to the storage service:

```bash
python scripts/upload_capture.py captures/session-001.webm session-001 \
  http://storage-unit:9000 --orchestrator-id orch-alpha --token supersecret
```
