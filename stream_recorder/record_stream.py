#!/usr/bin/env python3

"""Headless Pixel Streaming recorder using aiortc.

The script connects to the Pixel Streaming signalling server, subscribes to a chosen
streamer and records the incoming audio/video tracks to a WebM or MP4 file.  It
mimics the handshake normally performed by Epic's browser player; no project-side
changes are required on the Unreal build.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
from aiortc import (
    RTCIceCandidate,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
)
from aiortc.contrib.media import MediaRecorder, MediaRecorderContext

logger = logging.getLogger("pixelstream.recorder")


@dataclass
class RecorderConfig:
    signalling_url: str
    output_path: Path
    streamer_id: Optional[str]
    duration: Optional[float]
    inactivity_timeout: float = 15.0


class PixelStreamingRecorder:
    def __init__(self, cfg: RecorderConfig) -> None:
        self.cfg = cfg
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.pc: Optional[RTCPeerConnection] = None
        self.recorder: Optional[MediaRecorder] = None
        self.recorder_started = False
        self.recorder_start_lock = asyncio.Lock()
        self.player_id: Optional[str] = None
        self.peer_connection_options: Dict[str, Any] = {}
        self.active = asyncio.Event()
        self.close_event = asyncio.Event()
        self.shutting_down = False

    async def run(self) -> bool:
        logger.info("Connecting to signalling server %s", self.cfg.signalling_url)
        async with aiohttp.ClientSession() as session:
            self.session = session
            async with session.ws_connect(self.cfg.signalling_url, timeout=30) as ws:
                self.ws = ws
                await self.on_open()
                consumer = asyncio.create_task(self._consume())
                terminator = asyncio.create_task(self._wait_for_termination())
                done, pending = await asyncio.wait(
                    {consumer, terminator}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                for task in done:
                    exc = task.exception()
                    if exc:
                        raise exc

        await self._shutdown()
        return self.recorder_started

    async def _consume(self) -> None:
        assert self.ws is not None
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self.on_message(json.loads(msg.data))
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error("Websocket error: %s", msg.data)
                break
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                logger.info("Websocket closed")
                break
        self.close_event.set()

    async def _wait_for_termination(self) -> None:
        if self.cfg.duration is not None:
            await asyncio.sleep(self.cfg.duration)
            logger.info("Duration %ss elapsed, stopping", self.cfg.duration)
        else:
            await self.close_event.wait()
        await self._send_unsubscribe()
        await self._close_pc()
        await self._stop_recorder()
        self.shutting_down = True
        if self.ws is not None and not self.ws.closed:
            await self.ws.close()

    async def on_open(self) -> None:
        logger.info("Websocket connection established")
        await self._send_message({"type": "listStreamers"})

    async def on_message(self, message: Dict[str, Any]) -> None:
        msg_type = message.get("type")
        logger.debug("Received message: %s", message)

        if msg_type == "config":
            self.peer_connection_options = message.get("peerConnectionOptions", {})
            protocol = message.get("protocolVersion")
            logger.info("Received config (protocol %s)", protocol)
        elif msg_type == "streamerList":
            await self._handle_streamer_list(message)
        elif msg_type == "offer":
            await self._handle_offer(message)
        elif msg_type == "iceCandidate":
            await self._handle_remote_candidate(message)
        elif msg_type == "ping":
            await self._send_message({"type": "pong", "time": message.get("time")})
        elif msg_type == "playerCount":
            logger.debug("Player count: %s", message.get("count"))
        elif msg_type in {"qualityControlOwnership", "playerDisconnected", "requestQualityControl"}:
            logger.debug("Ignoring message type %s", msg_type)
        else:
            logger.debug("Unhandled signalling message: %s", msg_type)

    async def _handle_streamer_list(self, message: Dict[str, Any]) -> None:
        ids = message.get("ids", [])
        logger.info("Available streamers: %s", ids)
        target = self.cfg.streamer_id or (ids[0] if ids else None)
        if not target:
            logger.warning("No streamer available. Will request list again after timeout.")
            await asyncio.sleep(self.cfg.inactivity_timeout)
            await self._send_message({"type": "listStreamers"})
            return
        logger.info("Subscribing to streamer %s", target)
        await self._send_message({"type": "subscribe", "streamerId": target})

    async def _create_pc(self) -> RTCPeerConnection:
        if self.pc:
            return self.pc
        ice_servers: list[RTCIceServer] = []
        if self.peer_connection_options:
            for entry in self.peer_connection_options.get("iceServers", []):
                if isinstance(entry, dict):
                    ice_servers.append(RTCIceServer(**entry))
                else:
                    ice_servers.append(entry)
        configuration = RTCConfiguration(iceServers=ice_servers)
        for attr in ("bundlePolicy", "rtcpMuxPolicy", "iceTransportPolicy"):
            if self.peer_connection_options and attr in self.peer_connection_options:
                setattr(configuration, attr, self.peer_connection_options[attr])
        pc = RTCPeerConnection(configuration=configuration)
        pc.on("track", self._on_track)

        @pc.on("icecandidate")
        async def on_icecandidate(event: Any) -> None:
            candidate = event.candidate
            if candidate is None:
                await self._send_message({"type": "iceCandidate", "candidate": {}})
                return
            payload = {
                "candidate": {
                    "candidate": candidate.to_sdp(),
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex,
                }
            }
            if candidate.usernameFragment:
                payload["candidate"]["usernameFragment"] = candidate.usernameFragment
            await self._send_message({"type": "iceCandidate", **payload})

        self.pc = pc
        return pc

    def _ensure_recorder(self) -> MediaRecorder:
        if not self.recorder:
            output_dir = self.cfg.output_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            recording_kwargs: Dict[str, Any] = {}
            suffix = self.cfg.output_path.suffix.lower()
            if suffix == ".webm":
                recording_kwargs["format"] = "webm"
            elif suffix in {".mp4", ".m4v", ".mov"}:
                recording_kwargs["format"] = "mp4"
            self.recorder = MediaRecorder(str(self.cfg.output_path), **recording_kwargs)
            if suffix == ".webm":
                self._patch_recorder_for_webm()
        return self.recorder

    def _patch_recorder_for_webm(self) -> None:
        recorder = self.recorder
        if recorder is None:
            return

        def _webm_add_track(self_recorder, track) -> None:
            container = getattr(self_recorder, "_MediaRecorder__container", None)
            tracks = getattr(self_recorder, "_MediaRecorder__tracks", None)
            if container is None or tracks is None:
                raise RuntimeError("Recorder container unavailable")

            format_name = container.format.name

            if track.kind == "audio":
                if format_name == "webm":
                    codec_name = "libopus"
                elif format_name in ("wav", "alsa", "pulse"):
                    codec_name = "pcm_s16le"
                elif format_name == "mp3":
                    codec_name = "mp3"
                elif format_name == "ogg":
                    codec_name = "libopus"
                else:
                    codec_name = "aac"
                stream = container.add_stream(codec_name)
            else:
                if format_name == "image2":
                    stream = container.add_stream("png", rate=30)
                    stream.pix_fmt = "rgb24"
                else:
                    stream = container.add_stream("libvpx", rate=30)
                    stream.pix_fmt = "yuv420p"

            tracks[track] = MediaRecorderContext(stream)

        recorder.addTrack = types.MethodType(_webm_add_track, recorder)  # type: ignore[assignment]

    def _on_track(self, track) -> None:
        logger.info("Track received: %s", track.kind)
        recorder = self._ensure_recorder()
        recorder.addTrack(track)
        if not self.recorder_started:
            asyncio.ensure_future(self._start_recorder())

    async def _start_recorder(self) -> None:
        async with self.recorder_start_lock:
            if self.recorder_started:
                return
            recorder = self._ensure_recorder()
            await recorder.start()
            self.recorder_started = True
            logger.info("Recorder started")

    async def _handle_offer(self, message: Dict[str, Any]) -> None:
        pc = await self._create_pc()
        self.player_id = message.get("playerId")
        offer = RTCSessionDescription(sdp=message.get("sdp"), type="offer")
        await pc.setRemoteDescription(offer)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        response = {"type": "answer", "sdp": pc.localDescription.sdp}
        if self.player_id:
            response["playerId"] = self.player_id
        await self._send_message(response)
        logger.info("Sent SDP answer")

        # Epic's player requests quality control immediately so frames flow to us.
        try:
            await self._send_message({"type": "requestQualityControl"})
            logger.debug("Requested quality control ownership")
        except Exception as exc:
            logger.warning("Failed to request quality control: %s", exc)

        if self.cfg.duration is not None:
            self.active.set()

    async def _handle_remote_candidate(self, message: Dict[str, Any]) -> None:
        candidate_info = message.get("candidate")
        if not candidate_info:
            return
        candidate = RTCIceCandidate(
            sdpMid=candidate_info.get("sdpMid"),
            sdpMLineIndex=candidate_info.get("sdpMLineIndex"),
            candidate=candidate_info.get("candidate"),
        )
        pc = await self._create_pc()
        await pc.addIceCandidate(candidate)

    async def _send_message(self, payload: Dict[str, Any]) -> None:
        if self.player_id and payload.get("type") in {"answer", "iceCandidate", "layerPreference"}:
            payload.setdefault("playerId", self.player_id)
        if self.ws is None:
            raise RuntimeError("Websocket not connected")
        await self.ws.send_json(payload)
        logger.debug("Sent message: %s", payload)

    async def _send_unsubscribe(self) -> None:
        if self.shutting_down:
            return
        try:
            await self._send_message({"type": "unsubscribe"})
        except Exception:
            pass

    async def _close_pc(self) -> None:
        if self.pc:
            await self.pc.close()
            self.pc = None

    async def _stop_recorder(self) -> None:
        if self.recorder and self.recorder_started:
            await self.recorder.stop()
            logger.info("Recorder stopped. Output saved to %s", self.cfg.output_path)

    async def _shutdown(self) -> None:
        await self._stop_recorder()
        await self._close_pc()


async def async_main(args: argparse.Namespace) -> bool:
    cfg = RecorderConfig(
        signalling_url=args.signalling_url,
        output_path=Path(args.output).resolve(),
        streamer_id=args.streamer,
        duration=args.duration,
        inactivity_timeout=args.inactivity_timeout,
    )
    recorder = PixelStreamingRecorder(cfg)
    return await recorder.run()


def _maybe_upload(args: argparse.Namespace, recorded: bool) -> None:
    if not args.storage_url:
        if any((args.session_id, args.upload_orchestrator_id, args.storage_token)):
            logger.warning(
                "Upload parameters provided without --storage-url; skipping upload"
            )
        return

    if not args.session_id:
        raise ValueError("--storage-url requires --session-id for automatic upload")

    output_path = Path(args.output).resolve()
    if not recorded:
        logger.warning("No media tracks were recorded; skipping upload to %s", args.storage_url)
        return
    if not output_path.exists() or output_path.stat().st_size == 0:
        logger.warning(
            "Output %s is missing or empty; skipping upload to %s",
            output_path,
            args.storage_url,
        )
        return

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))
    from scripts.upload_capture import upload as upload_capture  # type: ignore

    logger.info(
        "Uploading %s to %s (session %s)",
        output_path,
        args.storage_url,
        args.session_id,
    )
    upload_capture(
        output_path,
        args.storage_url,
        args.session_id,
        orchestrator_id=args.upload_orchestrator_id,
        token=args.storage_token,
    )
    logger.info("Upload completed successfully")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record a Pixel Streaming session via WebRTC")
    parser.add_argument(
        "--signalling-url",
        required=True,
        help="WebSocket URL for the Pixel Streaming signalling server (e.g. ws://host:8888)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output WebM/MP4 file"
    )
    parser.add_argument(
        "--streamer",
        default=None,
        help="Streamer ID to subscribe to. Defaults to the first available streamer"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=60.0,
        help="Duration in seconds to record. Use 0 for indefinite until disconnected"
    )
    parser.add_argument(
        "--inactivity-timeout",
        type=float,
        default=10.0,
        help="Seconds to wait before re-requesting the streamer list when no streamers are available"
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("PIXELSTREAM_LOG", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity"
    )
    parser.add_argument(
        "--storage-url",
        default=None,
        help="Optional storage service base URL; when provided alongside --session-id the recording is uploaded automatically"
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Capture session identifier used when uploading"
    )
    parser.add_argument(
        "--upload-orchestrator-id",
        default=None,
        help="Optional orchestrator id passed through to the storage service during upload"
    )
    parser.add_argument(
        "--storage-token",
        default=None,
        help="Optional token supplied as X-Storage-Token when uploading"
    )
    args = parser.parse_args()
    if args.duration and args.duration <= 0:
        args.duration = None
    if bool(args.storage_url) ^ bool(args.session_id):
        parser.error("--storage-url and --session-id must be provided together for automatic upload")
    logging.basicConfig(level=getattr(logging, args.log_level))
    return args


def main() -> None:
    args = parse_args()
    try:
        recorded = asyncio.run(async_main(args))
        if not recorded:
            logger.warning("Recorder stopped without receiving any media tracks")
        _maybe_upload(args, recorded)
    except KeyboardInterrupt:
        logger.info("Interrupted")


if __name__ == "__main__":
    main()
