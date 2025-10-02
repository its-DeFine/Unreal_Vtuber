"""Simple HTTP service that coordinates Pixel Streaming recordings.

The service exposes a minimal API so the script runner can start and stop
recordings when payloads arrive. Captures are performed through
``PixelStreamingRecorder`` and stored on the orchestrator before they are optionally
uploaded to the storage service.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from aiohttp import web

from stream_recorder.record_stream import PixelStreamingRecorder, RecorderConfig

try:
    from scripts.upload_capture import upload as upload_capture
except Exception:  # pragma: no cover - optional dependency during dev
    upload_capture = None


LOGGER = logging.getLogger("pixelstream.manager")
LOG_LEVEL = os.getenv("RECORDER_LOG_LEVEL", os.getenv("PIXELSTREAM_LOG", "INFO"))
logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))

SIGNALLING_URL = os.getenv("SIGNALLING_URL", "ws://unreal-signaling:8080")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/captures"))
OUTPUT_SUFFIX = os.getenv("OUTPUT_SUFFIX", ".mp4")
STREAMER_ID = os.getenv("STREAMER_ID") or None
VIDEO_BITRATE = int(os.getenv("VIDEO_BITRATE_KBPS", "8000"))
AUDIO_BITRATE = int(os.getenv("AUDIO_BITRATE_KBPS", "192"))
FRAME_RATE = int(os.getenv("FRAME_RATE", "30"))
MODE = os.getenv("MODE", "transcode")
RAW_REMUX_COMMAND = os.getenv("RAW_REMUX_COMMAND") or None
PREFERRED_SPATIAL_LAYER = os.getenv("PREFERRED_SPATIAL_LAYER")
PREFERRED_TEMPORAL_LAYER = os.getenv("PREFERRED_TEMPORAL_LAYER")
ANSWER_START_BITRATE = int(os.getenv("ANSWER_START_BITRATE_KBPS", "8000"))
ANSWER_MAX_BITRATE = int(os.getenv("ANSWER_MAX_BITRATE_KBPS", "20000"))
INACTIVITY_TIMEOUT = float(os.getenv("INACTIVITY_TIMEOUT", "10"))
TAIL_SECONDS = float(os.getenv("TAIL_SECONDS", "2"))
PORT = int(os.getenv("PORT", "9001"))
HOST = os.getenv("HOST", "0.0.0.0")

STORAGE_URL = os.getenv("STORAGE_URL") or None
STORAGE_TOKEN = os.getenv("STORAGE_TOKEN") or None
UPLOAD_ORCHESTRATOR_ID = os.getenv("UPLOAD_ORCHESTRATOR_ID") or None
UPLOAD_ON_FAILURE = os.getenv("UPLOAD_ON_FAILURE", "true").lower() in {"1", "true", "yes", "on"}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class UploadConfig:
    storage_url: Optional[str]
    orchestrator_id: Optional[str]
    token: Optional[str]
    upload_on_failure: bool


class RecorderSession:
    def __init__(self, session_id: str, cfg: RecorderConfig, upload: UploadConfig) -> None:
        self.session_id = session_id
        self.cfg = cfg
        self.upload_cfg = upload
        self.recorder = PixelStreamingRecorder(cfg)
        self.recorded: bool = False
        self.error: Optional[str] = None
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        try:
            self.recorded = await self.recorder.run()
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            LOGGER.exception("Recorder session %s crashed", self.session_id)
        finally:
            LOGGER.info("Recorder session %s finished (recorded=%s)", self.session_id, self.recorded)

    async def stop(self, wait_tail: float) -> None:
        if wait_tail > 0:
            await asyncio.sleep(wait_tail)
        await self.recorder.stop()
        await self._task

    async def wait(self) -> None:
        await self._task

    async def upload(self) -> None:
        if not self.upload_cfg.storage_url:
            return
        if not self.recorded:
            LOGGER.warning("Session %s produced no media; skipping upload", self.session_id)
            return
        if upload_capture is None:
            LOGGER.warning("upload_capture.py unavailable; cannot upload session %s", self.session_id)
            return
        output_path = self.cfg.output_path
        if not output_path.exists() or output_path.stat().st_size == 0:
            LOGGER.warning("Output %s missing for session %s; skipping upload", output_path, self.session_id)
            return
        try:
            upload_capture(
                output_path,
                self.upload_cfg.storage_url,
                self.session_id,
                orchestrator_id=self.upload_cfg.orchestrator_id,
                token=self.upload_cfg.token,
            )
            LOGGER.info("Uploaded capture for session %s", self.session_id)
        except Exception:  # noqa: BLE001
            LOGGER.exception("Failed to upload capture for session %s", self.session_id)


class SessionManager:
    def __init__(self) -> None:
        self.sessions: Dict[str, RecorderSession] = {}
        self._lock = asyncio.Lock()

    async def start(
        self,
        session_id: str,
        signalling_url: Optional[str] = None,
        streamer_id: Optional[str] = None,
    ) -> RecorderSession:
        async with self._lock:
            if session_id in self.sessions:
                raise web.HTTPConflict(text="session already recording")
            if any(not sess._task.done() for sess in self.sessions.values()):
                raise web.HTTPConflict(text="another recording in progress")
            output_path = (OUTPUT_DIR / session_id).with_suffix(OUTPUT_SUFFIX)
            cfg = RecorderConfig(
                signalling_url=signalling_url or SIGNALLING_URL,
                output_path=output_path,
                streamer_id=streamer_id or STREAMER_ID,
                duration=None,
                inactivity_timeout=INACTIVITY_TIMEOUT,
                video_bitrate_kbps=VIDEO_BITRATE,
                audio_bitrate_kbps=AUDIO_BITRATE,
                frame_rate=FRAME_RATE,
                mode=MODE,
                raw_remux=RAW_REMUX_COMMAND,
                preferred_spatial_layer=int(PREFERRED_SPATIAL_LAYER) if PREFERRED_SPATIAL_LAYER else None,
                preferred_temporal_layer=int(PREFERRED_TEMPORAL_LAYER) if PREFERRED_TEMPORAL_LAYER else None,
                answer_start_bitrate_kbps=ANSWER_START_BITRATE,
                answer_max_bitrate_kbps=ANSWER_MAX_BITRATE,
            )
            session = RecorderSession(
                session_id,
                cfg,
                UploadConfig(
                    storage_url=STORAGE_URL,
                    orchestrator_id=UPLOAD_ORCHESTRATOR_ID,
                    token=STORAGE_TOKEN,
                    upload_on_failure=UPLOAD_ON_FAILURE,
                ),
            )
            self.sessions[session_id] = session
            LOGGER.info("Recording session %s started", session_id)
            return session

    async def stop(self, session_id: str, success: bool, upload: Optional[bool]) -> RecorderSession:
        async with self._lock:
            session = self.sessions.get(session_id)
            if session is None:
                raise web.HTTPNotFound(text="session not found")
        await session.stop(TAIL_SECONDS)
        should_upload = upload if upload is not None else (success or session.upload_cfg.upload_on_failure)
        if should_upload:
            await session.upload()
        async with self._lock:
            self.sessions.pop(session_id, None)
        return session

    async def status(self) -> Dict[str, Dict[str, Optional[str]]]:
        async with self._lock:
            return {
                session_id: {
                    "recorded": str(session.recorded),
                    "done": str(session._task.done()),
                    "error": session.error,
                    "output": str(session.cfg.output_path),
                }
                for session_id, session in self.sessions.items()
            }


MANAGER = SessionManager()


async def handle_start(request: web.Request) -> web.Response:
    payload = await request.json()
    session_id = payload.get("session_id")
    if not session_id:
        raise web.HTTPBadRequest(text="session_id required")
    signalling_url = payload.get("signalling_url")
    streamer_id = payload.get("streamer")
    session = await MANAGER.start(session_id, signalling_url, streamer_id)
    return web.json_response({
        "status": "recording",
        "session_id": session.session_id,
        "output": str(session.cfg.output_path),
    }, status=202)


async def handle_stop(request: web.Request) -> web.Response:
    payload = await request.json()
    session_id = payload.get("session_id")
    if not session_id:
        raise web.HTTPBadRequest(text="session_id required")
    success = bool(payload.get("success", True))
    upload = payload.get("upload")
    session = await MANAGER.stop(session_id, success=success, upload=upload)
    return web.json_response({
        "status": "stopped",
        "session_id": session.session_id,
        "recorded": session.recorded,
        "error": session.error,
    })


async def handle_status(request: web.Request) -> web.Response:
    data = await MANAGER.status()
    return web.json_response({"sessions": data})


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes(
        [
            web.get("/health", handle_health),
            web.get("/status", handle_status),
            web.post("/record/start", handle_start),
            web.post("/record/stop", handle_stop),
        ]
    )
    return app


def main() -> None:
    LOGGER.info("Recorder manager starting on %s:%s", HOST, PORT)
    web.run_app(create_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
