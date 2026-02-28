# Agent Negotiator (MCP)

`agent-negotiator` exposes a customer-facing MCP endpoint for orchestrator workload negotiation.

Current deployment runs as an embedded claw plugin service. Standalone startup is intentionally disabled (`src/index.ts` exits with an error).

## Customer-facing MCP tools

- `orchestrator_info`
- `fleet_overview`
- `negotiate_quote`
- `accept_quote`
- `session_status`
- `update_webrtc_connection`
- `validate_renter_control`
- `cancel_session`

`accept_quote` and `session_status` return a `session.control` block for active leases:

- `avatar_id`
- `runner_url`
- `runner_execute_url` (`POST /scripts/execute`)
- `runner_status_url_template` (`GET /scripts/{session_id}`)
- `game_tcp_port`

This enables deterministic post-lease embodied control through the script-runner path.

## Fleet allocator flow

The negotiator supports multi-orchestrator allocation for workstation/remote-ops fleets:

1. `fleet_overview` returns a per-orchestrator capacity snapshot.
2. `negotiate_quote` picks an orchestrator automatically (`lowest_price_then_capacity`) or honors `preferred_orchestrator_id`.
3. `accept_quote` provisions on the orchestrator bound to the quote and returns `orchestrator_id` in the response.

The consumer skill only needs one MCP endpoint; allocator routing is handled server-side.
See also: `docs/consumer-skill-flow.md` for the step-by-step consumer contract.

## Direct WebRTC route selection

`accept_quote` accepts an optional `connection` object so the renter can choose the direct WebRTC route at booking time:

- `direct_webrtc_base_url` (full base URL, e.g. `https://203.0.113.10`)
- `direct_webrtc_ip` (IP/host shortcut, with optional `scheme` of `http` or `https`)

Provide exactly one of `direct_webrtc_base_url` or `direct_webrtc_ip`.

When provided, provisioned URLs (`signaling_url`, `session.control.runner_url`) are generated from that selected route base. Responses also include:

- `session.connection_route.base_url`
- `session.connection_route.source` (`base_url`, `ip`, or `default`)

`update_webrtc_connection` lets the renter rotate the route later (for example, after IP allowlist changes). It updates the booking signaling URL and returns updated control endpoints for reconnect.

`validate_renter_control` adds a deterministic validation path that executes a command sequence through `runner_execute_url` and confirms terminal completion from `runner_status_url_template`.

## Internal safety controls

- Per-IP rate limit
- Killswitch (`NEGOTIATOR_KILLSWITCH=1`)
- SQLite state-machine enforcement for quotes/bookings
- JSONL audit log

## Embedded Claw Mode (temporary OpenClaw compatibility)

The package currently publishes an OpenClaw-compatible extension entrypoint:

- `package.json` → `main: "./dist/nanoclaw/index.js"`
- `package.json` → `openclaw.extensions: ["./dist/nanoclaw/plugin.js"]` (temporary bridge)
- `openclaw.plugin.json` defines id/config schema/channel id `mcp-negotiation`
- `nanoclaw.plugin.json` is kept only for forward compatibility with the planned hardened NanoClaw runtime

When enabled, the plugin registers:

- Channel: `mcp-negotiation`
- Service: `agent-negotiator-mcp`
- Command: `/negotiator` status

The plugin will auto-generate a default negotiator YAML under plugin `stateDir` when no config file is provided.

## API token auth

Set:

- `NEGOTIATOR_API_TOKEN=<secret>`

When set, all MCP endpoints except `/health` require:

- `Authorization: Bearer <secret>`

## Fleet registry (optional)

Set:

- `NEGOTIATOR_FLEET_REGISTRY_FILE=/path/to/fleet.yaml`

Example:

```yaml
orchestrators:
  - id: workstation-a
    health_url: http://workstation-a:9090
    signaling_public_base_url: https://stream-a.example.com
    max_concurrent_sessions: 2
  - id: workstation-b
    health_url: http://workstation-b:9090
    signaling_public_base_url: https://stream-b.example.com
    max_concurrent_sessions: 2
```

## Skill policy rails (PR223)

Set `NEGOTIATOR_SKILL_POLICY_FILE` to a `SKILL.md` containing a fenced yaml/json `negotiator_policy` block.

When configured, `accept_quote` enforces:

- consumer entitlement allowlist from `skill.md`
- paid rail proof (`402` + `ERC-4337` user operation hash)
- zero-price signed-message proof (HMAC signature with secret from env, default `NEGOTIATOR_SIGNED_MESSAGE_SECRET`)

## Verification

From `agent-negotiator/`:

```bash
npm run typecheck
npm test
npm run verify
```
