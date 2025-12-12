# Pixel Streaming Gating Architecture (Edge + Control Plane + Sidecar)

## Overview
Goal: gate user access to orchestrators without per-user IP whitelisting on the host. Use a fixed set of edge IPs, a control plane that issues short-lived tokens, and a sidecar that enforces host-level firewall rules for only the edge CIDRs.

## Components
- **User client**: Browser hitting your website.
- **Edge/relay**: Your fixed IP(s) per region (reverse proxy / TURN / ingress). Users connect here. Edge enforces auth and issues short-lived access tokens.
- **Control plane**: API that picks an orchestrator, mints tokens, and returns allowlist (CIDRs/ports) to sidecars. Also stores orchestrator health/latency.
- **Sidecar**: Runs on each orchestrator (iptables NET_ADMIN). Polls the control plane for allowed CIDRs/ports and applies DROP/ACCEPT rules. Can also use static env allowlist.
- **Orchestrator**: Pixel Streaming signaling + game + runner/recorder. Validates tokens presented by clients (JWT/HMAC) at signaling/runner.

## Flow (happy path)
1) User → your website → clicks “Start”.
2) Control plane selects nearest orchestrator (latency/region) and mints a short-lived token.
3) Control plane (or pre-baked config) ensures sidecar on that orchestrator allows only the edge/relay CIDRs (static) and necessary ports.
4) Website returns: orchestrator endpoints (HTTP/WS) + token. User connects via the edge/relay IP.
5) Sidecar allows traffic from edge CIDRs; signaling/runner validate the token; session proceeds.
6) Token expires → new token required; sidecar already limits exposure to edge IPs only.

## Why fixed edge IPs
- No churn in host allowlists; sidecars are pre-seeded with edge CIDRs.
- You can spin edge instances up/down behind stable IPs (Elastic IPs/static addresses) without updating orchestrator rules.
- Geo routing handled at the edge; orchestrators stay locked down to a small set of ingress IPs.

### Edge IP strategy (practical)
- Keep a small, fixed pool of edge IPs per region (e.g., a couple of EIPs per region). Pre-whitelist these in sidecars (and any upstream firewall).
- “Autoscale behind static IPs” = run a load balancer/NLB or an instance group that always presents the same public IP(s); you can add/remove edge instances without changing the IPs the orchestrators see.
- You cannot “teleport” one IP between regions for latency; use separate IPs per region and have the control plane route users to the nearest region’s edge IP.
- If you spin up edges with new IPs on demand, you must automate allowlist updates (sidecars + any upstream firewall) for all orchestrators before handing out the new endpoint—doable but more brittle than using a stable pool.

## Control plane contract (sidecar)
- Sidecar polls `CONTROL_PLANE_URL` with optional `?node_id=<NODE_ID>` and `Authorization: Bearer <API_TOKEN>`.
- Response JSON:
  ```json
  { "cidrs": ["203.0.113.10/32"], "ports": ["8080","8888","8889","7777","9877","3478","49160-49200/udp"] }
  ```
- Sidecar applies ACCEPT for those CIDRs/ports and DROP otherwise (fail-open optional).
- If no control plane URL is set, it uses static `WHITELIST_CIDRS`/`WHITELIST_PORTS` from env.
- This removes manual whitelisting on orchestrators: add/remove edge IPs in the control plane, sidecars pick it up on the next poll.

## Token validation (app layer)
- Token includes orchestrator id, expiry, and allowed services.
- Signaling/runner (or a thin shim) validate JWT/HMAC token on connect/start.
- Edge issues tokens after authenticating/authorizing the user.

## Operational steps
- Reserve a small, stable set of edge IPs per region. Pre-allow these in sidecar (and any upstream firewall if present).
- Deploy sidecar on each orchestrator with CONTROL_PLANE_URL, API_TOKEN, NODE_ID, and port list.
- Control plane stores orchestrator health/latency and selects node per session.
- Website calls control plane to get {orchestrator, token, endpoints}; client connects via edge IP.

## ASCII diagram

```
User ──HTTPS──> Edge/Relay (fixed IPs) ──> Control Plane (select + token)
                          │                        │
                          │                        └─ instruct sidecar allowlist (cidrs/ports)
                          │
                          └─ WebRTC/WS with token ─────────────────────> Orchestrator
                                                │
                                                └─ Sidecar iptables: allow edge CIDRs only; drop others
```

## Notes
- Sidecar does not open upstream firewalls (SG/UFW); ensure ports are allowed there if present.
- If you use UFW, open the needed ports and let the sidecar do fine-grained gating.
- Avoid per-user IP whitelisting; use fixed edge CIDRs + tokens for per-session control.
