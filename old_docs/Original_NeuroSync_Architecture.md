# NeuroSync (Original) – Audio + Blendshape Architecture

> This document reverse-engineers the **pre-fork** NeuroSync code that ships as two separate repos:
>
> * **NeuroSync_Local_API** – turns audio into 60 fps facial-blendshape frames.
> * **NeuroSync_Player**      – takes (audio + blendshapes) and streams them to Unreal Live Link Face while playing the sound locally.

## High-level data flow

```
┌──────────────────┐  text chunks     ┌────────────────────────┐
│  Producer (LLM)  │ ───────────────▶│  TTS Worker Thread     │
└──────────────────┘                 │  (utils/tts/tts_bridge)│
                                     └─────────┬──────────────┘
                                               │audio bytes (WAV/MP3)
                        ┌──────────────────────┴──────────────────────┐
                        │  (a) Local-TTS  OR  (b) ElevenLabs Cloud    │
                        └──────────────────────┬──────────────────────┘
                                               │audio bytes
                                               ▼
                              ┌────────────────────────────────┐
                              │  Flask Local API               │
                              │  /audio_to_blendshapes         │
                              │  (extract_features → model)    │
                              └────────────────┬───────────────┘
                                               │JSON  {blendshapes:[…]}
                                               ▼
                              ┌──────────────────────────────────────────┐
                              │  Player (run_audio_animation)           │
                              │  utils/generated_runners.py             │
                              └───────┬─────────────────┬───────────────┘
        shared threading.Event───────┘                 │
                                                      ▼
        ┌───────────────────────────────┐   ┌──────────────────────────┐
        │  Audio Thread (pygame)        │   │  Blendshape Thread       │
        │  play_audio_from_memory/path  │   │  send_pre_encoded_data   │
        │                               │   │  → UDP 127.0.0.1:11111   │
        └───────────────────────────────┘   └────────────┬─────────────┘
                                                         │UDP packets (PyLiveLinkFace)
                                                         ▼
                                                Unreal Live Link  Face
```

* **Audio** is *played locally* via Pygame; it is **not** sent over the network.
* **Blendshapes** are encoded and pushed over **UDP** to Unreal (Live Link Face protocol).

---

## Detailed component breakdown

### 1.  TTS generation (`utils/tts/tts_bridge.py`)
* Picks one of three modes per chunk:
  1. **Combined real-time endpoint** – returns audio *and* blendshapes in one shot.
  2. **Local TTS** (`call_local_tts`) – small Flask micro-service you run yourself.
  3. **ElevenLabs** (`get_elevenlabs_audio`) – cloud request.
* Output is always **`audio_bytes`** (WAV or MP3).

### 2.  Blendshape generation (`NeuroSync_Local_API`)
* Route `POST /audio_to_blendshapes` accepts raw bytes.
* Pipeline:
  1. `extract_audio_features` → MFCC + autocorr (60 fps frames).
  2. `process_audio_features` → Transformer (half-precision on GPU if available).
* Returns `[[f0..f67], …]` – one list per frame (68 values).

### 3.  Player coordination (`utils/generated_runners.py`)
* Converts raw blendshapes into UDP-friendly binary (`pre_encode_facial_data`).
* Creates **two threads** and a **shared `Event`:**
  * **Audio Thread** – plays WAV via `pygame.mixer`.
  * **Data Thread** – sends one facial frame every `1/60 s` using wall-clock time.
* When the `Event` is set both threads start almost simultaneously, providing *coarse* sync.

### 4.  Audio playback (`utils/audio/play_audio.py`)
* If audio was loaded **from bytes** it calls `play_audio_from_memory(..., sync=False)`
  → simple loop, no drift correction.
* If audio is a **file path** it calls `play_audio_from_path(..., sync=True)`
  → uses `pygame.mixer.music.get_pos()` to compensate drift.
  (This asymmetry is the main cause of lip-sync issues in Docker.)

### 5.  Blendshape transport (`livelink/connect/livelink_init.py`)
* UDP socket `AF_INET/SOCK_DGRAM` to `127.0.0.1:11111`.
* Unreal Engine must have the **Live Link Face** listener running on that port.

---

## Synchronisation strategy & limitations
| Aspect | Technique | Pitfalls |
|--------|-----------|----------|
| Start alignment | Both threads wait on same `Event`. | Any buffering in either path causes offset |
| Ongoing sync | Data thread uses system clock; audio thread uses mixer time (only when `sync=True`). | `play_audio_from_memory` lacks feedback, so drift can accumulate |
| Transport latency | Blendshapes use local UDP (negligible). | If you redirect UDP across network you must account for RTT |

### Why Docker breaks sync
1. Containers often get a **dummy audio device** → `pygame` plays instantaneously → blendshape thread lags behind.
2. Even with PulseAudio forwarding you incur extra buffering; without the `sync_playback_loop` feedback, timeline diverges.

---

## FAQ

**Do we need any more source files from the original repos?**  
At this point the critical path is covered (`tts_bridge`, `local_api`, `generated_runners`, `play_audio`, `send_to_unreal`, `livelink_init`).  Other files deal with UI, logging, or optional workers and will not change the audio–blendshape relationship.  We can revisit if an edge-case pops up.

**Is audio sent via UDP?**  
No. Only the *encoded facial frames* are transmitted via UDP.  Audio is local (Pygame) and therefore never reaches Unreal.

**Can we push audio directly into Unreal instead?**  
Yes, but it is not implemented.  Options you could explore:
1. **Live Link over TCP** with a custom protocol carrying PCM packets.
2. **Unreal's HTTP/REST or WebSocket** endpoints to import sound waves on the fly.
3. **Run an OSC or UDP audio stream** and consume it via a Blueprint plugin.

Implementing any of these would remove the need for a local speaker and allow perfect frame-locked lipsync because both audio and blendshapes would originate inside the engine.

---

*Last updated: 2025-05-11* 