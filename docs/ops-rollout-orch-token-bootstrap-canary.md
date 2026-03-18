# `/ops/rollout` ephemeral orch-token bootstrap canary

Status: implemented locally and verified on 2026-03-12.

Latest acceptance evidence from this run (`2026-03-12T21:36:03Z`):

- `./docs/validation/check-ops-rollout-orch-token-bootstrap.sh` returned `status=pass`.
- `Unreal_Vtuber/orchestrator-health/.venv_test/bin/python -m pytest Unreal_Vtuber/orchestrator-health/tests/test_power_api.py -k 'ops_rollout_execs_script or orch_token'` returned `2 passed, 46 deselected`.
- `Unreal_Vtuber/orchestrator-health/.venv_test/bin/python -m py_compile orchestrator-health/orchestrator_health/remote_health_service.py orchestrator-health/tests/test_power_api.py` returned `ok`.

This file records the implemented `/ops/rollout` env-token bridge plus the deterministic canary command plan for a remote rollout.

## Implemented bridge

`/ops/rollout` now supports both rollout token paths:

```bash
tools/encrypted-game-image/consume.sh \
  --payments-api-url <url> \
  --image-ref <ref> \
  --orch-token-file /root/.embody/orch-license-token.txt
```

and, when `orch_token` is present in the request body:

```bash
tools/encrypted-game-image/consume.sh \
  --payments-api-url <url> \
  --image-ref <ref> \
  --orch-token-env EMBODY_ROLLOUT_ORCH_TOKEN
```

The ephemeral token is injected only through the executor environment; the legacy file-token fallback remains intact.
The handler also keeps the secret surface narrow: rollout state writes omit `orch_token`, and `_cluster_executor_exec` returns `cmd`, `stdout`, and `stderr` without echoing executor env.

## Live code anchors

- `orchestrator-health/orchestrator_health/remote_health_service.py:245-267`
  `OpsRolloutRequest` now includes optional `orch_token`.
- `orchestrator-health/orchestrator_health/remote_health_service.py:2157-2168`
  `/ops/rollout` now switches between `--orch-token-file` and `--orch-token-env`, and passes executor env on the ephemeral-token path.
- `orchestrator-health/tests/test_power_api.py:984-1012`
  `test_ops_rollout_execs_script` asserts the legacy file-token fallback and no executor env.
- `orchestrator-health/tests/test_power_api.py:1015-1054`
  `test_ops_rollout_execs_script_with_orch_token` asserts the env-token path and injected executor env.
- `tools/encrypted-game-image/consume.sh:629-631`
  `--orch-token-env` remains the underlying script entrypoint used by the new request path.

## Implemented patch contract

Edit only these files:

- `orchestrator-health/orchestrator_health/remote_health_service.py`
- `orchestrator-health/tests/test_power_api.py`

Concrete names for the narrowest bridge:

- Request field: `orch_token`
- Executor env var: `EMBODY_ROLLOUT_ORCH_TOKEN`

Why this stayed the smallest viable change:

- `_cluster_executor_exec(..., env=...)` already exists in `remote_health_service.py`, so the executor helper does not need a signature change.
- `consume.sh` already accepts `--orch-token-env <ENV>`, so the script contract is already present.
- The current fallback path `--orch-token-file /root/.embody/orch-license-token.txt` stays valid when the new request field is absent.

Minimal implementation branch inside `/ops/rollout`:

```python
token_path = "/root/.embody/orch-license-token.txt"
executor_env = None
token_args = ["--orch-token-file", token_path]

if payload.orch_token:
    executor_env = {"EMBODY_ROLLOUT_ORCH_TOKEN": payload.orch_token}
    token_args = ["--orch-token-env", "EMBODY_ROLLOUT_ORCH_TOKEN"]

cmd = [
    "bash",
    f"{project_dir}/tools/encrypted-game-image/consume.sh",
    "--payments-api-url",
    payments_url,
    "--image-ref",
    image_ref,
    *token_args,
]
download = _cluster_executor_exec(executor, cmd, env=executor_env)
```

Delivered hunk map:

