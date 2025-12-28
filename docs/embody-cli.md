# Embody Orchestrator CLI (`scripts/embody_cli.sh`)

This repo ships a single entrypoint for onboarding and day-to-day operations: `./scripts/embody_cli.sh`.

## Recommended flow

1. Run the interactive dashboard:

```bash
./scripts/embody_cli.sh
```

2. If you want a one-shot status view:

```bash
./scripts/embody_cli.sh overview
```

3. Run health + end-to-end checks:

```bash
./scripts/embody_cli.sh verify --fix
```

## Command reference

- `setup` – onboarding wizard (writes `.env` + `.env.turn`, pulls encrypted image, starts the stack)
  - Non-interactive example:
    ```bash
    ./scripts/embody_cli.sh setup --non-interactive \
      --orchestrator-id <id> \
      --orchestrator-address <0x...> \
      --invite-code <code>
    ```
- `overview` – compact dashboard (power state, containers, key config)
- `verify` – health + consistency checks (runner TCP + record/download smoke tests when awake)
  - `--fix` recreates runner/recorder if allowlist env drift is detected
  - Also checks outbound HTTPS (needed for presigned uploads) and warns if Payments allowlists look misconfigured
- `payments` – Payments connectivity checks + viewer token helper (when a viewer token is available)
- `register` – register orchestrator in Payments (cached; skips when already registered)
- `license` / `license redeem` – view or redeem license token (invite code → token)
- `rollout` – load encrypted game image (wrapper for `tools/encrypted-game-image/rollout.sh`)
- `power` – sleep/wake the stack via `http://127.0.0.1:9090/power`
  - `power wake --ttl <seconds>` sets an auto-sleep TTL on wake
- Day-to-day stack control:
  - `start`, `stop`, `restart`, `status`, `logs [service]`, `health`
- `update` – fast-forward this repo to `origin/main` (no merges)

## Network / allowlists

The orchestrator uses allowlists to protect control endpoints:

- Script runner (9877): strict IP string match via `VTUBER_ALLOWED_ADDRESSES`
- Recorder control (8889): strict IP string match via `VTUBER_ALLOWED_ADDRESSES` (and optional `RECORDINGS_API_TOKEN`)
- Power API (9090): CIDR-aware allowlist via `POWER_ALLOWED_IPS` or `POWER_ALLOWED_IPS_FILE`

If `EDGE_CONFIG_URL` is configured, the `orchestrator-edge-rotator` sidecar manages allowlists automatically and can also add extra “always allowed” CIDRs/IPs:

- `EDGE_FIREWALL_EXTRA_CIDRS` – additional CIDRs to allow through host firewall (ex: Payments host for `/health`)
- `EDGE_POWER_EXTRA_CIDRS` – additional CIDRs allowed to call `/power` (ex: Payments host for wake/sleep)
- `EDGE_LOCAL_ALLOWLIST` – IPs prepended to `VTUBER_ALLOWED_ADDRESSES` (ex: Payments host for runner/recorder)

## Remote workloads (record → upload)

If you use Payments-driven recording jobs:

- The orchestrator must allowlist the Payments host IP for `/power`, runner, and recorder.
- The orchestrator must have **outbound HTTPS** access so it can `PUT` to presigned URLs.

See also:
- Recorder control docs: `docs/recorder-control.md`
- Onboarding guide: `docs/orchestrator-onboarding.md`
