#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import socketserver
import subprocess
import tempfile
import threading
import unittest
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER = REPO_ROOT / "tools" / "encrypted-game-image" / "resume_download.py"


@dataclass
class ArtifactServerState:
    blob: bytes
    fail_after: int
    etag: str = '"test-etag"'
    last_modified: str = "Sat, 07 Mar 2026 12:00:00 GMT"
    fail_next_full_get: bool = True
    lock: threading.Lock = field(default_factory=threading.Lock)


class ArtifactHandler(BaseHTTPRequestHandler):
    server_version = "ArtifactHTTP/1.0"
    protocol_version = "HTTP/1.1"
    state: ClassVar[ArtifactServerState]

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/artifact.age":
            self.send_error(404)
            return

        blob = self.state.blob
        total = len(blob)
        range_header = self.headers.get("Range")

        if range_header:
            if not range_header.startswith("bytes="):
                self.send_error(400)
                return
            spec = range_header.split("=", 1)[1]
            start_text, _, end_text = spec.partition("-")
            start = int(start_text or "0")
            end = int(end_text) if end_text else total - 1
            if start >= total:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{total}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            end = min(end, total - 1)
            payload = blob[start : end + 1]
            self.send_response(206)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("ETag", self.state.etag)
            self.send_header("Last-Modified", self.state.last_modified)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
            self.end_headers()
            self.wfile.write(payload)
            self.wfile.flush()
            return

        should_fail = False
        with self.state.lock:
            if self.state.fail_next_full_get:
                self.state.fail_next_full_get = False
                should_fail = True

        self.send_response(200)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("ETag", self.state.etag)
        self.send_header("Last-Modified", self.state.last_modified)
        self.send_header("Content-Length", str(total))
        self.end_headers()

        if should_fail:
            self.wfile.write(blob[: self.state.fail_after])
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_WR)
            self.connection.close()
            return

        self.wfile.write(blob)
        self.wfile.flush()

    def log_message(self, _format: str, *_args) -> None:
        return


class ResumeDownloadTest(unittest.TestCase):
    def test_resume_after_interruption_updates_state(self) -> None:
        blob = b"age-encryption.org/v1\n" + os.urandom(256 * 1024)
        state = ArtifactServerState(blob=blob, fail_after=16384)
        ArtifactHandler.state = state

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            rollout_state = tmp / "rollout_state.json"
            fallback_state = tmp / "rollout_state_fallback.json"
            cache_root = tmp / "cache"
            cache_fallback = tmp / "cache-fallback"
            probe_prefix = tmp / "probe.prefix"
            probe_headers = tmp / "probe.headers"
            probe_err = tmp / "probe.err"
            download_err = tmp / "download.err"
            work_dir = tmp / "rollout-work" / "job-xyz"
            work_dir.mkdir(parents=True, exist_ok=True)
            rollout_state.write_text(
                json.dumps(
                    {
                        "job_id": "job-xyz",
                        "status": "queued",
                        "history": [{"status": "queued", "at": "2026-03-07T09:59:00+00:00"}],
                    }
                )
            )

            server = ThreadingHTTPServer(("127.0.0.1", 0), ArtifactHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/artifact.age"
                cmd = [
                    "python3",
                    str(HELPER),
                    "--url",
                    url,
                    "--image-ref",
                    "ghcr.io/test/embody:enc-v1",
                    "--payments-api-url",
                    "http://payments:8081",
                    "--lease-id",
                    "lease-test",
                    "--state-file",
                    str(rollout_state),
                    "--state-fallback",
                    str(fallback_state),
                    "--cache-root-primary",
                    str(cache_root),
                    "--cache-root-fallback",
                    str(cache_fallback),
                    "--probe-prefix-path",
                    str(probe_prefix),
                    "--probe-headers-path",
                    str(probe_headers),
                    "--probe-stderr-path",
                    str(probe_err),
                    "--download-stderr-path",
                    str(download_err),
                    "--job-id",
                    "job-xyz",
                    "--work-dir",
                    str(work_dir),
                ]

                first = subprocess.run(cmd, check=False, capture_output=True, text=True)
                self.assertNotEqual(first.returncode, 0, first.stdout + first.stderr)

                cache_dirs = [path for path in cache_root.iterdir() if path.is_dir()]
                self.assertEqual(len(cache_dirs), 1)
                partial_path = cache_dirs[0] / "artifact.age.part"
                self.assertTrue(partial_path.exists())
                partial_size = partial_path.stat().st_size
                self.assertGreater(partial_size, 0)
                self.assertLess(partial_size, len(blob))

                partial_state = json.loads(rollout_state.read_text())
                self.assertEqual(partial_state["job_id"], "job-xyz")
                self.assertEqual(partial_state["history"][0]["status"], "queued")
                self.assertEqual(partial_state["status"], "error")
                self.assertEqual(partial_state["phase"], "downloading")
                self.assertEqual(partial_state["artifact_total_bytes"], len(blob))
                self.assertGreater(partial_state["artifact_downloaded_bytes"], 0)
                self.assertLess(partial_state["artifact_downloaded_bytes"], len(blob))
                self.assertEqual(partial_state["downloaded_bytes"], partial_state["artifact_downloaded_bytes"])
                self.assertEqual(partial_state["progress_percent"], partial_state["artifact_download_percent"])
                self.assertTrue(partial_state["can_resume"])
                self.assertEqual(partial_state["work_dir"], str(work_dir))

                second = subprocess.run(cmd, check=False, capture_output=True, text=True)
                self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
                payload = json.loads(second.stdout)

                artifact_path = Path(payload["artifact_path"])
                self.assertTrue(artifact_path.exists())
                self.assertEqual(artifact_path.read_bytes(), blob)
                self.assertEqual(payload["artifact_total_bytes"], len(blob))
                self.assertEqual(payload["artifact_downloaded_bytes"], len(blob))
                self.assertEqual(payload["artifact_download_percent"], 100.0)
                self.assertTrue(payload["artifact_resumed"])
                self.assertGreater(payload["artifact_resume_from_bytes"], 0)
                self.assertEqual(payload["artifact_download_action"], "resumed")

                final_state = json.loads(rollout_state.read_text())
                self.assertEqual(final_state["job_id"], "job-xyz")
                self.assertEqual(final_state["status"], "downloaded")
                self.assertEqual(final_state["phase"], "downloaded")
                self.assertEqual(final_state["artifact_total_bytes"], len(blob))
                self.assertEqual(final_state["artifact_downloaded_bytes"], len(blob))
                self.assertEqual(final_state["artifact_download_percent"], 100.0)
                self.assertEqual(final_state["downloaded_bytes"], len(blob))
                self.assertEqual(final_state["progress_percent"], 100.0)
                self.assertTrue(final_state["can_resume"])
                self.assertTrue(final_state["artifact_resumed"])
                self.assertGreater(final_state["artifact_resume_from_bytes"], 0)
                self.assertEqual(final_state["history"][0]["status"], "queued")
                self.assertEqual(final_state["history"][-1]["status"], "downloaded")
                self.assertFalse(partial_path.exists())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
