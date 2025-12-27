# Contributing

## Service images (GHCR)

This repo publishes a small set of **service images** to GitHub Container Registry (GHCR) so orchestrator hosts can do **pull-only** deployments (no local builds, no bind-mounted source trees).

**Images**
- `ghcr.io/its-define/unreal_vtuber/vtuber-script-runner`
- `ghcr.io/its-define/unreal_vtuber/recorder-control`
- `ghcr.io/its-define/unreal_vtuber/orchestrator-health`
- `ghcr.io/its-define/unreal_vtuber/vtuber-watchdog`
- `ghcr.io/its-define/unreal_vtuber/orchestrator-registration`

**Tagging rule**
- On `main`, every published service image gets **both**:
  - `:latest` (rolling)
  - `:sha-<gitsha>` (immutable / reproducible)
- On `staging`, every published service image gets **both**:
  - `:staging` (rolling)
  - `:sha-<gitsha>` (immutable / reproducible)
- `docker-compose.unreal.yml` pins these images via `EMBODY_SERVICE_IMAGE_TAG` (defaults to `latest`).

To pin service images to a specific build, set this in `.env` (copied from `orchestrator.env.example`):
```bash
EMBODY_SERVICE_IMAGE_TAG=sha-<gitsha>
```

## Build context hygiene

Avoid “wide” Docker build contexts (repo root) unless there is no alternative.

- Prefer placing Dockerfiles next to the minimal files they need.
- Keep the Pixel Streaming UI **out of orchestrator images** (UI is served from the edge/gateway).
- If you must use a wider context, add a tight `.dockerignore` so we don’t accidentally ship unrelated assets.
