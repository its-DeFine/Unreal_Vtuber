# Pull-mode job agent

The `orchestrator-job-agent` sidecar polls the Payments backend for recording jobs and executes them locally without requiring inbound runner/recorder access from Payments.

## How it works

1. Agent claims a pending job from Payments.
2. Agent wakes the stack (if needed), starts the recorder, and runs the script via the local script-runner.
3. Agent requests an upload URL from Payments, uploads the recording via recorder-control, and reports completion.

## Payments API contract (expected)

The agent expects these endpoints on the Payments backend (Bearer auth with orchestrator token):

- `POST /api/jobs/record/claim` -> `200` JSON job payload or `204` when no jobs.
- `POST /api/jobs/record/{job_id}/upload-url` -> `{ "upload_url": "...", "artifact_uri": "..." }`.
- `POST /api/jobs/record/{job_id}/complete` -> accepts artifact metadata.
- `POST /api/jobs/record/{job_id}/fail` -> accepts `{ "error": "..." }`.

Job payload fields used by the agent:
- `job_id` (required)
- `script` (required; vtuber-script-runner payload minus `session_id`)
- `recording_label`, `recording_streamer_id`, `wake_seconds`, `max_wait_seconds`, `delete_after_upload` (optional)

## Configuration

Environment variables (in `.env`):

- `JOB_AGENT_ENABLED` (default `0`)
- `JOB_AGENT_URL` (defaults to `PAYMENTS_API_URL`)
- `JOB_AGENT_POLL_SECONDS` (default `10`)
- `JOB_AGENT_HOST_GATEWAY` (default `172.18.0.1`)
- `JOB_AGENT_RUNNER_URL`, `JOB_AGENT_RECORDER_URL`, `JOB_AGENT_POWER_URL` (optional overrides)
- `JOB_AGENT_WAKE_SECONDS` (default `2400`)
- `JOB_AGENT_MAX_WAIT_SECONDS` (default `900`)
- `ORCHESTRATOR_TOKEN_DIR` (host path, default `/home/ubuntu/.embody`)
- `ORCHESTRATOR_TOKEN_FILE` (container path, default `/var/lib/vtuber/embody/orch-license-token.txt`)

Token handling:
- Prefer the token file written by onboarding (`~/.embody/orch-license-token.txt`).
- You can also set `ORCHESTRATOR_TOKEN` directly (not recommended for shared hosts).

## Local/EC2 mock server for testing

A tiny mock server is available for testing without Payments:

```
python3 tools/job-agent/mock_job_server.py
```

Point the agent at it:

```
JOB_AGENT_ENABLED=1
JOB_AGENT_URL=http://172.18.0.1:5001
```

The mock server loads `tools/job-agent/sample_job.json` by default and accepts uploads at `/uploads/...`.
