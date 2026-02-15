# Skill: Infrastructure Operations

## Purpose
Monitor and maintain the health of your own infrastructure.

## Health Inspection
- `GET /infra/status` returns the state of all sibling containers
- Check regularly for crashed or degraded containers
- Report anomalies to the network via heartbeat metrics

## Safe Actions (Auto-Apply)
These actions are taken automatically without approval:
- **Restart** a crashed or exited container
- **Clear logs** when disk usage is high
- **Report metrics** to the network heartbeat

## Risky Actions (Need Approval)
These actions require orchestrator approval via governance:
- **Change environment variables** on a container
- **Update container images** to a new version
- **Modify port mappings** for a service
- **Scale resources** (CPU, memory limits)

To request a risky action:
```
POST /infra/action
{"action": "update_env", "target": "container-name", "details": "reason for change"}
```
This submits a governance proposal and returns `status: pending_approval`.

## Escalation
- If a container keeps crashing after 3 restarts, escalate to the network
- If disk usage exceeds 90%, propose a cleanup action
- If response latency degrades, report to the orchestrator
