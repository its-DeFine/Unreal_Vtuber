# Optional unattended RTMP broadcast

The broadcast bridge republishes an existing local Pixel Streaming feed to one
RTMP/RTMPS destination. It is **opt-in** and joins signaling as an additional
WebRTC viewer; it does not replace or proxy browser viewing, signaling, or the
recorder-control sidecar.

The bridge runs in its own Compose project (`vtuber-broadcast`) from
`docker-compose.broadcast.yml`. Normal commands such as
`./scripts/embody_cli.sh start`, `stop`, and `restart` continue to manage only
the existing avatar stack. If broadcast has never been configured, no broadcast
container is created and the existing stack is unchanged.

## Architecture

```text
                                 +--> browser WebRTC viewer(s)
Unreal --> Pixel Streaming signaling +--> recorder-control (optional capture)
                                 +--> broadcast bridge --> FLV --> RTMP/RTMPS
```

- The bridge subscribes through the same Pixel Streaming signaling protocol as
  the recorder and browser clients.
- H.264 video is passed through to FLV without a video encode. VP8/VP9 is
  transcoded to H.264 when needed.
- WebRTC Opus audio is transcoded to AAC, which RTMP/FLV destinations expect.
- Docker `restart: unless-stopped` and an in-process exponential retry loop keep
  it unattended. The bridge waits for a missing streamer and reconnects after
  signaling, source, pipeline, or destination failures.

## Configure a destination securely

The preferred interactive flow uses an echo-free prompt:

```bash
./scripts/embody_cli.sh broadcast configure
```

The complete RTMP URL (including stream key/token) is stored only at:

```text
~/.embody/broadcast/rtmp-url
```

The directory is mode `0700` and the destination file is mode `0600`. The local
`config.json` contains only non-secret mode/source settings. The CLI rejects a
credential storage directory inside the git checkout.

For unattended configuration, pass the value through a private file, a named
environment variable, or standard input:

```bash
./scripts/embody_cli.sh broadcast configure --url-file /path/to/private/rtmp-url

# Example secret-manager pattern; the value never becomes a CLI argument:
secret-manager read embody/rtmp-url | \
  ./scripts/embody_cli.sh broadcast configure --url-stdin

# Supported, but remember that inherited environments may be inspectable by
# privileged local users:
RTMP_DESTINATION='<value supplied by your secret manager>' \
  ./scripts/embody_cli.sh broadcast configure --url-env RTMP_DESTINATION
```

There is intentionally no supported `--url <value>` or `--stream-key <value>`
form, because command arguments can leak through shell history and process
inspection.

You can select a specific Pixel Streaming source or a non-default local
signaling endpoint while configuring:

```bash
./scripts/embody_cli.sh broadcast configure \
  --streamer-id avatar-0 \
  --signaling-url ws://vtuber-unreal-signaling:80
```

The destination is mounted into the container as a read-only file. Its value is
not placed in Compose interpolation, container environment variables, process
arguments, status output, or normal logs. Bridge and CLI error rendering also
redacts RTMP-shaped URLs and configured URL/key fragments.

## Lifecycle

Start the independently configured broadcast:

```bash
./scripts/embody_cli.sh broadcast start
```

Inspect it in human-readable or machine-readable form:

```bash
./scripts/embody_cli.sh broadcast status
./scripts/embody_cli.sh broadcast status --json
```

Status reports only whether a destination is configured, never its value. It
includes container health, bridge state, retry attempt count, heartbeat, and a
sanitized last error. Exit status is:

- `0` when broadcast is intentionally disabled, or when an enabled bridge
  container is running and not unhealthy;
- non-zero when broadcast is enabled but its destination is missing, its
  container is stopped/absent, or Docker reports it unhealthy.

Follow sanitized bridge logs:

```bash
./scripts/embody_cli.sh broadcast logs --tail 200
./scripts/embody_cli.sh broadcast logs --follow
```

Stop only the broadcast project (WebRTC, Unreal, and recording are untouched):

```bash
./scripts/embody_cli.sh broadcast stop
```

`stop` retains the private configuration so a later `broadcast start` resumes
the same destination.

## Failure and recovery

While running, the bridge automatically:

1. waits indefinitely for the requested/first Pixel Streaming source;
2. retries a failed source or RTMP session with exponential backoff (2 seconds
   up to 30 seconds by default);
3. updates `~/.embody/broadcast/state/state.json` atomically with sanitized
   state and heartbeat data; and
4. restarts after a process/host-Docker restart because of
   `restart: unless-stopped`.

If configuration, mounts, or the container itself may be stale, force a clean
recreate without touching the avatar stack:

```bash
./scripts/embody_cli.sh broadcast recover
./scripts/embody_cli.sh broadcast status
```

Re-running `broadcast configure` safely stops an enabled old bridge before
replacing its local configuration. Run `broadcast start` afterward.

## Disable and remove the destination

```bash
./scripts/embody_cli.sh broadcast configure --disable
```

This stops/removes the separate broadcast Compose project, marks broadcasting
disabled, and removes the stored RTMP URL. It does not recreate, stop, or edit
any base-stack service. A subsequent normal avatar-stack start therefore has
exactly the same service set and WebRTC/recording behavior as before this
feature was configured.

## Account-free lifecycle test

Test mode uses local GStreamer video/audio test sources and fake sinks. It does
not connect to signaling or RTMP and does not require Unreal, a GPU, TURN, a
streaming account, or the encrypted game image:

```bash
./scripts/embody_cli.sh broadcast configure --test
./scripts/embody_cli.sh broadcast start
./scripts/embody_cli.sh broadcast status --json
./scripts/embody_cli.sh broadcast recover
./scripts/embody_cli.sh broadcast stop
./scripts/embody_cli.sh broadcast configure --disable
```

Only the existing public `recorder-control` service image is needed because it
already contains the GStreamer/WebRTC runtime; the encrypted game image is
never inspected or pulled by broadcast commands.

Developers can run the no-Docker/no-GPU operator lifecycle tests with:

```bash
pytest -q tools/broadcast/tests
```

Those tests use a fake Docker executable and assert that destination contents do
not reach Compose arguments/environment snapshots or status output.

## Local paths and advanced overrides

- Private operator directory: `~/.embody/broadcast`
- Override for testing/host policy: `EMBODY_BROADCAST_DIR=/secure/path`
- Compose project: `vtuber-broadcast`
- Container: `vtuber-broadcast-bridge`
- Source network: external Docker network `vtuber_network`
- Optional runtime image repository override: `EMBODY_BROADCAST_IMAGE_REPOSITORY=<repository>` (tagged with `EMBODY_SERVICE_IMAGE_TAG`, default `latest`)

Useful retry/encoding environment overrides (set in the invoking environment
before `broadcast start`/`recover`):

- `EMBODY_BROADCAST_RETRY_INITIAL_SECONDS` (default `2`)
- `EMBODY_BROADCAST_RETRY_MAX_SECONDS` (default `30`)
- `EMBODY_BROADCAST_VIDEO_BITRATE_KBPS` (VP8/VP9 transcode only; default `6000`)
- `EMBODY_BROADCAST_AUDIO_BITRATE_BPS` (default `128000`)

These values are non-secret. Destination credentials should remain in the
private destination file flow described above.
