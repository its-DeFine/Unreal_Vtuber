from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional

import aiohttp

from server.script_models import AudioAsset, CommandStep, ScriptRequest, ScriptStatus, SESSION_ROOT

logger = logging.getLogger(__name__)

class ScriptExecutionError(Exception):
    """Raised when a script fails to execute."""


class ScriptSessionManager:
    def __init__(self, tcp_host: str, tcp_port: int) -> None:
        self._lock = asyncio.Lock()
        self._active_session: Optional[str] = None
        self._statuses: Dict[str, ScriptStatus] = {}
        self._tcp_host = tcp_host
        self._tcp_port = tcp_port
        SESSION_ROOT.mkdir(parents=True, exist_ok=True)

    async def try_start(self, payload: ScriptRequest) -> ScriptStatus:
        async with self._lock:
            if self._active_session is not None:
                raise ScriptExecutionError("script execution already in progress")
            self._active_session = payload.session_id
            status = ScriptStatus.pending(payload.session_id, len(payload.commands))
            self._statuses[payload.session_id] = status
            return status

    async def finish(self, session_id: str) -> None:
        async with self._lock:
            if self._active_session == session_id:
                self._active_session = None

    def status(self, session_id: str) -> Optional[ScriptStatus]:
        status = self._statuses.get(session_id)
        return status

    async def schedule(
        self,
        payload: ScriptRequest,
        callback: Optional[Callable[[ScriptStatus], Awaitable[None]]] = None,
    ) -> ScriptStatus:
        status = await self.try_start(payload)

        async def _runner() -> None:
            final_status = await self._run_script(payload, status)
            if callback is not None:
                try:
                    await callback(final_status)
                except Exception:  # noqa: BLE001
                    logger.exception("script callback failed")

        asyncio.create_task(_runner())
        return status

    async def _run_script(self, payload: ScriptRequest, status: ScriptStatus) -> ScriptStatus:
        try:
            status.mark_running()
            await self._prepare_assets(payload)
            await self._execute(payload, status)
            status.mark_completed()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Script execution failed: %s", exc)
            status.mark_failed(str(exc))
        finally:
            await self.finish(payload.session_id)
            await self._cleanup(payload.session_id)
        return status

    async def _prepare_assets(self, payload: ScriptRequest) -> None:
        session_dir = SESSION_ROOT / payload.session_id
        audio_dir = session_dir / "audio"
        if session_dir.exists():
            shutil.rmtree(session_dir)
        audio_dir.mkdir(parents=True, exist_ok=True)

        async with aiohttp.ClientSession() as http:
            for asset in payload.audio:
                if asset.payload_b64 is not None:
                    asset.write_to(audio_dir)
                else:
                    await asset.download_into(http, audio_dir)

    async def _execute(self, payload: ScriptRequest, status: ScriptStatus) -> None:
        audio_map = payload.audio_index()
        session_dir = SESSION_ROOT / payload.session_id
        audio_dir = session_dir / "audio"

        try:
            for idx, command in enumerate(payload.commands, start=1):
                await asyncio.sleep(command.delay_ms / 1000)
                status.current_step = idx
                message = self._render_command(command, payload.session_id, audio_map, audio_dir)
                logger.debug("sending TCP command: %s", message)
                reader, writer = await asyncio.open_connection(self._tcp_host, self._tcp_port)
                try:
                    writer.write((message + "\r\n").encode("utf-8"))
                    await writer.drain()
                    await reader.read(1)
                except Exception:  # noqa: BLE001
                    logger.exception("TCP command failed")
                    raise
                finally:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:  # noqa: BLE001
                        pass

    def _render_command(
        self,
        command: CommandStep,
        session_id: str,
        audio_map: Dict[str, AudioAsset],
        audio_dir: Path,
    ) -> str:
        if command.type == "tcp":
            assert command.value is not None
            return command.value
        if command.type == "audio":
            asset = audio_map.get(command.id or "")
            if asset is None:
                raise ScriptExecutionError(f"audio id {command.id!r} not found")
            file_path = audio_dir / asset.filename
            if not file_path.exists():
                raise ScriptExecutionError(f"audio file missing: {asset.filename}")
            return f"TTSBYOB /opt/embody/sessions/{session_id}/audio/{asset.filename}"
        raise ScriptExecutionError(f"unknown command type: {command.type}")

    async def _cleanup(self, session_id: str) -> None:
        session_dir = SESSION_ROOT / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)

    def all_statuses(self) -> Dict[str, ScriptStatus]:
        return self._statuses


def create_session_manager() -> ScriptSessionManager:
    tcp_host = os.getenv("VTUBER_TCP_HOST", "host.docker.internal")
    tcp_port = int(os.getenv("VTUBER_TCP_PORT", "7777"))
    return ScriptSessionManager(tcp_host, tcp_port)
