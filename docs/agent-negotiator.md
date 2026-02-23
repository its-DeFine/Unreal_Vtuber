# Agent Negotiator (MCP)

`agent-negotiator` exposes a customer-facing MCP endpoint for orchestrator workload negotiation.

Deployment mode is NanoClaw-only:

1. Embedded NanoClaw extension (`nanoclaw.plugin.json` + `nanoclaw.extensions`)
2. Standalone startup is intentionally disabled (`src/index.ts` exits with an error)

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

## NanoClaw embedded mode

The package publishes a NanoClaw extension entrypoint:

- `package.json` → `main: "./dist/nanoclaw/index.js"`
- `package.json` → `nanoclaw.extensions: ["./dist/nanoclaw/plugin.js"]`
- `nanoclaw.plugin.json` defines id/config schema/channel id `mcp-negotiation`

When enabled, the plugin registers:

- Channel: `mcp-negotiation`
- Service: `agent-negotiator-mcp`
- Command: `/negotiator` status

The plugin will auto-generate a default negotiator YAML under plugin `stateDir` when no config file is provided.

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
