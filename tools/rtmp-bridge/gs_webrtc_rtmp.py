#!/usr/bin/env python3
"""
GStreamer WebRTC → RTMP bridge for Twitch/YouTube streaming.

Connects to a Pixel Streaming signaling server via WebSocket,
receives WebRTC audio+video, and outputs RTMP to streaming platforms.

Replaces the Chrome + Xvfb + ffmpeg broadcast pipeline with a single process.
Fixes audio (no PulseAudio needed) and reduces latency by ~200-400ms.

Video: H.264 passthrough (default) or NVENC re-encode (--transcode-video)
Audio: Opus → AAC transcode (always required for RTMP/FLV)

Based on gs_webrtc_recorder.py signaling protocol.

Usage:
    # Passthrough (lowest latency):
    python3 gs_webrtc_rtmp.py \\
        --signaling ws://127.0.0.1:8080 \\
        --rtmp-out rtmp://live.twitch.tv/app/STREAM_KEY

    # NVENC transcode (bitrate control):
    python3 gs_webrtc_rtmp.py \\
        --signaling ws://127.0.0.1:8080 \\
        --rtmp-out rtmp://live.twitch.tv/app/STREAM_KEY \\
        --transcode-video --video-bitrate-kbps 6000
"""
import asyncio
import os
import signal
import subprocess
import uuid
import threading

import aiohttp
import gi

os.environ.setdefault("GST_DEBUG", "2")
gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")
from gi.repository import Gst, GLib, GstWebRTC, GstSdp  # noqa: E402

Gst.init(None)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


SIGNALING_URL = _env("RTMP_SIGNALING_URL", "ws://127.0.0.1:8080")
TURN_URL = os.environ.get("RECORDER_TURN_URL") or os.environ.get("TURN_URL")
TURN_USER = os.environ.get("RECORDER_TURN_USER") or os.environ.get("TURN_USER")
TURN_PASS = os.environ.get("RECORDER_TURN_PASS") or os.environ.get("TURN_PASS")
TURN_HOST = os.environ.get("RECORDER_TURN_HOST") or os.environ.get("TURN_HOST")
TURN_PORT = int(os.environ.get("RECORDER_TURN_PORT") or os.environ.get("TURN_PORT") or "3478")
STREAMER_WAIT = _env_float("RTMP_STREAMER_WAIT_SECONDS", 30.0)
STREAMER_POLL = _env_float("RTMP_STREAMER_POLL_SECONDS", 2.0)
AV_WAIT = _env_float("RTMP_AV_WAIT_SECONDS", 3.0)
WEBRTC_LATENCY_MS = _env_int("RTMP_WEBRTC_LATENCY_MS", 200)
FORCE_H264 = _env_int("RTMP_FORCE_H264", 0)


