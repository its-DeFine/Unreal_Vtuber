# NeuroSync-Core (Forked) – Unified Audio & Blendshape Architecture

The **forked** version merges the `NeuroSync_Local_API` and large parts of the `NeuroSync_Player` into a single **monolithic package** (`neurosync`).  One Flask server now performs **all** steps – text generation, TTS, blendshape synthesis, local playback and Live Link streaming.

---
## 1  High-level data flow

```
┌──────────────┐  HTTP /text_to_blendshapes     ┌────────────────────────┐
│  Front-end   │───────────────────────────────▶│  Flask Server          │
│  (client)    │                               │  neurosync.server.app  │
└──────────────┘                               └────────────┬───────────┘
                                                         Queues
                                         ┌────────────────┴────────────────┐
                                         │  ①  LLM-Streaming Worker        │
                                         │      llm_streaming_worker       │
                                         └────────┬────────┬───────────────┘
                                              text│chunks  │
                                                   ▼       │
                                         │ ②  SentenceBuilder /           │
                                         │     TTS+Blendshape Worker       │
                                         │     tts_blendshape_worker       │
                                         └────────┬────────┬───────────────┘
                                      (WAV bytes) │        │ blendshape lists
                                                   ▼        ▼
         ┌───────────────────────────┐  put()  ┌───────────────────────────┐
         │ playback_audio_queue      │◀────────│ audio_blendshape_queue    │
         └────────────┬──────────────┘          └───────────┬──────────────┘
                      │                               │
                      │ ③ sounddevice OutputStream    │ ④ Player.stream_frames
                      ▼                               ▼
               Local Speakers                UDP 127.0.0.1:11111
                                            (Live Link Face)
```

Legend
* **① LLM worker** – streams tokens (OpenAI or HF) and places sentence-sized chunks onto `text_queue`.
* **② TTS worker** – converts each chunk to **WAV bytes** and **blendshape frames** (via internal model). Results enqueue to `audio_blendshape_queue`.
* **③ Playback worker** – reads WAV bytes, decodes with *SoundDevice* (not Pygame) and plays immediately.
* **④ Player** – encodes blendshapes and fires them over UDP to Unreal, aligned with a `frame_duration = 1/60 s` wall-clock.

> Enabling `/stream_text_to_blendshapes` activates the same workers but returns NDJSON chunks to the HTTP client **while** the server is playing/streaming.

---
## 2  Component map

| Layer | Module(s) | Notes |
|-------|-----------|-------|
| **HTTP API** | `neurosync.server.app` | Routes: `/audio_to_blendshapes`, `/text_to_blendshapes`, `/stream_text_to_blendshapes` |
| **LLM** | `llm_streaming_worker` in `app.py` + `neurosync.llm` package | Supports OpenAI **or** local llamas; pushes text chunks to queue |
| **TTS + Blendshapes** | `tts_blendshape_worker` | Uses HuggingFace Vits, ElevenLabs, or combined endpoint; converts produced WAV bytes to blendshapes via `generate_facial_data_from_bytes` |
| **Playback** | `audio_playback_worker` (sounddevice) | Stream-safe, one OutputStream reused |
| **Live Link** | `core/runtime/player.py` | Re-implemented Player with `play()` & `stream_frames()` (no separate script) |
| **Queues/Events** | `text_queue`, `audio_blendshape_queue`, `playback_audio_queue` | Provide back-pressure; workers are daemon threads |

---
## 3  How this differs from the *original* split design

| Aspect | Original (two repos) | Forked (NeuroSync-Core) | Impact |
|--------|----------------------|-------------------------|--------|
| Separation of concerns | Flask API **only** produced blendshapes; Player app handled TTS, audio, UDP | Single Flask server handles everything | Easier deployment (one container) but heavier server footprint |
| Audio playback lib | `pygame` | `sounddevice` (`PortAudio`) | Better latency and device selection; runs headless w/out X11 |
| Inter-thread sync | `Event` + two threads per request in Player | Workers + Player in same process; Player still uses `Event` internally | Tighter coupling; still wall-clock-based (can drift) |
| Streaming support | Not built-in; player pulled LLM/TTS locally | `/stream_text_to_blendshapes` streams NDJSON chunks | Enables thin clients & BYOC CLI |
| Client usage | Stand-alone Python scripts (`text_to_face.py` etc.) | `neurosync.cli.client` plus plain HTTP | Clients can be browser, Unity, etc. |
| Transport to Unreal | UDP Live Link Face | Same (Player encapsulated) | Unchanged |
| Audio to Unreal | Not sent | Still not sent | Mouth sync still relies on local playback timing |

---
## 4  Sync considerations in the fork

1. **Audio first** – Playback worker writes to the sound device immediately; the global `audio_start` timestamp is captured when the first block reaches the DAC.
2. **Blendshape timing** – `Player.stream_frames` waits until `audio_start + n⋅frame_dur` before sending each frame.
3. **Remaining drift** comes from OS scheduler jitter and UDP queueing; there is no feedback from the audio device.

> If running inside Docker without an output device, set `AUDIO_PLAYBACK_DEVICE=disabled` and rely on HTTP streaming to let a front-end play audio instead.

---
## 5  Key files to review

* `neurosync/server/app.py` – core of the server (3500 + LOC).  
* `neurosync/core/runtime/player.py` – unified audio + data player.  
* `neurosync/tts/tts_service.py` – provider-agnostic TTS interface.  
* `neurosync/llm/llm_service.py` – provider-agnostic LLM interface.

These mirror the pieces we inspected in the original document but live under one namespace.

---

*Last updated: 2025-05-11* 