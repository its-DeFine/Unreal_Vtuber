# BYOC Integration for VTuber Autonomy System

## Overview
Livepeer's Bring Your Own Container (BYOC) utility lets us pay external orchestrators to host the Embody VTuber stack. The orchestrator exposes the `agent-net` capability, while the BYOC worker living inside our main compose monitors the health of the Unreal streaming services.

## Current Layout

| Compose file | Purpose |
| --- | --- |
| `docker-compose.yml` | Core Pixel Streaming stack (TURN/signaling via companion file), Livepeer BYOC worker, Ollama helper, management + observability |
| `docker-compose.unreal.yml` | TURN server, signaling server, packaged `vtuber-unreal-game` container |
| `docker-compose.livepeer.yml` | Livepeer orchestrator attached to the shared `vtuber_network` bridge |

The worker and orchestrator live on the same Docker network so capability calls can be routed with zero proxy hops.

## Worker Monitoring Surface

The worker aggregates metrics and health probes for the following services:

- `vtuber-unreal-game` – headless Unreal container that now handles audio + blendshape playback internally
- `vtuber-unreal-signaling` – Pixel Streaming WebRTC signaling layer
- `vtuber-turn-server` – TURN relay for NAT traversal
- `livepeer-worker` itself for capability health
- `vtuber-ollama` – local model runtime (LLM prompts, embeddings)
- Optional broadcast relays such as `nginx_rtmp`

This trimmed scope keeps the BYOB jobs focused on the runtime required for live streaming rather than the deprecated NeuroSync/AutoGen stack.

## Livepeer Service Configuration

```yaml
livepeer-worker:
  environment:
    - CAPABILITY_NAME=agent-net
    - CAPABILITY_PRICE_PER_UNIT=0
    - CONNECTIVITY_PROOF_ENABLED=true
    - MIN_SERVICE_UPTIME=80.0
    - ORCH_URL=http://livepeer-orchestrator:9995

livepeer-orchestrator:
  image: livepeer/go-livepeer:latest
  networks:
    - vtuber_network  # shared with worker/unreal stack
```

## Payment Flow

1. A gateway call (from the central manager or scripted tooling) requests the `agent-net` capability.
2. Livepeer routes the request to the orchestrator associated with that capability.
3. The orchestrator forwards the job to the BYOC worker running in our stack.
4. When the worker reports success, the orchestrator cashes the spectator ticket and the agent earns rewards.

## Testing Checklist

```bash
# Verify worker is broadcasting health
curl http://localhost:9876/health

# Confirm orchestrator registration
sudo docker logs livepeer-orchestrator | grep agent-net

# Spot-check worker access to Unreal stack
sudo docker exec livepeer-worker curl -sf http://vtuber-unreal-signaling:8080 >/dev/null
```

## Next Steps

- Reinstate the gateway payment routines once the new compose split is validated.
- Feed worker metrics into Prometheus (exporter integration pending).