1. Add `orch_token` to `OpsRolloutRequest`.
2. Split rollout token handling into `token_args` plus optional `executor_env`.
3. Preserve the current file-token fallback when `orch_token` is absent.
4. Pass `env=executor_env` only on the env-token path.

Model change in `OpsRolloutRequest`:

```python
orch_token: Optional[str] = Field(
    default=None,
    description="Optional ephemeral orchestrator token used only for this rollout request.",
)
```

Behavioral contract:

1. If `orch_token` is omitted, `/ops/rollout` behaves exactly as it does today.
2. If `orch_token` is present, the executor receives the token only through `environment=...`.
3. The command switches to `--orch-token-env EMBODY_ROLLOUT_ORCH_TOKEN`.
4. The command does not include `--orch-token-file` in the env-token path.

## Local verification plan

Run the repo-local preflight first:

```bash
./docs/validation/check-ops-rollout-orch-token-bootstrap.sh
```

Then run the focused tests directly from the repo-local pytest environment:

```bash
cd orchestrator-health
.venv_test/bin/python -m pytest tests/test_power_api.py -k 'ops_rollout_execs_script or orch_token'
```

Current probes from this cycle:

- `cd /Users/geo/Projects/artifacts/openclaw/openclaw-head-engineer/workspace/Unreal_Vtuber/orchestrator-health && .venv_test/bin/python -m pytest tests/test_power_api.py -k 'ops_rollout_execs_script or orch_token'`
  passed with:
  `2 passed, 46 deselected`
- `cd /Users/geo/Projects/artifacts/openclaw/openclaw-head-engineer/workspace/Unreal_Vtuber && bash docs/validation/check-ops-rollout-orch-token-bootstrap.sh`
  returned:
  `status=pass`

## Focused test delta

Extend `test_ops_rollout_execs_script` to keep the current fallback explicit:

- assert the command still includes `--orch-token-file /root/.embody/orch-license-token.txt`
- assert `environment` is `None` or `{}` for the legacy path

Add one focused ephemeral-token test beside it:

```python
resp = client.post(
    "/ops/rollout",
    json={
        "no_verify": True,
        "payments_api_url": "http://payments:8081",
        "orch_token": "ephemeral-token",
    },
)
```

Assertions for that new test:

- `environment["EMBODY_ROLLOUT_ORCH_TOKEN"] == "ephemeral-token"`
- the command includes `--orch-token-env EMBODY_ROLLOUT_ORCH_TOKEN`
- the command omits `--orch-token-file`
- the HTTP response does not expose `environment`, `orch_token`, or the token value
- response remains `200`
- rollout state does not persist `orch_token` or the token value
- rollout state file still records `status in ("staged", "applied")`
- disk-space and running-container guards remain unchanged

Implementation note for the test:

- widen `DummyExecutor.exec_run(...)` so it captures both `cmd` and `environment`
- keep the existing fallback test on the current function
- add the env-token assertions in a second test so the fallback and ephemeral paths stay independently readable

## Deterministic canary command plan

The preflight script above now resolves the repo-local `.venv_test` automatically, runs the syntax check, and confirms the focused rollout tests before this canary step.

Use stdin-built JSON so the token does not appear in shell history:

```bash
export EMBODY_ROLLOUT_TOKEN='set-at-runtime'
python3 - <<'PY' | curl -sS -X POST http://127.0.0.1:9090/ops/rollout \
  -H 'Content-Type: application/json' \
  --data-binary @-
import json, os
print(json.dumps({
    "payments_api_url": "http://payments:8081",
    "image_ref": "ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1",
    "stage_only": True,
    "orch_token": os.environ["EMBODY_ROLLOUT_TOKEN"],
}))
PY
```

Expected result:

- the executor command uses `consume.sh --orch-token-env ...`
- the executor environment carries the ephemeral token
- the file-token fallback still works when `orch_token` is omitted

## Delegate closeout

The implementation and focused local verification are complete in this workspace.

Next safe step:

```bash
cd /Users/geo/Projects/artifacts/openclaw/openclaw-head-engineer/workspace/Unreal_Vtuber
sed -n '1,220p' docs/ops-rollout-orch-token-bootstrap-canary.md
```
