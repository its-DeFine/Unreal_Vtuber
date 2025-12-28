# Staging Environment

This repo supports a simple **staging lane** for the published **service images** (runner/recorder/health/rotator/watchdog/registration).

## Branches and GHCR tags

- `main` publishes service images tagged:
  - `:latest` (rolling)
  - `:sha-<gitsha>` (immutable)
- `staging` publishes service images tagged:
  - `:staging` (rolling)
  - `:sha-<gitsha>` (immutable)

## Use staging on an orchestrator host

In your `.env` (copied from `orchestrator.env.example`), set:
```bash
EMBODY_SERVICE_IMAGE_TAG=staging
```

Then pull + restart:
```bash
docker compose -f docker-compose.unreal.yml pull
docker compose -f docker-compose.unreal.yml up -d
```

## Notes

- The Pixel Streaming images (TURN/signaling/game) are currently pinned to `:latest` separately in `docker-compose.unreal.yml`.
- The encrypted game image is fetched via a Payments lease and is independent of `EMBODY_SERVICE_IMAGE_TAG`.
