#!/usr/bin/env python3
"""
Reference GStreamer WebRTC copy-recorder used inside the signaling container.

- Not deployed as a standalone API; we copy this into /opt/embody/recorder in the signaling container.
- Outputs MKV with H.264/Opus copied (no re-encode) to /recordings.
- See README in this folder for usage notes.
"""
import asyncio
import json
import os
import uuid
from pathlib import Path
import threading

import aiohttp
import gi

os.environ.setdefault("GST_DEBUG", "2")
gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")
from gi.repository import Gst, GLib, GstWebRTC, GstSdp

Gst.init(None)

SIGNALING_URL = os.environ.get("RECORDER_SIGNALING_URL", "ws://127.0.0.1:80")
OUTPUT_DIR = Path(os.environ.get("RECORDER_OUTPUT_DIR", "/recordings"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# TURN configuration via env; leave unset to skip TURN
TURN_URL = os.environ.get("RECORDER_TURN_URL") or os.environ.get("TURN_URL")
TURN_USER = os.environ.get("RECORDER_TURN_USER") or os.environ.get("TURN_USER")
TURN_PASS = os.environ.get("RECORDER_TURN_PASS") or os.environ.get("TURN_PASS")
TURN_HOST = os.environ.get("RECORDER_TURN_HOST") or os.environ.get("TURN_HOST")
TURN_PORT = int(os.environ.get("RECORDER_TURN_PORT") or os.environ.get("TURN_PORT") or "3478")

def _sanitize_label(raw: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in raw.strip())
    return cleaned or "capture"

class GstRecorder:
    def __init__(self, loop, label="capture", streamer_id=None):
        self.loop = loop
        self.label = _sanitize_label(label or "capture")
        self.streamer_id = streamer_id
        self.player_id = str(uuid.uuid4())
        self.base = OUTPUT_DIR / f"{self.label}_{int(loop.time())}"
        self.mkv = str(self.base) + ".mkv"
        self.pipeline = None
        self.webrtcbin = None
        self.ws = None
        self.transceivers_prepared = False
        self.video_queue = None
        self.audio_queue = None
        self.allow_flow = False
        self.video_probe = None
        self.audio_probe = None

    def log(self, msg):
        print(msg, flush=True)

    def create_pipeline(self):
        self.pipeline = Gst.Pipeline.new("pipeline")
        self.webrtcbin = Gst.ElementFactory.make("webrtcbin", "webrtcbin")
        self.webrtcbin.set_property("stun-server", "stun://stun.l.google.com:19302")
        if TURN_URL:
            self.webrtcbin.set_property("turn-server", TURN_URL)
        elif TURN_USER and TURN_PASS and TURN_HOST:
            self.webrtcbin.set_property("turn-server", f"turn://{TURN_USER}:{TURN_PASS}@{TURN_HOST}:{TURN_PORT}")
        self.webrtcbin.set_property("bundle-policy", 3)
        self.webrtcbin.connect("on-ice-candidate", self.on_ice_candidate)
        self.webrtcbin.connect("pad-added", self.on_pad_added)

        # Let webrtcbin create transceivers on offer/answer to avoid m-line mismatch

        self.mux = Gst.ElementFactory.make("matroskamux", "mux")
        sink = Gst.ElementFactory.make("filesink", "filesink")
        sink.set_property("location", self.mkv)

        for elem in [self.webrtcbin, self.mux, sink]:
            self.pipeline.add(elem)
        self.mux.link(sink)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_bus_message)

        self.pipeline.set_state(Gst.State.PLAYING)

    def on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.log(f"GST ERROR: {err}, {debug}")
        elif t == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            self.log(f"GST WARN: {warn}, {debug}")
        elif t == Gst.MessageType.STATE_CHANGED and message.src == self.pipeline:
            old, new, pending = message.parse_state_changed()
            self.log(f"Pipeline state changed: {old.value_nick} -> {new.value_nick}")

    def link_branch_to_mux(self, media, queue):
        template = "video_%u" if media == "video" else "audio_%u"
        sinkpad = self.mux.get_request_pad(template)
        if not sinkpad:
            self.log(f"Failed to request mux pad for {media}")
            return
        if queue.get_static_pad("src").link(sinkpad) != Gst.PadLinkReturn.OK:
            self.log(f"Failed to link {media} queue to mux")
        else:
            self.log(f"Linked {media} to mux pad {sinkpad.get_name()}")

    def buffer_gate(self, pad, info, media):
        if not self.allow_flow and (info.type & (Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST)):
            return Gst.PadProbeReturn.DROP
        return Gst.PadProbeReturn.OK

    def maybe_enable_flow(self):
        if self.video_queue and self.audio_queue and not self.allow_flow:
            self.allow_flow = True
            self.log("Audio+video ready, releasing buffers to mux")
            if self.video_probe and self.video_queue:
                self.video_queue.get_static_pad("src").remove_probe(self.video_probe)
                self.video_probe = None
            if self.audio_probe and self.audio_queue:
                self.audio_queue.get_static_pad("src").remove_probe(self.audio_probe)
                self.audio_probe = None

    def on_pad_added(self, webrtc, pad):
        caps = pad.get_current_caps()
        if not caps:
            self.log("Pad added without caps yet")
            return
        s = caps.get_structure(0)
        media = s.get_value("media") if s.has_field("media") else None
        self.log(f"New pad: {media} {caps.to_string()}")
        if media == "video":
            depay = Gst.ElementFactory.make("rtph264depay")
            parse = Gst.ElementFactory.make("h264parse")
            parse.set_property("config-interval", -1)
            queue = Gst.ElementFactory.make("queue")
            for e in [depay, parse, queue]:
                self.pipeline.add(e)
                e.sync_state_with_parent()
            depay.link(parse)
            parse.link(queue)
            pad.link(depay.get_static_pad("sink"))
            self.link_branch_to_mux(media, queue)
            self.video_queue = queue
            self.video_probe = queue.get_static_pad("src").add_probe(
                Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST, self.buffer_gate, "video"
            )
            self.maybe_enable_flow()
        elif media == "audio":
            depay = Gst.ElementFactory.make("rtpopusdepay")
            parse = Gst.ElementFactory.make("opusparse")
            queue = Gst.ElementFactory.make("queue")
            for e in [depay, parse, queue]:
                self.pipeline.add(e)
                e.sync_state_with_parent()
            depay.link(parse)
            parse.link(queue)
            pad.link(depay.get_static_pad("sink"))
            self.link_branch_to_mux(media, queue)
            self.audio_queue = queue
            self.audio_probe = queue.get_static_pad("src").add_probe(
                Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST, self.buffer_gate, "audio"
            )
            self.maybe_enable_flow()

    def on_ice_candidate(self, element, mline, candidate):
        asyncio.run_coroutine_threadsafe(self.send_ws({
            "type": "iceCandidate",
            "playerId": self.player_id,
            "candidate": {
                "candidate": candidate,
                "sdpMLineIndex": mline,
                "sdpMid": str(mline),
            },
        }), self.loop)

    async def send_ws(self, obj):
        if self.ws:
            await self.ws.send_json(obj)

    def on_answer_created(self, promise, ws):
        reply = promise.get_reply()
        ans = reply.get_value("answer")
        if not ans:
            self.log("No answer in promise reply")
            return
        # set local description
        self.webrtcbin.emit("set-local-description", ans, Gst.Promise.new())
        ans_text = ans.sdp.as_text()
        asyncio.run_coroutine_threadsafe(ws.send_json({"type": "answer", "sdp": ans_text, "playerId": self.player_id}), self.loop)
        self.log("Sent answer")

    def prepare_transceivers(self, sdpmsg):
        if self.transceivers_prepared:
            return
        count = sdpmsg.medias_len()
        self.log(f"Offer has {count} m-lines")
        for i in range(count):
            media = sdpmsg.get_media(i)
            kind = media.get_media().lower()
            direction = GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY
            if kind == "video":
                caps = Gst.Caps.from_string("application/x-rtp,media=video,encoding-name=H264")
            elif kind == "audio":
                caps = Gst.Caps.from_string("application/x-rtp,media=audio,encoding-name=OPUS")
            else:
                self.log(f"Skipping unsupported m-line {kind}")
                continue
            self.webrtcbin.emit("add-transceiver", direction, caps)
            self.log(f"Added recvonly transceiver for {kind}")
        self.transceivers_prepared = True

    async def handle_signaling(self):
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(SIGNALING_URL) as ws:
                self.ws = ws
                await ws.send_json({"type": "listStreamers"})
                subscribed = False
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    data = msg.json()
                    if data.get("type") == "streamerList" and not subscribed:
                        ids = data.get("ids", [])
                        target = self.streamer_id or (ids[0] if ids else None)
                        if not target:
                            raise RuntimeError("No streamer")
                        await ws.send_json({"type": "subscribe", "streamerId": target})
                        subscribed = True
                        self.log(f"Subscribed to {target}")
                    elif data.get("type") == "offer":
                        offer_sdp = data["sdp"]
                        _, sdpmsg = GstSdp.SDPMessage.new()
                        GstSdp.sdp_message_parse_buffer(offer_sdp.encode(), sdpmsg)
                        offer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.OFFER, sdpmsg)
                        self.prepare_transceivers(sdpmsg)
                        self.log("Setting remote description")
                        self.webrtcbin.emit("set-remote-description", offer, Gst.Promise.new())
                        promise = Gst.Promise.new_with_change_func(self.on_answer_created, ws)
                        self.log("Creating answer")
                        self.webrtcbin.emit("create-answer", None, promise)
                    elif data.get("type") == "iceCandidate":
                        cand = data.get("candidate")
                        if cand:
                            mline = cand.get("sdpMLineIndex", 0)
                            if mline is None or mline > 1:
                                self.log(f"Skipping ICE candidate for mline {mline}")
                                continue
                            self.webrtcbin.emit("add-ice-candidate", mline, cand.get("candidate"))
                    elif data.get("type") == "ping":
                        await ws.send_json({"type": "pong", "time": data.get("time")})

    async def run_async(self, duration=None):
        try:
            if duration:
                await asyncio.wait_for(self.handle_signaling(), timeout=duration)
            else:
                await self.handle_signaling()
        except asyncio.TimeoutError:
            self.log(f"Stopping after duration={duration}s")
        except asyncio.CancelledError:
            self.log("Run cancelled")
            raise

    def run(self, duration=None):
        self.create_pipeline()
        loop = GLib.MainLoop()
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        try:
            self.loop.run_until_complete(self.run_async(duration))
        except KeyboardInterrupt:
            self.log("Stopping on interrupt")
        finally:
            loop.quit()
            t.join()
            if self.pipeline:
                self.pipeline.send_event(Gst.Event.new_eos())
                bus = self.pipeline.get_bus()
                if bus:
                    bus.timed_pop_filtered(5 * Gst.SECOND, Gst.MessageType.EOS)
                self.pipeline.set_state(Gst.State.NULL)
            self.log(f"Recording complete: {self.mkv}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GStreamer WebRTC copy recorder")
    parser.add_argument("--duration", type=float, default=None, help="Seconds to record before stopping")
    parser.add_argument("--label", default="capture", help="Output label prefix")
    parser.add_argument("--streamer-id", default=None, help="Specific streamer id to subscribe to")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    rec = GstRecorder(loop, label=args.label, streamer_id=args.streamer_id)
    rec.run(duration=args.duration)
