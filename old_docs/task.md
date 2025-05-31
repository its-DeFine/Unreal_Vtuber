# NeuroSync × Livepeer BYOC – Migration Guide

This document is meant to be handed to your next Cursor (or human) programming session.  
It turns the existing **NeuroSync + Eliza/The-Org** docker-compose stack into a full **Livepeer generic-container pipeline** deployment so you can bill for inference through an on-chain orches­trator while preserving your current development workflow.

---
## 📝 High-Level Goal
Replace the sample `voice-cloning` worker with **NeuroSync** as the worker **without** re-downloading any model checkpoints in the container.  Spin up the remaining BYOC components (orchestrator, gateway, Caddy & web-app) so that:

* `NeuroSync-Core` exposes an HTTP endpoint that the orchestrator can call.
* On start-up NeuroSync registers itself via `/capability/register`.
* Your React front-end – or any other client – talks to `https://{caddy-host}/api/...` and everything just works, including signed headers, payments, SSE streaming and GPU inference.

---
## 0. Prerequisites
1. Docker ≥ 24 + `docker compose` CLI.
2. Nvidia GPU with driver & runtime.
3. Domain name (or wildcard DNS to your server) if you plan to test TLS with public certs.
4. ETH address with funds **if you want on-chain payments**.

---
## 1. Repo Layout After Migration
```
./
├─ docker-compose.yml              # existing NeuroSync + Eliza stack ← we will extend
├─ docker-compose.byoc.yml         # new override file (worker + orch + gateway + caddy)
├─ neurosync-worker/
│   ├─ entrypoint.sh               # registers capability then starts NeuroSync HTTP server
│   └─ server_adapter.py           # thin Flask/FastAPI wrapper that calls NeuroSync internals
└─ webapp-byoc/                    # copy of livepeer voice-cloning front-end adjusted to your API paths
```
> **Tip:** keep BYOC additions in a separate compose file so you can `docker compose -f docker-compose.yml -f docker-compose.byoc.yml up` and disable BYOC by simply omitting the override.

---
## 2. Tasks In Order

### 2.1 Fork & port the Python registration logic
1. Copy `/voice-cloning/server.py` → `neurosync-worker/server_adapter.py`.
2. Strip the `check_models_exist()` function – NeuroSync already has its checkpoints.
3. Replace the `infer()` stub so it calls into NeuroSync's public Python API (or direct gRPC/REST) and writes its response to a temp file or stream.
4. Keep the **registration code and `InferHandler` HTTP server** mostly intact.
5. Add **structured logging** (`logging.getLogger("neurosync.worker")`).  Wrap every external call with `logger.debug(...)`.

### 2.2 Create a tiny entrypoint
`entrypoint.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
python /app/server_adapter.py
```
Grant `chmod +x` in the Dockerfile.

### 2.3 Extend the NeuroSync Dockerfile
* Add `COPY neurosync-worker/ /app/` right before the final CMD.
* Switch the **CMD** to `entrypoint.sh` (or call it via `bash -c`).
* Install extra deps: `pip install requests requests-toolbelt huggingface_hub[cli]`.

### 2.4 docker-compose.byoc.yml (new)
```yaml
services:
  # === BYOC worker (inside same image as NeuroSync) ===
  neurosync-worker:
    build:
      context: .
      dockerfile: ./NeuroSync-Core/dockerfile  # reuse existing image definition
    container_name: neurosync_byoc_worker
    command: ["/app/entrypoint.sh"]
    env_file:
      - ./env_files/.neurosync.env
    environment:
      - ORCH_URL=https://orchestrator:9995
      - ORCH_SECRET=orch-secret
      - CAPABILITY_NAME=neurosync-s1
      - CAPABILITY_DESCRIPTION=semantic computation brain
      - CAPABILITY_URL=http://neurosync-worker:9876
      - CAPABILITY_PRICE_PER_UNIT=10
      - CAPABILITY_PRICE_SCALING=1
      - CAPABILITY_CAPACITY=1
    networks:
      - byoc
    runtime: nvidia
    depends_on:
      - orchestrator

  # === Orchestrator ===
  orchestrator:
    image: adastravideo/go-livepeer:dynamic-capabilities-2
    container_name: byoc-orchestrator
    volumes:
      - ./data/orchestrator:/data
    command: ["-orchestrator", "-orchSecret=orch-secret", "-serviceAddr=0.0.0.0:9995", "-v=5", "-network=offchain", "-dataDir=/data", "-pricePerUnit=1"]
    ports:
      - "9995:9995"
    networks:
      - byoc

  # === Gateway (optional for on-chain) ===
  gateway:
    image: adastravideo/go-livepeer:dynamic-capabilities-2
    container_name: byoc-gateway
    command: ["-gateway", "-orchAddr=https://orchestrator:9995", "-httpAddr=0.0.0.0:9999", "-network=offchain"]
    ports:
      - "9999:9999"
    volumes:
      - ./data/gateway:/data
    networks:
      - byoc

  # === Caddy ===
  caddy:
    image: caddy:latest
    container_name: byoc-caddy
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./webapp-byoc/dist:/var/www/html/app
    ports:
      - "8088:8088"
    networks:
      - byoc

networks:
  byoc:
    driver: bridge
```
> **Note:** all BYOC services share the same custom network `byoc` so that the worker can reach the orchestrator via `https://orchestrator:9995` and vice-versa.

