# Agent Negotiator (MCP)

`agent-negotiator` exposes a customer-facing MCP endpoint for orchestrator workload negotiation.

Current deployment is a temporary OpenClaw compatibility bridge:

1. Embedded OpenClaw-compatible extension (`openclaw.plugin.json` + `openclaw.extensions`)
2. Standalone startup is intentionally disabled (`src/index.ts` exits with an error)

Planned follow-up: revert this bridge to the hardened NanoClaw implementation once the secure runtime path is finalized.

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

## OpenClaw-style auth token

To match existing Chief/Athena auth behavior, set:

- `OPENCLAW_GATEWAY_TOKEN=<secret>`

When set, all MCP endpoints except `/health` require:

- `Authorization: Bearer <secret>` or
- `x-openclaw-token: <secret>`

## API model policy

`agent-negotiator` enforces API-backed model configuration in `negotiator.yaml`:

- Allowed `agent.provider`: `openai`, `anthropic`
- `agent.model` must be an API model ID
- Local/self-hosted markers (e.g. `ollama`, `llama.cpp`, `gguf`, `localhost`, `file:`) are rejected at config load time

## Verification

From `agent-negotiator/`:

```bash
npm run typecheck
npm test
npm run verify
```
