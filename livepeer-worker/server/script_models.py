from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Dict, Literal, Optional

import aiohttp
from pydantic import AnyHttpUrl, BaseModel, Field, root_validator, validator


class AudioAsset(BaseModel):
    """Audio payload metadata delivered alongside the script."""

    id: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    payload_b64: Optional[str] = None
    download_url: Optional[AnyHttpUrl] = None
    duration_ms: Optional[int] = Field(None, ge=0)

    @root_validator
    def _payload_source(cls, values: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
        payload, url = values.get("payload_b64"), values.get("download_url")
        if not payload and not url:
            raise ValueError("audio asset requires payload_b64 or download_url")
        if payload and url:
            raise ValueError("provide only one of payload_b64 or download_url")
        return values

    def write_to(self, target_dir: Path) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / self.filename
        if self.payload_b64 is not None:
            data = base64.b64decode(self.payload_b64)
            with target_path.open("wb") as fh:
                fh.write(data)
            return target_path

        # download from url
        if self.download_url is None:
            raise RuntimeError("audio asset missing both data and URL")
        return target_path

    async def download_into(self, session: aiohttp.ClientSession, target_dir: Path) -> Path:
        target_path = target_dir / self.filename
        if self.payload_b64 is not None:
            return self.write_to(target_dir)
        if self.download_url is None:
            raise RuntimeError("audio asset missing download URL")
        target_dir.mkdir(parents=True, exist_ok=True)
        async with session.get(str(self.download_url)) as resp:
            resp.raise_for_status()
            data = await resp.read()
        with target_path.open("wb") as fh:
            fh.write(data)
        return target_path


class CommandStep(BaseModel):
    delay_ms: int = Field(..., ge=0)
    type: Literal["tcp", "audio"]
    value: Optional[str] = None
    id: Optional[str] = Field(None, min_length=1)

    @validator("value", always=True)
    def _require_value(cls, value: Optional[str], values: Dict[str, object]) -> Optional[str]:
        if values.get("type") == "tcp" and not value:
            raise ValueError("tcp command requires value")
        return value

    @validator("id", always=True)
    def _require_audio_id(cls, value: Optional[str], values: Dict[str, object]) -> Optional[str]:
        if values.get("type") == "audio" and not value:
            raise ValueError("audio command requires id")
        return value


class ScriptRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    auth_token: Optional[str] = None
    commands: list[CommandStep] = Field(default_factory=list, min_items=1)
    audio: list[AudioAsset] = Field(default_factory=list)
    callback_url: Optional[AnyHttpUrl] = None

    @validator("commands")
    def _ensure_commands(cls, value: list[CommandStep]) -> list[CommandStep]:
        if not value:
            raise ValueError("commands list cannot be empty")
        return value

    @validator("audio")
    def _unique_audio_ids(cls, value: list[AudioAsset]) -> list[AudioAsset]:
        seen = set()
        for asset in value:
            if asset.id in seen:
                raise ValueError(f"duplicate audio id: {asset.id}")
            seen.add(asset.id)
        return value

    def audio_index(self) -> Dict[str, AudioAsset]:
        return {asset.id: asset for asset in self.audio}


class ScriptStatus(BaseModel):
    session_id: str
    state: Literal["pending", "running", "completed", "failed"]
    started_at: Optional[float]
    ended_at: Optional[float]
    current_step: int = 0
    total_steps: int = 0
    error: Optional[str] = None

    @classmethod
    def pending(cls, session_id: str, total_steps: int) -> "ScriptStatus":
        return cls(session_id=session_id, state="pending", started_at=None, ended_at=None, total_steps=total_steps)

    def mark_running(self) -> None:
        self.state = "running"
        self.started_at = time.monotonic()

    def mark_completed(self) -> None:
        self.state = "completed"
        self.ended_at = time.monotonic()

    def mark_failed(self, message: str) -> None:
        self.state = "failed"
        self.error = message
        self.ended_at = time.monotonic()


SESSION_ROOT = Path(os.getenv("VTUBER_SESSION_ROOT", "/opt/embody/sessions"))
