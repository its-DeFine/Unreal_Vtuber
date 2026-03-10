# Agent Index

Start here:

1. `WORKFLOW.md` for read order, execution wedge, and stop conditions.
2. `VERIFY.md` for the command matrix, evidence locations, and proof-of-done.
3. `docs/harness-engineering.md` for the repo map and subsystem boundaries.

Repo defaults:

- Main operator entrypoint: `./scripts/embody_cli.sh`
- Local-safe verification surfaces: `orchestrator-health/`, `tools/recorder/`
- Runtime-required surfaces: the compose stack, a configured host, and remote ops endpoints on `:9090`
- Public client session allocation/control is Payments-owned (`/api/sessions/*`), not Unreal_Vtuber-owned
- Forbidden unless the issue explicitly requires them: `.github/**`, `*.env*`, `*.pem`, `*.key`, `*secret*`, `*credentials*`, legal docs, encrypted image flow

Execution rules:

- Work from an issue-scoped branch and keep the change set surgical.
- Prefer the smallest verification step that proves the touched surface.
- Treat onboarding, rollout, power, upgrade, and remote ops as operator-only by default.
