# Unreal_Vtuber Workflow

This file is the repo-owned execution contract for agents working in `Unreal_Vtuber`.

## Read Order

Read these in order before making a non-trivial change:

1. `AGENTS.md`
2. `README.md`
3. `WORKFLOW.md`
4. `VERIFY.md`
5. `docs/harness-engineering.md`
6. `docs/embody-cli.md`
7. `docs/orchestrator-onboarding.md`
8. `docs/pixel-streaming-architecture.md`
9. `docs/unreal-integration.md`

Then inspect the code surface you plan to touch. Common first stops:

- `scripts/embody_cli.sh`
- `orchestrator.env.example`
- `orchestrator-health/tests/test_power_api.py`
- `tools/recorder/tests/test_control_server.py`

## Repo Contract

- Main operator entrypoint: `./scripts/embody_cli.sh`
- Main runtime definition: `docker-compose.unreal.yml`
- Best local-safe verification surfaces:
  - `orchestrator-health/`
  - `tools/recorder/`
- Runtime-only surfaces:
  - compose stack lifecycle
  - onboarding and encrypted image rollout
  - live allowlists, power control, and remote ops endpoints
- Repo boundary:
  - public client session allocation and `/api/sessions/*` control live in Payments, outside this repo

## Default Execution Loop

1. Confirm the real tracker key (Linear task key or GitHub issue number) before opening an implementation branch or PR.
2. Name the exact surface you are changing.
3. Pick the smallest wedge that satisfies the issue.
4. Choose the closest verification command from `VERIFY.md` before editing.
5. Make the smallest change that can pass that check.
6. Capture proof in the evidence path defined in `VERIFY.md`.
7. Stop when the requested acceptance check is met. Do not expand into adjacent cleanup.

## Proof Of Done

Use the proof rule that matches the change type:

- Docs-only change:
  - updated docs point to the right entrypoints and verification commands
  - file diff is the main artifact
- Local-safe code change:
  - run the closest local-safe command for the touched subsystem
  - store the command output under `logs/harness/...`
- Runtime-touching change:
  - complete the closest local-safe check first
  - then collect live-host evidence under `logs/harness/.../runtime/`
  - include the exact host, command, and endpoint used

## Stop Conditions

Stop and ask for a narrower packet if any of these become necessary:

- modifying `.github/**`, `.env*`, legal docs, secrets, or credential material
- changing encrypted image delivery or other production rollout plumbing
- changing live infra or allowlist values without explicit operator approval
- relying on a runtime-only check when no host or credentials are available
- treating harness work as permission to delete or redesign adjacent subsystems
- broadening from one subsystem fix into a repo-wide refactor
- opening an implementation branch or PR without a real tracker key (Linear task key or GitHub issue number)
- using placeholder branch or PR metadata such as `issue-0` or `<linear-key>`
- branch naming that does not follow `codex/<linear_key>-<slug>` or `codex/issue-<number>-<slug>`
- PR body missing `Linear: <linear_key>`, `Closes #<number>`, or `Refs #<number>`
