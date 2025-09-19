# Unreal VTuber

Lightweight Pixel Streaming stack for the Embody build, coupled with Livepeer BYOC infrastructure and observability tooling. The legacy NeuroSync (S1) and Kokoro TTS containers have been fully removed – audio and blendshapes are now generated inside the packaged Unreal runtime.

## Quick Start

1. **Clone + configure**
   ```bash
   git clone https://github.com/its-DeFine/Unreal_Vtuber.git
   cd Unreal_Vtuber
   cp .env.example .env
   cp .env.unreal.example .env.unreal
   ```
   Populate the `.env` file with Livepeer/manager credentials as needed. Update `.env.unreal` with your packaged game location details.

2. **Launch the stack**
   ```bash
   ./scripts/start_vtuber_unreal.sh start -d
   ```
   The helper script stitches together `docker-compose.yml` (infrastructure + Livepeer worker) and `docker-compose.unreal.yml` (TURN, signaling, packaged game).

3. **Validate Pixel Streaming**
   * Pixel Streaming UI: `http://localhost:8080`
   * Unreal TCP interface (inside container): `vtuber-unreal-game:7777`
   * Send a sample BYOB payload:
     ```bash
     ./scripts/start_vtuber_unreal.sh test
     ```
     The command feeds `TTS_BYOB_/opt/embody/sample-15s.mp3` to the in-container TCP loopback.

4. **Add new audio assets**
   ```bash
   scp your.mp3 ubuntu@<ec2-host>:/home/ubuntu/
   sudo docker cp your.mp3 vtuber-unreal-game:/opt/embody/
   sudo docker exec vtuber-unreal-game bash -lc 'printf "TTS_BYOB_/opt/embody/your.mp3\r\n" | nc -q 1 127.0.0.1 7777'
   ```

5. **Manage the stack**
   ```bash
   ./scripts/start_vtuber_unreal.sh ps       # container status
   ./scripts/start_vtuber_unreal.sh logs <service>
   ./scripts/start_vtuber_unreal.sh stop
   ```

## Compose Layout

* `docker-compose.yml` – Livepeer worker, Ollama helper, management agent, and monitoring exporters.
* `docker-compose.unreal.yml` – TURN server, signaling server, packaged `vtuber-unreal-game` container.
* `docker-compose.livepeer.yml` – Livepeer orchestrator. Attach this file when you need to run the orchestrator on the same `vtuber_network` bridge shared by the worker.

## Legacy Notes

Historical documentation, NeuroSync assets, Kokoro TTS Dockerfiles, and AutoGen stacks have been removed. Pull an older commit if you need to reference the superseded pipeline.

## Support

Please contact the maintainers for issues or deployment assistance.
