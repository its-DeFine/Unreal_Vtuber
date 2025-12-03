import asyncio
import json
import os
import signal
from pathlib import Path
from typing import Optional

from aiohttp import web

RECORDER_CTRL_PORT = int(os.environ.get("RECORDER_CTRL_PORT", "8889"))
SIGNALING_URL = os.environ.get("RECORDER_SIGNALING_URL", "ws://unreal-signaling:80")
OUTPUT_DIR = Path(os.environ.get("RECORDER_OUTPUT_DIR", "/recordings")).resolve()
PY_RECORDER = os.environ.get("PY_RECORDER_PATH", "/opt/embody/recorder/gs_webrtc_recorder.py")

ALLOWED_IPS = {
    ip.strip()
    for ip in (os.environ.get("VTUBER_ALLOWED_ADDRESSES") or os.environ.get("RECORDINGS_ALLOWED_IPS") or "").split(",")
    if ip.strip()
}
RECORDER_API_TOKEN = os.environ.get("RECORDINGS_API_TOKEN")

STATE = {"proc": None, "label": None, "streamer": None, "started": None, "mkv": None}


def _sanitize_label(raw: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in raw.strip())
    return cleaned or "capture"


def client_ip(request: web.Request) -> Optional[str]:
    host = request.remote
    if not host:
        return None
    if host.startswith("::ffff:"):
        return host.replace("::ffff:", "")
    return host


def ensure_auth(request: web.Request):
    ip = client_ip(request)
    if ALLOWED_IPS and (ip is None or ip not in ALLOWED_IPS):
        raise web.HTTPForbidden(text="Forbidden (IP)")
    if RECORDER_API_TOKEN:
        auth = request.headers.get("authorization", "")
        token = auth.split(" ", 1)[1].strip() if auth.lower().startswith("bearer ") else auth.strip()
        if not token:
            raise web.HTTPUnauthorized(text="Missing token")
        if token != RECORDER_API_TOKEN:
            raise web.HTTPForbidden(text="Forbidden (token)")


async def handle_status(request: web.Request):
    ensure_auth(request)
    proc = STATE["proc"]
    return web.json_response(
        {
            "active": proc is not None,
            "pid": proc.pid if proc else None,
            "label": STATE["label"],
            "streamer_id": STATE["streamer"],
            "started_at": STATE["started"],
            "output": STATE["mkv"],
        }
    )


async def handle_start(request: web.Request):
    ensure_auth(request)
    if STATE["proc"]:
        raise web.HTTPConflict(text="Recorder already running")
    try:
        data = await request.json()
    except Exception:
        data = {}
    label = _sanitize_label(data.get("label") or "capture")
    duration = data.get("duration")
    streamer_id = data.get("streamer_id")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = ["python3", PY_RECORDER, "--label", label]
    if duration:
        cmd += ["--duration", str(duration)]
    if streamer_id:
        cmd += ["--streamer-id", streamer_id]

    env = os.environ.copy()
    env.setdefault("RECORDER_SIGNALING_URL", SIGNALING_URL)
    env.setdefault("RECORDER_OUTPUT_DIR", str(OUTPUT_DIR))

    proc = await asyncio.create_subprocess_exec(*cmd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    run_token = object()
    STATE.update(
        {
            "proc": proc,
            "label": label,
            "streamer": streamer_id,
            "started": asyncio.get_event_loop().time(),
            "mkv": str(OUTPUT_DIR / f"{label}_{int(asyncio.get_event_loop().time())}.mkv"),
            "run_token": run_token,
        }
    )

    async def _drain(prefix: str, stream):
        if not stream:
            return
        async for line in stream:
            print(f"[recorder {prefix}] {line.decode(errors='ignore').rstrip()}")

    asyncio.create_task(_drain("out", proc.stdout))
    asyncio.create_task(_drain("err", proc.stderr))

    async def _waiter():
        code = await proc.wait()
        print(f"[recorder] exited with {code}")
        if STATE.get("run_token") is run_token:
            STATE.update({"proc": None, "label": None, "streamer": None, "started": None, "mkv": None, "run_token": None})

    asyncio.create_task(_waiter())

    return web.json_response(
        {
            "started": True,
            "pid": proc.pid,
            "label": label,
            "streamer_id": streamer_id,
            "duration": duration,
            "output": STATE["mkv"],
        }
    )


async def handle_stop(request: web.Request):
    ensure_auth(request)
    if not STATE["proc"]:
        raise web.HTTPConflict(text="No recorder running")
    run_token = STATE.get("run_token")
    try:
        STATE["proc"].send_signal(signal.SIGINT)
    except ProcessLookupError:
        pass
    STATE.update({"proc": None, "label": None, "streamer": None, "started": None, "mkv": None, "run_token": run_token})
    return web.json_response({"stopped": True})


async def handle_download(request: web.Request):
    ensure_auth(request)
    name = request.match_info.get("filename", "")
    target = (OUTPUT_DIR / name).resolve()
    try:
        target.relative_to(OUTPUT_DIR)
    except ValueError:
        raise web.HTTPForbidden(text="Invalid path")
    if not target.exists() or not target.is_file():
        raise web.HTTPNotFound(text="File not found")
    return web.FileResponse(target)

async def handle_delete(request: web.Request):
    ensure_auth(request)
    name = request.match_info.get("filename", "")
    target = (OUTPUT_DIR / name).resolve()
    try:
        target.relative_to(OUTPUT_DIR)
    except ValueError:
        raise web.HTTPForbidden(text="Invalid path")
    if not target.exists() or not target.is_file():
        raise web.HTTPNotFound(text="File not found")
    target.unlink()
    return web.json_response({"deleted": True, "file": name})

async def handle_root(request: web.Request):
    return web.json_response({"service": "gs-recorder-control", "active": STATE["proc"] is not None})


def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/recordings/status", handle_status)
    app.router.add_post("/recordings/start", handle_start)
    app.router.add_post("/recordings/stop", handle_stop)
    app.router.add_get("/recordings/{filename}", handle_download)
    app.router.add_delete("/recordings/{filename}", handle_delete)
    return app


def main():
    web.run_app(make_app(), host="0.0.0.0", port=RECORDER_CTRL_PORT)


if __name__ == "__main__":
    main()
