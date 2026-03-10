# Agent Index

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

- Do not start implementation work without a real GitHub issue number.
- Never use placeholder issue IDs such as `issue-0`.
- Work from `codex/issue-<number>-<slug>`, open a draft PR first, and include `Closes #<number>` or `Refs #<number>` in the PR body.
- Prefer the smallest verification step that proves the touched surface.
- Treat onboarding, rollout, power, upgrade, and remote ops as operator-only by default.
