# NeuroSync × Livepeer BYOC Overlay

This README walks you through the **Bring-Your-Own-Container (BYOC)** overlay that plugs the existing NeuroSync stack into Livepeer's generic-container pipeline.  This is **add-on infrastructure** – nothing here interferes with your current development workflow.  Simply include the overlay compose file when you want BYOC, omit it when you don't.

> ℹ️  The overlay is **self-contained** – no vendoring of Livepeer images into your main compose file, and the only changes to the base image are an extra layer with ~5 MiB of Python code + dependencies.

---

## TL;DR

```bash
# one-time – create shared Docker network
$ docker network create byoc || true

# build the worker image + spin up the overlay
$ docker compose -f docker-compose.yml -f docker-compose.byoc.yml up --build

# open the demo front-end
$ open http://localhost:8088  # or use your browser of choice
```

You should see:

1. The worker container registering its capability with the orchestrator.
2. The orchestrator exposing `https://orchestrator:9995/capability/list` with your capability.
3. The Caddy proxy serving the demo web-app and forwarding `/api/*` routes to the orchestrator.

---

## File Overview

| File / Directory                 | Purpose                                                    |
|---------------------------------|------------------------------------------------------------|
| `NeuroSync-Core/dockerfile`      | Base image + **COPY** of `neurosync-worker` + new entrypoint|
| `neurosync-worker/`             | Thin FastAPI adapter that registers & streams VTuber frames |
| `docker-compose.byoc.yml`        | Overlay services: worker, orchestrator, gateway, Caddy     |
| `Caddyfile`                      | Static front-end + reverse-proxy for orchestrator           |
| `webapp-byoc/` (optional)        | React demo front-end (copy of Livepeer voice-cloning webapp)|

---

## Logging Philosophy

* **Structured JSON**, one-line per event – easy to ship to Loki, Datadog…
* **Key fields**: `capability`, `job_id`, `request_id`, `duration_ms`, `severity`.
* **Never throw away context** – prefer `logger.debug()` with full payloads instead of `print()`.

Sample log (pretty-printed):

```jsonc
{
  "timestamp": "2025-05-08T12:34:56Z",
  "level": "INFO",
  "name": "neurosync.worker",
  "msg": "VTuber job accepted",
  "job_id": "42e9f63d",
  "character": "ada"
}
```

Feel free to run the container with `LOG_LEVEL=DEBUG` while developing – the worker honours standard logging environment variables.

---

## Extending the Stub

* Replace the placeholder generator in `server_adapter.py::_stream` with a call into the NeuroSync pipeline.
* Implement real-time audio + blendshape generation and `yield` frames matching `NEUROSYNC_REALTIME_FRAME_SCHEMA`.
* Wire-up **gpu utilisation metrics** at `/metrics` using Prometheus format for future autoscaling.

---

Happy hacking 🚀 