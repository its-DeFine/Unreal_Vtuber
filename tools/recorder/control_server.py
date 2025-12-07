import asyncio
import datetime
import json
import os
import uuid
import signal
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiohttp import ClientSession, web

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
}


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response(status=204)
    else:
        resp = await handler(request)
    for key, value in CORS_HEADERS.items():
        resp.headers[key] = value
    return resp

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

PLANNER_URL = os.environ.get("PLANNER_URL")
RUNNER_URL = os.environ.get("RUNNER_URL", "http://vtuber-script-runner:9877")
PLAN_DEFAULT_SPACING_MS = int(os.environ.get("PLAN_SPEECH_SPACING_MS", "2000"))
RUNNER_POLL_SECONDS = int(os.environ.get("RUNNER_POLL_SECONDS", "120"))

# In-memory plan/run cache for quick lookup (intentionally simple for single-instance use).
PLANS: Dict[str, Dict[str, Any]] = {}
RUNS: Dict[str, Dict[str, Any]] = {}

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
    auth = request.headers.get("authorization", "")
    token = auth.split(" ", 1)[1].strip() if auth.lower().startswith("bearer ") else auth.strip()

    # Token can satisfy auth even if the IP is not explicitly allowlisted.
    if RECORDER_API_TOKEN:
        if not token:
            raise web.HTTPUnauthorized(text="Missing token")
        if token != RECORDER_API_TOKEN:
            raise web.HTTPForbidden(text="Forbidden (token)")
    if ALLOWED_IPS and (ip is None or ip not in ALLOWED_IPS):
        # If the caller presented a valid token, let it pass even if IP is outside the allowlist.
        if RECORDER_API_TOKEN and token == RECORDER_API_TOKEN:
            return
        raise web.HTTPForbidden(text="Forbidden (IP)")


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


async def _start_recorder(label: str, duration: Optional[int], streamer_id: Optional[str]) -> Dict[str, Any]:
    if STATE["proc"]:
        raise web.HTTPConflict(text="Recorder already running")

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

    return {
        "started": True,
        "pid": proc.pid,
        "label": label,
        "streamer_id": streamer_id,
        "duration": duration,
        "output": STATE["mkv"],
    }


async def handle_start(request: web.Request):
    ensure_auth(request)
    try:
        data = await request.json()
    except Exception:
        data = {}
    label = _sanitize_label(data.get("label") or "capture")
    duration = data.get("duration")
    streamer_id = data.get("streamer_id")

    result = await _start_recorder(label=label, duration=duration, streamer_id=streamer_id)
    return web.json_response(result)


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


async def _call_planner(prompt: str, mode: Optional[str], spacing_ms: int) -> Dict[str, Any]:
    if not PLANNER_URL:
        # Fallback stub when planner URL not provided: create a simple speech-only plan.
        return {
            "plan_id": uuid.uuid4().hex,
            "prompt": prompt,
            "mode": mode,
            "speech_spacing_ms": spacing_ms,
            "resolved_commands": [prompt],
        }

    params = {"resolve_aliases": "true", "speech_spacing_ms": spacing_ms}
    payload = {"prompt": prompt}
    if mode:
        payload["mode"] = mode

    async with ClientSession() as session:
        async with session.post(PLANNER_URL, params=params, json=payload) as resp:
            if resp.status >= 300:
                text = await resp.text()
                raise web.HTTPBadRequest(text=f"planner error ({resp.status}): {text}")
            data = await resp.json()
            return data


def _is_speech_command(cmd: str) -> bool:
    upper = cmd.upper()
    return upper.startswith("TTS") or upper.startswith("SAY") or "SPEECH" in upper


def _extract_speech(plan: Dict[str, Any]) -> List[str]:
    raw = plan.get("resolved_commands") or plan.get("commands") or []
    speech: List[str] = []
    for entry in raw:
        if isinstance(entry, str):
            if _is_speech_command(entry) or not speech:
                speech.append(entry)
        elif isinstance(entry, dict):
            val = entry.get("value") or entry.get("command")
            if isinstance(val, str) and (_is_speech_command(val) or not speech):
                speech.append(val)
    return speech


def _runner_commands_from_speech(speech: List[str], spacing_ms: int) -> List[Dict[str, Any]]:
    commands: List[Dict[str, Any]] = []
    for idx, cmd in enumerate(speech):
        commands.append({"delay_ms": 0 if idx == 0 else spacing_ms, "type": "tcp", "value": cmd})
    return commands


