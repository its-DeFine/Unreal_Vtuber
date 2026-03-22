# Agent Index

This repo uses Linear tasks as the internal unit of work and PRs as the execution artifact. GitHub issues are optional external/public intake, not a prerequisite for internal repo work.

Start here:

1. `README.md` for the operator-facing runtime overview and top-level workflow.
2. `WORKFLOW.md` for the canonical execution wedge, read order, and stop conditions.
3. `VERIFY.md` for the command matrix, evidence locations, and proof-of-done.
4. `docs/harness-engineering.md` for the repo map and subsystem boundaries.

Repo defaults:

- Main operator entrypoint: `./scripts/embody_cli.sh`
- Local-safe verification surfaces: `orchestrator-health/`, `tools/recorder/`
- Runtime-required surfaces: the compose stack, a configured host, and remote ops endpoints on `:9090`
- Public client session allocation/control is Payments-owned (`/api/sessions/*`), not Unreal_Vtuber-owned
- Forbidden unless the issue explicitly requires them: `.github/**`, `*.env*`, `*.pem`, `*.key`, `*secret*`, `*credentials*`, legal docs, encrypted image flow

Execution rules:

- If no real Linear task key is supplied, stop before opening an implementation branch or PR. Never use placeholder keys such as `<linear-key>`.
- Work from `codex/<linear_key>-<slug>`, open a draft PR first, and include `Linear: <linear_key>` in the PR body.
- Prefer the smallest verification step that proves the touched surface.
- Treat onboarding, rollout, power, upgrade, and remote ops as operator-only by default.
