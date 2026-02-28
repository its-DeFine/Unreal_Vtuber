# Consumer Skill Flow (Multi-Orchestrator)

This is the target `SKILL.md` interaction contract for renter/consumer agents.

## Contract

The consumer talks to one MCP endpoint (the negotiator). The negotiator handles fleet routing.

## Tool sequence

1. `fleet_overview`
   - Purpose: discover current orchestrator availability.
2. `negotiate_quote`
   - Inputs: `session_type`, `duration_min`, `resolution`
   - Optional: `preferred_orchestrator_id`
   - Output includes: `quote_id`, `orchestrator_id`, `valid_until`
3. `accept_quote`
   - Inputs: `quote_id`, `customer_id`
   - Optional direct route: `connection.direct_webrtc_base_url` OR `connection.direct_webrtc_ip`
   - Output includes: `booking_id`, `orchestrator_id`, `session.signaling_url`, `session.control`
4. `session_status`
   - Inputs: `booking_id`, `customer_id`
   - Output includes active control URLs and `time_remaining_min`.
5. `update_webrtc_connection` (optional)
   - Use when allowlist/network route changes during the lease.
6. `validate_renter_control`
   - Deterministic command-path verification through script-runner.
7. `cancel_session` (optional)
   - Ends lease and tears down on the correct orchestrator.

## Allocation behavior

- Default strategy: `lowest_price_then_capacity`.
- Capacity is computed per orchestrator using:
  - GPU telemetry from orchestrator-health
  - active bookings in the negotiator store scoped by `orchestrator_id`
  - per-orchestrator or global capacity thresholds.

## Required env for fleet mode

- `NEGOTIATOR_FLEET_REGISTRY_FILE=/path/to/fleet.yaml`
- `NEGOTIATOR_API_TOKEN=<token>` (recommended)

