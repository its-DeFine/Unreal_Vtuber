# Unreal VTuber

> **Disclaimer**
> By deploying the orchestrator and associated services described in this repository, you acknowledge that the services are provided by Atumera LLC and agree to the Terms & Conditions and Privacy Policy located in `legal/`.


## Quick Start

1. **Clone + configure**
   ```bash
   git clone https://github.com/its-DeFine/Unreal_Vtuber.git
   cd Unreal_Vtuber
   cp .example.env .env
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

## Orchestrator Onboarding

1. **Prep the machine**
   - Install NVIDIA drivers, Docker Engine, and Docker Compose.
   - Open TCP `9995` to the internet for the Livepeer orchestrator. If you plan to expose Pixel Streaming, also open `8080`, `8888`, `8889`, and TURN ports `3478` plus `49160-49200/udp`.
   - Whitelist `86.106.133.188` on TCP `8080` so the Embody job manager can reach your signaling server.

2. **Configure secrets**
   - Copy `cp .example.env .env` and set `ORCHESTRATOR_HOST`, `LIVEPEER_ORCH_SECRET`, and Ethereum addresses.
   - Place your keystore JSON in `config/keystore/` and write the passphrase to `config/ethpass`.
   - (Optional) Generate a throwaway wallet with `scripts/generate_livepeer_wallet.sh` and fund it with Arbitrum ETH.

3. **Launch orchestrator, worker, and Unreal stack**
   ```bash
   sudo docker compose -f docker-compose.livepeer.yml up -d && \
   sudo docker compose up -d && \
   sudo docker compose -f docker-compose.yml -f docker-compose.unreal.yml up -d
   ```

4. **Verify**
   - `curl -k https://<public-ip>:9995/process/token` should return HTTP `400`.
   - `sudo docker compose -f docker-compose.livepeer.yml logs livepeer-orchestrator --tail=50` should show `Unlocked ETH account` and `Listening for RPC`.
   - `sudo docker compose logs livepeer-worker --tail=50` should report the capability registered at `http://livepeer-worker:9876`.

## Legacy Notes

Historical documentation, NeuroSync assets, Kokoro TTS Dockerfiles, and AutoGen stacks have been removed. Pull an older commit if you need to reference the superseded pipeline.

## Support

Please contact the maintainers for issues or deployment assistance.
