# Changelog

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

