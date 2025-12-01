import importlib
import pathlib
import sys

import pytest
from aiohttp.test_utils import TestClient, TestServer


# Ensure repo root on sys.path for imports
sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))


@pytest.fixture
def control_server(tmp_path, monkeypatch):
    # Point recorder output to a temp dir for isolation
    monkeypatch.setenv("RECORDER_OUTPUT_DIR", str(tmp_path))
    # Clear any allowlist to simplify auth during tests
    monkeypatch.setenv("VTUBER_ALLOWED_ADDRESSES", "")
    # Reload module to pick up env changes
    import tools.recorder.control_server as cs

    importlib.reload(cs)
    return cs


@pytest.mark.asyncio
async def test_download_allows_file(control_server, tmp_path):
    target = tmp_path / "clip.mkv"
    target.write_text("dummy")
    app = control_server.make_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        resp = await client.get(f"/recordings/{target.name}")
        assert resp.status == 200
        body = await resp.read()
        assert body == b"dummy"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_download_blocks_traversal(control_server):
    app = control_server.make_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        resp = await client.get("/recordings/../etc/passwd")
        assert resp.status == 403
    finally:
        await client.close()


def test_label_sanitization(control_server):
    bad = "../../evil name.txt"
    cleaned = control_server._sanitize_label(bad)  # noqa: SLF001 - internal helper
    assert cleaned == "----evil-name-txt"
