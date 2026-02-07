# Audio Output in Docker Containers

When running the Unreal Engine game container on headless Linux servers (EC2 GPU instances, cloud VMs), audio output requires explicit configuration. Without it, PixelStreaming2's WebRTC audio track will be silent even though UE reports sound waves as "playing."

## The Problem

Headless Linux servers typically have no audio hardware. When UE5 initializes its AudioMixer via SDL, it falls back to the `dummy` audio driver:

```
LogAudioMixerSDL: Hinting SDL to use 'dummy' audio driver.
LogAudioMixerSDL: Display: Initialized SDL using dummy platform API backend.
```

The dummy driver calls SDL's audio render callback but does not properly drive UE's AudioMixer render pipeline. PixelStreaming2 registers a `SubmixBufferListener` on `MasterSubmixDefault` to capture audio for WebRTC — with the dummy backend, these buffers contain zeros.

**Symptoms:**
- UE logs show `The sound wave '...' is playing by the owner '...'` (audio IS playing inside UE)
- WebRTC audio track contains silence
- Twitch/YouTube stream has video but no audio
- `ffmpeg -i segment.ts -af volumedetect -f null -` shows `-91 dB` (silence)

## Solution: PulseAudio Forwarding

PulseAudio with a virtual null sink provides a real audio backend that SDL connects to properly. Even though the physical output goes nowhere, PulseAudio drives the audio callback correctly, allowing UE's AudioMixer to render real PCM data into the submix buffers.

### Step 1: Install and Configure PulseAudio on the Host

```bash
# Install PulseAudio (if not already present)
sudo apt-get install -y pulseaudio

# Configure PulseAudio to never exit on idle
mkdir -p ~/.config/pulse
cat > ~/.config/pulse/daemon.conf <<'EOF'
exit-idle-time = -1
flat-volumes = no
default-sample-format = float32le
default-sample-rate = 48000
default-sample-channels = 6
EOF

# Start PulseAudio
pulseaudio --start --exit-idle-time=-1

# Enable auto-start on boot (systemd user service)
systemctl --user enable pulseaudio.service
systemctl --user enable pulseaudio.socket

# Enable lingering so user services run without an active login session
sudo loginctl enable-linger $(whoami)
```

### Step 2: Add Audio Mounts to Docker Compose

Create or update a Docker Compose override file to forward PulseAudio into the game container:

```yaml
# docker-compose.audio.override.yml
services:
  unreal-game:
    environment:
      # Force SDL to use PulseAudio instead of the dummy driver
      - SDL_AUDIODRIVER=pulseaudio
      # Point to the host's PulseAudio socket
      - PULSE_SERVER=unix:/run/user/1000/pulse/native
      # Required for PulseAudio client to find the socket
      - XDG_RUNTIME_DIR=/run/user/1000
    volumes:
      # Mount PulseAudio socket from host
      - /run/user/1000/pulse:/run/user/1000/pulse:ro
      # Mount PulseAudio cookie for authentication
      - ${HOME}/.config/pulse/cookie:/home/embody/.config/pulse/cookie:ro
```

> **Note:** The cookie mount maps the host user's PulseAudio cookie to the container user's expected path. Adjust `/home/embody` if the container runs as a different user. Both users must share the same UID, or configure PulseAudio for anonymous access (`auth-anonymous=1`).

Then launch with the override:

```bash
docker compose -f docker-compose.unreal.yml -f docker-compose.audio.override.yml up -d
```

### Step 3: Verify

After the container starts, check the UE logs:

```bash
# GOOD (fixed):
# LogAudioMixerSDL: Display: Initialized SDL using pulseaudio platform API backend.

# BAD (still broken):
# LogAudioMixerSDL: Hinting SDL to use 'dummy' audio driver.
```

Verify PulseAudio sees the game as a client:

```bash
pactl list clients short
# Should show a client entry for the game process

pactl list sinks short
# Sink state should be RUNNING (not SUSPENDED/IDLE) when audio plays
```

Optional — capture PulseAudio monitor to confirm real audio:

```bash
parecord --channels=2 --rate=44100 --format=s16le \
  -d auto_null.monitor /tmp/test.raw &
RECPID=$!

# ... trigger audio playback in UE (TTS command, etc.) ...
sleep 5
kill $RECPID

# Analyze the raw capture
python3 -c "
import struct
data = open('/tmp/test.raw','rb').read()
samples = struct.unpack(f'<{len(data)//2}h', data)
peak = max(abs(s) for s in samples)
rms = (sum(s*s for s in samples)/len(samples))**0.5
print(f'Peak: {peak}/32767 ({peak/32767*100:.0f}%)')
print(f'RMS: {rms:.0f}')
print('AUDIO OK' if peak > 100 else 'SILENCE - check config')
"
```

## Important Caveats

1. **PulseAudio must start BEFORE the container.** If PulseAudio dies or restarts after UE has started, the audio connection breaks silently. You must restart the game container.

2. **SSH session cycling can kill PulseAudio.** Each SSH connection may spawn a new PulseAudio instance. Use `loginctl enable-linger` and `exit-idle-time = -1` to keep it persistent across session changes.

3. **AWS kernels lack ALSA.** AWS Linux kernels ship with `CONFIG_SND` disabled — there is no ALSA subsystem and `snd-dummy` is not available. Do not waste time with `modprobe snd-dummy`. PulseAudio with its built-in `module-null-sink` is the only viable approach on these instances.

4. **UID matching.** The container user and host PulseAudio user must share the same UID for socket authentication. If UIDs differ, either align them or set `auth-anonymous=1` in the PulseAudio config.

5. **"Using Audio Hardware Device Dummy Output" is expected.** This just means PulseAudio's sink is named "Dummy Output" (because it's a virtual null sink). What matters is the SDL backend line showing `pulseaudio`, not `dummy`.

6. **D-Bus errors are harmless.** `Failed to connect to the bus: Failed to connect to socket /run/dbus/system_bus_socket` errors come from the embedded Chromium process inside UE and do not affect audio.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| UE still shows `dummy` audio driver | Verify `SDL_AUDIODRIVER=pulseaudio` is set in the container environment and PulseAudio is running on the host (`pactl info`) |
| `Connection refused` in container logs | PulseAudio socket not mounted or PulseAudio not running — check `ls /run/user/1000/pulse/native` on host |
| `Access denied` from PulseAudio | UID mismatch between host and container user, or cookie not mounted correctly |
| Audio works initially then stops | PulseAudio restarted (SSH session change) — restart the game container |
| `LogAudioCaptureCore: No Audio Capture implementations found` | This is about audio INPUT (microphone), not output — expected and harmless |

## References

- [Audio output in containers | Unreal Containers](https://unrealcontainers.com/docs/concepts/audio-output) — official guide confirming PulseAudio as the recommended approach
- [Getting Started with Pixel Streaming | UE5 Docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/getting-started-with-pixel-streaming-in-unreal-engine) — official Pixel Streaming documentation
