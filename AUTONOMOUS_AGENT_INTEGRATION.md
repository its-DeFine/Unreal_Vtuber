# Integrating an Autonomous Agent

This guide outlines how to plug an autonomous agent into the existing VTuber BYOC architecture provided in this repository. The repository already contains the NeuroBridge services, NeuroSync worker, and Eliza components.

## 1. Repository Structure

```
NeuroBridge/              # Local API + player
neurosync-worker/         # BYOC worker exposing REST endpoints
eliza-livepeer-integration/ # Eliza packages and plugins
webapp/                   # Front-end interface
```

An additional workspace `autonomous-starter` can be added to host your autonomous agent implementation. This directory is referenced in `package.json` and docker compose files but is not included by default.

## 2. Creating the Agent Workspace

1. Create a new directory at the repository root:

```bash
mkdir autonomous-starter
```

2. Inside `autonomous-starter`, initialize a Node project and install Eliza dependencies:

```bash
cd autonomous-starter
npm init -y
npm install @elizaos/core
```

3. Implement your agent logic in `src/index.ts`. A minimal example looks like:

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

4. Provide a simple `Dockerfile` so the agent can run as a service:

```Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
CMD ["node", "dist/index.js"]
```

5. Add build scripts in `package.json` and compile the TypeScript source during image build.

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

After adding the new workspace, rebuild the docker images:

```bash
docker compose -f docker-compose.bridge.yml -f docker-compose.byoc.yml build autonomous_starter
```

Start the entire stack:

```bash
docker compose -f docker-compose.bridge.yml -f docker-compose.byoc.yml up
```

The webapp will be available on `http://localhost:8088` while the autonomous agent runs inside `autonomous_starter`.

