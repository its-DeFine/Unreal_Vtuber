# PixelStreaming Stream Config Schema

Reference for PixelStreaming2 config keys used by the Unreal VTuber stack.
Values map to `pixel-streaming/config/*.ini` files mounted into containers at runtime.

See also: [pixel-streaming-architecture.md](pixel-streaming-architecture.md)

## Required Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Codec` | string | `H264` | Video codec. One of `H264`, `VP8`, `VP9`, `AV1`. H264 is required for stable RTMP passthrough (no decode/re-encode). |
| `LatencyMode` | string | `LowLatency` | Encoder latency mode. `LowLatency` allows periodic keyframes; `UltraLowLatency` suppresses IDR frames and can degrade quality over long sessions. |
| `KeyframeInterval` | integer | `60` | Frames between forced IDR keyframes. At 30fps this equals ~2s, matching Twitch ingest guidance. |

## Encoder Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `H264Profile` | string | `Baseline` | H.264 encoding profile (`Baseline`, `Main`, `High`). Baseline provides the broadest decoder compatibility. |
| `TargetBitrate` | integer | `45000000` | Target encoder bitrate in bits/s. Controls the steady-state quality under CBR. |
| `MaxBitrate` | integer | `52000000` | Maximum encoder bitrate in bits/s. Caps the encoder ceiling. |
| `MinQP` | integer | `8` | Minimum quantization parameter (0–51). Lower = higher quality floor. |
| `MaxQP` | integer | `28` | Maximum quantization parameter (0–51). Higher = more compression allowed. |

## Negotiation Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `WebRTCNegotiateCodecs` | boolean | `true` | When true, PixelStreaming2 negotiates codec preferences with the WebRTC peer. |

## Display Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ResolutionSizeX` | integer | `1920` | Horizontal render resolution in pixels (GameUserSettings.ini). |
| `ResolutionSizeY` | integer | `1080` | Vertical render resolution in pixels (GameUserSettings.ini). |
| `MaxFPS` | integer | `60` | Framerate cap via `t.MaxFPS` console variable. |

## Config File Mapping

These keys appear across multiple INI files and UE config namespaces:

- **`Engine.ini`** — `[/Script/PixelStreaming2.PixelStreaming2Settings]` and `[/Script/PixelStreaming2Settings.PixelStreaming2PluginSettings]`
- **`Game.ini`** — `[/Script/PixelStreaming2Settings.PixelStreaming2PluginSettings]` (for builds that load plugin settings from `config=Game`)
- **`ConsoleVariables.ini`** — `PixelStreaming.Encoder.*` and `PixelStreaming.WebRTC.*` CVars
- **`GameUserSettings.ini`** — `[/Script/Engine.GameUserSettings]` for resolution

The stack ships duplicate keys across namespaces ("shotgun overrides") because different UE5 versions read from different config sections.
