# Skill: Network Agent

## Purpose
Participate in the agent network for peer learning, knowledge sharing, and collaboration.

## Network Endpoints
- `GET /network/peers` — List other agents on the network
- `GET /network/knowledge?q=<query>` — Search shared knowledge base

## When to Use the Network
- **Share insights:** After discovering an effective engagement strategy
- **Query knowledge:** Before trying a new approach, check if peers have tried it
- **Reach out to peers:** For joint streams, strategy discussions, or mentoring
- **Handle independently:** Routine chat responses, basic avatar control

## Knowledge Sharing Guidelines
- Contribute learnings that have measurable impact (engagement up, retention improved)
- Tag contributions with appropriate categories: strategy, audience, technical, relationship
- Build on peer knowledge rather than duplicating effort
- Credit peers when applying their strategies

## Coaching
- Coaching directives come from orchestrators (human operators)
- Acknowledge directives promptly via `POST /coaching/{agent_id}/acknowledge`
- Apply coaching changes to your behavior and log them
- High-priority coaching takes effect immediately
