from __future__ import annotations

import asyncio
import base64
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Literal, Optional

import aiohttp
from fastapi import FastAPI, HTTPException, Request
from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

SESSION_ROOT = Path(os.getenv("VTUBER_SESSION_ROOT", "/opt/embody/sessions"))
TCP_HOST = os.getenv("VTUBER_TCP_HOST", "127.0.0.1")
TCP_PORT = int(os.getenv("VTUBER_TCP_PORT", "7777"))
ALLOWED_ADDRESSES = [addr.strip() for addr in os.getenv("VTUBER_ALLOWED_ADDRESSES", "").split(",") if addr.strip()]
DEFAULT_AUDIO_HOLD_MS = int(os.getenv("VTUBER_AUDIO_HOLD_MS", "15000"))


class AudioAsset(BaseModel):
    id: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    payload_b64: Optional[str] = None
    download_url: Optional[AnyHttpUrl] = None
    duration_ms: Optional[int] = Field(None, ge=0)

    @model_validator(mode="after")
    def _source(cls, values: "AudioAsset") -> "AudioAsset":
        has_payload = bool(values.payload_b64)
        has_url = bool(values.download_url)
        if not has_payload and not has_url:
            raise ValueError("audio asset requires payload_b64 or download_url")
        if has_payload and has_url:
            raise ValueError("provide only one of payload_b64 or download_url")
        return values

    def write_to(self, target_dir: Path) -> None:
        data = base64.b64decode(self.payload_b64) if self.payload_b64 else None
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / self.filename
        if data is not None:
            target_path.write_bytes(data)

    async def download_into(self, session: aiohttp.ClientSession, target_dir: Path) -> None:
        if self.download_url is None:
            raise ValueError("download URL missing")
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / self.filename
        async with session.get(str(self.download_url)) as resp:
            resp.raise_for_status()
            target_path.write_bytes(await resp.read())


class CommandStep(BaseModel):
    delay_ms: int = Field(..., ge=0)
    type: Literal["tcp", "audio"]
    value: Optional[str] = None
    id: Optional[str] = None

    @model_validator(mode="after")
    def _validate(cls, values: "CommandStep") -> "CommandStep":
        if values.type == "tcp" and not values.value:
            raise ValueError("tcp commands require value")
        if values.type == "audio" and not values.id:
            raise ValueError("audio commands require id")
        return values


class ScriptRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    commands: list[CommandStep] = Field(default_factory=list)
    audio: list[AudioAsset] = Field(default_factory=list)
    callback_url: Optional[AnyHttpUrl] = None

    @field_validator("commands")
    def _non_empty(cls, value: list[CommandStep]) -> list[CommandStep]:
        if not value:
            raise ValueError("commands list cannot be empty")
        return value

    @field_validator("audio")
    def _unique_audio(cls, value: list[AudioAsset]) -> list[AudioAsset]:
        seen = set()
        for asset in value:
            if asset.id in seen:
                raise ValueError(f"duplicate audio id {asset.id}")
            seen.add(asset.id)
        return value

    def audio_index(self) -> Dict[str, AudioAsset]:
        return {asset.id: asset for asset in self.audio}


class ScriptStatus(BaseModel):
    session_id: str
    state: Literal["pending", "running", "completed", "failed"] = "pending"
    current_step: int = 0
    total_steps: int = 0
    error: Optional[str] = None


app = FastAPI()
_session_lock = asyncio.Lock()
_active_session: Optional[str] = None
_statuses: Dict[str, ScriptStatus] = {}


async def _prepare_assets(payload: ScriptRequest) -> Path:
    session_dir = SESSION_ROOT / payload.session_id
    audio_dir = session_dir / "audio"
    if session_dir.exists():
        shutil.rmtree(session_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession() as http:
        for asset in payload.audio:
            if asset.payload_b64:
                asset.write_to(audio_dir)
            else:
                await asset.download_into(http, audio_dir)
    return audio_dir


async def _execute_script(payload: ScriptRequest, status: ScriptStatus) -> None:
    audio_dir = await _prepare_assets(payload)
    audio_map = payload.audio_index()
    status.state = "running"
    status.total_steps = len(payload.commands)

    try:
        for idx, command in enumerate(payload.commands, start=1):
            await asyncio.sleep(command.delay_ms / 1000)
            status.current_step = idx
            message = _render_command(command, payload.session_id, audio_map, audio_dir)
            logger.info("TCP command -> %s", message)
            reader, writer = await asyncio.open_connection(TCP_HOST, TCP_PORT)
            try:
                writer.write((message + "\r\n").encode("utf-8"))
                await writer.drain()
                await asyncio.sleep(0.05)
                if command.type == "audio":
                    asset = audio_map.get(command.id or "")
                    hold_ms = asset.duration_ms if asset and asset.duration_ms else DEFAULT_AUDIO_HOLD_MS
                    await asyncio.sleep(hold_ms / 1000)
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
        status.state = "completed"
    except Exception as exc:  # noqa: BLE001
        status.state = "failed"
        status.error = str(exc)
        logger.exception("Script execution failed")
    finally:
        try:
            shutil.rmtree(SESSION_ROOT / payload.session_id, ignore_errors=True)
        except Exception:
            logger.warning("Failed to cleanup session directory", exc_info=True)
        async with _session_lock:
            global _active_session
            if _active_session == payload.session_id:
                _active_session = None


def _render_command(
    command: CommandStep,
    session_id: str,
    audio_map: Dict[str, AudioAsset],
    audio_dir: Path,
) -> str:
    if command.type == "tcp":
        assert command.value is not None
        return command.value
    asset = audio_map.get(command.id or "")
    if asset is None:
        raise ValueError(f"audio asset {command.id!r} not found")
    file_path = audio_dir / asset.filename
    if not file_path.exists():
        raise ValueError(f"audio file missing: {asset.filename}")
    return f"TTS_BYOB_/opt/embody/sessions/{session_id}/audio/{asset.filename}"


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/scripts/execute")
async def execute_script(payload: ScriptRequest, request: Request) -> ScriptStatus:
    client_ip = request.client.host if request.client else None
    if ALLOWED_ADDRESSES and (client_ip not in ALLOWED_ADDRESSES):
        raise HTTPException(status_code=403, detail="client address not allowed")
    global _active_session
    async with _session_lock:
        if _active_session is not None:
            raise HTTPException(status_code=409, detail="script already running")
        _active_session = payload.session_id
        status = ScriptStatus(session_id=payload.session_id)
        _statuses[payload.session_id] = status

    asyncio.create_task(_execute_script(payload, status))
    return status


@app.get("/scripts/{session_id}")
async def get_status(session_id: str) -> ScriptStatus:
    status = _statuses.get(session_id)
    if status is None:
        raise HTTPException(status_code=404, detail="session not found")
    return status