### 2.5 Caddyfile
```caddyfile
:8088 {
  root * /var/www/html/app
  file_server

  handle_path /api/* {
    reverse_proxy https://orchestrator:9995 {
      transport http {
        tls_insecure_skip_verify  # because orchestrator uses self-signed certs in dev
      }
    }
  }
}
```

### 2.6 Front-end (VTuber flavour)
1. Copy `/voice-cloning/webapp/` → `webapp-byoc/`.
2. Update the API base path and request construction so the front-end sends the **NeurosyncVTuberRequest** JSON body (see schema below) to `/process/request/v1/vtuber/start`.
3. Ensure headers `Livepeer-Job` and `Livepeer-Job-Payment` are still attached.
4. Run `npm install && npm run build` – the static files land in `webapp-byoc/dist` (already mounted into Caddy).

### 2.7 Run Everything
```bash
docker network create byoc || true
# build & start both existing core stack and BYOC overlay
docker compose -f docker-compose.yml -f docker-compose.byoc.yml up --build
```
*Open* `http://localhost:8088` → connect wallet → trigger job → inspect logs.

---
## 3. Architectural Suggestions & Best Practices
1. **Health Checks** – add `/healthz` endpoint in `server_adapter.py`; orchestrator will soon support auto-deregistration of unhealthy workers.
2. **Horizontal Scaling** – spin up multiple `neurosync-worker` replicas with distinct container names; orchestrator will load-balance by round-robin while respecting each replica's `capacity`.
3. **Observability** – ship container logs to Loki or Datadog; tag with `capability`, `request_id`, `duration_ms`.
4. **TLS** – in production put orchestrator behind Caddy/Nginx and give it a trusted cert so you can remove `tls_insecure_skip_verify`.
5. **Security** – rotate `orch-secret`; don't hard-code it in Git; use Docker secrets or Vault.
6. **Payments** – start with `-network=offchain` (free); once stable, switch to `arbitrum-one-mainnet`, point gateway to funded key.

---
## 4. Checklist for the Next Coding Session
- [x] Port and test `server_adapter.py` with a single NeuroSync inference call (text-echo prototype).
- [x] Update Dockerfile & verify GPU visibility (`torch.cuda.is_available()`).
- [x] Compose up the BYOC overlay; ensure capability registers.
- [x] Front-end successfully fetches `/process/token` then `/process/request/start-echo-test`.
- [ ] Verify orchestrator capacity counters are decremented/incremented correctly.
- [x] Add structured JSON logs.

### 2.8 Implement VTuber job endpoint in NeuroSync
* Add a new route **`/v1/vtuber/start`** inside `server_adapter.py` (or reuse the generic POST handler) that:
  1. Parses the incoming body against the `NeurosyncVTuberRequest` schema (use `jsonschema` for validation; return 400 on failure).
  2. Boots / configures NeuroSync with the requested `character`, `knowledge_source_url`, and `job_id`.
  3. Streams **Server-Sent Events** or **chunked JSON** where each event matches the `NeurosyncRealtimeFrame` schema.  Include `sequence_number` and base-64 audio if available.
  4. Stops automatically when `model_time_seconds` elapses or on client disconnect.

* Emit structured logs for: request received, validation errors, start/stop timestamps, per-frame latency.

_Append both schema definitions (request & frame) to the end of the file or include them in your repo's `schemas/` folder for re-use and testing._

Happy hacking 🚀 – your future self will thank you for the logs! 

## 5. Next Milestones – VTuber Job Integration

- [ ] Replace the temporary `start-echo-test` endpoint with real streaming logic once NeuroSync Core exposes the required APIs.
- [ ] Wire `server_adapter.py` to call NeuroSync-Core's `/stream_text_to_blendshapes` (or an equivalent internal function) so audio & blendshapes are produced by the engine rather than a dummy echo.
- [ ] Refactor capability env-vars: use `CAPABILITY_NAME=start-echo-test` during development, then migrate to `CAPABILITY_NAME=v1-vtuber-start` (or similar) for production.
- [ ] Extend the front-end service (rename `textEcho.ts` → `vtuberService.ts`) to send a full `NeurosyncVTuberRequest` JSON body and consume chunked JSON / SSE frames.
- [ ] Define TypeScript interfaces for `NeurosyncVTuberRequest` & `NeurosyncRealtimeFrame` so UI code is strongly typed.
- [ ] Add unit tests under `neurosync-worker/tests/` validating schema adherence, 200-OK, and the happy-path streaming response.
- [ ] Document the contract (request + frame) in `docs/byoc-vtuber-capability.md`.

### Notes on worker ↔ NeuroSync-Core integration

The BYOC worker should remain a **thin adapter**:
1. Perform capability registration and JSON validation.
2. Delegate heavy lifting to NeuroSync-Core (either via an in-process import or an HTTP call to the local Flask server).
3. Stream results back to the orchestrator as chunked `application/json` which the gateway already proxies to the browser.

Recommended path for lowest latency is an *in-process* call – e.g. import `neurosync.server.app` and reuse its `stream_text_to_blendshapes()` logic – to avoid an extra loopback HTTP hop.  Keep the loopback option as a fallback for heterogeneous deployments. 