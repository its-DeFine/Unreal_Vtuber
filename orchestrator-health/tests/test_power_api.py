import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def power_app(monkeypatch, tmp_path):
    # Clear env to defaults for predictable tests
    monkeypatch.delenv("POWER_ALLOWED_IPS", raising=False)
    monkeypatch.delenv("VTUBER_ALLOWED_ADDRESSES", raising=False)
    monkeypatch.delenv("POWER_ALLOWED_PROJECT_PREFIXES", raising=False)
    monkeypatch.setenv("DOCKER_API_VERSION", "1.41")
    monkeypatch.setenv("POWER_STATE_FILE", str(tmp_path / "power_state.json"))
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    app = svc.app
    return app, svc


def test_allowed_ips_fallbacks_to_vtuber(monkeypatch):
    monkeypatch.setenv("VTUBER_ALLOWED_ADDRESSES", "1.1.1.1,2.2.2.2")
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    assert svc.POWER_ALLOWED_IPS == ["1.1.1.1", "2.2.2.2"]


def test_allowed_ips_uses_primary_if_set(monkeypatch):
    monkeypatch.setenv("POWER_ALLOWED_IPS", "3.3.3.3")
    monkeypatch.setenv("VTUBER_ALLOWED_ADDRESSES", "1.1.1.1")
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    assert svc.POWER_ALLOWED_IPS == ["3.3.3.3"]


def test_allowed_ips_empty_primary_falls_back_to_vtuber(monkeypatch):
    monkeypatch.setenv("POWER_ALLOWED_IPS", "")
    monkeypatch.setenv("VTUBER_ALLOWED_ADDRESSES", "1.1.1.1")
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    assert svc.POWER_ALLOWED_IPS == ["1.1.1.1"]


