# Headless Pixel Streaming Recorder

This prototype records Pixel Streaming sessions without modifying the Unreal project. It connects to the signalling server, subscribes to the target streamer and stores a synchronized audio/video file.

## Recorder Overview

Captures are triggered manually (either on the orchestrator or from a
whitelisted workstation). There’s no background container auto-recording payloads:
run `stream_recorder/record_stream.py` whenever you need a clip. The rest of
this document walks through manual usage and the tuning flags now baked into the
recorder.

## Requirements

- Python 3.10+
- `aiortc` (1.13 or newer), `aiohttp`, `numpy` (see `stream_recorder/requirements.txt`)
- Shell access to the orchestrator that is running the Pixel Streaming stack (the recorder runs there and talks to `ws://127.0.0.1:8080`)

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
  --signalling-url ws://127.0.0.1:8080 \
  --output captures/session-001.webm \
  --duration 120 \
  --streamer orch-alpha

# Capture the raw RTP payloads without re-encoding (requires a later remux):

python stream_recorder/record_stream.py \
  --signalling-url ws://127.0.0.1:8080 \
  --output captures/session-raw.mp4 \
  --duration 60 \
  --mode raw
```

Arguments:

- `--signalling-url` – WebSocket endpoint of the Pixel Streaming signalling server (usually `ws://127.0.0.1:8080` when the recorder runs on the orchestrator).
- `--output` – Destination file (extension determines container format).
- `--duration` – Seconds to record (omit or set 0 to run until the stream ends).
- `--streamer` – Optional explicit streamer id (otherwise the first available stream is chosen).
- `--video-bitrate` / `--audio-bitrate` – Control the local transcode quality (defaults: 6000 kbps video, 128 kbps audio).
- `--frame-rate` – Override the transcoder FPS (default 30).
- `--mode` – Select `transcode` (default) or `raw`. Raw mode dumps the encoded RTP payloads to `.h264` / `.opus` alongside the requested output.
- `--raw-remux` – Optional command (such as a shell script or `ffmpeg` wrapper) invoked after capture to remux the raw dumps into the final container.
- `--preferred-spatial-layer` / `--preferred-temporal-layer` – Request specific SFU layers so the recorder matches the browser’s high-quality feed.
- `--answer-start-bitrate` / `--answer-max-bitrate` – Inject high-range `x-google-*` hints into the SDP answer (defaults 60 Mbps / 80 Mbps).
- `--encoder-min-qp` / `--encoder-max-qp` – Push encoder QP bounds over the data channel (defaults 10 / 30).
- `--encoder-*-bitrate` – Send minimum/target/maximum encoder bitrates (in bps) via the data channel so UE jumps to the desired quality immediately.
- `--webrtc-*-bitrate` – Mirror the browser’s WebRTC hints (min/start/max, in bps) to shorten congestion-control ramp-up.

The recorder automatically responds to signalling pings, exchanges SDP offer/answer, forwards ICE candidates, and writes the resulting media stream via `aiortc.MediaRecorder`.

If upload arguments are omitted you can still call `scripts/upload_capture.py` manually after recording.

> Run the recorder directly on the orchestrator (or inside a container launched with `--network host`) so it can reach the local signalling server at `ws://127.0.0.1:8080` without exposing additional ports to the public Internet.

### Tips for Higher Quality Captures

- Prefer MP4 outputs (`--output captures/foo.mp4`) when you plan to edit or share clips broadly; the recorder will encode with H.264 (`libx264`).
- For WebM outputs, bump `--video-bitrate` (for example `--video-bitrate 8000`) if you see pixelation; WebM uses `libvpx` by default.
- Ensure the upstream Pixel Streaming session is rendering at the target resolution/bitrate—recordings cannot exceed source quality.
- In `--mode raw`, the recorder writes `*.h264` and `*.opus` dumps. Use your own remux command (for example an `ffmpeg` invocation that understands raw RTP payloads) to package those into MP4/WebM without re-encoding.
- When the recorder runs on the orchestrator it now mirrors the Epic browser client by issuing quality-control commands over the data channel. Tune the `RECORDER_ENCODER_*` and `RECORDER_WEBRTC_*` environment variables (or the matching CLI flags) to change the bitrates/quantisers it requests.
- The Unreal container loads high-quality defaults from `pixel-streaming/config/ConsoleVariables.ini`. Edit that file (or override the bind mount in `docker-compose.unreal.yml`) if you need different Pixel Streaming CVars at boot.

## High-Quality Capture Playbook

Past recordings looked blocky because four pieces were out of sync: Unreal booted with conservative encoder CVars, the recorder never requested quality control, TURN credentials were stale, and aiortc ramped bitrate slowly. The fixes are now baked into this repo; follow this checklist whenever you stand up (or debug) a capture host.

1. **Unreal encoder defaults** – `docker-compose.unreal.yml` mounts
   `pixel-streaming/config/ConsoleVariables.ini` into the game container. That
   INI forces a CBR 15–20 Mbps stream with QP 10–30 at 60 fps. Update the file
   if you need different limits, but do not edit the container in-place; the
   bind mount ensures every restart inherits the same settings.

2. **Recorder handshakes like the Epic web player** – `record_stream.py`
   requests quality control, pushes encoder/WebRTC bitrate knobs, and logs the
   commands when the data channel opens. The knobs are exposed via
   `RECORDER_ENCODER_*`, `RECORDER_WEBRTC_*`, and the matching CLI flags so you
   can experiment without touching code.

3. **TURN credentials must be fresh** – anytime you restart the stack (or move
   the host) run `./scripts/generate_turn_credentials.sh` before
   `docker compose up`. Stale credentials were the primary reason the streamer
   kept disconnecting during early tests.

4. **Verify the stream is healthy before blaming the recorder** – if
   `docker compose logs unreal-game` shows segfaults, fix the packaged build
   first. The recorder will loop (and the stats will stay near zero) until the
   streamer actually publishes media.

5. **Use raw mode for fidelity and inspect stats** – `--mode raw` writes the
   encoded RTP payloads (`*.h264` + `*.opus`) plus a ready-to-play MKV when you
   remux. The recorder logs a `Stats:` line every five seconds with video/audio
   bitrate, FPS, and jitter—watch those to confirm the stream ramps to the
   expected quality immediately.

With those pieces in place the latest captures (`session-aiortc-hq-debug.*`) hit
15–20 Mbps almost immediately and match what the Epic browser client sees.

### Troubleshooting Checklist

If quality regresses:

1. Check Unreal logs for crashes (`docker compose logs unreal-game`).
2. Make sure TURN credentials were regenerated before the most recent restart.
3. Confirm the data channel logs show the encoder/WebRTC commands (look for the
   `Requesting quality control over data channel` line in the recorder output).
4. Use `ffprobe` on the raw `.h264` dump to confirm target bitrate and runtime.
5. If the stats logger prints 0 kbps for minutes, the stream never delivered
   frames—go back to step 1.
