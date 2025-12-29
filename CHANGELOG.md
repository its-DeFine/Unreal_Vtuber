# Changelog

## Unreleased

Changes merged after `v1.2.2` (current tagged release).

## v1.2.2 (2025-12-29)

### Highlights

- Docs: document the `upgrade` CLI command (update repo + pull/recreate containers).

### Included PRs

- [#118](https://github.com/its-DeFine/Unreal_Vtuber/pull/118) docs: document CLI upgrade command

## v1.2.1 (2025-12-29)

### Highlights

- CLI: add `upgrade` to update + pull/recreate service containers.
- Onboarding: default to control-plane (“edge plane”) assignment (no manual edge IP needed).
- Edge rotator: fix edge config token shadowing that caused plane polling 401s.
- Docs: clarify VRAM requirement + invite contact.

### Included PRs

- [#114](https://github.com/its-DeFine/Unreal_Vtuber/pull/114) docs: add VRAM requirement + invite contact
- [#115](https://github.com/its-DeFine/Unreal_Vtuber/pull/115) onboard: default to control-plane edge assignment
- [#116](https://github.com/its-DeFine/Unreal_Vtuber/pull/116) edge-rotator: fix edge config token shadowing
- [#117](https://github.com/its-DeFine/Unreal_Vtuber/pull/117) CLI: add upgrade to pull + recreate containers

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