def test_power_state_roundtrip(power_app, monkeypatch):
    app, svc = power_app
    client = TestClient(app)
    monkeypatch.setattr(svc, "_sleep_all_containers", lambda *args, **kwargs: {})
    # no auth enforcement when allowlist empty
    resp = client.post("/power", json={"action": "sleep", "reason": "pytest"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "sleeping"
    resp = client.get("/power")
    assert resp.status_code == 200
    assert resp.json()["state"] == "sleeping"


def test_ip_allowlist_supports_cidrs(power_app):
    _app, svc = power_app
    assert svc._ip_in_allowlist("1.1.1.1", ["1.1.1.1"])
    assert svc._ip_in_allowlist("1.1.1.1", ["1.1.1.0/24"])
    assert not svc._ip_in_allowlist("2.2.2.2", ["1.1.1.0/24"])


def test_allowed_ips_file_overrides_env(monkeypatch, tmp_path):
    allow_file = tmp_path / "allowed.txt"
    allow_file.write_text("10.0.0.0/8\n")
    monkeypatch.setenv("POWER_ALLOWED_IPS_FILE", str(allow_file))
    monkeypatch.setenv("POWER_ALLOWED_IPS", "1.1.1.1")

    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    assert svc._get_power_allowed_ips() == ["10.0.0.0/8"]


def test_wake_with_awake_seconds_sets_awake_until(power_app, monkeypatch):
    app, svc = power_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_wake_all_containers", lambda *args, **kwargs: {})
    scheduled: dict[str, object] = {}

    def fake_schedule(seconds: int, reason: str) -> None:
        scheduled["seconds"] = seconds
        scheduled["reason"] = reason

    monkeypatch.setattr(svc, "_schedule_auto_sleep", fake_schedule)

    resp = client.post("/power", json={"action": "wake", "awake_seconds": 10, "reason": "pytest"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "awake"
    assert data["awake_until"] is not None
    assert scheduled["seconds"] == 10


def test_project_power_roundtrip(power_app, monkeypatch):
    app, svc = power_app
    client = TestClient(app)

    class DummyContainer:
        def __init__(self, name: str, status: str, *, labels: dict[str, str]):
            self.name = name
            self.status = status
            self.labels = labels
            self.attrs = {"State": {}}

        def reload(self) -> None:  # pragma: no cover - used by service code
            return None

    project = "vtuber-embody-0"
    containers = [
        DummyContainer(
            name="vtuber-embody-0-unreal-game",
            status="running",
            labels={"com.docker.compose.project": project, "com.docker.compose.service": "unreal-game"},
        )
    ]

    def fake_list(project_name=None):
        assert project_name == project
        return containers

    def fake_sleep(*, reason=None, project_name=None):
        assert project_name == project
        for c in containers:
            c.status = "exited"
        return {}

    def fake_wake(*, timeout_seconds=90, project_name=None):
        assert project_name == project
        for c in containers:
            c.status = "running"
        return {}

    monkeypatch.setattr(svc, "_list_project_containers", fake_list)
    monkeypatch.setattr(svc, "_sleep_all_containers", fake_sleep)
    monkeypatch.setattr(svc, "_wake_all_containers", fake_wake)

    resp = client.get(f"/power/projects/{project}")
    assert resp.status_code == 200
    assert resp.json()["state"] == "awake"
    assert resp.json()["project"] == project

    resp = client.post(f"/power/projects/{project}", json={"action": "sleep", "reason": "pytest"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "sleeping"
    assert resp.json()["project"] == project

    resp = client.post(f"/power/projects/{project}", json={"action": "wake", "reason": "pytest"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "awake"
    assert resp.json()["project"] == project


def test_project_power_rejects_non_vtuber_projects(power_app):
    app, _svc = power_app
    client = TestClient(app)
    resp = client.get("/power/projects/docker-default")
    assert resp.status_code == 403


@pytest.fixture
def cluster_app(monkeypatch, tmp_path):
    monkeypatch.delenv("POWER_ALLOWED_IPS", raising=False)
    monkeypatch.delenv("VTUBER_ALLOWED_ADDRESSES", raising=False)
    monkeypatch.delenv("POWER_ALLOWED_PROJECT_PREFIXES", raising=False)
    monkeypatch.setenv("DOCKER_API_VERSION", "1.41")
    monkeypatch.setenv("POWER_STATE_FILE", str(tmp_path / "power_state.json"))
    monkeypatch.setenv("EXPERIMENTAL_REMOTE_CLUSTER_CONTROL", "1")
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    app = svc.app
    return app, svc


@pytest.fixture
def ops_app(monkeypatch, tmp_path):
    monkeypatch.delenv("POWER_ALLOWED_IPS", raising=False)
    monkeypatch.delenv("VTUBER_ALLOWED_ADDRESSES", raising=False)
    monkeypatch.delenv("POWER_ALLOWED_PROJECT_PREFIXES", raising=False)
    monkeypatch.setenv("DOCKER_API_VERSION", "1.41")
    monkeypatch.setenv("POWER_STATE_FILE", str(tmp_path / "power_state.json"))
    monkeypatch.setenv("EXPERIMENTAL_REMOTE_OPS", "1")
    monkeypatch.setenv("POWER_ALLOWED_IPS", "127.0.0.1")
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    app = svc.app
    return app, svc


def test_ops_endpoints_disabled_by_default(power_app):
    app, _svc = power_app
    client = TestClient(app)

    resp = client.post("/ops/upgrade", json={"apply": False})
    assert resp.status_code == 404

    resp = client.post("/ops/rollout", json={})
    assert resp.status_code == 404


def test_ops_endpoints_require_allowlist(monkeypatch, tmp_path):
    monkeypatch.delenv("POWER_ALLOWED_IPS", raising=False)
    monkeypatch.delenv("VTUBER_ALLOWED_ADDRESSES", raising=False)
    monkeypatch.setenv("DOCKER_API_VERSION", "1.41")
    monkeypatch.setenv("POWER_STATE_FILE", str(tmp_path / "power_state.json"))
    monkeypatch.setenv("EXPERIMENTAL_REMOTE_OPS", "1")
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    client = TestClient(svc.app)
    resp = client.post("/ops/upgrade", json={"apply": False})
    assert resp.status_code == 403


def test_ops_upgrade_execs_script(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_require_auth_strict", lambda _req: None)

    class DummyResult:
        def __init__(self, exit_code: int = 0, stdout: str = "", stderr: str = ""):
            self.exit_code = exit_code
            self.output = (stdout.encode("utf-8"), stderr.encode("utf-8"))

    class DummyExecutor:
        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            if cmd[:3] == ["git", "-C", "/tmp/repo"]:
                if cmd[3:6] == ["rev-parse", "--is-inside-work-tree"]:
                    return DummyResult(stdout="true\n")
                if cmd[3:5] == ["status", "--porcelain"]:
                    return DummyResult(stdout="")
                if cmd[3:6] == ["rev-parse", "--short", "HEAD"]:
                    return DummyResult(stdout="abc123\n")
                if cmd[3:5] == ["fetch", "-q"]:
                    return DummyResult(stdout="")
                if cmd[3:6] == ["pull", "-q", "--ff-only"]:
                    return DummyResult(stdout="")
                return DummyResult(stdout="")
            raise AssertionError(f"unexpected cmd: {cmd}")

    monkeypatch.setattr(svc, "_cluster_executor_container", lambda: DummyExecutor())
    monkeypatch.setattr(svc, "_cluster_project_dir", lambda: "/tmp/repo")

    resp = client.post("/ops/upgrade", json={"apply": False})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ops_rollout_execs_script(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_require_auth_strict", lambda _req: None)
    monkeypatch.setattr(svc, "docker_client", type("DummyDocker", (), {"containers": type("C", (), {"list": lambda *args, **kwargs: []})()})())

    class DummyResult:
        exit_code = 0
        output = (b"loaded\n", b"")

    class DummyExecutor:
        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            assert cmd[0] == "bash"
            assert cmd[1].endswith("/tmp/repo/tools/encrypted-game-image/consume.sh")
            return DummyResult()

    monkeypatch.setattr(svc, "_cluster_executor_container", lambda: DummyExecutor())
    monkeypatch.setattr(svc, "_cluster_project_dir", lambda: "/tmp/repo")

    resp = client.post("/ops/rollout", json={"no_verify": True, "payments_api_url": "http://payments:8081"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

def test_cluster_deploy_disabled_by_default(power_app):
    app, _svc = power_app
    client = TestClient(app)
    resp = client.post("/cluster/deploy", json={"avatar_id": "embody-0", "slot": 0})
    assert resp.status_code == 404


def test_cluster_deploy_calls_compose(cluster_app, monkeypatch):
    app, svc = cluster_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_docker_port_conflicts", lambda _ports, **_kwargs: {})

    called: dict[str, object] = {}

    def fake_compose_instance(*, project: str, args: list[str], env: dict[str, str]):
        called["project"] = project
        called["args"] = args
        called["env"] = env
        return {"exit_code": 0, "stdout": "", "stderr": "", "cmd": []}

    monkeypatch.setattr(svc, "_cluster_compose_instance", fake_compose_instance)

    resp = client.post("/cluster/deploy", json={"avatar_id": "demo-0", "slot": 1, "gpu": "0"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["project"] == "vtuber-demo-0"
    assert called["project"] == "vtuber-demo-0"

    env = called["env"]
    assert env["VTUBER_SIGNALING_PUBLIC_PORT"] == "8081"
    assert env["VTUBER_RUNNER_PORT"] == "9878"
    assert env["VTUBER_RECORDER_PORT"] == "8890"
    assert env["VTUBER_GAME_TCP_PORT"] == "7778"
    assert env["NVIDIA_VISIBLE_DEVICES"] == "0"


def test_cluster_deploy_rejects_empty_slug(cluster_app):
    app, _svc = cluster_app
    client = TestClient(app)
    resp = client.post("/cluster/deploy", json={"avatar_id": "!!!", "slot": 0})
    assert resp.status_code == 400


def test_cluster_deploy_rejects_port_conflicts(cluster_app, monkeypatch):
    app, svc = cluster_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_docker_port_conflicts", lambda _ports, **_kwargs: {8081: "busy-container"})
    resp = client.post("/cluster/deploy", json={"avatar_id": "embody-0", "slot": 1})
    assert resp.status_code == 409
    assert "8081" in resp.json()["detail"]


def test_cluster_deploy_force_recreate(cluster_app, monkeypatch):
    app, svc = cluster_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_docker_port_conflicts", lambda _ports, **_kwargs: {})

    called: dict[str, object] = {}

    def fake_compose_instance(*, project: str, args: list[str], env: dict[str, str]):
        called["project"] = project
        called["args"] = args
        called["env"] = env
        return {"exit_code": 0, "stdout": "", "stderr": "", "cmd": []}

    monkeypatch.setattr(svc, "_cluster_compose_instance", fake_compose_instance)

    resp = client.post("/cluster/deploy", json={"avatar_id": "embody-0", "slot": 0, "recreate": True})
    assert resp.status_code == 200
    assert called["project"] == "vtuber-embody-0"
    assert called["args"] == ["up", "--force-recreate", "-d"]


def test_cluster_deploy_accepts_config_overrides(cluster_app, monkeypatch):
    app, svc = cluster_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_docker_port_conflicts", lambda _ports, **_kwargs: {})

    called: dict[str, object] = {}

    def fake_compose_instance(*, project: str, args: list[str], env: dict[str, str]):
        called["project"] = project
        called["args"] = args
        called["env"] = env
        return {"exit_code": 0, "stdout": "", "stderr": "", "cmd": []}

    monkeypatch.setattr(svc, "_cluster_compose_instance", fake_compose_instance)

    resp = client.post(
        "/cluster/deploy",
        json={
            "avatar_id": "embody-0",
            "slot": 0,
            "console_variables_file": "./pixel-streaming/config/ConsoleVariables.lowload.30fps.720p.ini",
            "game_user_settings_file": "./pixel-streaming/config/GameUserSettings.lowload.30fps.720p.ini",
            "embody_extra_args": "-ForceRes -ResX=1280 -ResY=720",
        },
    )
    assert resp.status_code == 200

    env = called["env"]
    assert env["VTUBER_CONSOLE_VARIABLES_FILE"].endswith("ConsoleVariables.lowload.30fps.720p.ini")
    assert env["VTUBER_GAME_USER_SETTINGS_FILE"].endswith("GameUserSettings.lowload.30fps.720p.ini")
    assert env["EMBODY_EXTRA_ARGS"] == "-ForceRes -ResX=1280 -ResY=720"


def test_cluster_deploy_rejects_invalid_override_paths(cluster_app):
    app, _svc = cluster_app
    client = TestClient(app)

    resp = client.post("/cluster/deploy", json={"avatar_id": "embody-0", "slot": 0, "console_variables_file": "/etc/passwd"})
    assert resp.status_code == 400

    resp = client.post(
        "/cluster/deploy",
        json={"avatar_id": "embody-0", "slot": 0, "console_variables_file": "./pixel-streaming/config/../secrets.ini"},
    )
    assert resp.status_code == 400

    resp = client.post(
        "/cluster/deploy",
        json={"avatar_id": "embody-0", "slot": 0, "console_variables_file": "./somewhere/else.ini"},
    )
    assert resp.status_code == 400


def test_cluster_down_requires_target(cluster_app):
    app, _svc = cluster_app
    client = TestClient(app)
    resp = client.post("/cluster/down", json={})
    assert resp.status_code == 422


def test_cluster_down_calls_compose(cluster_app, monkeypatch):
    app, svc = cluster_app
    client = TestClient(app)

    def fake_compose_instance(*, project: str, args: list[str], env: dict[str, str]):
        assert project == "vtuber-embody-0"
        assert args == ["down"]
        assert env == {"VTUBER_AVATAR_SLUG": "embody-0", "VTUBER_INSTANCE_PROJECT_NAME": "vtuber-embody-0"}
        return {"exit_code": 0, "stdout": "", "stderr": "", "cmd": []}

    monkeypatch.setattr(svc, "_cluster_compose_instance", fake_compose_instance)

    resp = client.post("/cluster/down", json={"project": "vtuber-embody-0"})
    assert resp.status_code == 200
    assert resp.json()["project"] == "vtuber-embody-0"


def test_cluster_down_with_avatar_id_calls_compose(cluster_app, monkeypatch):
    app, svc = cluster_app
    client = TestClient(app)

    def fake_compose_instance(*, project: str, args: list[str], env: dict[str, str]):
        assert project == "vtuber-embody-0"
        assert args == ["down"]
        assert env == {"VTUBER_AVATAR_SLUG": "embody-0", "VTUBER_INSTANCE_PROJECT_NAME": "vtuber-embody-0"}
        return {"exit_code": 0, "stdout": "", "stderr": "", "cmd": []}

    monkeypatch.setattr(svc, "_cluster_compose_instance", fake_compose_instance)

    resp = client.post("/cluster/down", json={"avatar_id": "Embody-0"})
    assert resp.status_code == 200
    assert resp.json()["project"] == "vtuber-embody-0"


def test_docker_port_conflicts_ignores_target_project(cluster_app, monkeypatch):
    _app, svc = cluster_app

    class DummyContainer:
        def __init__(self, name: str, project: str, host_port: int):
            self.name = name
            self.attrs = {
                "Config": {"Labels": {"com.docker.compose.project": project}},
                "NetworkSettings": {"Ports": {"80/tcp": [{"HostPort": str(host_port)}]}},
            }

        def reload(self) -> None:  # pragma: no cover - exercised by service code
            return None

    class DummyDocker:
        def __init__(self, containers):
            self._containers = containers

            class _Containers:
                def __init__(self, parent):
                    self._parent = parent

                def list(self, all: bool = False, **_kwargs):  # noqa: A002 - match docker SDK signature
                    return self._parent._containers

            self.containers = _Containers(self)

    want = {8081}
    same_project = DummyContainer("same", "vtuber-embody-0", 8081)
    other_project = DummyContainer("other", "vtuber-other", 8081)

    monkeypatch.setattr(svc, "docker_client", DummyDocker([same_project]))
    assert svc._docker_port_conflicts(want, ignore_project="vtuber-embody-0") == {}
    assert svc._docker_port_conflicts(want, ignore_project=None) == {8081: "same"}

    monkeypatch.setattr(svc, "docker_client", DummyDocker([same_project, other_project]))
    assert svc._docker_port_conflicts(want, ignore_project="vtuber-embody-0") == {8081: "other"}


def test_meta_endpoint_reports_git_and_containers(power_app, monkeypatch):
    app, svc = power_app
    client = TestClient(app)

    class DummyExecResult:
        def __init__(self, exit_code: int, stdout: str):
            self.exit_code = exit_code
            self.output = (stdout.encode("utf-8"), b"")

    class DummyExecutor:
        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002 - match docker SDK signature
            assert cmd[0] == "cat"
            path = cmd[1]
            if path.endswith("/.git/HEAD"):
                return DummyExecResult(0, "ref: refs/heads/main\n")
            if path.endswith("/.git/refs/heads/main"):
                return DummyExecResult(0, "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n")
            return DummyExecResult(1, "")

    class DummyContainer:
        def __init__(self):
            self.name = "vtuber-unreal-game"
            self.status = "running"
            self.attrs = {
                "Config": {
                    "Labels": {
                        "com.docker.compose.project": "unreal_vtuber",
                        "com.docker.compose.service": "unreal-game",
                    },
                    "Image": "ghcr.io/its-define/unreal_vtuber/embody-ue-ps:latest",
                }
            }

            class _Image:
                id = "sha256:abc123"

            self.image = _Image()

        def reload(self) -> None:  # pragma: no cover - used by service code
            return None

    class DummyDocker:
        def __init__(self, executor, containers):
            self._executor = executor
            self._containers = containers

            class _Containers:
                def __init__(self, parent):
                    self._parent = parent

                def list(self, all: bool = False, **_kwargs):  # noqa: A002 - match docker SDK signature
                    assert all is True
                    return self._parent._containers

                def get(self, name: str):  # noqa: ANN001 - match docker SDK signature
                    if name == "vtuber-orchestrator-edge-rotator":
                        return self._parent._executor
                    raise KeyError(name)

            self.containers = _Containers(self)

    monkeypatch.setattr(svc, "docker_client", DummyDocker(DummyExecutor(), [DummyContainer()]))

    resp = client.get("/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert data["git"]["sha"].startswith("deadbeef")
    assert data["containers"][0]["name"] == "vtuber-unreal-game"
    assert data["containers"][0]["image_id"] == "sha256:abc123"
