# Game Image Updates (Encrypted)

The Unreal game image is delivered as an **encrypted artifact**. Orchestrators do not pull it anonymously from GHCR.

Updating the game image is done via a **Payments lease** (download → decrypt → load into Docker). This is exposed through:
- the local CLI (`./scripts/embody_cli.sh rollout ...`), and
- the `orchestrator-health` remote ops endpoint (`:9090/ops/rollout`) when allowlisted.

## Low-downtime flow (stage while live, apply during idle)

Staging is safe while users are live because it only **loads** the new image (no restarts).
Applying requires an idle window because `unreal-game` containers must be **stopped**.

```bash
# 1) While users are live (no restart):
sudo ./scripts/embody_cli.sh rollout --stage

# 2) During an idle window:
sudo ./scripts/embody_cli.sh power sleep
sudo ./scripts/embody_cli.sh rollout --apply-staged
sudo ./scripts/embody_cli.sh power wake --ttl 3600
```

Notes:
- `rollout --stage` downloads/decrypts/loads the next image and writes a “pending rollout” state.
- `rollout --apply-staged` switches the next wake/start to the staged image (it will refuse while any `unreal-game` is running).

## Remote automation (no SSH)

Remote callers can use the same stage/apply behavior via `orchestrator-health` on port `9090`.

Requirements:
- `POWER_ALLOWED_IPS` / `POWER_ALLOWED_IPS_FILE` must allowlist the caller IP (otherwise `/ops/*` returns `403`).
- `/ops/rollout` will return `409` if any `unreal-game` container is running (unless `stage_only=true`).

Stage only (prefetch while live):
```json
{
  "payments_api_url": "http://<payments>:8081",
  "image_ref": "ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1",
  "stage_only": true,
  "min_free_gb": 15
}
```

Apply staged (idle window; requires sleep):
```json
{
  "image_ref": "ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1",
  "skip_download": true,
  "recreate_stopped": true
}
```

See `docs/embody-cli.md` for endpoint details.

