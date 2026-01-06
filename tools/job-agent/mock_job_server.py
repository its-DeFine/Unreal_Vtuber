from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

DEFAULT_PORT = 5001
JOB_PATH = Path(__file__).resolve().parent / "sample_job.json"
UPLOAD_DIR = Path(os.environ.get("MOCK_UPLOAD_DIR", "./mock_uploads")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class JobState:
    job: Dict[str, Any]
    leased: bool
    completed: Dict[str, Any] | None
    failed: Dict[str, Any] | None

    def __init__(self, job: Dict[str, Any]):
        self.job = job
        self.leased = False
        self.completed = None
        self.failed = None


def load_job() -> Dict[str, Any]:
    job_path = Path(os.environ.get("MOCK_JOB_PATH", str(JOB_PATH)))
    try:
        return json.loads(job_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Failed to load job JSON: {job_path}: {exc}")


STATE = JobState(load_job())


class Handler(BaseHTTPRequestHandler):
    server_version = "mock-job-server/1.0"

    def _read_json(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self.end_headers()

    def _match(self, pattern: str) -> re.Match[str] | None:
        return re.match(pattern, self.path)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/status":
            payload = {
                "job_id": STATE.job.get("job_id"),
                "leased": STATE.leased,
                "completed": STATE.completed,
                "failed": STATE.failed,
            }
            self._send_json(200, payload)
            return
        self._send_json(200, {"service": "mock-job-server"})

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/api/jobs/record/claim":
            if STATE.leased or STATE.completed or STATE.failed:
                self._send_empty(204)
                return
            STATE.leased = True
            self._send_json(200, STATE.job)
            return

        match = self._match(r"^/api/jobs/record/([^/]+)/upload-url$")
        if match:
            job_id = match.group(1)
            payload = self._read_json()
            filename = str(payload.get("filename") or "").strip()
            if not filename:
                self._send_json(400, {"error": "filename required"})
                return
            host = os.environ.get("MOCK_JOB_PUBLIC_HOST") or self.headers.get("Host", f"localhost:{DEFAULT_PORT}")
            upload_url = f"http://{host}/uploads/{job_id}/{filename}"
            self._send_json(200, {"upload_url": upload_url, "artifact_uri": f"mock://{job_id}/{filename}"})
            return

        match = self._match(r"^/api/jobs/record/([^/]+)/complete$")
        if match:
            STATE.completed = self._read_json()
            self._send_json(200, {"status": "ok"})
            return

        match = self._match(r"^/api/jobs/record/([^/]+)/fail$")
        if match:
            STATE.failed = self._read_json()
            self._send_json(200, {"status": "ok"})
            return

        self._send_json(404, {"error": "not found"})

    def do_PUT(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        match = self._match(r"^/uploads/([^/]+)/(.+)$")
        if not match:
            self._send_json(404, {"error": "not found"})
            return
        job_id = match.group(1)
        filename = match.group(2)
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        data = self.rfile.read(length) if length > 0 else b""
        target = UPLOAD_DIR / job_id / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self._send_json(200, {"uploaded": True, "bytes": len(data)})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return


def main() -> None:
    host = os.environ.get("MOCK_JOB_HOST", "0.0.0.0")
    port = int(os.environ.get("MOCK_JOB_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"mock job server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
