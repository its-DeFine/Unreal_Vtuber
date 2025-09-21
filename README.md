# Unreal VTuber

> **Disclaimer**
> By deploying the orchestrator and associated services described in this repository, you acknowledge that the services are provided by Atumera LLC and agree to the Terms & Conditions and Privacy Policy located in `legal/`.

> **Docker network tip**
> The compose files expect a bridge called `vtuber_network` with the label `com.docker.compose.network=vtuber_network`. Let Compose create it automatically, or run:
> `docker network create --label com.docker.compose.network=vtuber_network vtuber_network`
> If you already created `vtuber_network` without that label, remove it first with `docker network rm vtuber_network` before launching the stack.


## Orchestrator Onboarding

 **Prep the machine**
   - Install NVIDIA drivers, Docker Engine, and Docker Compose.
   - Open TCP `9995` to the internet for the Livepeer orchestrator, also open `8080`, `8888`, `8889`, and TURN ports `3478` plus `49160-49200/udp`.
   - Whitelist `86.106.133.188` on TCP `8080` so that we can access the pixel streamed game instance.

2. **Configure secrets**
   - Copy `cp .example.env .env` and set `ORCHESTRATOR_HOST`, `LIVEPEER_ORCH_SECRET`, and Ethereum addresses.
   - Place your keystore JSON in `config/keystore/` and write the passphrase to `config/ethpass`.
   - (Optional) Generate a throwaway wallet with `scripts/generate_livepeer_wallet.sh` and fund it with Arbitrum ETH.
   - Use the capability name you filled in the onboarding form(CAPABILITY_NAME).

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
