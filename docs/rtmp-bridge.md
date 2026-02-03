# RTMP Bridge (Pixel Streaming → Twitch/YouTube)

This repo supports an optional **broadcast-only** bridge that takes Pixel Streaming
(WebRTC) output from the Unreal container and publishes it to RTMP endpoints (Twitch,
YouTube, etc).

## What It Does

Pipeline:

1. Unreal runs Pixel Streaming (WebRTC) inside `unreal-game`
2. `rtmp-bridge` connects to `unreal-signaling` over WebSocket signaling
3. GStreamer receives audio+video:
   - Video: WebRTC H.264 (prefer passthrough) or NVENC transcode
   - Audio: WebRTC Opus → AAC (required for RTMP/FLV)
4. `rtmpsink` publishes to `RTMP_OUTS` (Twitch/YouTube RTMP URLs)

## Enable / Run

The service is disabled by default via a compose profile.

1. Set RTMP outputs in `.env` (NOT committed):
   - `RTMP_OUTS=rtmp://live.twitch.tv/app/<STREAM_KEY>`
2. Start the bridge:

```bash
docker compose --profile broadcast up -d rtmp-bridge
```

Stop:

```bash
docker compose --profile broadcast down rtmp-bridge
```

## Config

All settings are via env vars (see `orchestrator.env.example`):
- `RTMP_OUTS` (required)
- `RTMP_TRANSCODE_VIDEO` (default `1`)
- `RTMP_VIDEO_BITRATE_KBPS` (default `6000`)
- `RTMP_AUDIO_BITRATE_KBPS` (default `160`)
- `RTMP_FPS` (default `30`)
- `RTMP_WEBRTC_LATENCY_MS` (default `200`)

## Notes

- **Secrets:** never commit Twitch/YouTube RTMP keys; keep them in `.env` or your
  secret manager.
- **Codec stability:** for long-running RTMP streams, prefer Unreal outputting H.264
  directly (PixelStreaming2 `Codec=H264`) so the bridge can avoid VP9 decode → H.264
  re-encode.

