"""Expose local Docker service health over HTTP for remote monitoring."""
from __future__ import annotations

import os
import logging

from fastapi import FastAPI, HTTPException

from .service_monitor import ServiceMonitor

logger = logging.getLogger(__name__)

app = FastAPI(title="Orchestrator Health", version="1.0.0")
monitor = ServiceMonitor()


@app.get("/health")
def read_health() -> dict:
    try:
        return monitor.check_services()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Remote health check failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


def main() -> None:
    import uvicorn

    port = int(os.environ.get("ORCHESTRATOR_HEALTH_PORT", "9090"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
