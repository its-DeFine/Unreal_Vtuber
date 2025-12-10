Whitelist sidecar for Pixel Streaming hosts.

It reconciles iptables rules on the host to only allow specified CIDRs to reach the Pixel Streaming stack ports. Runs with `CAP_NET_ADMIN` and `network_mode: host` in compose.

Environment variables:

- `CONTROL_PLANE_URL` – Optional URL returning JSON with `allowed_ips`/`allowlist`/`allow` array. Supports `{node_id}` placeholder.
- `NODE_ID` – Injected into `CONTROL_PLANE_URL` when `{node_id}` is present.
- `API_TOKEN` – Bearer token for the control-plane request.
- `WHITELIST_STATIC_CIDRS` – Comma-separated static CIDRs used when control-plane fetch fails or is unset.
- `WHITELIST_PORTS` – Comma-separated ports to guard (default: `80,8888,8889,9877`).
- `POLL_INTERVAL_SECONDS` – How often to reconcile (default: `5`).
- `FAIL_OPEN` – When true (default), skip drops if no allowlist is available; set to `false` to fail-closed.
- `WHITELIST_CHAIN` – Custom chain name (default: `WHITELIST_AGENT`).

The agent creates/flushes a dedicated chain, adds loopback + established passthrough, allows the configured CIDRs on the target ports, and appends a drop rule for those ports.
