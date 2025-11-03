# Unreal Integration (BYOB Pipeline)

This document captures the current Pixel Streaming pipeline after retiring the NeuroSync (S1) stack and local Kokoro TTS services. All facial blendshapes and audio playback are now generated directly inside the packaged Unreal container.

## Stack Overview

The runtime stack now lives across two repositories:

* `Embody-Inc/payments-backend` – Docker Compose project that monitors the Unreal services and schedules orchestrator payouts.
* `docker-compose.unreal.yml` (this repo) – TURN, signaling, and the packaged `vtuber-unreal-game` container.

No additional application containers are required for S1/TTS processing.

## Launching the stack

```bash
./scripts/start_vtuber_unreal.sh start -d
```

An orchestrator registration helper (`orchestrator-registration` service) now runs alongside the Unreal compose file. Configure `PAYMENTS_API_URL` plus the `ORCHESTRATOR_*` variables in `.env` so the helper can post to the payments backend when the stack boots. Start the backend independently from the `Embody-Inc/payments-backend` project. The helper retries with backoff for up to five minutes but exits cleanly even if the backend is unreachable.

The helper script will:

1. Ensure `vtuber_network` exists.
2. Load values from `.env` and `.env.unreal` (create them from the provided examples if missing).
3. Start the Unreal Pixel Streaming compose file. Launch the payments backend from its dedicated repo when payouts are required.

After the services come up in detached mode you should see:

* Pixel Streaming UI – `http://localhost:8080`
* Unreal TCP loopback interface – reachable **inside** `vtuber-unreal-game` on `127.0.0.1:7777`

Use `./scripts/start_vtuber_unreal.sh ps` to confirm container status or `./scripts/start_vtuber_unreal.sh logs unreal-game` for tailing output.

## Sending speech commands

The Unreal build only accepts BYOB (`bring your own bytes`) playback requests from inside the container. Use the helper script’s `test` command or issue your own payloads:

```bash
./scripts/start_vtuber_unreal.sh test
# or manually
sudo docker exec vtuber-unreal-game bash -lc \
  'printf "TTS_BYOB_/opt/embody/sample-15s.mp3\r\n" | nc -q 1 127.0.0.1 7777'
```

A carriage-return/line-feed terminator (`\r\n`) is required. Replace the path with any MP3 that exists inside the container. The default image ships with `/opt/embody/sample-15s.mp3` for quick validation.

## Updating audio assets

1. Copy the new file onto the EC2 host: `scp local.mp3 ubuntu@<host>:/home/ubuntu/`.
2. Inject it into the container: `sudo docker cp local.mp3 vtuber-unreal-game:/opt/embody/`.
3. Trigger playback with `TTS_BYOB_/opt/embody/local.mp3\r\n`.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| No audio despite command | Exec **inside** `vtuber-unreal-game`; host-level `nc` will be ignored.
| Command hangs | Ensure `nc` is available in the container (`sudo docker exec vtuber-unreal-game which nc`).
| Pixel Streaming page offline | Confirm `vtuber-unreal-signaling` is healthy (`docker ps`) and ports 8080/8888/8889 are not blocked.
| TURN handshakes failing | Validate TURN credentials in `.env.turn` and that `vtuber-turn-server` is running.

## Legacy components

* All NeuroSync S1, SCB, Kokoro TTS, and AutoGen containers have been removed from the deployment.
* Historical troubleshooting docs have been archived in git history. Pull an older commit if you need reference material for the deprecated stack.
