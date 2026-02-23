# Agent Negotiator (MCP)

`agent-negotiator` exposes a customer-facing MCP endpoint for orchestrator workload negotiation.

It supports two deployment modes:

1. Standalone container/service (current compose overlay)
2. Embedded NanoClaw extension (`nanoclaw.plugin.json` + `nanoclaw.extensions`)

## Customer-facing MCP tools

- `orchestrator_info`
- `negotiate_quote`
- `accept_quote`
- `session_status`
- `cancel_session`

## Internal safety controls

- Per-IP rate limit
- Killswitch (`NEGOTIATOR_KILLSWITCH=1`)
- SQLite state-machine enforcement for quotes/bookings
- JSONL audit log

## Standalone deployment

Use compose overlay:

```bash
docker compose -f docker-compose.unreal.yml -f docker-compose.negotiator.yml up -d
```

Relevant env values:

- `NEGOTIATOR_HOST` (default `0.0.0.0`)
- `NEGOTIATOR_PORT` (default `9100`)
- `NEGOTIATOR_CONFIG_FILE` (default `/config/negotiator.yaml`)
- `NEGOTIATOR_RATE_LIMIT` (default `30` req/min per IP)
- `NEGOTIATOR_KILLSWITCH` (`0` or `1`)
- `NEGOTIATOR_SIGNALING_PUBLIC_BASE_URL` (optional; routable base URL returned in `signaling_url`)
- `NEGOTIATOR_SIGNALING_CHECK_BASE_URL` (optional; internal base URL used for signaling health polls)

## NanoClaw embedded mode

The package publishes a NanoClaw extension entrypoint:

- `package.json` → `nanoclaw.extensions: ["./dist/nanoclaw/plugin.js"]`
- `nanoclaw.plugin.json` defines id/config schema/channel id `mcp-negotiation`

When enabled, the plugin registers:

- Channel: `mcp-negotiation`
- Service: `agent-negotiator-mcp`
- Command: `/negotiator` status

The plugin will auto-generate a default negotiator YAML under plugin `stateDir` when no config file is provided.

## Verification

From `agent-negotiator/`:

```bash
npm run typecheck
npm test
npm run verify
```
