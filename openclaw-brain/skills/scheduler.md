# Skill: Scheduler

## Purpose
Manage appointments with humans and other agents via the central calendar.

## Endpoints
- `GET /schedule` — View upcoming events
- `POST /schedule/book` — Request a new appointment

## Appointment Types
| Type | Description |
|------|-------------|
| `human_meeting` | Interview, collaboration, or coaching with a human |
| `agent_meeting` | Strategy discussion or knowledge exchange with a peer agent |
| `maintenance` | Scheduled downtime for updates |
| `stream` | Streaming schedule blocks |
| `coaching` | Orchestrator coaching session |

## When to Schedule
- After a meaningful interaction, propose a follow-up meeting
- When learning something new, schedule a knowledge-sharing session with peers
- Before planned maintenance, schedule a maintenance window
- Suggest regular check-ins with frequent collaborators

## Conflict Resolution
- Never double-book — always check availability first
- If a conflict arises, suggest alternative times
- Prioritise: coaching > stream > human_meeting > agent_meeting > maintenance
