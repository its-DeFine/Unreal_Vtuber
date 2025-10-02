from __future__ import annotations

import asyncio
import base64
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Literal, Optional, Tuple

import aiohttp
from fastapi import FastAPI, HTTPException, Request
from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

SESSION_ROOT = Path(os.getenv("VTUBER_SESSION_ROOT", "/opt/embody/sessions"))
TCP_HOST = os.getenv("VTUBER_TCP_HOST", "unreal-game")
TCP_PORT = int(os.getenv("VTUBER_TCP_PORT", "7777"))
TCP_CONNECT_RETRIES = int(os.getenv("VTUBER_TCP_RETRIES", "20"))
TCP_RETRY_DELAY = float(os.getenv("VTUBER_TCP_RETRY_DELAY", "0.5"))
ALLOWED_ADDRESSES = [addr.strip() for addr in os.getenv("VTUBER_ALLOWED_ADDRESSES", "").split(",") if addr.strip()]
DEFAULT_AUDIO_HOLD_MS = int(os.getenv("VTUBER_AUDIO_HOLD_MS", "15000"))
RECORDER_ENDPOINT = os.getenv("VTUBER_RECORDER_ENDPOINT", "http://127.0.0.1:9001").strip()
RECORDER_TIMEOUT = float(os.getenv("VTUBER_RECORDER_TIMEOUT", "5"))


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


async def _prepare_assets(payload: ScriptRequest) -> Tuple[Path, Dict[str, str]]:
    session_dir = SESSION_ROOT / payload.session_id
    audio_dir = session_dir / "audio"
    if session_dir.exists():
        shutil.rmtree(session_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession() as http:
        sanitized: Dict[str, str] = {}
        for idx, asset in enumerate(payload.audio):
            if asset.payload_b64:
                asset.write_to(audio_dir)
            else:
                await asset.download_into(http, audio_dir)
            original = audio_dir / asset.filename
            if original.exists():
                safe_name = _sanitize_filename(idx, original.suffix or ".mp3")
                original.rename(audio_dir / safe_name)
                sanitized[asset.id] = safe_name
        return audio_dir, sanitized


async def _execute_script(payload: ScriptRequest, status: ScriptStatus) -> None:
    await _notify_recorder_start(payload.session_id)
    audio_dir, sanitized_files = await _prepare_assets(payload)
    audio_map = payload.audio_index()
    status.state = "running"
    status.total_steps = len(payload.commands)
    success = False

    try:
        for idx, command in enumerate(payload.commands, start=1):
            await asyncio.sleep(command.delay_ms / 1000)
            status.current_step = idx
            message = _render_command(command, payload.session_id, audio_map, audio_dir, sanitized_files)
            logger.info("TCP command -> %s", message)
            reader, writer = await _open_command_connection()
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
        success = True
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
        await _notify_recorder_stop(payload.session_id, success)


def _render_command(
    command: CommandStep,
    session_id: str,
    audio_map: Dict[str, AudioAsset],
    audio_dir: Path,
    sanitized_files: Dict[str, str],
) -> str:
    if command.type == "tcp":
        assert command.value is not None
        return command.value
    asset = audio_map.get(command.id or "")
    if asset is None:
        raise ValueError(f"audio asset {command.id!r} not found")
    filename = sanitized_files.get(asset.id or "") or asset.filename
    file_path = audio_dir / filename
    if not file_path.exists():
        raise ValueError(f"audio file missing: {filename}")
    return f"TTS_BYOB_/opt/embody/sessions/{session_id}/audio/{filename}"


def _sanitize_filename(index: int, suffix: str) -> str:
    safe_index = index % 10000
    return f"{safe_index:04d}{suffix}"


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


async def _notify_recorder_start(session_id: str) -> None:
    if not RECORDER_ENDPOINT:
        return
    payload = {"session_id": session_id}
    await _send_recorder_request("record/start", payload)


async def _notify_recorder_stop(session_id: str, success: bool) -> None:
    if not RECORDER_ENDPOINT:
        return
    payload = {"session_id": session_id, "success": success}
    await _send_recorder_request("record/stop", payload)


async def _send_recorder_request(path: str, payload: Dict[str, str | bool]) -> None:
    url = f"{RECORDER_ENDPOINT.rstrip('/')}/{path.lstrip('/')}"
    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(url, json=payload, timeout=RECORDER_TIMEOUT) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    logger.warning(
                        "Recorder endpoint %s responded with %s: %s",
                        url,
                        resp.status,
                        text,
                    )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to contact recorder endpoint %s", url)


async def _open_command_connection() -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    last_exc: Optional[Exception] = None
    attempts = max(1, TCP_CONNECT_RETRIES)
    for attempt in range(1, attempts + 1):
        try:
            return await asyncio.open_connection(TCP_HOST, TCP_PORT)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "TCP connect attempt %s/%s failed (%s). Retrying in %.2fs",
                attempt,
                attempts,
                exc,
                TCP_RETRY_DELAY,
            )
            await asyncio.sleep(TCP_RETRY_DELAY)
    assert last_exc is not None
    raise last_exc


@app.get("/scripts/{session_id}")
async def get_status(session_id: str) -> ScriptStatus:
    status = _statuses.get(session_id)
    if status is None:
        raise HTTPException(status_code=404, detail="session not found")
    return status
