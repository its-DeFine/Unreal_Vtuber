# Harness Engineering

This repo is the harness point for the Unreal VTuber runtime stack. The goal is to make the repository readable, verifiable, and operable without reconstructing intent from chat history.

## What This Repo Owns

| Surface | Role | Best first verification |
| --- | --- | --- |
| `scripts/embody_cli.sh` | Main operator entrypoint for onboarding and day-to-day actions | `./scripts/embody_cli.sh overview`, `./scripts/embody_cli.sh health`, `./scripts/embody_cli.sh verify` |
| `docker-compose.unreal.yml` | Runtime stack wiring for signaling, game, TURN, runner, recorder, health, and registration | Runtime-required on a configured host |
| `orchestrator-health/` | FastAPI health, power, and remote ops surface on `:9090` | `pytest orchestrator-health/tests` |
| `tools/recorder/` | Recorder-control HTTP service and file handling | `PYTHONPATH=. pytest tools/recorder/tests` |

## Repo Boundary

- Public client session allocation and `/api/sessions/*` control live in the Payments backend, not in `Unreal_Vtuber`.
- This repo owns the runtime stack that those external session APIs eventually target: signaling, runner, recorder, health, and orchestration helpers.

## Read The Repo In This Shape

1. `README.md` for the operator-facing top-level workflow.
2. `WORKFLOW.md` for the execution contract.
3. `VERIFY.md` for command buckets, evidence paths, and stop conditions.
4. `docs/embody-cli.md` when the task touches the CLI surface.
5. `docs/orchestrator-onboarding.md` when the task touches setup, registration, or ingress.
6. `docs/pixel-streaming-architecture.md` when the task touches compose/runtime behavior.
7. `docs/unreal-integration.md` when the task touches the BYOB Unreal pipeline.

## Verification Tiers

- Local-safe:
  - `orchestrator-health/`
  - `tools/recorder/`
- Runtime-required:
  - host health, dashboard, and full verify commands through `./scripts/embody_cli.sh`
- Privileged/operator-only:
  - onboarding
  - encrypted rollout
  - power control
  - upgrade
  - remote ops and cluster mutation on `:9090`

The repo is harness-ready only when a task states which tier it needs before work begins.

## Evidence Contract

- Local-safe outputs go under `logs/harness/<date>/<change-id>/local/`
- Runtime outputs go under `logs/harness/<date>/<change-id>/runtime/`
- Docs-only work may use a short `notes.md` plus the diff itself as evidence
- Prefer machine-readable outputs for runtime checks whenever possible

## Default No-Touch Zones

Do not modify these unless the issue explicitly requires them:

- `.github/**`
- `.env*`
- `*.pem`
- `*.key`
- `*secret*`
- `*credentials*`
- legal docs
- encrypted image distribution flow

## What Success Looks Like

An agent should be able to answer these from the repo alone:

1. What should I read first?
2. What is the main operator entrypoint?
3. What can I verify locally without secrets or a live host?
4. What requires a live runtime?
5. What counts as proof that the change worked?
6. Which surfaces require an explicit operator decision?
