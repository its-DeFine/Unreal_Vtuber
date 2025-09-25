# Unreal VTuber Payments Backend

The Embody Unreal VTuber stack now ships with a lightweight payments backend that
monitors the Pixel Streaming containers and automatically accrues payouts for the
host orchestrator. Once the tracked balance reaches a configurable threshold, the
backend issues an on-chain transfer using the configured wallet.

## What this contains
- `docker-compose.unreal.yml` – TURN, signaling and packaged Unreal Engine build.
- `backend/docker-compose.yml` – payments backend container that monitors the Unreal services.
- `backend/payments` – Python package with the monitoring + payout logic.

## Quick start
1. Copy the sample env: `cp backend/.env.example backend/.env` and update the following values:
   - `ORCHESTRATOR_ADDRESS` – wallet that should receive rewards.
   - `PAYMENT_INCREMENT_ETH` – ETH credited for each successful health check.
   - `PAYMENT_PAYOUT_THRESHOLD_ETH` – when reached, a transfer is triggered.
   - Optional signing material: set either `PAYMENT_PRIVATE_KEY` **or** the
     keystore path/password variables. Leave them unset to run in dry-run mode.
2. Launch the services:
   ```bash
   docker network create vtuber_network 2>/dev/null || true
   docker compose -f docker-compose.unreal.yml up -d
   docker compose -f backend/docker-compose.yml up -d
   ```
3. Tail the backend logs to confirm balance accrual:
   ```bash
   docker compose -f backend/docker-compose.yml logs -f payments-backend
   ```

## Adding signing credentials
The backend supports two mutually exclusive signing modes:
- `PAYMENT_PRIVATE_KEY` – raw hex private key (never commit this).
- `PAYMENT_KEYSTORE_PATH` + `PAYMENT_KEYSTORE_PASSWORD` – decrypts a standard
  Web3 keystore file before submitting transactions.

If neither set, the backend runs in dry-run mode and simply logs the transfers
it *would* submit once the threshold is met.

## Monitoring configuration
`MONITORED_SERVICES` defaults to the three Unreal containers that constitute a
healthy deployment: `vtuber-unreal-game`, `vtuber-unreal-signaling`, and
`vtuber-turn-server`. Override the variable in `.env` if you add or rename
services in `docker-compose.unreal.yml`.

## Data storage
Ledger state is persisted under `backend/data/balances.json`. Mount this path to
external storage if you need the payment history to survive container recreation.

## Registry & top-100 checks
On startup the backend records orchestrator metadata under
`backend/data/registry.json`. When `TOP_CONTRACT_*` variables are configured, it
pulls the on-chain top 100 list and only enables automatic payments if the
registered wallet appears in that set. The registration outcome (first-time
flag, outstanding balance status, and top-100 membership) is logged during
boot.

## Bootstrap multiple orchestrators
Environments that manage several Unreal hosts can preload their metadata so the
backend automatically refreshes every registry entry on startup:

- Create `backend/data/orchestrators.json` (or point `PAYMENTS_BOOTSTRAP_ORCHESTRATORS_PATH`
  at another location) with an array of objects containing
  `orchestrator_id`/`address` pairs. Optional fields such as
  `capability`, `contact_email`, `host_public_ip`, `host_name`,
  `services_healthy`, `health_url`, `health_timeout`,
  `monitored_services`, and `min_service_uptime` map directly to the
  registration API payload.
- A ready-to-edit template lives at `backend/data/orchestrators.sample.json`.
  Copy it to `orchestrators.json` and extend the array with the rest of your
  fleet.
- Alternatively, set `PAYMENTS_BOOTSTRAP_ORCHESTRATORS` to a JSON string (the
  same shape as the file) inside `.env` when you prefer environment-only
  configuration.

Each orchestrator should expose the standard `/health` endpoint (served by
`payments.remote_health_service`) so the backend can evaluate remote uptime.
Set `PAYMENTS_DEFAULT_HEALTH_TIMEOUT` and `PAYMENTS_DEFAULT_MIN_SERVICE_UPTIME`
to control global fallbacks; per-orchestrator overrides can be provided in the
bootstrap file or registration payload. By default the bootstrap flow skips the
top-100 contract check to avoid blocking non-public wallets; set
`PAYMENTS_BOOTSTRAP_SKIP_RANK_VALIDATION=false` if you want the stricter
behaviour. The legacy single orchestrator mode remains available via
`PAYMENTS_SINGLE_ORCHESTRATOR_MODE=true` alongside the bootstrap list.

## Multi-orchestrator payouts
During every cycle the backend now iterates over every registered orchestrator,
pulls its latest `/health` payload (or falls back to a local Docker monitor),
updates the ledger, and triggers payouts to the address stored for that
orchestrator. Cooldowns, balances, and eligibility flags are isolated per ID, so
an outage on one host no longer blocks rewards for the rest of the fleet.

## Development
Install dependencies with `pip install -r backend/requirements.txt` and run the
loop locally via `python -m payments.main`. Set `PAYMENT_DRY_RUN=false` only on
trusted machines with access to the signing key.

## Further Reading

- [Payments + Orchestrator Deployment Guide](docs/payments-deployment.md) – network topology, required ports, and configuration checklist for multi-host deployments.

## Audit logging
`payments-log-collector` (Fluent Bit) tails the backend container logs and the
registry state, writing JSON lines to `backend/data/audit/payments-audit.log` for
long-term retention. Set `PAYMENTS_AUDIT_LOG_PATH` if you need the registry
audit trail to land somewhere else (the payments backend appends every
registration and cooldown transition to that file). Mount the `backend/data`
directory to durable storage in production so audit artefacts survive
redeployments.

## Self-registration API
The payments service now ships with a FastAPI server bound to `PAYMENTS_API_HOST:PAYMENTS_API_PORT`.
Operators can let each Unreal orchestrator host report its metadata instead of editing `.env` manually.
A helper script lives at `scripts/register_orchestrator.py`; run it during compose startup or as part of
your provisioning pipeline. The script reads the standard `ORCHESTRATOR_*` variables plus
`PAYMENTS_API_URL` and retries with exponential backoff until the backend accepts the registration.

### Endpoint summary
- `POST /api/orchestrators/register` – accepts JSON `{"orchestrator_id", "address", ...}` and records the metadata.
  Requests are rate-limited and rejected unless the wallet is part of the current top-100 set. The response includes
  eligibility flags, cooldown status, and the current ledger balance.
- `GET /api/orchestrators` – returns the full registry including balances. Requires `X-Admin-Token` when
  `PAYMENTS_API_ADMIN_TOKEN` is set.
- `GET /api/orchestrators/{id}` – single orchestrator view with cooldown timestamps and health markers.

### Cooldown behaviour
If all monitored containers are down three cycles in a row the backend pauses payouts for one hour. During this window
the registry entry remains visible but `eligible_for_payments` is `false`. Re-registration simply refreshes metadata;
payments automatically resume once the cooldown expires and the orchestrator is back in the top set.

To trigger a manual registration from a host, run:

```bash
PAYMENTS_API_URL=https://payments.example.com \
ORCHESTRATOR_ID=orch-123 ORCHESTRATOR_ADDRESS=0xabc... \
python3 scripts/register_orchestrator.py
```
