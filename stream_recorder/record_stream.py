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
import contextlib
import json
import logging
import os
import struct
import subprocess
import sys
import time
import types
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
from aiortc import (
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
)
from aiortc.sdp import candidate_from_sdp
from aiortc.codecs import h264 as h264_codec
from aiortc.contrib.media import MediaRecorder, MediaRecorderContext

logger = logging.getLogger("pixelstream.recorder")

TO_STREAMER_MESSAGES = {
    "RequestQualityControl": {"id": 1, "structure": []},
    "FpsRequest": {"id": 2, "structure": []},
    "AverageBitrateRequest": {"id": 3, "structure": []},
    "StartStreaming": {"id": 4, "structure": []},
    "RequestInitialSettings": {"id": 7, "structure": []},
    "Command": {"id": 51, "structure": ["string"]},
}


@dataclass
class RecorderConfig:
    signalling_url: str
    output_path: Path
    streamer_id: Optional[str]
    duration: Optional[float]
    inactivity_timeout: float = 15.0
    video_bitrate_kbps: Optional[int] = None
    audio_bitrate_kbps: Optional[int] = None
    frame_rate: int = 30
    mode: str = "transcode"
    raw_remux: Optional[str] = None
    preferred_spatial_layer: Optional[int] = None
    preferred_temporal_layer: Optional[int] = None
    answer_start_bitrate_kbps: int = 60000
    answer_max_bitrate_kbps: int = 80000
    encoder_min_qp: int = 10
    encoder_max_qp: int = 30
    encoder_min_bitrate_bps: int = 10_000_000
    encoder_target_bitrate_bps: int = 15_000_000
    encoder_max_bitrate_bps: int = 20_000_000
    webrtc_min_bitrate_bps: int = 12_000_000
    webrtc_start_bitrate_bps: int = 15_000_000
    webrtc_max_bitrate_bps: int = 22_000_000


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
        self.raw_capture: Optional["RawCaptureManager"] = None
        self.client_id = str(uuid.uuid4())
        self.protocol_version: Optional[str] = None
        self.current_streamer: Optional[str] = None
        self.stop_requested = False
        self.data_channel = None
        self.stats_task: Optional[asyncio.Task] = None
        self._stats_prev: Dict[str, Dict[str, float]] = {}

    async def run(self) -> bool:
        logger.info("Connecting to signalling server %s", self.cfg.signalling_url)
        retry_delay = 1.0
        async with aiohttp.ClientSession() as session:
            self.session = session
            while not self.shutting_down:
                self.stop_requested = False
                try:
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
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    if self.shutting_down:
                        break
                    logger.warning("Signalling connection error: %s", exc)
                finally:
                    await self._close_pc()
                    self.ws = None

                if self.recorder_started or self.shutting_down:
                    break

                await asyncio.sleep(min(retry_delay, self.cfg.inactivity_timeout))
                retry_delay = min(retry_delay * 2, 5.0)
                logger.info("Retrying signalling connection")

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
        if self.stop_requested:
            self.shutting_down = True
        if self.ws is not None and not self.ws.closed:
            await self.ws.close()

    async def on_open(self) -> None:
        logger.info("Websocket connection established")
        self.current_streamer = None
        await self._send_message({"type": "listStreamers"})

    async def on_message(self, message: Dict[str, Any]) -> None:
        msg_type = message.get("type")
        logger.debug("Received message: %s", message)

        if msg_type == "config":
            self.peer_connection_options = message.get("peerConnectionOptions", {})
            protocol = message.get("protocolVersion")
            logger.info("Received config (protocol %s)", protocol)
            if protocol:
                self.protocol_version = protocol
        elif msg_type == "streamerList":
            await self._handle_streamer_list(message)
        elif msg_type == "offer":
            await self._handle_offer(message)
        elif msg_type == "streamerDisconnected":
            await self._handle_streamer_disconnected()
        elif msg_type == "streamerIdChanged":
            await self._handle_streamer_id_changed(message)
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
        self.current_streamer = target
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

        @pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(
                "Data channel discovered: label=%s state=%s", channel.label, channel.readyState
            )
            self.data_channel = channel

            async def configure() -> None:
                try:
                    await self._configure_stream_quality()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Quality configuration failed: %s", exc)

            @channel.on("open")
            def on_open() -> None:
                logger.info("Data channel %s opened", channel.label)
                self.data_channel = channel
                asyncio.ensure_future(configure())

            @channel.on("close")
            def on_close() -> None:
                logger.info("Data channel %s closed", channel.label)
                if self.data_channel is channel:
                    self.data_channel = None

            if channel.readyState == "open":
                asyncio.ensure_future(configure())

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
        if self.stats_task is None or self.stats_task.done():
            self.stats_task = asyncio.create_task(self._stats_loop())
        return pc

    async def _configure_stream_quality(self) -> None:
        try:
            logger.info("Requesting quality control over data channel")
            await self._send_to_streamer("RequestQualityControl")
            await self._send_to_streamer("FpsRequest")
            await self._send_to_streamer("StartStreaming")
            logger.info(
                "Pushing encoder bitrates min=%sbps target=%sbps max=%sbps and QP=%s-%s",
                self.cfg.encoder_min_bitrate_bps,
                self.cfg.encoder_target_bitrate_bps,
                self.cfg.encoder_max_bitrate_bps,
                self.cfg.encoder_min_qp,
                self.cfg.encoder_max_qp,
            )
            await self._send_command({"Encoder.MinQP": self.cfg.encoder_min_qp})
            await self._send_command({"Encoder.MaxQP": self.cfg.encoder_max_qp})
            await self._send_command({"Encoder.MinBitrate": self.cfg.encoder_min_bitrate_bps})
            await self._send_command({"Encoder.TargetBitrate": self.cfg.encoder_target_bitrate_bps})
            await self._send_command({"Encoder.MaxBitrate": self.cfg.encoder_max_bitrate_bps})
            logger.info(
                "Announcing WebRTC bitrate window min=%sbps start=%sbps max=%sbps",
                self.cfg.webrtc_min_bitrate_bps,
                self.cfg.webrtc_start_bitrate_bps,
                self.cfg.webrtc_max_bitrate_bps,
            )
            await self._send_command({"WebRTC.MinBitrate": self.cfg.webrtc_min_bitrate_bps})
            await self._send_command({"WebRTC.StartBitrate": self.cfg.webrtc_start_bitrate_bps})
            await self._send_command({"WebRTC.MaxBitrate": self.cfg.webrtc_max_bitrate_bps})
            await self._send_to_streamer("RequestInitialSettings")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Unable to push quality commands over data channel: %s", exc)

    def _ensure_recorder(self) -> MediaRecorder:
        if self.cfg.mode == "raw":
            raise RuntimeError("MediaRecorder not available in raw mode")
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
            self._patch_recorder()
        return self.recorder

    def _patch_recorder(self) -> None:
        recorder = self.recorder
        if recorder is None:
            return

        def _custom_add_track(self_recorder, track) -> None:
            container = getattr(self_recorder, "_MediaRecorder__container", None)
            tracks = getattr(self_recorder, "_MediaRecorder__tracks", None)
            if container is None or tracks is None:
                raise RuntimeError("Recorder container unavailable")

            format_name = container.format.name

            if track.kind == "audio":
                codec_name = self._select_audio_codec(format_name)
                stream = container.add_stream(codec_name)
                self._configure_audio_stream(stream)
            else:
                codec_name = self._select_video_codec(format_name)
                stream = container.add_stream(codec_name, rate=self.cfg.frame_rate)
                self._configure_video_stream(stream, codec_name)

            tracks[track] = MediaRecorderContext(stream)

        recorder.addTrack = types.MethodType(_custom_add_track, recorder)  # type: ignore[assignment]

    def _select_video_codec(self, format_name: str) -> str:
        if format_name == "webm":
            return "libvpx"
        return "libx264"

    def _select_audio_codec(self, format_name: str) -> str:
        if format_name == "webm":
            return "libopus"
        if format_name in ("wav", "alsa", "pulse"):
            return "pcm_s16le"
        if format_name == "mp3":
            return "mp3"
        if format_name == "ogg":
            return "libopus"
        return "aac"

    def _configure_video_stream(self, stream: Any, codec_name: str) -> None:
        stream.pix_fmt = "yuv420p"
        target_bitrate = int(self.cfg.video_bitrate_kbps * 1000) if self.cfg.video_bitrate_kbps else None
        if target_bitrate:
            stream.bit_rate = target_bitrate
        ctx = getattr(stream, "codec_context", None)
        if ctx is not None:
            if target_bitrate:
                ctx.bit_rate = target_bitrate
            if codec_name == "libx264":
                ctx.options.setdefault("preset", "veryfast")
                ctx.options.setdefault("profile", "high")
            elif codec_name == "libvpx":
                ctx.options.setdefault("deadline", "realtime")
                ctx.options.setdefault("cpu-used", "1")

    def _configure_audio_stream(self, stream: Any) -> None:
        target_bitrate = int(self.cfg.audio_bitrate_kbps * 1000) if self.cfg.audio_bitrate_kbps else None
        if target_bitrate:
            stream.bit_rate = target_bitrate
            ctx = getattr(stream, "codec_context", None)
            if ctx is not None:
                ctx.bit_rate = target_bitrate

    def _on_track(self, track) -> None:
        logger.info("Track received: %s", track.kind)
        if self.cfg.mode == "raw":
            if self.raw_capture is None:
                self.raw_capture = RawCaptureManager(self.cfg.output_path, self.cfg.raw_remux)
            receiver = None
            if self.pc:
                for candidate in self.pc.getReceivers():
                    if candidate.track is track:
                        receiver = candidate
                        break
            attached = self.raw_capture.add_track(track, receiver)
            logger.debug("Raw attach for %s returned %s", track.kind, attached)
            if attached and not self.recorder_started:
                self.recorder_started = True
        else:
            recorder = self._ensure_recorder()
            recorder.addTrack(track)
            if not self.recorder_started:
                asyncio.ensure_future(self._start_recorder())

    async def _start_recorder(self) -> None:
        async with self.recorder_start_lock:
            if self.recorder_started:
                return
            if self.cfg.mode == "raw":
                self.recorder_started = True
                logger.info("Raw recorder armed")
            else:
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
        tuned_sdp = self._tune_answer_bitrates(answer.sdp)
        await pc.setLocalDescription(
            RTCSessionDescription(sdp=tuned_sdp, type=answer.type)
        )

        response = {"type": "answer", "sdp": pc.localDescription.sdp}
        if self.player_id:
            response["playerId"] = self.player_id
        await self._send_message(response)
        logger.info("Sent SDP answer")

        # Request quality control so the streamer sends us the high-quality stream.
        try:
            await self._send_message({"type": "requestQualityControl"})
            logger.debug("Requested quality control ownership")
        except Exception as exc:
            logger.warning("Failed to request quality control: %s", exc)

        if self.cfg.preferred_spatial_layer is not None:
            layer_msg = {"type": "layerPreference", "spatialLayer": self.cfg.preferred_spatial_layer}
            if self.cfg.preferred_temporal_layer is not None:
                layer_msg["temporalLayer"] = self.cfg.preferred_temporal_layer
            try:
                await self._send_message(layer_msg)
                logger.info("Requested layer preference spatial=%s temporal=%s",
                            self.cfg.preferred_spatial_layer, layer_msg.get("temporalLayer"))
            except Exception as exc:
                logger.warning("Failed to request layer preference: %s", exc)

        if self.cfg.duration is not None:
            self.active.set()

    async def _handle_streamer_disconnected(self) -> None:
        logger.warning("Streamer %s disconnected", self.current_streamer)
        await self._close_pc()
        self.recorder_started = False
        self.player_id = None
        if not self.shutting_down:
            await asyncio.sleep(self.cfg.inactivity_timeout)
            await self._send_message({"type": "listStreamers"})

    async def _handle_streamer_id_changed(self, message: Dict[str, Any]) -> None:
        old_id = message.get("oldId") or self.current_streamer
        new_id = message.get("newId")
        logger.info("Streamer id changed from %s to %s", old_id, new_id)
        if new_id:
            self.current_streamer = new_id
            if not self.shutting_down:
                await self._send_message({"type": "subscribe", "streamerId": new_id})

    async def _handle_remote_candidate(self, message: Dict[str, Any]) -> None:
        candidate_info = message.get("candidate")
        if not candidate_info:
            return
        candidate_sdp = candidate_info.get("candidate")
        if not candidate_sdp:
            return
        candidate = candidate_from_sdp(candidate_sdp)
        candidate.sdpMid = candidate_info.get("sdpMid")
        candidate.sdpMLineIndex = candidate_info.get("sdpMLineIndex")
        pc = await self._create_pc()
        await pc.addIceCandidate(candidate)

    async def _send_message(self, payload: Dict[str, Any]) -> None:
        if self.player_id and payload.get("type") in {"answer", "iceCandidate", "layerPreference"}:
            payload.setdefault("playerId", self.player_id)
        elif payload.get("type") in {"subscribe", "unsubscribe", "playerDisconnected"}:
            payload.setdefault("playerId", self.player_id or self.client_id)
        if self.ws is None:
            raise RuntimeError("Websocket not connected")
        await self.ws.send_json(payload)
        logger.debug("Sent message: %s", payload)

    async def _send_to_streamer(self, message_type: str, data: Optional[list] = None) -> None:
        if self.data_channel is None or self.data_channel.readyState != "open":
            raise RuntimeError("Data channel not ready")
        payload = self._encode_datachannel_message(message_type, data or [])
        logger.debug("Sending data channel message %s payload=%s", message_type, data or [])
        self.data_channel.send(payload)
        logger.debug("Sent data channel message %s", message_type)

    async def _send_command(self, command: Dict[str, Any]) -> None:
        await self._send_to_streamer("Command", [json.dumps(command)])

    @staticmethod
    def _encode_datachannel_message(message_type: str, message_data: list) -> bytes:
        definition = TO_STREAMER_MESSAGES.get(message_type)
        if definition is None:
            raise ValueError(f"Unsupported streamer message {message_type}")
        if len(message_data) != len(definition["structure"]):
            raise ValueError(
                f"Invalid payload for {message_type}: expected {len(definition['structure'])} elements"
            )
        buffer = bytearray()
        buffer.append(definition["id"])
        for value, field_type in zip(message_data, definition["structure"]):
            if field_type == "string":
                chars = list(str(value))
                buffer.extend(struct.pack("<H", len(chars)))
                for ch in chars:
                    buffer.extend(struct.pack("<H", ord(ch)))
            elif field_type == "uint8":
                buffer.extend(struct.pack("<B", int(value)))
            elif field_type == "uint16":
                buffer.extend(struct.pack("<H", int(value)))
            elif field_type == "int16":
                buffer.extend(struct.pack("<h", int(value)))
            elif field_type == "float":
                buffer.extend(struct.pack("<f", float(value)))
            elif field_type == "double":
                buffer.extend(struct.pack("<d", float(value)))
            else:
                raise ValueError(f"Unsupported field type {field_type}")
        return bytes(buffer)

    async def _stats_loop(self) -> None:
        logger.debug("Starting WebRTC stats logger")
        try:
            while not self.shutting_down:
                await asyncio.sleep(5)
                if not self.pc:
                    continue
                try:
                    stats = await self.pc.getStats()
                except Exception as exc:  # noqa: BLE001
                    logger.debug("getStats failed: %s", exc)
                    continue
                self._log_media_stats(stats, time.monotonic())
        except asyncio.CancelledError:
            logger.debug("Stats logger cancelled")
            raise

    def _log_media_stats(self, stats: Dict[str, Any], timestamp: float) -> None:
        entries = []
        for kind in ("video", "audio"):
            report = next(
                (
                    entry
                    for entry in stats.values()
                    if getattr(entry, "type", None) == "inbound-rtp"
                    and getattr(entry, "kind", None) == kind
                ),
                None,
            )
            if not report:
                continue
            key = f"{kind}_rtp"
            prev = self._stats_prev.get(key)
            bitrate = None
            if prev is not None:
                delta_bytes = getattr(report, "bytesReceived", 0) - prev.get("bytes", 0)
                delta_t = max(timestamp - prev.get("time", timestamp), 1e-6)
                bitrate = (delta_bytes * 8) / delta_t / 1000.0
            self._stats_prev[key] = {
                "bytes": getattr(report, "bytesReceived", 0),
                "time": timestamp,
            }
            if bitrate is None:
                continue
            if kind == "video":
                fps = getattr(report, "framesPerSecond", None)
                frames = getattr(report, "framesDecoded", None)
                entries.append(
                    f"video bitrate={bitrate:.0f} kbps fps={fps} framesDecoded={frames}"
                )
            else:
                jitter = getattr(report, "jitter", None)
                entries.append(f"audio bitrate={bitrate:.0f} kbps jitter={jitter}")
        if entries:
            logger.info("Stats: %s", " | ".join(entries))

    async def _send_unsubscribe(self) -> None:
        if self.shutting_down:
            return
        try:
            await self._send_message({"type": "unsubscribe"})
        except Exception:
            pass

    def _tune_answer_bitrates(self, sdp: str) -> str:
        start_bps = max(self.cfg.answer_start_bitrate_kbps, 1) * 1000
        max_bps = max(self.cfg.answer_max_bitrate_kbps, self.cfg.answer_start_bitrate_kbps) * 1000
        lines = []
        for line in sdp.splitlines():
            if line.startswith("a=fmtp:") and (
                "x-google" in line or "profile-level-id" in line or "apt=" in line
            ):
                line = self._ensure_bitrate_hint(line, "x-google-start-bitrate", start_bps)
                line = self._ensure_bitrate_hint(line, "x-google-max-bitrate", max_bps)
            lines.append(line)
        return "\r\n".join(lines) + "\r\n"

    @staticmethod
    def _ensure_bitrate_hint(line: str, key: str, value: int) -> str:
        parts = line.split(";")
        replaced = False
        for idx, part in enumerate(parts):
            token = part.strip()
            if token.startswith(f"{key}="):
                parts[idx] = f"{key}={value}"
                replaced = True
        if not replaced:
            parts.append(f"{key}={value}")
        return ";".join(parts)

    async def _close_pc(self) -> None:
        if self.pc:
            await self.pc.close()
            self.pc = None

    async def _stop_recorder(self) -> None:
        if self.cfg.mode == "raw":
            if self.raw_capture:
                try:
                    await self.raw_capture.finalize()
                except Exception as exc:
                    logger.warning("Raw capture finalize failed: %s", exc)
        else:
            if self.recorder and self.recorder_started:
                try:
                    await self.recorder.stop()
                    logger.info("Recorder stopped. Output saved to %s", self.cfg.output_path)
                except Exception as exc:
                    logger.warning("Recorder stop failed: %s", exc)

    async def _shutdown(self) -> None:
        await self._stop_recorder()
        await self._close_pc()
        if not self.shutting_down:
            try:
                await self._send_message({"type": "playerDisconnected"})
            except Exception:
                pass
        if self.stats_task:
            self.stats_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.stats_task
            self.stats_task = None

    async def stop(self) -> None:
        """Request a graceful shutdown of the recording session."""
        logger.info("Stop requested")
        self.stop_requested = True
        self.close_event.set()


