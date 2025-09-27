from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

DEFAULT_STORAGE_ROOT = Path(os.environ.get("STORAGE_SERVICE_ROOT", "./captures"))
DEFAULT_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

API_TOKEN = os.environ.get("STORAGE_SERVICE_TOKEN")

app = FastAPI(title="Autonomy Storage Service", version="1.0.0")


def _check_token(x_storage_token: Optional[str] = Header(default=None)) -> None:
    if API_TOKEN and x_storage_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")


def _session_path(orchestrator_id: Optional[str], session_id: str) -> Path:
    safe_session = session_id.replace("/", "_")
    if orchestrator_id:
        safe_orchestrator = orchestrator_id.replace("/", "_")
        return DEFAULT_STORAGE_ROOT / safe_orchestrator / safe_session
    return DEFAULT_STORAGE_ROOT / safe_session


@app.post("/api/captures", dependencies=[Depends(_check_token)])
async def upload_capture(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    orchestrator_id: Optional[str] = Form(default=None),
) -> JSONResponse:
    target_dir = _session_path(orchestrator_id, session_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    extension = Path(file.filename or "capture.webm").suffix or ".webm"
    target_file = target_dir / f"{timestamp}{extension}"
    with target_file.open("wb") as buffer:
        content = await file.read()
        buffer.write(content)
    return JSONResponse(
        {
            "stored_path": str(target_file.resolve()),
            "size": target_file.stat().st_size,
        }
    )


@app.get("/api/captures", dependencies=[Depends(_check_token)])
def list_captures(orchestrator_id: Optional[str] = None):
    base = DEFAULT_STORAGE_ROOT
    if orchestrator_id:
        base = base / orchestrator_id
    if not base.exists():
        return []
    results = []
    for path in sorted(base.rglob("*")):
        if path.is_file():
            results.append(
                {
                    "path": str(path.relative_to(DEFAULT_STORAGE_ROOT)),
                    "size": path.stat().st_size,
                    "modified": datetime.utcfromtimestamp(path.stat().st_mtime).isoformat() + "Z",
                }
            )
    return results


@app.get("/api/captures/{orchestrator_id}/{session}/{filename}", dependencies=[Depends(_check_token)])
def download_capture(orchestrator_id: str, session: str, filename: str) -> FileResponse:
    path = DEFAULT_STORAGE_ROOT / orchestrator_id / session / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="capture not found")
    return FileResponse(path)
