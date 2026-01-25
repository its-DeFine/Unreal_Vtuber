# Changelog

## Unreleased

Changes merged after `v1.3.1` (current tagged release).

- (none yet)

## v1.3.1 (2026-01-25)

### Highlights

- Remote ops parity: richer `/meta`, config push, and `upgrade/rollout` support.
- Encrypted game image: staged rollout (prefetch) + pending rollout state; persist last verify in `/meta`.
- CLI: repo auto-update on launch (ff-only, best-effort; opt-out via `EMBODY_CLI_NO_AUTO_UPDATE=1`).
- Remote ops: pin orchestrator to `{ref, service_image_tag}` and apply safely during sleep (`--no-start`).
- consume.sh: more robust base64 decode detection.

### What this enables

- Multi-avatar capacity on a single GPU host (“cluster mode”): run multiple independent avatar *slots* on one machine, each with its own signaling + runner + recorder stack.
- A real path to “autoscale”: capacity becomes “how many slots are registered + healthy”, so you can scale **up** (more slots per host) and scale **out** (more hosts) using the same allocation primitives.
- No-SSH fleet operations: remote metadata + remote upgrade/rollout endpoints are stable enough to drive from a control plane (or simple scripts) instead of manually logging into boxes.
- Safer rollouts: staged encrypted image delivery + pinning to `{ref, service_image_tag}` makes it practical to keep hosts on known-good versions and update them while sleeping.

### Developer notes (how to think about capacity)

- The unit of allocatable capacity is a **signaling server registration**. Each cluster slot contributes one.
- Cluster mode is intentionally deterministic:
  - Signaling port: `8080 + slot`
  - Runner port: `9877 + slot`
  - Recorder-control port: `8889 + slot`
- Per-slot sleep/wake is supported via `/power/projects/{project}` (and CLI wrappers), so you can scale down unused slots without powering off the whole host.
- Defaults & knobs:
  - CLI repo auto-update is on by default; disable with `EMBODY_CLI_NO_AUTO_UPDATE=1` (auto-update is skipped automatically when the repo is dirty or on detached HEAD).
  - CLI auto-upgrade-when-sleeping is on by default; disable with `EMBODY_CLI_AUTO_UPGRADE_WHEN_SLEEPING=0`.
  - Remote ops endpoints are enabled by default (`EXPERIMENTAL_REMOTE_OPS=1`); opt out with `EXPERIMENTAL_REMOTE_OPS=0` and recreate `orchestrator-health`.
  - Remote cluster control (`/cluster/*`) is opt-in: set `EXPERIMENTAL_REMOTE_CLUSTER_CONTROL=1` and recreate `orchestrator-health`.

### Included PRs

