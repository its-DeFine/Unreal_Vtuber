# Skill: client-embodied-control

Purpose: run a deterministic buyer-side lease flow and validate embodied control after booking.

## Preconditions

1. MCP negotiator is reachable (`/health` OK).
2. Buyer has an auth token if gateway auth is enabled.
3. Runner is reachable for active sessions (allowlist + token policy configured).

## Flow

1. Get a quote
- Call `negotiate_quote` with `session_type`, `duration_min`, `resolution`.

2. Accept quote (lease handshake)
- Call `accept_quote` with `quote_id` + `customer_id`.
- Capture:
  - `booking_id`
  - `session.signaling_url`
  - `session.token`
  - `session.control.runner_execute_url`
  - `session.control.runner_status_url_template`

3. Send embodied control command
- `POST` to `session.control.runner_execute_url` with payload:
```json
{
  "session_id": "buyer-session-001",
  "commands": [
    { "delay_ms": 0, "type": "tcp", "value": "TTS_BYOB_/opt/embody/sample-15s.mp3" }
  ],
  "audio": []
}
```

4. Verify command execution
- Poll `runner_status_url_template` with `session_id` until terminal state.
- Pass condition: final `state == "completed"`.

5. Verify lease status
- Call `session_status` with `booking_id` + `customer_id`.
- Pass condition: `status == "active"` and `control` block is present.

## Deterministic acceptance checks

1. Lease handshake pass: `accept_quote` returns `booking_id`.
2. Control endpoint pass: `session.control.runner_execute_url` present.
3. Command execution pass: runner status for command session is `completed`.
4. Lease status pass: `session_status` returns `active`.
