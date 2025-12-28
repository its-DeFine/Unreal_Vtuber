# Changelog

## Unreleased

Changes merged after `v1.1.0` (current tagged release).

### Highlights

- CLI improvements: verify/register/payments checks and more robust invite/license flows.
- Edge rotation hardening: plane-managed allowlists + drift healing.
- Service images now support a `staging` lane (see `docs/staging.md`).

### Included PRs

- #90 cli: allow selecting NVIDIA GPU
- #94 ops: disable watchtower rolling restarts
- #95 cli: auto-configure edge-config plane
- #96 Fix signaling matchmaker args survive rotator recreate
- #101 encrypted-image consume: invite redeem + lease robustness
- #103 Edge rotator: plane-managed allowlists + drift-healing
- #104 Onboarding: Payments bootstrap edge-plane autodetect
- #105 CLI: verify/register/payments + health hardening
- #106 cli: redeem invite + rollout wrapper

## v1.1.0 (2025-12-20)

### Highlights

- One-command orchestrator onboarding wizard (interactive).
- Encrypted game image consume improvements + clearer operator docs.
- Multi-edge verification + allowlist guidance.

### Included PRs

- #85 Orchestrator: one-command onboarding
- #86 tools: fix `tools/rollout.sh` awk compatibility
- #87 docs: clarify encrypted image refs

## v1.0.0 (2025-12-18)

This is the first tagged release of the Unreal VTuber Pixel Streaming stack.

### Highlights

- Encrypted game image distribution via S3 artifacts + Payments-issued leases (no registry creds needed on orchestrators).
- Published “service images” to support pull-only orchestrator deployments (runner/recorder/health/watchdog/registration).
- Reduced Unreal game image size by fixing layered payload bloat (issue #37).
- Signaling image no longer bundles the web UI (UI is expected to be served by the edge/gateway).

### Included PRs

- #80 Signaling: remove bundled UI from GHCR image
- #81 Publish service images for pull-only deployments
- #82 Fix UE game image bloat (issue #37)
- #83 Encrypted game image: add producer/consumer scripts
