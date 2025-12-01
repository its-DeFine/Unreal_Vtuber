import importlib
import pytest
from aiohttp.test_utils import TestClient, TestServer


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
        # should not serve parent path; either 403 (forbidden) or 404 (not found)
        assert resp.status in {403, 404}
    finally:
        await client.close()


def test_label_sanitization(control_server):
    bad = "../../evil name.txt"
    cleaned = control_server._sanitize_label(bad)  # noqa: SLF001 - internal helper
    assert "evil-name-txt" in cleaned
    assert ".." not in cleaned
