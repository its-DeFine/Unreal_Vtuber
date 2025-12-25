# Orchestrator Edge Rotator (sidecar)

This container runs on the **orchestrator GPU host** and automates the key pieces required to “move an orchestrator between edges” without SSHing into the box:

1) **Host firewall gating** (UFW is common, but we program `iptables` directly): allow only the selected edge IP(s) to reach the orchestrator on the protected ports (e.g. `8080`, `9090`).
2) **Matchmaker target rotation**: update `.env` (writes matchmaker flags into `SIGNALING_EXTRA_ARGS`) and recreate the signaling container so it re-registers with the chosen edge matchmaker.
3) **Per-edge service allowlists**: update `.env` `VTUBER_ALLOWED_ADDRESSES` (used by runner/recorder IP allowlists) and recreate the affected containers so only the selected edge(s) can call them.

It is designed to work even when the stack is “sleeping” (only `orchestrator-health` is up) by recreating containers with `docker compose up --no-start ...`.

## Control plane contract

The rotator polls a URL (API Gateway / control plane) for desired configuration.

Request:
- `GET $EDGE_CONFIG_URL?orchestrator_id=<ORCHESTRATOR_ID>`
- Optional `Authorization: Bearer $EDGE_CONFIG_TOKEN`

Response JSON (minimal):
```json
{
  "edge_id": "stg-w2",
  "matchmaker_host": "staging-edge-w2.app.embody.zone",
  "matchmaker_port": 8889,
  "edge_cidrs": ["35.164.115.11/32"]
}
```

Note:
- For `VTUBER_ALLOWED_ADDRESSES`, the rotator can only translate `/32` edge CIDRs into allowed IP strings (runner/recorder do strict IP string matching; no CIDR support).

Accepted aliases:
- `matchmaker_address` instead of `matchmaker_host`
- `edge_ip` / `edge_ips` (IPv4s; converted to `/32`)
- `edge_host` (DNS; resolved to A records; converted to `/32`)
- `turn_external_ip` (optional; if `EDGE_UPDATE_TURN=true`, updates `.env.turn`; if omitted and exactly one `/32` edge IP is selected, the rotator uses that as a fallback)

## Environment

Required:
- `EDGE_CONFIG_URL`

Optional:
- `EDGE_CONFIG_TOKEN`
- `EDGE_POLL_INTERVAL_SECONDS` (default `15`)
- `EDGE_PROJECT_DIR` (default `/home/ubuntu/Unreal_Vtuber`) – must match the host path (see compose wiring).
- `EDGE_ALLOW_PORTS` (default `8080/tcp,8888/tcp,8889/tcp,9090/tcp,9877/tcp,3478/tcp,3478/udp,49160-49200/udp`)
  - Note: the stack exposes signaling as `8080:80`; the rotator also enforces `80/tcp` so the `8080` allowlist actually applies.
- `EDGE_ENFORCE_EXCLUSIVE` (default `true`) – add DROP rules for the managed ports so only edge CIDRs can reach them.
- `EDGE_SIGNALING_PUBLIC_PORT` (default `8080`) – used when generating matchmaker args (`--public_port`).
- `EDGE_MATCHMAKER_DEFAULT_PORT` (default `8889`)
- `EDGE_UPDATE_TURN` (default `false`) – if enabled and control plane returns `turn_external_ip`, rewrite `.env.turn` and recreate `turn-server`.
- `EDGE_WAKE_SETTLE_SECONDS` (default `60`) – after a wake transition, avoid restarts during this window.
- `EDGE_FIREWALL_EXTRA_CIDRS` (default empty) – additional CIDRs to allow (ex: Payments health checker IP).
- `EDGE_LOCAL_ALLOWLIST` (default `127.0.0.1,::1,172.17.0.1,172.18.0.1`) – base tokens prepended to `VTUBER_ALLOWED_ADDRESSES` when the rotator rewrites it.
- `EDGE_POWER_ALLOWED_IPS_FILE` (default `/var/lib/vtuber/power-state/power_allowed_ips.txt`) – writes edge CIDRs for `/power` allowlisting.

## Security notes

- This container needs `NET_ADMIN` + `network_mode: host` to program host firewall rules.
- It needs access to the Docker daemon (`/var/run/docker.sock`) to recreate the signaling container.
- It does **not** require AWS permissions (it does not touch EC2 security groups).
- Firewall rules are installed via `iptables` in `DOCKER-USER` (to cover docker-mapped ports) and `INPUT`.
