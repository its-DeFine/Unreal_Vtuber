# Unreal VTuber Payments Backend

The Embody Unreal VTuber stack now ships with a lightweight payments backend that
monitors the Pixel Streaming containers and automatically accrues payouts for the
host orchestrator. Once the tracked balance reaches a configurable threshold, the
backend issues an on-chain transfer using the configured wallet.

## What this contains
- `docker-compose.unreal.yml` – TURN, signaling and packaged Unreal Engine build.
- `docker-compose.yml` – payments backend container that monitors the Unreal services.
- `backend/payments` – Python package with the monitoring + payout logic.

## Quick start
1. Copy the sample env: `cp .example.env .env` and update the following values:
   - `ORCHESTRATOR_ADDRESS` – wallet that should receive rewards.
   - `PAYMENT_INCREMENT_ETH` – ETH credited for each successful health check.
   - `PAYMENT_PAYOUT_THRESHOLD_ETH` – when reached, a transfer is triggered.
   - Optional signing material: set either `PAYMENT_PRIVATE_KEY` **or** the
     keystore path/password variables. Leave them unset to run in dry-run mode.
2. Launch the services:
   ```bash
   docker network create vtuber_network 2>/dev/null || true
   docker compose -f docker-compose.unreal.yml up -d
   docker compose up -d
   ```
3. Tail the backend logs to confirm balance accrual:
   ```bash
   docker compose logs -f payments-backend
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

## Development
Install dependencies with `pip install -r backend/requirements.txt` and run the
loop locally via `python -m payments.main`. Set `PAYMENT_DRY_RUN=false` only on
trusted machines with access to the signing key.