class RawCaptureManager:
    def __init__(self, output_path: Path, remux_command: Optional[str]) -> None:
        self.output_path = output_path
        stem = output_path.with_suffix("")
        self.video_path = stem.with_suffix(".h264")
        self.audio_path = stem.with_suffix(".opus")
        self.remux_command = remux_command
        self.video_sink: Optional[RawVideoSink] = None
        self.audio_sink: Optional[RawAudioSink] = None
        self._patched_receivers: list[tuple[Any, Any]] = []

    def add_track(self, track: Any, receiver: Any) -> bool:
        if receiver is None:
            logger.warning("Unable to locate receiver for track %s (type=%s, attrs=%s)", track.kind, type(track), getattr(track, "__dict__", {}))
            return False

        if track.kind == "video":
            if self.video_sink is None:
                self.video_path.parent.mkdir(parents=True, exist_ok=True)
                self.video_sink = RawVideoSink(self.video_path)
            sink = self.video_sink
        elif track.kind == "audio":
            if self.audio_sink is None:
                self.audio_path.parent.mkdir(parents=True, exist_ok=True)
                self.audio_sink = RawAudioSink(self.audio_path)
            sink = self.audio_sink
        else:
            logger.debug("Skipping unsupported track kind %s", track.kind)
            return False

        original = receiver._handle_rtp_packet

        async def wrapped(packet, *args, **kwargs):
            try:
                sink.handle(packet)
            except Exception as exc:
                logger.debug("Raw sink error for %s packet: %s", track.kind, exc)
            return await original(packet, *args, **kwargs)

        receiver._handle_rtp_packet = wrapped
        self._patched_receivers.append((receiver, original))
        return True

    async def finalize(self) -> None:
        for sink in (self.video_sink, self.audio_sink):
            if sink is not None:
                sink.close()
        for receiver, original in self._patched_receivers:
            receiver._handle_rtp_packet = original
        self._patched_receivers.clear()
        logger.info("Raw capture saved video=%s audio=%s", self.video_path, self.audio_path)
        if self.remux_command and self.video_sink and self.audio_sink:
            await self._remux()

    async def _remux(self) -> None:
        cmd = [
            self.remux_command,
            "-y",
            "-f",
            "h264",
            "-i",
            str(self.video_path),
            "-f",
            "opus",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-i",
            str(self.audio_path),
            "-c",
            "copy",
            str(self.output_path),
        ]
        logger.info("Remuxing raw capture with command: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("Remux command failed (%s): %s", proc.returncode, stderr.decode().strip())
        else:
            logger.info("Remuxed capture written to %s", self.output_path)


class RawVideoSink:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.file = path.open("wb")

    def handle(self, packet: Any) -> None:
        _, data = h264_codec.H264PayloadDescriptor.parse(packet.payload)
        if data:
            self.file.write(data)

    def close(self) -> None:
        self.file.close()


class RawAudioSink:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.file = path.open("wb")

    def handle(self, packet: Any) -> None:
        self.file.write(packet.payload)

    def close(self) -> None:
        self.file.close()


async def async_main(args: argparse.Namespace) -> bool:
    cfg = RecorderConfig(
        signalling_url=args.signalling_url,
        output_path=Path(args.output).resolve(),
        streamer_id=args.streamer,
        duration=args.duration,
        inactivity_timeout=args.inactivity_timeout,
        video_bitrate_kbps=args.video_bitrate,
        audio_bitrate_kbps=args.audio_bitrate,
        frame_rate=args.frame_rate,
        mode=args.mode,
        raw_remux=args.raw_remux,
        preferred_spatial_layer=args.preferred_spatial_layer,
        preferred_temporal_layer=args.preferred_temporal_layer,
        answer_start_bitrate_kbps=args.answer_start_bitrate,
        answer_max_bitrate_kbps=args.answer_max_bitrate,
        encoder_min_qp=args.encoder_min_qp,
        encoder_max_qp=args.encoder_max_qp,
        encoder_min_bitrate_bps=args.encoder_min_bitrate,
        encoder_target_bitrate_bps=args.encoder_target_bitrate,
        encoder_max_bitrate_bps=args.encoder_max_bitrate,
        webrtc_min_bitrate_bps=args.webrtc_min_bitrate,
        webrtc_start_bitrate_bps=args.webrtc_start_bitrate,
        webrtc_max_bitrate_bps=args.webrtc_max_bitrate,
    )
    recorder = PixelStreamingRecorder(cfg)
    return await recorder.run()



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
        "--video-bitrate",
        type=int,
        default=6000,
        help="Target video bitrate in kbps for the local recording encoder (default: 6000)"
    )
    parser.add_argument(
        "--audio-bitrate",
        type=int,
        default=128,
        help="Target audio bitrate in kbps for the local recording encoder (default: 128)"
    )
    parser.add_argument(
        "--frame-rate",
        type=int,
        default=30,
        help="Frame rate to request from the recorder's transcoder"
    )
    parser.add_argument(
        "--mode",
        choices=["transcode", "raw"],
        default="transcode",
        help="Recording pipeline to use (transcode: re-encode via aiortc; raw: dump encoded payloads)"
    )
    parser.add_argument(
        "--raw-remux",
        default=None,
        help="Optional command (e.g. ffmpeg) to remux raw dumps into the final output container"
    )
    parser.add_argument(
        "--preferred-spatial-layer",
        type=int,
        default=None,
        help="Preferred spatial layer index to request when SFU is enabled"
    )
    parser.add_argument(
        "--preferred-temporal-layer",
        type=int,
        default=None,
        help="Preferred temporal layer index to request when SFU is enabled"
    )
    parser.add_argument(
        "--answer-start-bitrate",
        type=int,
        default=int(os.getenv("RECORDER_ANSWER_START_BITRATE_KBPS", "60000")),
        help="Start bitrate hint (kbps) injected into the SDP answer"
    )
    parser.add_argument(
        "--answer-max-bitrate",
        type=int,
        default=int(os.getenv("RECORDER_ANSWER_MAX_BITRATE_KBPS", "80000")),
        help="Max bitrate hint (kbps) injected into the SDP answer"
    )
    parser.add_argument(
        "--encoder-min-qp",
        type=int,
        default=int(os.getenv("RECORDER_ENCODER_MIN_QP", "10")),
        help="Minimum encoder QP pushed over the data channel"
    )
    parser.add_argument(
        "--encoder-max-qp",
        type=int,
        default=int(os.getenv("RECORDER_ENCODER_MAX_QP", "30")),
        help="Maximum encoder QP pushed over the data channel"
    )
    parser.add_argument(
        "--encoder-min-bitrate",
        type=int,
        default=int(os.getenv("RECORDER_ENCODER_MIN_BITRATE", "10000000")),
        help="Minimum encoder bitrate in bps pushed over the data channel"
    )
    parser.add_argument(
        "--encoder-target-bitrate",
        type=int,
        default=int(os.getenv("RECORDER_ENCODER_TARGET_BITRATE", "15000000")),
        help="Target encoder bitrate in bps pushed over the data channel"
    )
    parser.add_argument(
        "--encoder-max-bitrate",
        type=int,
        default=int(os.getenv("RECORDER_ENCODER_MAX_BITRATE", "20000000")),
        help="Maximum encoder bitrate in bps pushed over the data channel"
    )
    parser.add_argument(
        "--webrtc-min-bitrate",
        type=int,
        default=int(os.getenv("RECORDER_WEBRTC_MIN_BITRATE", "12000000")),
        help="Minimum WebRTC bitrate in bps pushed over the data channel"
    )
    parser.add_argument(
        "--webrtc-start-bitrate",
        type=int,
        default=int(os.getenv("RECORDER_WEBRTC_START_BITRATE", "15000000")),
        help="Starting WebRTC bitrate in bps pushed over the data channel"
    )
    parser.add_argument(
        "--webrtc-max-bitrate",
        type=int,
        default=int(os.getenv("RECORDER_WEBRTC_MAX_BITRATE", "22000000")),
        help="Maximum WebRTC bitrate in bps pushed over the data channel"
    )
    args = parser.parse_args()
    if args.duration and args.duration <= 0:
        args.duration = None
    logging.basicConfig(level=getattr(logging, args.log_level))
    return args


def main() -> None:
    args = parse_args()
    try:
        recorded = asyncio.run(async_main(args))
        if not recorded:
            logger.warning("Recorder stopped without receiving any media tracks")
    except KeyboardInterrupt:
        logger.info("Interrupted")


if __name__ == "__main__":
    main()
