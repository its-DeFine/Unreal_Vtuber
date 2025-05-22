# Integrating an Autonomous Agent

This guide outlines how to plug an autonomous agent into the existing VTuber BYOC architecture provided in this repository. The repository already contains the NeuroBridge services, NeuroSync worker, and Eliza components.

## 1. Repository Structure

```
NeuroBridge/              # Local API + player
neurosync-worker/         # BYOC worker exposing REST endpoints
eliza-livepeer-integration/ # Eliza packages and plugins
webapp/                   # Front-end interface
```

The repository already ships with an `autonomous-starter` workspace containing a basic agent.  The agent uses the `@elizaos/plugin-bootstrap` plugin which provides a set of core tools (file system access, shell commands, etc.).  You can use this workspace as a starting point for your own agent or modify it to suit your needs.

## 2. Exploring the Agent Workspace

Open the `autonomous-starter` directory to see the sample project structure.  The entry point is `src/index.ts` which creates an agent and registers the bootstrap plugin.  You can add additional plugins or customize the agent behaviour as needed. A simplified example looks like:

```ts
import { createAgent } from '@elizaos/core';

async function main() {
  const agent = await createAgent({
    name: 'demo-agent',
    plugins: [], // add Eliza plugins as needed
  });

  await agent.start();
}

main().catch(console.error);
```
```

4. Review the provided `Dockerfile` in `autonomous-starter`. It installs dependencies and runs the compiled agent.  Adjust it if you add extra build steps or change the entry script.

## 3. Wiring into Docker Compose

`docker-compose.bridge.yml` already contains a commented section for `autonomous_starter`. Uncomment and adjust the service definition to build the new directory:

```yaml
  autonomous_starter:
    build:
      context: ./autonomous-starter
      dockerfile: Dockerfile
    container_name: autonomous_starter_s3
    command: node dist/index.js
    ports:
      - "3100:3000"
    environment:
      - PORT=3000
      - LOG_LEVEL=debug
    networks:
      - scb_bridge_net
    depends_on:
      - neurosync
```

With this service enabled the agent can communicate with NeuroSync through the BYOC worker or directly via the SCB endpoints exposed by `NeuroSync_Local_API`.

## 4. Interacting with the Agent

The autonomous agent can post events or directives to the SCB using the API provided by `NeuroSync_Local_API`:

```bash
curl -X POST http://neurosync:5000/scb/event \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from agent"}'
```

This allows the agent to drive avatar behavior in real time.

## 5. Rebuild and Run

After installing dependencies in `autonomous-starter`, rebuild the Docker images:

```bash
docker compose -f docker-compose.bridge.yml -f docker-compose.byoc.yml build autonomous_starter
```

Start the entire stack:

```bash
docker compose -f docker-compose.bridge.yml -f docker-compose.byoc.yml up
```

The webapp will be available on `http://localhost:8088` while the autonomous agent runs inside `autonomous_starter`.