async def handle_create_plan(request: web.Request):
    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise web.HTTPBadRequest(text="prompt is required")
    mode = body.get("mode")
    spacing_ms = int(body.get("speech_spacing_ms") or PLAN_DEFAULT_SPACING_MS)

    plan_data = await _call_planner(prompt=prompt, mode=mode, spacing_ms=spacing_ms)
    plan_id = plan_data.get("plan_id") or uuid.uuid4().hex
    speech_commands = _extract_speech(plan_data) or ([prompt] if prompt else [])
    record = {
        "plan_id": plan_id,
        "prompt": prompt,
        "mode": mode,
        "speech_spacing_ms": spacing_ms,
        "speech_commands": speech_commands,
        "raw": plan_data,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    PLANS[plan_id] = record
    return web.json_response(record)


async def handle_get_plan(request: web.Request):
    plan_id = request.match_info.get("plan_id", "")
    plan = PLANS.get(plan_id)
    if not plan:
        raise web.HTTPNotFound(text="plan not found")
    return web.json_response(plan)


async def _call_runner(session_id: str, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
    payload = {"session_id": session_id, "commands": commands, "audio": []}
    async with ClientSession() as session:
        async with session.post(f"{RUNNER_URL}/scripts/execute", json=payload) as resp:
            if resp.status >= 300:
                text = await resp.text()
                raise web.HTTPBadRequest(text=f"runner error ({resp.status}): {text}")
            return await resp.json()


async def _poll_runner(session_id: str) -> Dict[str, Any]:
    deadline = asyncio.get_event_loop().time() + RUNNER_POLL_SECONDS
    async with ClientSession() as session:
        while True:
            async with session.get(f"{RUNNER_URL}/scripts/{session_id}") as resp:
                if resp.status == 404:
                    raise web.HTTPNotFound(text="runner session not found")
                data = await resp.json()
                state = data.get("state")
                if state in {"completed", "failed"}:
                    return data
            if asyncio.get_event_loop().time() > deadline:
                raise web.HTTPGatewayTimeout(text="runner polling timed out")
            await asyncio.sleep(1)


async def handle_run_plan(request: web.Request):
    ensure_auth(request)
    body = await request.json()
    plan_id = body.get("plan_id")
    prompt = (body.get("prompt") or "").strip()
    mode = body.get("mode")
    spacing_ms = int(body.get("speech_spacing_ms") or PLAN_DEFAULT_SPACING_MS)
    record_clip = bool(body.get("record", True))
    execute = bool(body.get("execute", True))
    streamer_id = body.get("streamer_id")

    plan = PLANS.get(plan_id or "")
    if not plan:
        plan_resp = await _call_planner(prompt=prompt, mode=mode, spacing_ms=spacing_ms)
        speech_commands = _extract_speech(plan_resp)
        plan_id = plan_resp.get("plan_id") or uuid.uuid4().hex
        plan = {
            "plan_id": plan_id,
            "prompt": prompt,
            "mode": mode,
            "speech_spacing_ms": spacing_ms,
            "speech_commands": speech_commands,
            "raw": plan_resp,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
        PLANS[plan_id] = plan

    speech_commands = plan.get("speech_commands") or ([prompt] if prompt else [])
    if not speech_commands:
        raise web.HTTPBadRequest(text="no speech commands available for this plan")

    commands = _runner_commands_from_speech(speech_commands, spacing_ms)
    session_id = body.get("run_id") or uuid.uuid4().hex

    if record_clip:
        label = _sanitize_label(body.get("label") or session_id)
        duration = body.get("duration")
        await _start_recorder(label=label, duration=duration, streamer_id=streamer_id)

    runner_status = None
    if execute:
        await _call_runner(session_id=session_id, commands=commands)
        runner_status = await _poll_runner(session_id=session_id)

    clip_file = STATE.get("mkv")
    if record_clip:
        try:
            await handle_stop(request)
        except Exception:
            pass

    clip_name = Path(clip_file).name if clip_file else None
    clip_url = f"/recordings/{clip_name}" if clip_name else None

    run_record = {
        "run_id": session_id,
        "plan_id": plan_id,
        "prompt": plan.get("prompt"),
        "mode": plan.get("mode"),
        "speech_spacing_ms": spacing_ms,
        "speech_commands": speech_commands,
        "runner_status": runner_status,
        "recording": {"file": clip_name, "download_url": clip_url} if clip_name else None,
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    RUNS[session_id] = run_record
    return web.json_response(run_record)


async def handle_get_run(request: web.Request):
    run_id = request.match_info.get("run_id", "")
    run = RUNS.get(run_id)
    if not run:
        raise web.HTTPNotFound(text="run not found")
    return web.json_response(run)

async def handle_options(_: web.Request):
    return web.Response(headers=CORS_HEADERS)


async def handle_root(request: web.Request):
    return web.json_response({"service": "gs-recorder-control", "active": STATE["proc"] is not None})


def make_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/", handle_root)
    app.router.add_get("/recordings/status", handle_status)
    app.router.add_post("/recordings/start", handle_start)
    app.router.add_post("/recordings/stop", handle_stop)
    app.router.add_get("/recordings/{filename}", handle_download)
    app.router.add_delete("/recordings/{filename}", handle_delete)
    app.router.add_post("/api/plans", handle_create_plan)
    app.router.add_get("/api/plans/{plan_id}", handle_get_plan)
    app.router.add_post("/api/runs", handle_run_plan)
    app.router.add_get("/api/runs/{run_id}", handle_get_run)
    app.router.add_route("OPTIONS", "/{path_info:.*}", handle_options)
    return app


def main():
    web.run_app(make_app(), host="0.0.0.0", port=RECORDER_CTRL_PORT)


if __name__ == "__main__":
    main()
