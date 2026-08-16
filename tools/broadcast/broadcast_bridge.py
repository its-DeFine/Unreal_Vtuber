#!/usr/bin/env python3
"""Unattended Pixel Streaming WebRTC to RTMP bridge.

The bridge joins the existing signaling server as one more WebRTC viewer. It
never replaces the browser/WebRTC path. H.264 is copied when available; VP8 or
VP9 is transcoded to H.264, and Opus audio is transcoded to AAC for FLV/RTMP.

The RTMP destination is read from a mounted file so it is not exposed through
process arguments, container environment, Compose interpolation, status, or
normal logs. ``BROADCAST_MODE=test`` runs local GStreamer test sources into a
fake sink and exercises the same supervisor/state lifecycle without signaling,
Unreal, a GPU, or an external streaming account.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import tempfile
import threading
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


_RTMP_URL_RE = re.compile(r"(?i)rtmps?://[^\s\"'<>\]\[()]+")
_GST_LOADED = False
Gst = None
GLib = None
GstWebRTC = None
GstSdp = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def validate_destination(raw: str) -> str:
    """Validate a destination without returning or logging it on failure."""
    value = raw.strip()
    if not value or any(char in value for char in ("\r", "\n", "\x00")):
        raise ValueError("destination file is empty or contains invalid control characters")
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError as exc:
        raise ValueError("destination is not a valid RTMP URL") from exc
    if parsed.scheme.lower() not in {"rtmp", "rtmps"} or not parsed.hostname:
        raise ValueError("destination must be an rtmp:// or rtmps:// URL with a host")
    return value


def read_destination(path: Path) -> str:
    try:
        value = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError("destination file is missing") from exc
    except OSError as exc:
        raise ValueError("destination file cannot be read") from exc
    return validate_destination(value)


class SecretRedactor:
    """Remove RTMP URLs and useful URL fragments from operator-visible text."""

    def __init__(self, destination: str = "") -> None:
        candidates: set[str] = set()
        value = destination.strip()
        if value:
            candidates.update({value, urllib.parse.unquote(value)})
            try:
                parsed = urllib.parse.urlsplit(value)
            except ValueError:
                parsed = None
            if parsed is not None:
                for candidate in (
                    parsed.username,
                    parsed.password,
                    parsed.path,
                    parsed.query,
                    parsed.fragment,
                ):
                    if candidate and len(candidate) >= 4:
                        candidates.add(candidate)
                        candidates.add(urllib.parse.unquote(candidate))
                for segment in parsed.path.split("/"):
                    if len(segment) >= 4:
                        candidates.add(segment)
                        candidates.add(urllib.parse.unquote(segment))
        # Replace longer values first so a path/key cannot leave a revealing
        # suffix after the complete URL has already been partially replaced.
        self._candidates = sorted((c for c in candidates if len(c) >= 4), key=len, reverse=True)

    def __call__(self, value: Any) -> str:
        text = str(value or "")
        text = _RTMP_URL_RE.sub("[redacted-rtmp-destination]", text)
        for candidate in self._candidates:
            text = text.replace(candidate, "[redacted]")
        return text


class StateStore:
    """Atomic, sanitized state shared with the host-side CLI."""

    def __init__(self, path: Path, mode: str, redactor: SecretRedactor) -> None:
        self.path = path
        self.mode = mode
        self.redactor = redactor
        self._lock = threading.Lock()
        self._last_heartbeat_write = 0.0
        self._data: dict[str, Any] = {
            "version": 1,
            "mode": mode,
            "pid": os.getpid(),
            "status": "starting",
            "connected": False,
            "attempts": 0,
            "started_at": _utc_now(),
            "updated_at": _utc_now(),
            "heartbeat_at": _utc_now(),
            "last_error": None,
        }

    def set_redactor(self, redactor: SecretRedactor) -> None:
        with self._lock:
            self.redactor = redactor

    def update(self, status: Optional[str] = None, **values: Any) -> None:
        with self._lock:
            if status is not None:
                self._data["status"] = status
            for key, value in values.items():
                if key == "last_error" and value:
                    value = self.redactor(value)
                self._data[key] = value
            now = _utc_now()
            self._data["updated_at"] = now
            self._data["heartbeat_at"] = now
            self._last_heartbeat_write = time.monotonic()
            self._write_locked()

    def heartbeat(self) -> None:
        # Signaling is polled once per second, but a five-second persisted
        # heartbeat is ample for the 45-second container health window and
        # avoids an fsync on every poll for long-running broadcasts.
        with self._lock:
            if time.monotonic() - self._last_heartbeat_write < 5.0:
                return
        self.update()

    def _write_locked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".state.", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            # State is sanitized and its parent directory is private. Read
            # permission lets a non-root Docker operator inspect a root-owned
            # state file created by the container.
            os.chmod(tmp_name, 0o644)
            os.replace(tmp_name, self.path)
        finally:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass


def _load_gst() -> None:
    global _GST_LOADED, Gst, GLib, GstWebRTC, GstSdp
    if _GST_LOADED:
        return
    import gi

    gi.require_version("Gst", "1.0")
    gi.require_version("GstWebRTC", "1.0")
    gi.require_version("GstSdp", "1.0")
    from gi.repository import GLib as _GLib
    from gi.repository import Gst as _Gst
    from gi.repository import GstSdp as _GstSdp
    from gi.repository import GstWebRTC as _GstWebRTC

    _Gst.init(None)
    Gst = _Gst
    GLib = _GLib
    GstWebRTC = _GstWebRTC
    GstSdp = _GstSdp
    _GST_LOADED = True


class TestPipelineSession:
    """Local source/sink used to validate lifecycle without external systems."""

    def __init__(
        self,
        stop_event: threading.Event,
        heartbeat: Callable[[], None],
        on_streaming: Callable[[], None],
        redactor: SecretRedactor,
    ) -> None:
        self.stop_event = stop_event
        self.heartbeat = heartbeat
        self.on_streaming = on_streaming
        self.redactor = redactor

    def run(self) -> None:
        _load_gst()
        pipeline = Gst.parse_launch(
            "videotestsrc is-live=true pattern=smpte ! queue ! fakesink sync=false "
            "audiotestsrc is-live=true wave=sine ! queue ! fakesink sync=false"
        )
        bus = pipeline.get_bus()
        change = pipeline.set_state(Gst.State.PLAYING)
        if change == Gst.StateChangeReturn.FAILURE:
            pipeline.set_state(Gst.State.NULL)
            raise RuntimeError("test pipeline failed to enter PLAYING")
        self.on_streaming()
        try:
            while not self.stop_event.wait(1.0):
                message = bus.timed_pop_filtered(
                    0,
                    Gst.MessageType.ERROR | Gst.MessageType.EOS,
                )
                if message and message.type == Gst.MessageType.ERROR:
                    error, debug = message.parse_error()
                    raise RuntimeError(self.redactor(f"GStreamer test error: {error}; {debug or ''}"))
                if message and message.type == Gst.MessageType.EOS:
                    raise RuntimeError("test pipeline ended unexpectedly")
                self.heartbeat()
        finally:
            pipeline.set_state(Gst.State.NULL)


class WebRtcRtmpSession:
    """One WebRTC/signaling session feeding one RTMP sink."""

    def __init__(
        self,
        destination: str,
        signaling_url: str,
        streamer_id: Optional[str],
        stop_event: threading.Event,
        heartbeat: Callable[[], None],
        on_streaming: Callable[[], None],
        redactor: SecretRedactor,
    ) -> None:
        _load_gst()
        self.destination = destination
        self.signaling_url = signaling_url
        self.streamer_id = streamer_id or None
        self.stop_event = stop_event
        self.heartbeat = heartbeat
        self.on_streaming_callback = on_streaming
        self.redactor = redactor
        self.player_id = str(uuid.uuid4())
        self.streamer_wait_seconds = max(0.0, _env_float("BROADCAST_STREAMER_WAIT_SECONDS", 0.0))
        self.streamer_poll_seconds = max(0.5, _env_float("BROADCAST_STREAMER_POLL_SECONDS", 2.0))
        self.av_wait_seconds = max(0.0, _env_float("BROADCAST_AV_WAIT_SECONDS", 3.0))
        self.video_bitrate_kbps = max(250, _env_int("BROADCAST_VIDEO_BITRATE_KBPS", 6000))
        self.audio_bitrate_bps = max(32000, _env_int("BROADCAST_AUDIO_BITRATE_BPS", 128000))

        self.loop = asyncio.new_event_loop()
        self.pipeline = None
        self.webrtcbin = None
        self.mux = None
        self.ws = None
        self.glib_loop = None
        self.glib_thread = None
        self.transceivers_prepared = False
        self.video_queue = None
        self.audio_queue = None
        self.video_probe = None
        self.audio_probe = None
        self.flow_timeout_id = None
        self.allow_flow = False
        self.streaming_reported = False
        self.failure_reason: Optional[str] = None

    def log(self, message: Any) -> None:
        print(self.redactor(message), flush=True)

    def _make(self, factory: str, name: Optional[str] = None):
        element = Gst.ElementFactory.make(factory, name)
        if element is None:
            raise RuntimeError(f"required GStreamer element is unavailable: {factory}")
        return element

    def _fail(self, reason: Any) -> None:
        if self.failure_reason is None:
            self.failure_reason = self.redactor(reason)
            self.log(self.failure_reason)
        if self.ws is not None and not self.ws.closed:
            try:
                asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)
            except Exception:
                pass

    def create_pipeline(self) -> None:
        self.pipeline = Gst.Pipeline.new("broadcast-pipeline")
        self.webrtcbin = self._make("webrtcbin", "webrtcbin")
        self.webrtcbin.set_property("stun-server", "stun://stun.l.google.com:19302")
        self.webrtcbin.set_property("bundle-policy", 3)
        self.webrtcbin.connect("on-ice-candidate", self.on_ice_candidate)
        self.webrtcbin.connect("pad-added", self.on_pad_added)

        self.mux = self._make("flvmux", "mux")
        self.mux.set_property("streamable", True)
        sink = self._make("rtmpsink", "rtmp-sink")
        # The only point where the destination enters GStreamer. It is never
        # printed, placed in argv, or put in the container environment.
        sink.set_property("location", self.destination)
        if sink.find_property("sync") is not None:
            sink.set_property("sync", False)
        if sink.find_property("async") is not None:
            sink.set_property("async", False)

        for element in (self.webrtcbin, self.mux, sink):
            self.pipeline.add(element)
        if not self.mux.link(sink):
            raise RuntimeError("could not link FLV mux to RTMP sink")

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_bus_message)
        if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError("broadcast pipeline failed to enter PLAYING")

    def on_bus_message(self, _bus, message) -> None:
        if message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            self._fail(f"GStreamer pipeline error: {error}; {debug or ''}")
        elif message.type == Gst.MessageType.EOS and not self.stop_event.is_set():
            self._fail("GStreamer pipeline ended unexpectedly")

    def _add_and_sync(self, elements: list[Any]) -> None:
        for element in elements:
            self.pipeline.add(element)
            if not element.sync_state_with_parent():
                raise RuntimeError(f"could not synchronize GStreamer element {element.get_name()}")

    @staticmethod
    def _link_chain(elements: list[Any]) -> None:
        for left, right in zip(elements, elements[1:]):
            if not left.link(right):
                raise RuntimeError(f"could not link {left.get_name()} to {right.get_name()}")

    def _request_mux_pad(self, media: str):
        pad = None
        if hasattr(self.mux, "request_pad_simple"):
            pad = self.mux.request_pad_simple(media)
        if pad is None:
            pad = self.mux.get_request_pad(media)
        if pad is None:
            raise RuntimeError(f"could not request FLV mux {media} pad")
        return pad

    def _link_queue_to_mux(self, media: str, queue) -> None:
        sink_pad = self._request_mux_pad(media)
        result = queue.get_static_pad("src").link(sink_pad)
        if result != Gst.PadLinkReturn.OK:
            raise RuntimeError(f"could not link {media} branch to FLV mux")

    def _buffer_gate(self, _pad, info, _media):
        if not self.allow_flow and info.type & (Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST):
            return Gst.PadProbeReturn.DROP
        return Gst.PadProbeReturn.OK

    def _release_flow(self, reason: str) -> None:
        if self.allow_flow:
            return
        self.allow_flow = True
        self.log(reason)
        if self.video_probe is not None and self.video_queue is not None:
            self.video_queue.get_static_pad("src").remove_probe(self.video_probe)
            self.video_probe = None
        if self.audio_probe is not None and self.audio_queue is not None:
            self.audio_queue.get_static_pad("src").remove_probe(self.audio_probe)
            self.audio_probe = None
        if self.flow_timeout_id is not None:
            GLib.source_remove(self.flow_timeout_id)
            self.flow_timeout_id = None
        if not self.streaming_reported:
            self.streaming_reported = True
            self.on_streaming_callback()

    def _schedule_flow_release(self) -> None:
        if self.allow_flow or self.flow_timeout_id is not None:
            return
        if self.av_wait_seconds <= 0:
            self._release_flow("Media available; starting broadcast")
            return

        def release_if_waiting():
            if not self.allow_flow and (self.video_queue is not None or self.audio_queue is not None):
                self._release_flow("Media wait elapsed; broadcasting available tracks")
            self.flow_timeout_id = None
            return False

        self.flow_timeout_id = GLib.timeout_add(int(self.av_wait_seconds * 1000), release_if_waiting)

    def _maybe_release_flow(self) -> None:
        if self.video_queue is not None and self.audio_queue is not None:
            self._release_flow("Audio and video ready; starting broadcast")

    def _build_video_branch(self, encoding: str):
        if encoding == "H264":
            depay = self._make("rtph264depay")
            parser = self._make("h264parse")
            parser.set_property("config-interval", -1)
            caps_filter = self._make("capsfilter")
            caps_filter.set_property(
                "caps",
                Gst.Caps.from_string("video/x-h264,stream-format=avc,alignment=au"),
            )
            queue = self._make("queue")
            elements = [depay, parser, caps_filter, queue]
        elif encoding in {"VP8", "VP9"}:
            depay = self._make("rtpvp8depay" if encoding == "VP8" else "rtpvp9depay")
            decoder = self._make("vp8dec" if encoding == "VP8" else "vp9dec")
            convert = self._make("videoconvert")
            encoder = self._make("x264enc")
            encoder.set_property("bitrate", self.video_bitrate_kbps)
            try:
                encoder.set_property("tune", "zerolatency")
                encoder.set_property("speed-preset", "veryfast")
            except TypeError:
                # Defaults are still valid if a distro exposes enum-only
                # setters through PyGObject.
                pass
            encoder.set_property("key-int-max", 60)
            parser = self._make("h264parse")
            parser.set_property("config-interval", -1)
            caps_filter = self._make("capsfilter")
            caps_filter.set_property(
                "caps",
                Gst.Caps.from_string("video/x-h264,stream-format=avc,alignment=au"),
            )
            queue = self._make("queue")
            elements = [depay, decoder, convert, encoder, parser, caps_filter, queue]
        else:
            raise RuntimeError(f"unsupported WebRTC video codec: {encoding or 'unknown'}")
        return elements, queue

    def _build_audio_branch(self):
        depay = self._make("rtpopusdepay")
        decoder = self._make("opusdec")
        convert = self._make("audioconvert")
        resample = self._make("audioresample")
        raw_caps = self._make("capsfilter")
        raw_caps.set_property("caps", Gst.Caps.from_string("audio/x-raw,rate=44100,channels=2"))
        encoder = Gst.ElementFactory.make("avenc_aac") or Gst.ElementFactory.make("voaacenc")
        if encoder is None:
            raise RuntimeError("required GStreamer AAC encoder is unavailable")
        if encoder.find_property("bitrate") is not None:
            encoder.set_property("bitrate", self.audio_bitrate_bps)
        parser = self._make("aacparse")
        aac_caps = self._make("capsfilter")
        aac_caps.set_property(
            "caps",
            Gst.Caps.from_string("audio/mpeg,mpegversion=4,stream-format=raw"),
        )
        queue = self._make("queue")
        return [depay, decoder, convert, resample, raw_caps, encoder, parser, aac_caps, queue], queue

    def on_pad_added(self, _webrtc, pad) -> None:
        try:
            caps = pad.get_current_caps() or pad.query_caps(None)
            if not caps or caps.get_size() < 1:
                raise RuntimeError("WebRTC media pad arrived without capabilities")
            structure = caps.get_structure(0)
            media = structure.get_value("media") if structure.has_field("media") else ""
            encoding = structure.get_value("encoding-name") if structure.has_field("encoding-name") else ""
            encoding = str(encoding or "").upper()

            if media == "video" and self.video_queue is None:
                elements, queue = self._build_video_branch(encoding)
                self._add_and_sync(elements)
                self._link_chain(elements)
                self.video_queue = queue
                self.video_probe = queue.get_static_pad("src").add_probe(
                    Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST,
                    self._buffer_gate,
                    "video",
                )
                self._link_queue_to_mux("video", queue)
                if pad.link(elements[0].get_static_pad("sink")) != Gst.PadLinkReturn.OK:
                    raise RuntimeError("could not attach WebRTC video pad")
                self.log(f"WebRTC video ready ({encoding})")
                self._maybe_release_flow()
                self._schedule_flow_release()
            elif media == "audio" and self.audio_queue is None:
                elements, queue = self._build_audio_branch()
                self._add_and_sync(elements)
                self._link_chain(elements)
                self.audio_queue = queue
                self.audio_probe = queue.get_static_pad("src").add_probe(
                    Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST,
                    self._buffer_gate,
                    "audio",
                )
                self._link_queue_to_mux("audio", queue)
                if pad.link(elements[0].get_static_pad("sink")) != Gst.PadLinkReturn.OK:
                    raise RuntimeError("could not attach WebRTC audio pad")
                self.log("WebRTC audio ready (OPUS -> AAC)")
                self._maybe_release_flow()
                self._schedule_flow_release()
        except Exception as exc:
            self._fail(exc)

    def on_ice_candidate(self, _element, mline: int, candidate: str) -> None:
        if self.stop_event.is_set():
            return
        message = {
            "type": "iceCandidate",
            "playerId": self.player_id,
            "candidate": {
                "candidate": candidate,
                "sdpMLineIndex": mline,
                "sdpMid": str(mline),
            },
        }
        try:
            asyncio.run_coroutine_threadsafe(self.send_ws(message), self.loop)
        except RuntimeError:
            pass

    async def send_ws(self, value: dict[str, Any]) -> None:
        if self.ws is not None and not self.ws.closed:
            await self.ws.send_json(value)

    def on_answer_created(self, promise, _unused) -> None:
        try:
            reply = promise.get_reply()
            answer = reply.get_value("answer") if reply is not None else None
            if answer is None:
                raise RuntimeError("WebRTC answer creation returned no answer")
            self.webrtcbin.emit("set-local-description", answer, Gst.Promise.new())
            payload = {"type": "answer", "sdp": answer.sdp.as_text(), "playerId": self.player_id}
            asyncio.run_coroutine_threadsafe(self.send_ws(payload), self.loop)
            self.log("WebRTC answer sent")
        except Exception as exc:
            self._fail(exc)

    def prepare_transceivers(self, sdp_message) -> None:
        if self.transceivers_prepared:
            return
        for index in range(sdp_message.medias_len()):
            media = sdp_message.get_media(index)
            kind = media.get_media().lower()
            direction = GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY
            if kind == "video":
                caps = Gst.Caps.from_string("application/x-rtp,media=video")
            elif kind == "audio":
                caps = Gst.Caps.from_string("application/x-rtp,media=audio,encoding-name=OPUS")
            else:
                continue
            self.webrtcbin.emit("add-transceiver", direction, caps)
        self.transceivers_prepared = True

    async def handle_signaling(self) -> None:
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=None, sock_connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(self.signaling_url, heartbeat=20) as ws:
                self.ws = ws
                subscribed = False
                deadline = None
                if self.streamer_wait_seconds > 0:
                    deadline = self.loop.time() + self.streamer_wait_seconds
                await ws.send_json({"type": "listStreamers"})

                while not self.stop_event.is_set():
                    if self.failure_reason:
                        raise RuntimeError(self.failure_reason)
                    try:
                        message = await ws.receive(timeout=1.0)
                    except asyncio.TimeoutError:
                        self.heartbeat()
                        if not subscribed:
                            if deadline is not None and self.loop.time() > deadline:
                                raise RuntimeError("timed out waiting for a Pixel Streaming source")
                            # Poll at the configured rate without blocking stop
                            # handling or state heartbeats.
                            now = self.loop.time()
                            last_poll = getattr(self, "_last_streamer_poll", 0.0)
                            if now - last_poll >= self.streamer_poll_seconds:
                                await ws.send_json({"type": "listStreamers"})
                                self._last_streamer_poll = now
                        continue

                    if message.type in {
                        aiohttp.WSMsgType.CLOSE,
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.ERROR,
                    }:
                        break
                    if message.type != aiohttp.WSMsgType.TEXT:
                        continue
                    try:
                        data = message.json()
                    except (ValueError, TypeError):
                        continue
                    if not isinstance(data, dict):
                        continue

                    kind = data.get("type")
                    if kind == "streamerList" and not subscribed:
                        ids = data.get("ids") or []
                        target = None
                        if self.streamer_id and self.streamer_id in ids:
                            target = self.streamer_id
                        elif not self.streamer_id and ids:
                            target = ids[0]
                        if target:
                            await ws.send_json({"type": "subscribe", "streamerId": target})
                            subscribed = True
                            self.streamer_id = target
                            self.log("Subscribed to Pixel Streaming source")
                    elif kind == "offer":
                        offer_sdp = data.get("sdp") or ""
                        result, sdp_message = GstSdp.SDPMessage.new()
                        if result != GstSdp.SDPResult.OK:
                            raise RuntimeError("could not allocate SDP message")
                        if GstSdp.sdp_message_parse_buffer(offer_sdp.encode(), sdp_message) != GstSdp.SDPResult.OK:
                            raise RuntimeError("could not parse WebRTC offer")
                        offer = GstWebRTC.WebRTCSessionDescription.new(
                            GstWebRTC.WebRTCSDPType.OFFER,
                            sdp_message,
                        )
                        self.prepare_transceivers(sdp_message)
                        self.webrtcbin.emit("set-remote-description", offer, Gst.Promise.new())
                        promise = Gst.Promise.new_with_change_func(self.on_answer_created, None)
                        self.webrtcbin.emit("create-answer", None, promise)
                    elif kind == "iceCandidate":
                        candidate = data.get("candidate") or {}
                        text = candidate.get("candidate")
                        mline = candidate.get("sdpMLineIndex", 0)
                        if text and isinstance(mline, int) and mline >= 0:
                            self.webrtcbin.emit("add-ice-candidate", mline, text)
                    elif kind == "ping":
                        await ws.send_json({"type": "pong", "time": data.get("time")})
                    self.heartbeat()

        self.ws = None
        if self.stop_event.is_set():
            return
        raise RuntimeError(self.failure_reason or "Pixel Streaming signaling connection closed")

    def run(self) -> None:
        asyncio.set_event_loop(self.loop)
        try:
            self.create_pipeline()
            self.glib_loop = GLib.MainLoop()
            self.glib_thread = threading.Thread(target=self.glib_loop.run, name="broadcast-glib", daemon=True)
            self.glib_thread.start()
            self.loop.run_until_complete(self.handle_signaling())
            if self.failure_reason and not self.stop_event.is_set():
                raise RuntimeError(self.failure_reason)
        finally:
            # Cleanup also runs when pipeline construction or dependency
            # loading fails, so the retry supervisor does not leak a pipeline
            # or asyncio loop on every attempt.
            if self.pipeline is not None:
                if self.stop_event.is_set():
                    self.pipeline.send_event(Gst.Event.new_eos())
                    bus = self.pipeline.get_bus()
                    if bus is not None:
                        bus.timed_pop_filtered(2 * Gst.SECOND, Gst.MessageType.EOS)
                self.pipeline.set_state(Gst.State.NULL)
            if self.glib_loop is not None:
                self.glib_loop.quit()
            if self.glib_thread is not None:
                self.glib_thread.join(timeout=3)
            self.loop.close()


class BroadcastSupervisor:
    def __init__(self) -> None:
        self.mode = (os.environ.get("BROADCAST_MODE") or "rtmp").strip().lower()
        if self.mode not in {"rtmp", "test"}:
            raise ValueError("BROADCAST_MODE must be 'rtmp' or 'test'")
        self.destination_path = Path(
            os.environ.get("BROADCAST_RTMP_URL_FILE") or "/run/embody-broadcast/destination"
        )
        self.signaling_url = (
            os.environ.get("BROADCAST_SIGNALING_URL") or "ws://vtuber-unreal-signaling:80"
        ).strip()
        self.streamer_id = (os.environ.get("BROADCAST_STREAMER_ID") or "").strip() or None
        self.state_path = Path(
            os.environ.get("BROADCAST_STATE_FILE") or "/var/lib/embody-broadcast/state.json"
        )
        self.retry_initial = max(0.1, _env_float("BROADCAST_RETRY_INITIAL_SECONDS", 2.0))
        self.retry_max = max(self.retry_initial, _env_float("BROADCAST_RETRY_MAX_SECONDS", 30.0))
        self.stop_event = threading.Event()
        self.redactor = SecretRedactor()
        self.state = StateStore(self.state_path, self.mode, self.redactor)
        self.attempts = 0
        self.session_streamed = False

    def install_signal_handlers(self) -> None:
        def stop(_signum, _frame):
            self.stop_event.set()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

    def log(self, message: Any) -> None:
        print(self.redactor(message), flush=True)

    def on_streaming(self) -> None:
        self.session_streamed = True
        self.state.update(
            "streaming",
            connected=True,
            retry_in_seconds=None,
            last_error=None,
            streamer_id=self.streamer_id,
        )

    def _wait_for_retry(self, delay: float) -> None:
        deadline = time.monotonic() + delay
        while not self.stop_event.is_set():
            remaining = max(0.0, deadline - time.monotonic())
            if remaining <= 0:
                return
            self.state.update(retry_in_seconds=round(remaining, 1))
            self.stop_event.wait(min(5.0, remaining))

    def run(self) -> int:
        self.install_signal_handlers()
        self.state.update("starting", connected=False)
        delay = self.retry_initial
        try:
            while not self.stop_event.is_set():
                self.attempts += 1
                self.session_streamed = False
                try:
                    if self.mode == "test":
                        self.state.update(
                            "starting",
                            attempts=self.attempts,
                            connected=False,
                            retry_in_seconds=None,
                            last_error=None,
                        )
                        self.log("Starting local broadcast lifecycle test pipeline")
                        session = TestPipelineSession(
                            self.stop_event,
                            self.state.heartbeat,
                            self.on_streaming,
                            self.redactor,
                        )
                    else:
                        destination = read_destination(self.destination_path)
                        self.redactor = SecretRedactor(destination)
                        self.state.set_redactor(self.redactor)
                        self.state.update(
                            "connecting",
                            attempts=self.attempts,
                            connected=False,
                            retry_in_seconds=None,
                            last_error=None,
                        )
                        self.log("Connecting Pixel Streaming source to configured RTMP destination")
                        session = WebRtcRtmpSession(
                            destination,
                            self.signaling_url,
                            self.streamer_id,
                            self.stop_event,
                            self.state.heartbeat,
                            self.on_streaming,
                            self.redactor,
                        )
                    session.run()
                    if self.stop_event.is_set():
                        break
                    raise RuntimeError("broadcast session ended unexpectedly")
                except Exception as exc:
                    if self.stop_event.is_set():
                        break
                    message = self.redactor(exc)
                    self.log(f"Broadcast attempt failed: {message}")
                    # A session that had reached media flow gets a fast retry;
                    # only consecutive pre-connect failures back off to max.
                    retry_delay = self.retry_initial if self.session_streamed else delay
                    self.state.update(
                        "retrying",
                        connected=False,
                        attempts=self.attempts,
                        last_error=message,
                        retry_in_seconds=retry_delay,
                    )
                    self._wait_for_retry(retry_delay)
                    delay = min(self.retry_max, retry_delay * 2)
        finally:
            self.state.update(
                "stopped",
                connected=False,
                retry_in_seconds=None,
            )
            self.log("Broadcast bridge stopped")
        return 0


def main() -> int:
    try:
        return BroadcastSupervisor().run()
    except Exception as exc:
        # A supervisor-construction failure cannot yet know the destination;
        # still redact any RTMP-shaped value defensively.
        print(f"Broadcast bridge failed to initialize: {SecretRedactor()(exc)}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