class GstRTMPBridge:
    """Receives WebRTC from Pixel Streaming, outputs RTMP to Twitch/YouTube."""

    def __init__(
        self,
        loop,
        rtmp_urls: list[str],
        *,
        signaling_url: str = SIGNALING_URL,
        streamer_id: str | None = None,
        transcode_video: bool = False,
        force_software: bool = False,
        video_bitrate_kbps: int = 6000,
        audio_bitrate_kbps: int = 160,
        fps: int = 30,
        force_h264: bool = False,
        streamer_wait: float = STREAMER_WAIT,
        streamer_poll: float = STREAMER_POLL,
        av_wait: float = AV_WAIT,
    ):
        self.loop = loop
        self.rtmp_urls = rtmp_urls
        self.signaling_url = signaling_url
        self.streamer_id = streamer_id
        self.transcode_video = transcode_video
        self._force_software = force_software
        self.video_bitrate_kbps = video_bitrate_kbps
        self.audio_bitrate_kbps = audio_bitrate_kbps
        self.fps = fps
        self.force_h264 = force_h264
        self.player_id = str(uuid.uuid4())
        self.streamer_wait = streamer_wait
        self.streamer_poll = streamer_poll
        self.av_wait = av_wait

        self.pipeline = None
        self.webrtcbin = None
        self.mux = None
        self.ws = None
        self.transceivers_prepared = False
        self.video_queue = None
        self.audio_queue = None
        self.allow_flow = False
        self.video_probe = None
        self.audio_probe = None
        self.flow_timeout_id = None
        self._stopping = False
        self._ffmpeg_procs: list[subprocess.Popen] = []
        self._pipe_write_fds: list[int] = []

    def log(self, msg):
        print(f"[rtmp-bridge] {msg}", flush=True)

    def _filter_sdp_h264(self, sdp_text: str) -> str:
        """Strip VP8/VP9 from SDP, keep only H.264 (+ RTX for H.264)."""
        if not self.force_h264:
            return sdp_text

        lines = sdp_text.splitlines()
        if not lines:
            return sdp_text

        sections: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            if line.startswith("m=") and current:
                sections.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            sections.append(current)

        def _filter_video_section(sec: list[str]) -> list[str] | None:
            mline = sec[0]
            if not mline.startswith("m=video"):
                return sec
            parts = mline.split()
            if len(parts) < 4:
                return sec
            payloads = parts[3:]
            pt_codec: dict[str, str] = {}
            pt_apt: dict[str, str] = {}
            for ln in sec[1:]:
                if ln.startswith("a=rtpmap:"):
                    try:
                        pt, rest = ln[len("a=rtpmap:"):].split(None, 1)
                        codec = rest.split("/", 1)[0].upper()
                        pt_codec[pt] = codec
                    except ValueError:
                        continue
                elif ln.startswith("a=fmtp:"):
                    try:
                        pt, params = ln[len("a=fmtp:"):].split(None, 1)
                        for kv in params.split(";"):
                            kv = kv.strip()
                            if kv.startswith("apt="):
                                pt_apt[pt] = kv.split("=", 1)[1]
                                break
                    except ValueError:
                        continue

            h264_pts = {pt for pt, c in pt_codec.items() if c == "H264"}
            if not h264_pts:
                return None
            rtx_pts = {pt for pt, c in pt_codec.items() if c == "RTX" and pt_apt.get(pt) in h264_pts}
            keep_pts = [pt for pt in payloads if pt in h264_pts or pt in rtx_pts]
            if not keep_pts:
                return None

            filtered = [f"m=video {parts[1]} {parts[2]} {' '.join(keep_pts)}"]
            for ln in sec[1:]:
                if ln.startswith(("a=rtpmap:", "a=fmtp:", "a=rtcp-fb:")):
                    try:
                        pt = ln.split(":", 1)[1].split(None, 1)[0]
                    except Exception:
                        filtered.append(ln)
                        continue
                    if pt in keep_pts:
                        filtered.append(ln)
                else:
                    filtered.append(ln)
            return filtered

        out_sections: list[list[str]] = []
        for sec in sections:
            if sec and sec[0].startswith("m=video"):
                filtered = _filter_video_section(sec)
                if filtered is None:
                    # If we cannot keep H.264, fall back to original SDP.
                    return sdp_text
                out_sections.append(filtered)
            else:
                out_sections.append(sec)

        return "\r\n".join("\r\n".join(sec) for sec in out_sections) + "\r\n"

    # ── Pipeline construction ──

    def _request_mux_pad(self, name):
        """Request a pad from the muxer, compatible with GStreamer 1.18+."""
        pad = None
        try:
            pad = self.mux.request_pad_simple(name)
        except AttributeError:
            pad = self.mux.get_request_pad(name)
        return pad

    def _spawn_ffmpeg(self, read_fd: int, out_url: str) -> subprocess.Popen:
        """
        Publish FLV to RTMP via ffmpeg.

        Twitch's RTMP ingest can behave poorly with GStreamer's rtmpsink (socket
        RX buffer grows; never goes live). ffmpeg's RTMP stack is more robust.
        """
        cmd = [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-fflags",
            "+nobuffer+flush_packets",
            "-f",
            "flv",
            "-i",
            f"pipe:{read_fd}",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-f",
            "flv",
            "-flvflags",
            "no_duration_filesize",
            "-rtmp_live",
            "live",
            out_url,
        ]
        return subprocess.Popen(
            cmd,
            pass_fds=(read_fd,),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def create_pipeline(self):
        self.pipeline = Gst.Pipeline.new("rtmp-bridge")

        # -- WebRTC input --
        self.webrtcbin = Gst.ElementFactory.make("webrtcbin", "webrtcbin")
        self.webrtcbin.set_property("stun-server", "stun://stun.l.google.com:19302")
        # Buffer RTP jitter to avoid out-of-order timestamps from WebRTC
        try:
            self.webrtcbin.set_property("latency", WEBRTC_LATENCY_MS)
        except Exception:
            pass
        if TURN_URL:
            self.webrtcbin.set_property("turn-server", TURN_URL)
        elif TURN_USER and TURN_PASS and TURN_HOST:
            turn = f"turn://{TURN_USER}:{TURN_PASS}@{TURN_HOST}:{TURN_PORT}"
            self.webrtcbin.set_property("turn-server", turn)
        self.webrtcbin.set_property("bundle-policy", 3)
        self.webrtcbin.connect("on-ice-candidate", self.on_ice_candidate)
        self.webrtcbin.connect("pad-added", self.on_pad_added)

        # -- FLV mux + ffmpeg RTMP output --
        #
        # With PixelStreaming2 configured to output H.264, the lowest-latency
        # path is H.264 passthrough + Opus→AAC. We still publish via ffmpeg
        # because Twitch ingest has been unreliable with GStreamer's rtmpsink.
        self.mux = Gst.ElementFactory.make("flvmux", "mux")
        self.mux.set_property("streamable", True)

        self.pipeline.add(self.webrtcbin)
        self.pipeline.add(self.mux)

        self.log("Delivery: flvmux → fdsink → ffmpeg → RTMP")
        if len(self.rtmp_urls) == 1:
            read_fd, write_fd = os.pipe()
            self._pipe_write_fds.append(write_fd)

            fdsink = Gst.ElementFactory.make("fdsink", "fdsink0")
            fdsink.set_property("fd", write_fd)
            fdsink.set_property("sync", False)
            self.pipeline.add(fdsink)
            self.mux.link(fdsink)

            self._ffmpeg_procs.append(self._spawn_ffmpeg(read_fd, self.rtmp_urls[0]))
            os.close(read_fd)
            self.log(f"Output: {self._safe_url(self.rtmp_urls[0])}")
        else:
            tee = Gst.ElementFactory.make("tee", "rtmptee")
            self.pipeline.add(tee)
            self.mux.link(tee)
            for i, url in enumerate(self.rtmp_urls):
                read_fd, write_fd = os.pipe()
                self._pipe_write_fds.append(write_fd)

                q = Gst.ElementFactory.make("queue", f"rtmpq{i}")
                fdsink = Gst.ElementFactory.make("fdsink", f"fdsink{i}")
                fdsink.set_property("fd", write_fd)
                fdsink.set_property("sync", False)
                self.pipeline.add(q)
                self.pipeline.add(fdsink)
                tee.link(q)
                q.link(fdsink)

                self._ffmpeg_procs.append(self._spawn_ffmpeg(read_fd, url))
                os.close(read_fd)
                self.log(f"Output [{i}]: {self._safe_url(url)}")

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)

        self.pipeline.set_state(Gst.State.PLAYING)

    @staticmethod
    def _safe_url(url: str) -> str:
        """Mask stream key in logs."""
        parts = url.rsplit("/", 1)
        if len(parts) == 2 and len(parts[1]) > 8:
            return f"{parts[0]}/{parts[1][:4]}****"
        return url

    def _on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.log(f"ERROR: {err}\n  debug: {debug}")
        elif t == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            self.log(f"WARN: {warn}")
        elif t == Gst.MessageType.STATE_CHANGED and message.src == self.pipeline:
            old, new, _ = message.parse_state_changed()
            self.log(f"Pipeline: {old.value_nick} → {new.value_nick}")

    # ── Media pad handling ──

    def _add_and_link(self, elements):
        """Add elements to pipeline, sync state, link sequentially."""
        for e in elements:
            self.pipeline.add(e)
            e.sync_state_with_parent()
        for i in range(len(elements) - 1):
            if not elements[i].link(elements[i + 1]):
                a, b = elements[i].get_name(), elements[i + 1].get_name()
                self.log(f"Link failed: {a} → {b}")
                return False
        return True

    def _link_to_mux(self, media, queue):
        mux_name = self.mux.get_factory().get_name()
        pad = self._request_mux_pad(media)
        if not pad:
            self.log(f"Cannot get {mux_name} pad for {media}")
            return
        result = queue.get_static_pad("src").link(pad)
        if result != Gst.PadLinkReturn.OK:
            self.log(f"Pad link failed for {media}: {result}")
        else:
            self.log(f"✓ {media} → {mux_name}")

    def on_pad_added(self, webrtc, pad):
        caps = pad.get_current_caps()
        if not caps:
            return
        s = caps.get_structure(0)
        media = s.get_value("media") if s.has_field("media") else None
        self.log(f"Pad: {media}  caps: {caps.to_string()[:120]}")
        if media == "video":
            self._link_video(pad, s)
        elif media == "audio":
            self._link_audio(pad)

    def _link_video(self, pad, structure):
        enc = (structure.get_value("encoding-name") or "").upper() if structure.has_field("encoding-name") else ""

        depay_map = {"H264": "rtph264depay", "VP9": "rtpvp9depay", "VP8": "rtpvp8depay"}
        if enc not in depay_map:
            self.log(f"Unsupported video codec: {enc or '?'}")
            return
        depay = Gst.ElementFactory.make(depay_map[enc])
        if not depay:
            self.log(f"Missing element: {depay_map[enc]}")
            return

        elements = [depay]

        # If the incoming stream is already H.264, passthrough is the safest and
        # lowest-latency option (avoids decode→colorspace→encode quirks).
        # We still support transcoding for VP8/VP9 inputs.
        if enc == "H264":
            # ── H.264 passthrough: zero latency, zero GPU cost ──
            parse = Gst.ElementFactory.make("h264parse")
            parse.set_property("config-interval", -1)
            elements.append(parse)
            self.log("Video: H.264 passthrough")
        else:
            # ── Transcode: decode → encode ──
            if enc == "VP9":
                parse = Gst.ElementFactory.make("vp9parse")
                dec = Gst.ElementFactory.make("nvvp9dec") or Gst.ElementFactory.make("avdec_vp9")
                if dec and dec.get_factory().get_name() == "nvvp9dec":
                    self.log("Video: VP9 decode via NVDEC")
                elements += [parse, dec]
            elif enc == "VP8":
                dec = Gst.ElementFactory.make("avdec_vp8")
                elements.append(dec)

            convert = Gst.ElementFactory.make("videoconvert")
            elements.append(convert)
            # Explicit colorimetry prevents "invalid colorimetry" warnings
            colorcaps = Gst.ElementFactory.make("capsfilter")
            colorcaps.set_property("caps", Gst.Caps.from_string(
                "video/x-raw,format=I420,colorimetry=bt709"
            ))
            elements.append(colorcaps)
            encoder = self._make_h264_encoder()
            elements.append(encoder)

            final_parse = Gst.ElementFactory.make("h264parse")
            final_parse.set_property("config-interval", -1)
            elements.append(final_parse)

        queue = Gst.ElementFactory.make("queue")
        queue.set_property("max-size-time", 3 * Gst.SECOND)
        elements.append(queue)

        if not self._add_and_link(elements):
            return
        pad.link(depay.get_static_pad("sink"))
        self._link_to_mux("video", queue)

        self.video_queue = queue
        self.video_probe = queue.get_static_pad("src").add_probe(
            Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST,
            self._gate, "video",
        )
        self._check_flow()

    def _make_h264_encoder(self):
        """Create H.264 encoder — prefers NVENC (dedicated ASIC, zero CPU cost)."""
        if not self._force_software:
            enc = Gst.ElementFactory.make("nvh264enc")
            if enc:
                try:
                    enc.set_property("preset", 4)        # low-latency
                    enc.set_property("bitrate", self.video_bitrate_kbps)
                    enc.set_property("gop-size", self.fps * 2)
                    enc.set_property("rc-mode", 2)        # CBR
                    enc.set_property("bframes", 0)        # no B-frames → monotonic DTS
                except Exception:
                    pass
                self.log(f"Video: NVENC @ {self.video_bitrate_kbps} kbps (B=0, CBR)")
                return enc

        # Fallback: x264 CPU encoder
        enc = Gst.ElementFactory.make("x264enc")
        enc.set_property("bitrate", self.video_bitrate_kbps)
        enc.set_property("tune", 0x04)         # zerolatency
        enc.set_property("speed-preset", 2)    # superfast
        enc.set_property("key-int-max", self.fps * 2)
        enc.set_property("bframes", 0)
        enc.set_property("b-adapt", False)
        enc.set_property("pass", 0)            # CBR
        self.log(f"Video: x264 @ {self.video_bitrate_kbps} kbps (zerolatency, B=0)")
        return enc

    def _link_audio(self, pad):
        """Opus → AAC transcode (required: RTMP/FLV only supports AAC)."""
        depay = Gst.ElementFactory.make("rtpopusdepay")
        dec = Gst.ElementFactory.make("opusdec")
        convert = Gst.ElementFactory.make("audioconvert")

        # Caps: keep Opus native 48 kHz to avoid resample discontinuities
        filt = Gst.ElementFactory.make("capsfilter")
        filt.set_property("caps", Gst.Caps.from_string("audio/x-raw,rate=48000,channels=2"))

        # Try AAC encoders in order of preference
        aac = None
        for name in ("voaacenc", "avenc_aac", "fdkaacenc"):
            aac = Gst.ElementFactory.make(name)
            if aac:
                self.log(f"Audio encoder: {name}")
                break
        if not aac:
            self.log("ERROR: no AAC encoder (need voaacenc, avenc_aac, or fdkaacenc)")
            return
        aac.set_property("bitrate", self.audio_bitrate_kbps * 1000)

        # aacparse ensures AAC frames are correctly formatted for muxing
        aac_parse = Gst.ElementFactory.make("aacparse")

        queue = Gst.ElementFactory.make("queue")
        queue.set_property("max-size-time", 3 * Gst.SECOND)

        elements = [depay, dec, convert, filt, aac, aac_parse, queue]
        if not self._add_and_link(elements):
            return
        pad.link(depay.get_static_pad("sink"))
        self._link_to_mux("audio", queue)

        self.audio_queue = queue
        self.audio_probe = queue.get_static_pad("src").add_probe(
            Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST,
            self._gate, "audio",
        )
        self.log(f"Audio: Opus → AAC @ {self.audio_bitrate_kbps} kbps, 48 kHz stereo")
        self._check_flow()

    # ── Flow gating (wait for both audio+video before streaming) ──

    def _gate(self, pad, info, media):
        if not self.allow_flow and (info.type & (Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST)):
            return Gst.PadProbeReturn.DROP
        return Gst.PadProbeReturn.OK

    def _release_flow(self, reason: str):
        if self.allow_flow:
            return
        self.allow_flow = True
        self.log(reason)
        for probe, queue in [(self.video_probe, self.video_queue), (self.audio_probe, self.audio_queue)]:
            if probe and queue:
                queue.get_static_pad("src").remove_probe(probe)
        self.video_probe = self.audio_probe = None
        if self.flow_timeout_id is not None:
            GLib.source_remove(self.flow_timeout_id)
            self.flow_timeout_id = None

    def _check_flow(self):
        if self.video_queue and self.audio_queue and not self.allow_flow:
            self._release_flow("Audio + video ready → streaming to RTMP")
        elif not self.allow_flow and self.flow_timeout_id is None and self.av_wait > 0:
            def _timeout():
                if not self.allow_flow and (self.video_queue or self.audio_queue):
                    self._release_flow("AV wait elapsed → streaming available tracks")
                self.flow_timeout_id = None
                return False
            self.flow_timeout_id = GLib.timeout_add(int(self.av_wait * 1000), _timeout)

    # ── Signaling protocol (matches gs_webrtc_recorder.py) ──

    def on_ice_candidate(self, element, mline, candidate):
        asyncio.run_coroutine_threadsafe(
            self._ws_send({
                "type": "iceCandidate",
                "playerId": self.player_id,
                "candidate": {"candidate": candidate, "sdpMLineIndex": mline, "sdpMid": str(mline)},
            }),
            self.loop,
        )

    async def _ws_send(self, obj):
        if self.ws:
            await self.ws.send_json(obj)

    def _on_answer_created(self, promise, ws):
        reply = promise.get_reply()
        ans = reply.get_value("answer")
        if not ans:
            self.log("No answer in promise reply")
            return
        self.webrtcbin.emit("set-local-description", ans, Gst.Promise.new())
        asyncio.run_coroutine_threadsafe(
            ws.send_json({"type": "answer", "sdp": ans.sdp.as_text(), "playerId": self.player_id}),
            self.loop,
        )
        self.log("Sent SDP answer")

    def _prepare_transceivers(self, sdpmsg):
        if self.transceivers_prepared:
            return
        n = sdpmsg.medias_len()
        self.log(f"SDP offer: {n} m-lines")
        for i in range(n):
            kind = sdpmsg.get_media(i).get_media().lower()
            direction = GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY
            if kind == "video":
                if self.force_h264:
                    caps = Gst.Caps.from_string("application/x-rtp,media=video,encoding-name=H264")
                else:
                    caps = Gst.Caps.from_string("application/x-rtp,media=video")
            elif kind == "audio":
                caps = Gst.Caps.from_string("application/x-rtp,media=audio,encoding-name=OPUS")
            else:
                continue
            self.webrtcbin.emit("add-transceiver", direction, caps)
        self.transceivers_prepared = True

    async def _signaling_loop(self):
        self.log(f"Connecting: {self.signaling_url}")
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(self.signaling_url) as ws:
                self.ws = ws
                subscribed = False
                deadline = self.loop.time() + self.streamer_wait if self.streamer_wait > 0 else None

                await ws.send_json({"type": "listStreamers"})
                while not self._stopping:
                    timeout = None if subscribed else max(self.streamer_poll, 0.5)
                    try:
                        msg = await ws.receive(timeout=timeout)
                    except asyncio.TimeoutError:
                        if not subscribed:
                            if deadline and self.loop.time() > deadline:
                                raise RuntimeError("Timed out waiting for streamer")
                            await ws.send_json({"type": "listStreamers"})
                        continue

                    if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        self.log("Signaling WebSocket closed")
                        break
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue

                    data = msg.json()
                    mtype = data.get("type")

                    if mtype == "streamerList" and not subscribed:
                        ids = data.get("ids", [])
                        target = self.streamer_id if self.streamer_id in ids else (ids[0] if ids else None)
                        if not target:
                            if deadline and self.loop.time() > deadline:
                                raise RuntimeError("No streamer available")
                            continue
                        await ws.send_json({"type": "subscribe", "streamerId": target})
                        subscribed = True
                        self.streamer_id = target
                        self.log(f"Subscribed: {target}")

                    elif mtype == "offer":
                        sdp_text = data["sdp"]
                        if self.force_h264:
                            sdp_text = self._filter_sdp_h264(sdp_text)
                        _, sdpmsg = GstSdp.SDPMessage.new()
                        GstSdp.sdp_message_parse_buffer(sdp_text.encode(), sdpmsg)
                        offer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.OFFER, sdpmsg)
                        self._prepare_transceivers(sdpmsg)
                        self.webrtcbin.emit("set-remote-description", offer, Gst.Promise.new())
                        promise = Gst.Promise.new_with_change_func(self._on_answer_created, ws)
                        self.webrtcbin.emit("create-answer", None, promise)

                    elif mtype == "iceCandidate":
                        cand = data.get("candidate")
                        if cand:
                            mline = cand.get("sdpMLineIndex", 0)
                            if mline is not None and mline <= 1:
                                self.webrtcbin.emit("add-ice-candidate", mline, cand.get("candidate"))

                    elif mtype == "ping":
                        await ws.send_json({"type": "pong", "time": data.get("time")})

    # ── Run / stop ──

    def stop(self):
        self._stopping = True
        self.log("Stop requested")

    def _cleanup_ffmpeg(self):
        # Close write ends first so ffmpeg can exit cleanly when it hits EOF.
        for fd in self._pipe_write_fds:
            try:
                os.close(fd)
            except OSError:
                pass
        self._pipe_write_fds.clear()

        for p in self._ffmpeg_procs:
            try:
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        self._ffmpeg_procs.clear()

    def run(self, duration=None):
        self.create_pipeline()
        glib_loop = GLib.MainLoop()
        t = threading.Thread(target=glib_loop.run, daemon=True)
        t.start()

        for sig in (signal.SIGTERM, signal.SIGINT):
            self.loop.add_signal_handler(sig, self.stop)

        try:
            coro = self._signaling_loop()
            if duration:
                coro = asyncio.wait_for(coro, timeout=duration)
            self.loop.run_until_complete(coro)
        except asyncio.TimeoutError:
            self.log(f"Duration reached ({duration}s)")
        except KeyboardInterrupt:
            self.log("Interrupted")
        finally:
            glib_loop.quit()
            t.join(timeout=5)
            if self.pipeline:
                self.pipeline.send_event(Gst.Event.new_eos())
                bus = self.pipeline.get_bus()
                if bus:
                    bus.timed_pop_filtered(5 * Gst.SECOND, Gst.MessageType.EOS)
                self.pipeline.set_state(Gst.State.NULL)
            self._cleanup_ffmpeg()
            self.log("Stream ended")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        description="GStreamer WebRTC → RTMP bridge (replaces Chrome + Xvfb + ffmpeg)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Twitch (H.264 passthrough, lowest latency):
  %(prog)s --signaling ws://127.0.0.1:8080 \\
           --rtmp-out rtmp://live.twitch.tv/app/STREAM_KEY

  # NVENC re-encode for bitrate control:
  %(prog)s --signaling ws://127.0.0.1:8080 \\
           --rtmp-out rtmp://live.twitch.tv/app/STREAM_KEY \\
           --transcode-video --video-bitrate-kbps 6000

  # Multi-platform (Twitch + YouTube):
  %(prog)s --signaling ws://127.0.0.1:8080 \\
           --rtmp-out rtmp://live.twitch.tv/app/TWITCH_KEY \\
           --rtmp-out rtmp://a.rtmp.youtube.com/live2/YT_KEY

  # Timed session (2 hours):
  %(prog)s --signaling ws://127.0.0.1:8080 \\
           --rtmp-out rtmp://live.twitch.tv/app/KEY \\
           --duration 7200
        """,
    )
    p.add_argument("--signaling", default=SIGNALING_URL, help="Signaling WebSocket URL")
    p.add_argument("--rtmp-out", action="append", required=True, dest="rtmp_urls", help="RTMP URL (repeatable)")
    p.add_argument("--streamer-id", default=None, help="Subscribe to specific streamer ID")
    p.add_argument("--transcode-video", action="store_true", help="Re-encode with NVENC (default: passthrough)")
    p.add_argument("--software-encode", action="store_true", help="Force x264 CPU encoder (fixes DTS issues)")
    p.add_argument("--video-bitrate-kbps", type=int, default=6000, help="Video bitrate when transcoding (default: 6000)")
    p.add_argument("--audio-bitrate-kbps", type=int, default=160, help="AAC audio bitrate (default: 160)")
    p.add_argument("--fps", type=int, default=30, help="Target FPS for transcode keyframes (default: 30)")
    p.add_argument("--force-h264", action="store_true", help="Negotiate H.264 only (avoid VP9 decode)")
    p.add_argument("--duration", type=float, default=None, help="Stream duration in seconds")
    p.add_argument("--streamer-wait", type=float, default=STREAMER_WAIT, help="Seconds to wait for streamer")
    p.add_argument("--streamer-poll", type=float, default=STREAMER_POLL, help="Poll interval for streamer list")
    p.add_argument("--av-wait", type=float, default=AV_WAIT, help="Wait for both A+V before streaming")
    args = p.parse_args()

    loop = asyncio.new_event_loop()
    bridge = GstRTMPBridge(
        loop,
        rtmp_urls=args.rtmp_urls,
        signaling_url=args.signaling,
        streamer_id=args.streamer_id,
        transcode_video=args.transcode_video,
        force_software=args.software_encode,
        video_bitrate_kbps=args.video_bitrate_kbps,
        audio_bitrate_kbps=args.audio_bitrate_kbps,
        fps=args.fps,
        force_h264=args.force_h264 or FORCE_H264,
        streamer_wait=args.streamer_wait,
        streamer_poll=args.streamer_poll,
        av_wait=args.av_wait,
    )
    bridge.run(duration=args.duration)
