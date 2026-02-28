# Skill: add-mcp-negotiation

Purpose: add an embedded MCP negotiation channel to an orchestrator using NanoClaw plugin conventions, while preserving standalone execution support.

## What this skill installs

1. NanoClaw plugin wiring
- `nanoclaw.plugin.json`
- `package.json` `nanoclaw.extensions` metadata
- `src/nanoclaw/plugin.ts`
- `src/nanoclaw/channel.ts`
- `src/nanoclaw/plugin-config.ts`
- `src/nanoclaw/default-config.ts`

2. Shared negotiator lifecycle
- `src/service.ts`
- `src/index.ts` reworked to call shared lifecycle for standalone mode

3. Existing negotiation system (kept)
- `src/channels/mcp.ts`
- `src/negotiation/*`

## Implementation rules

1. Keep hard business boundaries in orchestrator process
- Price bounds and capacity checks stay in `src/channels/mcp.ts` + `src/negotiation/*`.
- Agent reasoning prompt must not be the only enforcement point.

2. Keep two run modes with shared internals
- Standalone: `node dist/index.js`
- Embedded: NanoClaw loads `dist/nanoclaw/plugin.js` from package metadata

3. Default-safe config behavior
- If plugin config omits `configFile`, write a default YAML under plugin state dir.
- Never crash on missing config file when default can be generated.

4. Registration contract
- Register channel id `mcp-negotiation`.
- Register service id `agent-negotiator-mcp`.
- Optional command: `/negotiator` status.

## Verification checklist

1. Static checks
- `npm run typecheck`

2. Unit/integration
- `npm test`

3. Full flow
- `npm run verify`

4. NanoClaw plugin load smoke test
- Ensure `nanoclaw.plugin.json` exists in package root.
- Ensure `package.json` contains:
  - `nanoclaw.extensions: ["./dist/nanoclaw/plugin.js"]`
  - `channels` includes `mcp-negotiation` in manifest.

## Expected outputs

- Customer tools still available over MCP SSE/HTTP:
  - `orchestrator_info`
  - `negotiate_quote`
  - `accept_quote`
  - `session_status`
  - `cancel_session`
- Internal safety systems still active:
  - rate limiter
  - killswitch
  - SQLite state machine
  - JSONL audit log

## Known non-goals

- This skill does not implement cross-orchestrator agent mesh.
- This skill does not replace orchestrator-health APIs; it consumes them.
