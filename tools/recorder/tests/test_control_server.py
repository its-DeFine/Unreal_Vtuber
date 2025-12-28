import importlib
import hashlib
import pytest
from aiohttp import web
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


@pytest.mark.asyncio
async def test_upload_puts_file_to_url(control_server, tmp_path):
    payload = b"dummy"
    target = tmp_path / "clip.mkv"
    target.write_bytes(payload)

    received: dict = {}

    async def handle_put(request: web.Request) -> web.Response:
        received["body"] = await request.read()
        return web.Response(status=200)

    upload_app = web.Application()
    upload_app.router.add_put("/upload", handle_put)
    upload_server = TestServer(upload_app)
    upload_client = TestClient(upload_server)
    await upload_client.start_server()

    app = control_server.make_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        upload_url = str(upload_client.make_url("/upload"))
        resp = await client.post(
            f"/recordings/{target.name}/upload",
            json={"upload_url": upload_url},
        )
        assert resp.status == 200
        body = await resp.json()
        assert body["uploaded"] is True
        assert body["file"] == target.name
        assert body["bytes"] == len(payload)
        assert body["sha256"] == f"sha256:{hashlib.sha256(payload).hexdigest()}"
        assert received["body"] == payload
    finally:
        await client.close()
        await upload_client.close()
