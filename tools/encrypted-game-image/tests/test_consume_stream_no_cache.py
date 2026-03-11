#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONSUME = REPO_ROOT / "tools" / "encrypted-game-image" / "consume.sh"
RESCUE_ENV = "RESUME_DOWNLOAD_ALLOW_STALE_COMPLETE_CACHE_ON_PROBE_FAILURE"
IMAGE_REF = "ghcr.io/test/embody:enc-v1"
LEASE_ID = "lease-stream-no-cache"
AGE_SECRET = "AGE-SECRET-KEY-1TESTKEYTESTKEYTESTKEYTESTKEYTESTKEYTESTKEY\n"
ARTIFACT_BLOB = b"age-encryption.org/v1\nstreaming-test-payload\n"


class LeaseAndArtifactHandler(BaseHTTPRequestHandler):
    server_version = "TestHTTP/1.0"
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/licenses/lease":
            self.send_error(404)
            return

        body = json.dumps(
            {
                "lease_id": LEASE_ID,
                "secret_b64": base64.b64encode(AGE_SECRET.encode("utf-8")).decode("ascii"),
                "artifact_url": f"http://127.0.0.1:{self.server.server_address[1]}/artifact.age",
                "lease_seconds": 900,
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/artifact.age":
            self.send_error(404)
            return

        if self.headers.get("Range"):
            self.send_response(400)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Length", str(len(ARTIFACT_BLOB)))
        self.end_headers()
        self.wfile.write(ARTIFACT_BLOB)
        self.wfile.flush()

    def log_message(self, _format: str, *_args) -> None:
        return


class ConsumeStreamNoCacheTest(unittest.TestCase):
    def _write_executable(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def _make_stub_tools(self, bin_dir: Path) -> None:
        self._write_executable(
            bin_dir / "age",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "cat\n",
        )
        self._write_executable(
            bin_dir / "zstd",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "cat\n",
        )
        self._write_executable(
            bin_dir / "docker",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "[[ \"${1:-}\" == \"load\" ]] || exit 2\n"
            "python3 -c 'import os, sys; from pathlib import Path; "
            "data = sys.stdin.buffer.read(); "
            "Path(os.environ[\"DOCKER_MARKER_PATH\"]).write_text(str(len(data)), encoding=\"utf-8\"); "
            "sys.stdout.write(\"Loaded image: stub\\n\"); "
            "raise SystemExit(0 if data else 1)'\n",
        )

    def _run_consume(
        self, *, rescue: bool
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object] | None, int | None]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            stub_bin = tmp / "bin"
            stub_bin.mkdir()
            self._make_stub_tools(stub_bin)

            rollout_state = tmp / "rollout_state.json"
            fallback_state = tmp / "rollout_state_fallback.json"
            work_dir = tmp / "rollout-work" / "job-stream"
            docker_marker = tmp / "docker.bytes"

            server = ThreadingHTTPServer(("127.0.0.1", 0), LeaseAndArtifactHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base_url = f"http://127.0.0.1:{server.server_address[1]}"
                env = dict(os.environ)
                env["PATH"] = f"{stub_bin}:{env['PATH']}"
                env["TERM"] = "dumb"
                env["DOCKER_MARKER_PATH"] = str(docker_marker)
                if rescue:
                    env[RESCUE_ENV] = "1"

                cmd = [
                    "bash",
                    str(CONSUME),
                    "--payments-api-url",
                    base_url,
                    "--image-ref",
                    IMAGE_REF,
                    "--orch-token",
                    "test-token",
                    "--rollout-state-file",
                    str(rollout_state),
                    "--rollout-state-fallback",
                    str(fallback_state),
                    "--rollout-work-dir",
                    str(work_dir),
                    "--rollout-job-id",
                    "job-stream",
                    "--stream-no-cache",
                    "--no-heartbeat",
                    "--no-color",
                    "--no-fx",
                ]
                proc = subprocess.run(cmd, check=False, capture_output=True, text=True, env=env)
                state_data = None
                if rollout_state.exists():
                    state_data = json.loads(rollout_state.read_text(encoding="utf-8"))
                docker_bytes = None
                if docker_marker.exists():
                    docker_bytes = int(docker_marker.read_text(encoding="utf-8"))
                return proc, state_data, docker_bytes
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_probe_failure_aborts_by_default(self) -> None:
        proc, rollout_state, docker_marker = self._run_consume(rescue=False)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIsNone(docker_marker)
        self.assertIsNotNone(rollout_state)
        assert rollout_state is not None
        self.assertEqual(rollout_state["status"], "error")
        self.assertEqual(rollout_state["phase"], "downloading")
        self.assertEqual(rollout_state["detail"], "artifact header probe failed for stream/no-cache mode")

    def test_probe_failure_continues_when_rescue_env_enabled(self) -> None:
        proc, rollout_state, docker_marker = self._run_consume(rescue=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIsNotNone(docker_marker)
        assert docker_marker is not None
        self.assertGreater(docker_marker, 0)
        self.assertIn("Loaded encrypted image via lease_id=lease-stream-no-cache", proc.stdout)
        self.assertIn(
            "continuing because RESUME_DOWNLOAD_ALLOW_STALE_COMPLETE_CACHE_ON_PROBE_FAILURE=1 is set",
            proc.stderr,
        )
        self.assertIsNotNone(rollout_state)
        assert rollout_state is not None
        self.assertEqual(rollout_state["status"], "staged")
        self.assertEqual(rollout_state["phase"], "staged")
        self.assertEqual(rollout_state["detail"], "Encrypted artifact streamed and image loaded into docker")


if __name__ == "__main__":
    unittest.main()
