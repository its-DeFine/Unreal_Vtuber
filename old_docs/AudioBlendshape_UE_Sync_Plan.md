# Audio + Blendshape Full-Sync Pipeline to Unreal Engine

> Version 0.1 • 2025-05-11  
> _Author: product-engineering guild_

---

## 1  Objectives
1. Stream **raw/encoded audio** _and_ **68-slot ARKit blendshape frames** from the NeuroSync sender to Unreal Engine in real time.
2. Achieve **≤ ±20 ms A/V skew** over a localhost link (stretch goal: ≤ ±40 ms over LAN/WAN).
3. Maintain compatibility with:
   • **Original NeuroSync repos** (`NeuroSync_Local_API` + `NeuroSync_Player`).  
   • **Forked monolithic repo** (`NeuroSync-Core`).
4. Keep the current **Live Link Face** driven facial rig intact; only extend transport layers.
5. Provide exhaustive **structured logs** for every pipeline stage (`DEBUG`, `TRACE`).

---

## 2  High-Level Architecture (target state)

```mermaid
graph TD
  A(Audio / Blendshape Producer) -->|UDP:11111| B[UE LiveLink Provider (Blendshapes)]
  A -->|UDP:11112 (Opus-PCM)| C[UE Audio Receiver]
  C --> D[RingBuffer ▷ USoundWaveStreaming]
  D -->|Clock ↔| B
  B --> E[MetaHuman Skeleton]
```

* **Port 11111** – _unchanged_ Live Link Face blendshape RTP-style packets.  
* **Port 11112** – **new** audio channel (PCM 48 kHz or Opus-encoded).  
* **Clock sync** – shared timestamp in packet header (`uint64 nanos`).

---

## 3  Key Design Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Transport | **Custom UDP** (CBOR header + payload) | Low-latency, mirrors existing Live Link path, avoids UE TCP stall risk. |
| Codec | Start with **PCM float32 48 kHz**, optional **Opus** flag | Simplifies prototype; Opus reduces BW for WAN. |
| Time base | **Sender monotonic-nanos** epoch per session | Works on Windows/Linux; no leap-second issues. |
| Unreal side | C++ `AudioReceiver` module + `USoundWaveProcedural` | Full control, tested in [Runtime MetaHuman Lip Sync](https://forums.unrealengine.com/t/lip-syncing-in-realtime-from-audio/1857173). |
| Sync strat | Audio is **master clock**; blendshape frames scheduled via same timestamps | Matches human perception—video can lag audio a few ms. |

---

## 4  Implementation Road-map (Original Repos)

### 4.1  Sender-side (Python)
1. **`utils/net/audio_sender.py`**  _🆕_  
   • Accept `pcm_frames` (numpy array) & `t0_nanos`.  
   • Chunk into 20 ms packets (960 samples @48 kHz).  
   • `struct.pack` header: `[uint64 timestamp, uint16 seq, uint8 codec_id]`.  
   • Optional **Opus** encode via `pyogg`.
2. **Patch `utils/generated_runners.py`**  
   • Replace local `pygame` playback with `AudioSender`.  
   • Retain old playback for `DEBUG_LOCAL_AUDIO=1`.
3. **Blendshape thread** – prepend the **same timestamp** to each `datagram`.  
   Use existing Live Link packet format but extend first 8 bytes for `timestamp_nanos` (non-breaking: Unreal ignores extras today).
4. **Logging**  
   • Add `logger.bind(component="audio_sender", seq=..., ts=...)` (structlog).  
   • Emit WARN if network send queue > 3.

### 4.2  Receiver-side (Unreal C++)
1. **Create `AudioLiveLinkReceiver` Plugin**  
   • `FAudioReceiverThread` – `FRunnable`, binds UDP 11112.  
   • Parses header, pushes PCM into `TArray<uint8>` ring buffer.  
   • Emits `FOnPacketArrived` delegate with `Timestamp`.
2. **`UProceduralSoundWave`**  
   • Stream from ring buffer; start playback when first 3 packets buffered.  
   • Expose `double AudioStartTime` (engine seconds).
3. **Blendshape time-align**  
   • In existing `FLiveLinkFaceImporter`, subtract `AudioStartTime` from packet ts → schedule `UpdateSubjectFrame()` _exactly_ `Δt` ahead.  
   • If `|skew| > 40 ms` → drop/duplicate frames; log event.
4. **Debug HUD**  
   • Toggle `CTRL+L` – display `AudioLatency`, `BlendshapeLatency`, `Skew`, `PacketLoss%`.
5. **Blueprint Integration**
   • Expose key functionalities of the `AudioLiveLinkReceiver` plugin (e.g., audio start/stop events, status, received timestamps) to Blueprints for easier integration into game logic and Animation Blueprints.
   • Animation Blueprints will continue to consume the synchronized blendshape data via the existing Live Link system, driven by the C++ synchronized timing.

### 4.3  Testing Harness
| Test | Procedure | Success Criteria |
|------|-----------|------------------|
| "Ping Pong" | Send 3-s sine tone + jaw-open wave. | Jaw movement matches audio peaks (≤20 ms). |
| Packet loss | Drop every 10th audio packet. | No crash; minor pop; blendshape stream OK. |
| WAN RTT 100 ms | `tc qdisc` add delay | Both streams keep sync within 40 ms. |

---

## 5  Porting to **NeuroSync-Core** (forked repo)
1. Replace `sounddevice` playback in **`core/runtime/player.py`** with `AudioSender` import.  
   • If `AUDIO_PLAYBACK_DEVICE=disabled` **and** `UE_AUDIO_HOST` set → auto-send.
2. Expose new **gRPC** endpoint `/stream_text_to_blendshapes_audio` returning **NDJSON** with signed URLs for audio (for web clients) ⏤ _optional_.
3. Re-use Unreal plugin _as-is_; only one receiver required.

---

## 6  Risk Register & Mitigations
| Risk | Mitigation |
|------|------------|
| Unreal sample-queue underrun on low-end PCs | Pre-buffer ≥60 ms; adaptive jitter buffer. |
| UDP blocked by firewall | Allow TCP fallback (WebSocket) at 70 ms penalty. |
| Opus decode adds 10 ms | Keep PCM for LAN; auto-switch if `--wan`. |
| Drift over long (>10 min) sessions | Periodic **RTCP-style** SYNC packet with absolute epoch; recalc offset. |

---

## 7  Task Breakdown & Estimates (SP)
1. Python `AudioSender` + tests …… 5  
2. Modify original player runner …… 3  
3. Unreal UDP receiver plugin …… 13  
4. Sync logic & jitter buffer …… 8  
5. Metrics HUD & logs …… 2  
6. Docs + CI workﬂows …… 3  
**Total ≈ 34 SP** (~3 sprints).

---

## 8  References
* Epic UE Forum – "Lip syncing in realtime from audio" <https://forums.unrealengine.com/t/lip-syncing-in-realtime-from-audio/1857173>  
* Runtime MetaHuman Lip Sync plugin demo (YouTube) <https://www.youtube.com/live/fuwml1edE9w?t=0s>  
* NeuroSync Local API & Player (original repos)  
* UE 5 `USoundWaveProcedural` documentation.

---

> _Next step_: spike the **AudioReceiver** plugin and validate A/V skew on localhost. 