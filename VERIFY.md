# Verification Contract

This file is the canonical command matrix for `Unreal_Vtuber`.

## Assumptions

- Run commands from the repo root unless the command explicitly changes directories.
- Use a Python environment that has `pytest` plus the packages needed by the touched subsystem.

## Evidence Location

Store verification evidence under:

`logs/harness/<YYYY-MM-DD>/<change-id>/`

Recommended layout:

- `logs/harness/<date>/<change-id>/local/` for local-safe checks
- `logs/harness/<date>/<change-id>/runtime/` for live-host checks
- `logs/harness/<date>/<change-id>/notes.md` for short proof-of-done notes when the evidence is not self-explanatory

`logs/` is already gitignored, so machine-generated evidence can stay local. Keep heavy binaries out of the repo.

## Issue / PR Traceability

For implementation work, traceability is part of proof-of-done:

- use a real GitHub issue number
- use branch naming `codex/issue-<number>-<slug>`
- include `Closes #<number>` or `Refs #<number>` in the PR body
- never use placeholder issue IDs such as `issue-0`

## Proof Rules

- Docs-only change:
  - proof is the doc diff plus the command matrix staying grounded in real repo commands
- Local-safe change:
  - proof is the relevant command output captured under `local/`
- Runtime-required change:
  - proof is the local check plus runtime output under `runtime/`
- Privileged/operator-only action:
  - do not run by default
  - require an explicit operator ask plus redacted evidence if executed

## Local-Safe Commands

Use these first when the touched surface matches.

| Surface | Command | What it proves |
| --- | --- | --- |
| `scripts/embody_cli.sh` | `bash -n scripts/embody_cli.sh` | CLI syntax still parses after repo-local changes |
| `orchestrator-health/` | `pytest orchestrator-health/tests` | Local FastAPI power and remote-ops behavior without a live host |
| `tools/recorder/` | `PYTHONPATH=. pytest tools/recorder/tests` | Recorder control HTTP behavior and upload/download safety |

## Runtime-Required Commands

These require a configured host or running stack.

On a clean/default runtime, `script-runner` is parked unless the operator intentionally enables the `script-runner` compose profile. Treat runner-specific checks as conditional in that default mode.

| Command | Scope | Notes |
| --- | --- | --- |
| `./scripts/embody_cli.sh health` | quick local host status | Read-only health probes for signaling and orchestrator-health; runner state is only meaningful when `script-runner` is intentionally enabled |
| `./scripts/embody_cli.sh overview` | operator dashboard | Read-only summary of power state, containers, and registration |
| `./scripts/embody_cli.sh verify` | live host verification | Runtime check for stack readiness and record/download; runner TCP is conditional and should report `SKIP` when `script-runner` is parked from the default runtime |

## Privileged Or Operator-Only Commands

Do not treat these as default agent actions.

| Command or surface | Why it is restricted |
| --- | --- |
| `./scripts/embody_cli.sh setup` | Writes config, redeems tokens, and starts onboarding |
| `./scripts/embody_cli.sh rollout` | Pulls and applies encrypted game images |
| `./scripts/embody_cli.sh power ...` | Changes live stack power state |
| `./scripts/embody_cli.sh upgrade` | Pulls repo/container updates on a live host |
| `./scripts/embody_cli.sh verify --fix` | May recreate services and mutate runtime state |
| `POST http://<host>:9090/ops/*` | Remote control path behind allowlists |
| `POST http://<host>:9090/cluster/*` | Remote cluster lifecycle control |

## Stop Conditions

Stop instead of improvising when:

- the required command is runtime-only and no live host is available
- the only available path uses secrets, `.env`, or privileged infra state
- the command would mutate live services and the issue did not explicitly request it
- the evidence cannot be captured in a deterministic way