- [#161](https://github.com/its-DeFine/Unreal_Vtuber/pull/161) Issue #160: remote ops parity (meta/version + remote config + upgrade/rollout)
- [#162](https://github.com/its-DeFine/Unreal_Vtuber/pull/162) consume.sh: fix base64 decode detection
- [#164](https://github.com/its-DeFine/Unreal_Vtuber/pull/164) Issue #163: auto-update repo on CLI launch
- [#168](https://github.com/its-DeFine/Unreal_Vtuber/pull/168) Issue #167: staged encrypted rollouts + persist verify/meta
- [#170](https://github.com/its-DeFine/Unreal_Vtuber/pull/170) Issue #169: enable remote ops by default
- [#172](https://github.com/its-DeFine/Unreal_Vtuber/pull/172) Issue #171: fix docs for orchestrator-health recreate
- [#176](https://github.com/its-DeFine/Unreal_Vtuber/pull/176) Remote ops: pin git ref + service image tag

## v1.3.1-beta.6 (2026-01-19)

### Highlights

- Docs: recommend `cluster deploy --no-update ...` when pinned to a release tag.

### Included PRs

- [#156](https://github.com/its-DeFine/Unreal_Vtuber/pull/156) docs: cluster deploy uses --no-update when pinned

## v1.3.1-beta.5 (2026-01-19)

### Highlights

- Docs: onboarding improvements for cluster mode + per-avatar power control.

### Included PRs

- [#155](https://github.com/its-DeFine/Unreal_Vtuber/pull/155) docs: onboarding for v1.3.1-beta.4 (cluster + per-avatar power)

## v1.3.1-beta.4 (2026-01-19)

### Highlights

- Orchestrator health: per-project sleep/wake for cluster instances (`/power/projects/{project}` + CLI `power --project`).

### Included PRs

- [#154](https://github.com/its-DeFine/Unreal_Vtuber/pull/154) orchestrator-health: per-project sleep/wake for cluster instances

## v1.3.1-beta.3 (2026-01-19)

### Highlights

- CLI: auto-generate multi-avatar cluster config from GPU capacity (free VRAM + skip busy GPUs + spread across GPUs).

### Included PRs

- [#152](https://github.com/its-DeFine/Unreal_Vtuber/pull/152) feat(cli): auto-generate multi-avatar cluster from GPU capacity

## v1.3.1-beta.2 (2026-01-19)

### Highlights

- Edge rotator: cluster fixes (iptables-nft/DOCKER-USER allowlist, cluster-mode recreate).
- CI/ops: publish service images with git release tags (enables version pinning).

### Included PRs

- [#149](https://github.com/its-DeFine/Unreal_Vtuber/pull/149) Issue #148: edge-rotator cluster fixes
- [#151](https://github.com/its-DeFine/Unreal_Vtuber/pull/151) Issue #150: publish service images with release tags

## v1.3.1-beta.1 (2026-01-19)

### Highlights

- CLI: one-command cluster deploy wrapper + game image preflight (avoid GHCR `denied`; use `rollout` for encrypted game images).

### Included PRs

- [#147](https://github.com/its-DeFine/Unreal_Vtuber/pull/147) CLI: one-command cluster deploy + game image preflight

## v1.3.0-beta.1 (2026-01-16)

### Highlights

- Cluster mode: multi-instance avatar stacks with deterministic ports.

### Included PRs

- [#143](https://github.com/its-DeFine/Unreal_Vtuber/pull/143) Cluster mode: multi-instance avatar stacks (deterministic ports)

## v1.2.4 (2026-01-16)

### Highlights

- Recorder: harden headless recorder for unattended runs.

### Included PRs

- [#136](https://github.com/its-DeFine/Unreal_Vtuber/pull/136) Harden headless recorder

## v1.2.3 (2026-01-16)

### Highlights

- Onboarding/CLI: fix Payments `/power` allowlist seeding and add a one-command “fix” for allowlist issues.

### Included PRs

- [#139](https://github.com/its-DeFine/Unreal_Vtuber/pull/139) Fix onboarding /power allowlist seeding
- [#141](https://github.com/its-DeFine/Unreal_Vtuber/pull/141) CLI: one-command fix for Payments /power allowlist

## v1.2.2 (2026-01-16)

### Highlights

- Repo automation: launch factory starter kit chores/workflows.

## v1.2.1 (2025-12-29)

### Highlights

- CLI: add `upgrade` to update + pull/recreate service containers.
- Onboarding: default to control-plane (“edge plane”) assignment (no manual edge IP needed).
- Edge rotator: fix edge config token shadowing that caused plane polling 401s.
- Docs: clarify VRAM requirement + invite contact; document the `upgrade` command.

### Included PRs

- [#114](https://github.com/its-DeFine/Unreal_Vtuber/pull/114) docs: add VRAM requirement + invite contact
- [#115](https://github.com/its-DeFine/Unreal_Vtuber/pull/115) onboard: default to control-plane edge assignment
- [#116](https://github.com/its-DeFine/Unreal_Vtuber/pull/116) edge-rotator: fix edge config token shadowing
- [#117](https://github.com/its-DeFine/Unreal_Vtuber/pull/117) CLI: add upgrade to pull + recreate containers
- [#118](https://github.com/its-DeFine/Unreal_Vtuber/pull/118) docs: document CLI upgrade command

## v1.2.0 (2025-12-28)

### Highlights

- CLI dashboard + end-to-end verification (runner TCP + record/download smoke tests).
- Control-plane (“edge plane”) support: plane-managed allowlists, drift healing, and matchmaker config updates.
- Recorder-control improvements: deterministic output filenames + S3 presigned upload support.
- Service images now support a `staging` lane (see `docs/staging.md`).

### Included PRs

- [#90](https://github.com/its-DeFine/Unreal_Vtuber/pull/90) cli: allow selecting NVIDIA GPU
- [#93](https://github.com/its-DeFine/Unreal_Vtuber/pull/93) Orchestrator: embody_cli + power sleep-all + wake TTL
- [#94](https://github.com/its-DeFine/Unreal_Vtuber/pull/94) ops: disable watchtower rolling restarts
- [#95](https://github.com/its-DeFine/Unreal_Vtuber/pull/95) cli: auto-configure edge-config plane
- [#96](https://github.com/its-DeFine/Unreal_Vtuber/pull/96) Fix signaling matchmaker args survive rotator recreate
- [#101](https://github.com/its-DeFine/Unreal_Vtuber/pull/101) encrypted-image consume: invite redeem + lease robustness
- [#103](https://github.com/its-DeFine/Unreal_Vtuber/pull/103) Edge rotator: plane-managed allowlists + drift-healing
- [#104](https://github.com/its-DeFine/Unreal_Vtuber/pull/104) Onboarding: Payments bootstrap edge-plane autodetect
- [#105](https://github.com/its-DeFine/Unreal_Vtuber/pull/105) CLI: verify/register/payments + health hardening
- [#106](https://github.com/its-DeFine/Unreal_Vtuber/pull/106) cli: redeem invite + rollout wrapper
- [#107](https://github.com/its-DeFine/Unreal_Vtuber/pull/107) CI/docs: add staging lane for service images
- [#108](https://github.com/its-DeFine/Unreal_Vtuber/pull/108) cli: improve onboarding prompts + image load UX
- [#109](https://github.com/its-DeFine/Unreal_Vtuber/pull/109) CLI: dashboard + end-to-end verify
- [#110](https://github.com/its-DeFine/Unreal_Vtuber/pull/110) cli: fix runner tcp state polling
- [#111](https://github.com/its-DeFine/Unreal_Vtuber/pull/111) Recorder S3 upload + payments allowlist
- [#112](https://github.com/its-DeFine/Unreal_Vtuber/pull/112) cli: fix verify false warnings
- [#113](https://github.com/its-DeFine/Unreal_Vtuber/pull/113) docs: clarify CLI flow + allowlists

## v1.1.0 (2025-12-20)

### Highlights

- One-command orchestrator onboarding wizard (interactive).
- Encrypted game image consume improvements + clearer operator docs.
- Multi-edge verification + allowlist guidance.

### Included PRs

- [#85](https://github.com/its-DeFine/Unreal_Vtuber/pull/85) Orchestrator: one-command onboarding
- [#86](https://github.com/its-DeFine/Unreal_Vtuber/pull/86) tools: fix `tools/rollout.sh` awk compatibility
- [#87](https://github.com/its-DeFine/Unreal_Vtuber/pull/87) docs: clarify encrypted image refs

## v1.0.0 (2025-12-18)

This is the first tagged release of the Unreal VTuber Pixel Streaming stack.

### Highlights

- Encrypted game image distribution via S3 artifacts + Payments-issued leases (no registry creds needed on orchestrators).
- Published “service images” to support pull-only orchestrator deployments (runner/recorder/health/watchdog/registration).
- Reduced Unreal game image size by fixing layered payload bloat (issue #37).
- Signaling image no longer bundles the web UI (UI is expected to be served by the edge/gateway).

### Included PRs

- [#80](https://github.com/its-DeFine/Unreal_Vtuber/pull/80) Signaling: remove bundled UI from GHCR image
- [#81](https://github.com/its-DeFine/Unreal_Vtuber/pull/81) Publish service images for pull-only deployments
- [#82](https://github.com/its-DeFine/Unreal_Vtuber/pull/82) Fix UE game image bloat (issue #37)
- [#83](https://github.com/its-DeFine/Unreal_Vtuber/pull/83) Encrypted game image: add producer/consumer scripts
