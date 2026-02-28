# Agent Negotiator (MCP)

`agent-negotiator` exposes a customer-facing MCP endpoint for orchestrator workload negotiation.

Current deployment runs as an embedded claw plugin service. Standalone startup is intentionally disabled (`src/index.ts` exits with an error).

## Customer-facing MCP tools

- `orchestrator_info`
- `negotiate_quote`
- `accept_quote`
- `session_status`
- `validate_renter_control`
- `cancel_session`

`accept_quote` and `session_status` return a `session.control` block for active leases:

- `avatar_id`
- `runner_url`
- `runner_execute_url` (`POST /scripts/execute`)
- `runner_status_url_template` (`GET /scripts/{session_id}`)
- `game_tcp_port`

This enables deterministic post-lease embodied control through the script-runner path.

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
