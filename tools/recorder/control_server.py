import asyncio
import json
import os
import signal
import time
from pathlib import Path
from typing import Optional

import aiohttp
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


def _float_setting(data: dict, field: str, env: str) -> Optional[float]:
    value = data.get(field)
    if value is None:
        value = os.environ.get(env)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    streamer_wait_seconds = _float_setting(data, "streamer_wait_seconds", "RECORDER_STREAMER_WAIT_SECONDS")
    streamer_poll_seconds = _float_setting(data, "streamer_poll_seconds", "RECORDER_STREAMER_POLL_SECONDS")
    av_wait_seconds = _float_setting(data, "av_wait_seconds", "RECORDER_AV_WAIT_SECONDS")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{label}_{int(time.time() * 1000)}.mkv"
    output_path = (OUTPUT_DIR / filename).resolve()
    cmd = ["python3", PY_RECORDER, "--label", label, "--output", str(output_path)]
    if duration:
        cmd += ["--duration", str(duration)]
    if streamer_id:
        cmd += ["--streamer-id", streamer_id]
    if streamer_wait_seconds is not None:
        cmd += ["--streamer-wait-seconds", str(streamer_wait_seconds)]
    if streamer_poll_seconds is not None:
        cmd += ["--streamer-poll-seconds", str(streamer_poll_seconds)]
    if av_wait_seconds is not None:
        cmd += ["--av-wait-seconds", str(av_wait_seconds)]

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
            "started": time.time(),
            "mkv": str(output_path),
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


async def handle_upload(request: web.Request):
    ensure_auth(request)
    name = request.match_info.get("filename", "")
    target = (OUTPUT_DIR / name).resolve()
    try:
        target.relative_to(OUTPUT_DIR)
    except ValueError:
        raise web.HTTPForbidden(text="Invalid path")
    if not target.exists() or not target.is_file():
        raise web.HTTPNotFound(text="File not found")

    try:
        data = await request.json()
    except Exception:
        data = {}
    upload_url = (data.get("upload_url") or data.get("url") or "").strip()
    if not upload_url:
        raise web.HTTPBadRequest(text="Missing upload_url")

    delete_after = bool(data.get("delete_after"))

    import hashlib

    h = hashlib.sha256()
    size = 0
    with target.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)

    async with aiohttp.ClientSession() as session:
        with target.open("rb") as handle:
            async with session.put(upload_url, data=handle, headers={"Content-Length": str(size)}) as resp:
                if resp.status < 200 or resp.status >= 300:
                    body = (await resp.text())[:200]
                    raise web.HTTPBadRequest(text=f"Upload failed (status={resp.status}): {body}")

    if delete_after:
        try:
            target.unlink()
        except Exception:
            pass

    return web.json_response(
        {
            "uploaded": True,
            "file": name,
            "bytes": size,
            "sha256": f"sha256:{h.hexdigest()}",
            "deleted_after_upload": delete_after,
        }
    )

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
    app.router.add_post("/recordings/{filename}/upload", handle_upload)
    return app


def main():
    web.run_app(make_app(), host="0.0.0.0", port=RECORDER_CTRL_PORT)


if __name__ == "__main__":
    main()
