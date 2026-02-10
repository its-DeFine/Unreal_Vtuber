import json
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
    # Avoid touching the real Docker daemon in tests unless explicitly enabled by a fixture.
    monkeypatch.setenv("EXPERIMENTAL_REMOTE_CLUSTER_CONTROL", "0")
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


def test_wake_does_not_500_when_wake_all_containers_errors(power_app, monkeypatch):
    app, svc = power_app
    client = TestClient(app)

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(svc, "_wake_all_containers", boom)

    resp = client.post("/power", json={"action": "wake", "reason": "pytest"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "awake"


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


def test_ops_endpoints_require_allowlist_by_default(power_app):
    app, _svc = power_app
    client = TestClient(app)

    resp = client.post("/ops/upgrade", json={"apply": False})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "POWER_ALLOWED_IPS must be set for remote ops"

    resp = client.post("/ops/rollout", json={})
    assert resp.status_code == 403

    resp = client.post("/ops/pull-image", json={"image": "ghcr.io/example/image:latest"})
    assert resp.status_code == 403


def test_ops_endpoints_can_be_disabled(monkeypatch, tmp_path):
    monkeypatch.delenv("POWER_ALLOWED_IPS", raising=False)
    monkeypatch.delenv("VTUBER_ALLOWED_ADDRESSES", raising=False)
    monkeypatch.delenv("POWER_ALLOWED_PROJECT_PREFIXES", raising=False)
    monkeypatch.setenv("DOCKER_API_VERSION", "1.41")
    monkeypatch.setenv("POWER_STATE_FILE", str(tmp_path / "power_state.json"))
    monkeypatch.setenv("EXPERIMENTAL_REMOTE_OPS", "0")
    import orchestrator_health.remote_health_service as svc

    importlib.reload(svc)
    client = TestClient(svc.app)
    resp = client.post("/ops/upgrade", json={"apply": False})
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
            git_prefix_a = ["git", "-C", "/tmp/repo"]
            git_prefix_b = ["git", "-c", "safe.directory=/tmp/repo", "-C", "/tmp/repo"]

            if cmd[: len(git_prefix_a)] == git_prefix_a:
                git_cmd = cmd[len(git_prefix_a) :]
            elif cmd[: len(git_prefix_b)] == git_prefix_b:
                git_cmd = cmd[len(git_prefix_b) :]
            else:
                raise AssertionError(f"unexpected cmd: {cmd}")

            if git_cmd[:3] == ["rev-parse", "--is-inside-work-tree"]:
                    return DummyResult(stdout="true\n")
            if git_cmd[:2] == ["status", "--porcelain"]:
                    return DummyResult(stdout="")
            if git_cmd[:3] == ["rev-parse", "--short", "HEAD"]:
                    return DummyResult(stdout="abc123\n")
            if git_cmd[:2] == ["fetch", "-q"]:
                    return DummyResult(stdout="")
            if git_cmd[:3] == ["pull", "-q", "--ff-only"]:
                    return DummyResult(stdout="")
            return DummyResult(stdout="")

    monkeypatch.setattr(svc, "_cluster_executor_container", lambda: DummyExecutor())
    monkeypatch.setattr(svc, "_cluster_project_dir", lambda: "/tmp/repo")

    resp = client.post("/ops/upgrade", json={"apply": False})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ops_upgrade_rejects_ref_with_whitespace(ops_app):
    app, _svc = ops_app
    client = TestClient(app)
    resp = client.post("/ops/upgrade", json={"ref": "bad ref"})
    assert resp.status_code == 422


def test_ops_upgrade_rejects_invalid_service_image_tag(ops_app):
    app, _svc = ops_app
    client = TestClient(app)
    resp = client.post("/ops/upgrade", json={"service_image_tag": "bad tag"})
    assert resp.status_code == 422


def test_ops_upgrade_checkout_ref_execs_script(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_require_auth_strict", lambda _req: None)

    class DummyResult:
        def __init__(self, exit_code: int = 0, stdout: str = "", stderr: str = ""):
            self.exit_code = exit_code
            self.output = (stdout.encode("utf-8"), stderr.encode("utf-8"))

    class DummyExecutor:
        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            git_prefix_a = ["git", "-C", "/tmp/repo"]
            git_prefix_b = ["git", "-c", "safe.directory=/tmp/repo", "-C", "/tmp/repo"]

            if cmd[: len(git_prefix_a)] == git_prefix_a:
                git_cmd = cmd[len(git_prefix_a) :]
            elif cmd[: len(git_prefix_b)] == git_prefix_b:
                git_cmd = cmd[len(git_prefix_b) :]
            else:
                raise AssertionError(f"unexpected cmd: {cmd}")

            if git_cmd[:3] == ["rev-parse", "--is-inside-work-tree"]:
                return DummyResult(stdout="true\n")
            if git_cmd[:2] == ["status", "--porcelain"]:
                return DummyResult(stdout="")
            if git_cmd[:3] == ["rev-parse", "--short", "HEAD"]:
                return DummyResult(stdout="abc123\n")
            if git_cmd[:4] == ["fetch", "-q", "--tags", "origin"]:
                return DummyResult(stdout="")
            if git_cmd[:4] == ["show-ref", "--quiet", "--verify", "refs/tags/v1.2.3"]:
                return DummyResult(exit_code=0)
            if git_cmd[:4] == ["show-ref", "--quiet", "--verify", "refs/remotes/origin/v1.2.3"]:
                return DummyResult(exit_code=1)
            if git_cmd[:4] == ["checkout", "-q", "--detach", "v1.2.3"]:
                return DummyResult(stdout="")
            return DummyResult(stdout="")

    monkeypatch.setattr(svc, "_cluster_executor_container", lambda: DummyExecutor())
    monkeypatch.setattr(svc, "_cluster_project_dir", lambda: "/tmp/repo")

    resp = client.post("/ops/upgrade", json={"ref": "v1.2.3", "apply": False})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ops_upgrade_sleeping_apply_uses_no_start(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_require_auth_strict", lambda _req: None)
    monkeypatch.setattr(svc, "_detect_compose_identity", lambda: None)
    monkeypatch.setattr(svc, "_read_power_state", lambda: svc.PowerState(state="sleeping"))

    class DummyResult:
        def __init__(self, exit_code: int = 0, stdout: str = "", stderr: str = ""):
            self.exit_code = exit_code
            self.output = (stdout.encode("utf-8"), stderr.encode("utf-8"))

    class DummyContainer:
        def __init__(self, service: str):
            self.labels = {"com.docker.compose.service": service}

    monkeypatch.setattr(
        svc,
        "_list_project_containers",
        lambda _project=None: [  # noqa: ARG005
            DummyContainer("turn-server"),
            DummyContainer("vtuber-auto-updater"),
            DummyContainer("orchestrator-registration"),
            DummyContainer("orchestrator-health"),
            DummyContainer("orchestrator-edge-rotator"),
        ],
    )

    class DummyExecutor:
        def __init__(self):
            self.commands = []

        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            self.commands.append(cmd)
            git_prefix_a = ["git", "-C", "/tmp/repo"]
            git_prefix_b = ["git", "-c", "safe.directory=/tmp/repo", "-C", "/tmp/repo"]

            if cmd[: len(git_prefix_a)] == git_prefix_a:
                git_cmd = cmd[len(git_prefix_a) :]
            elif cmd[: len(git_prefix_b)] == git_prefix_b:
                git_cmd = cmd[len(git_prefix_b) :]
            else:
                git_cmd = None

            if git_cmd is not None:
                if git_cmd[:3] == ["rev-parse", "--is-inside-work-tree"]:
                    return DummyResult(stdout="true\n")
                if git_cmd[:2] == ["status", "--porcelain"]:
                    return DummyResult(stdout="")
                if git_cmd[:3] == ["rev-parse", "--short", "HEAD"]:
                    return DummyResult(stdout="abc123\n")
                if git_cmd[:2] == ["fetch", "-q"]:
                    return DummyResult(stdout="")
                if git_cmd[:3] == ["pull", "-q", "--ff-only"]:
                    return DummyResult(stdout="")
                return DummyResult(stdout="")

            if cmd[:2] == ["docker", "compose"]:
                if "up" in cmd:
                    assert "--no-start" in cmd
                    assert "-d" not in cmd
                return DummyResult(stdout="")

            raise AssertionError(f"unexpected cmd: {cmd}")

    executor = DummyExecutor()
    monkeypatch.setattr(svc, "_cluster_executor_container", lambda: executor)
    monkeypatch.setattr(svc, "_cluster_project_dir", lambda: "/tmp/repo")

    resp = client.post("/ops/upgrade", json={"apply": True})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ops_upgrade_awake_apply_skips_port_binding_services_when_game_not_running(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_require_auth_strict", lambda _req: None)
    monkeypatch.setattr(svc, "_detect_compose_identity", lambda: None)
    monkeypatch.setattr(svc, "_read_power_state", lambda: svc.PowerState(state="awake"))

    class DummyResult:
        def __init__(self, exit_code: int = 0, stdout: str = "", stderr: str = ""):
            self.exit_code = exit_code
            self.output = (stdout.encode("utf-8"), stderr.encode("utf-8"))

    class DummyContainer:
        def __init__(self, service: str, *, status: str = "created"):
            self.labels = {"com.docker.compose.service": service}
            self.status = status

        def reload(self) -> None:  # pragma: no cover - used by service code
            return None

    # Simulate a cluster-mode box:
    # - base stack is "awake" but unreal-game is not running (created)
    # - if we tried to `up -d unreal-signaling` we'd hit port conflicts with the instance stack
    monkeypatch.setattr(
        svc,
        "_list_project_containers",
        lambda _project=None: [  # noqa: ARG005
            DummyContainer("turn-server", status="running"),
            DummyContainer("unreal-signaling", status="created"),
            DummyContainer("unreal-game", status="created"),
            DummyContainer("vtuber-script-runner", status="created"),
            DummyContainer("recorder-control", status="created"),
            DummyContainer("vtuber-watchdog", status="running"),
            DummyContainer("vtuber-auto-updater", status="running"),
            DummyContainer("orchestrator-registration", status="exited"),
            DummyContainer("orchestrator-health", status="running"),
            DummyContainer("orchestrator-edge-rotator", status="running"),
        ],
    )

    class DummyExecutor:
        def __init__(self):
            self.commands = []

        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            self.commands.append(cmd)
            git_prefix_a = ["git", "-C", "/tmp/repo"]
            git_prefix_b = ["git", "-c", "safe.directory=/tmp/repo", "-C", "/tmp/repo"]

            if cmd[: len(git_prefix_a)] == git_prefix_a:
                git_cmd = cmd[len(git_prefix_a) :]
            elif cmd[: len(git_prefix_b)] == git_prefix_b:
                git_cmd = cmd[len(git_prefix_b) :]
            else:
                git_cmd = None

            if git_cmd is not None:
                if git_cmd[:3] == ["rev-parse", "--is-inside-work-tree"]:
                    return DummyResult(stdout="true\n")
                if git_cmd[:2] == ["status", "--porcelain"]:
                    return DummyResult(stdout="")
                if git_cmd[:3] == ["rev-parse", "--short", "HEAD"]:
                    return DummyResult(stdout="abc123\n")
                if git_cmd[:2] == ["fetch", "-q"]:
                    return DummyResult(stdout="")
                if git_cmd[:3] == ["pull", "-q", "--ff-only"]:
                    return DummyResult(stdout="")
                return DummyResult(stdout="")

            if cmd[:2] == ["docker", "compose"]:
                if "up" in cmd:
                    assert "-d" in cmd
                    assert "--no-start" not in cmd
                    # Must NOT try to start base port-binding services.
                    for svc_name in (
                        "unreal-signaling",
                        "unreal-game",
                        "vtuber-script-runner",
                        "recorder-control",
                        "orchestrator-registration",
                    ):
                        assert svc_name not in cmd
                    # But should still include safe always-on services.
                    assert "turn-server" in cmd
                    assert "vtuber-watchdog" in cmd
                    assert "vtuber-auto-updater" in cmd
                return DummyResult(stdout="")

            raise AssertionError(f"unexpected cmd: {cmd}")

    executor = DummyExecutor()
    monkeypatch.setattr(svc, "_cluster_executor_container", lambda: executor)
    monkeypatch.setattr(svc, "_cluster_project_dir", lambda: "/tmp/repo")

    resp = client.post("/ops/upgrade", json={"apply": True})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ops_upgrade_recreate_game_includes_unreal_game(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_require_auth_strict", lambda _req: None)
    monkeypatch.setattr(svc, "_detect_compose_identity", lambda: None)
    monkeypatch.setattr(svc, "_read_power_state", lambda: svc.PowerState(state="sleeping"))

    class DummyResult:
        def __init__(self, exit_code: int = 0, stdout: str = "", stderr: str = ""):
            self.exit_code = exit_code
            self.output = (stdout.encode("utf-8"), stderr.encode("utf-8"))

    class DummyContainer:
        def __init__(self, service: str):
            self.labels = {"com.docker.compose.service": service}

    monkeypatch.setattr(
        svc,
        "_list_project_containers",
        lambda _project=None: [  # noqa: ARG005
            DummyContainer("turn-server"),
            DummyContainer("unreal-signaling"),
            DummyContainer("unreal-game"),
            DummyContainer("vtuber-script-runner"),
            DummyContainer("orchestrator-health"),
            DummyContainer("orchestrator-edge-rotator"),
        ],
    )

    class DummyExecutor:
        def __init__(self):
            self.commands = []

        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            self.commands.append(cmd)
            git_prefix_a = ["git", "-C", "/tmp/repo"]
            git_prefix_b = ["git", "-c", "safe.directory=/tmp/repo", "-C", "/tmp/repo"]

            if cmd[: len(git_prefix_a)] == git_prefix_a:
                git_cmd = cmd[len(git_prefix_a) :]
            elif cmd[: len(git_prefix_b)] == git_prefix_b:
                git_cmd = cmd[len(git_prefix_b) :]
            else:
                git_cmd = None

            if git_cmd is not None:
                if git_cmd[:3] == ["rev-parse", "--is-inside-work-tree"]:
                    return DummyResult(stdout="true\n")
                if git_cmd[:2] == ["status", "--porcelain"]:
                    return DummyResult(stdout="")
                if git_cmd[:3] == ["rev-parse", "--short", "HEAD"]:
                    return DummyResult(stdout="abc123\n")
                if git_cmd[:2] == ["fetch", "-q"]:
                    return DummyResult(stdout="")
                if git_cmd[:3] == ["pull", "-q", "--ff-only"]:
                    return DummyResult(stdout="")
                return DummyResult(stdout="")

            if cmd[:2] == ["docker", "compose"]:
                if "pull" in cmd:
                    assert "unreal-game" not in cmd
                if "up" in cmd:
                    assert "--no-start" in cmd
                    assert "unreal-game" in cmd
                return DummyResult(stdout="")

            raise AssertionError(f"unexpected cmd: {cmd}")

    executor = DummyExecutor()
    monkeypatch.setattr(svc, "_cluster_executor_container", lambda: executor)
    monkeypatch.setattr(svc, "_cluster_project_dir", lambda: "/tmp/repo")

    resp = client.post("/ops/upgrade", json={"apply": True, "recreate_game": True})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ops_upgrade_recreate_all_recreates_full_stack(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_require_auth_strict", lambda _req: None)
    monkeypatch.setattr(svc, "_detect_compose_identity", lambda: None)
    monkeypatch.setattr(svc, "_read_power_state", lambda: svc.PowerState(state="sleeping"))

    class DummyResult:
        def __init__(self, exit_code: int = 0, stdout: str = "", stderr: str = ""):
            self.exit_code = exit_code
            self.output = (stdout.encode("utf-8"), stderr.encode("utf-8"))

    class DummyContainer:
        def __init__(self, service: str):
            self.labels = {"com.docker.compose.service": service}

    services = [
        "turn-server",
        "unreal-signaling",
        "unreal-game",
        "vtuber-script-runner",
        "recorder-control",
        "vtuber-watchdog",
        "vtuber-auto-updater",
        "orchestrator-registration",
        "orchestrator-health",
        "orchestrator-edge-rotator",
    ]
    monkeypatch.setattr(
        svc,
        "_list_project_containers",
        lambda _project=None: [DummyContainer(s) for s in services],  # noqa: ARG005
    )

    class DummyExecutor:
        def __init__(self):
            self.commands = []

        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            self.commands.append(cmd)
            git_prefix_a = ["git", "-C", "/tmp/repo"]
            git_prefix_b = ["git", "-c", "safe.directory=/tmp/repo", "-C", "/tmp/repo"]

            if cmd[: len(git_prefix_a)] == git_prefix_a:
                git_cmd = cmd[len(git_prefix_a) :]
            elif cmd[: len(git_prefix_b)] == git_prefix_b:
                git_cmd = cmd[len(git_prefix_b) :]
            else:
                git_cmd = None

            if git_cmd is not None:
                if git_cmd[:3] == ["rev-parse", "--is-inside-work-tree"]:
                    return DummyResult(stdout="true\n")
                if git_cmd[:2] == ["status", "--porcelain"]:
                    return DummyResult(stdout="")
                if git_cmd[:3] == ["rev-parse", "--short", "HEAD"]:
                    return DummyResult(stdout="abc123\n")
                if git_cmd[:2] == ["fetch", "-q"]:
                    return DummyResult(stdout="")
                if git_cmd[:3] == ["pull", "-q", "--ff-only"]:
                    return DummyResult(stdout="")
                return DummyResult(stdout="")

            if cmd[:2] == ["docker", "compose"]:
                if "pull" in cmd:
                    # Avoid pulling the game image; also don't pull self/executor.
                    assert "unreal-game" not in cmd
                    assert "orchestrator-health" not in cmd
                    assert "orchestrator-edge-rotator" not in cmd
                    for svc_name in (
                        "turn-server",
                        "unreal-signaling",
                        "vtuber-script-runner",
                        "recorder-control",
                        "vtuber-watchdog",
                        "vtuber-auto-updater",
                        "orchestrator-registration",
                    ):
                        assert svc_name in cmd
                if "up" in cmd:
                    # Sleeping stacks should recreate stopped containers without starting them.
                    assert "--no-start" in cmd
                    assert "-d" not in cmd
                    # Full stack recreate should include the game (but not self/executor).
                    assert "--force-recreate" in cmd
                    assert "unreal-game" in cmd
                    assert "orchestrator-health" not in cmd
                    assert "orchestrator-edge-rotator" not in cmd
                return DummyResult(stdout="")

            raise AssertionError(f"unexpected cmd: {cmd}")

    executor = DummyExecutor()
    monkeypatch.setattr(svc, "_cluster_executor_container", lambda: executor)
    monkeypatch.setattr(svc, "_cluster_project_dir", lambda: "/tmp/repo")

    resp = client.post("/ops/upgrade", json={"apply": True, "recreate_all": True})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ops_upgrade_recreate_orchestrator_health_schedules_background_job(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_require_auth_strict", lambda _req: None)
    monkeypatch.setattr(svc, "_detect_compose_identity", lambda: None)
    monkeypatch.setattr(svc, "_read_power_state", lambda: svc.PowerState(state="sleeping"))

    class DummyResult:
        def __init__(self, exit_code: int = 0, stdout: str = "", stderr: str = ""):
            self.exit_code = exit_code
            self.output = (stdout.encode("utf-8"), stderr.encode("utf-8"))

    class DummyContainer:
        def __init__(self, service: str):
            self.labels = {"com.docker.compose.service": service}

    monkeypatch.setattr(
        svc,
        "_list_project_containers",
        lambda _project=None: [  # noqa: ARG005
            DummyContainer("turn-server"),
            DummyContainer("orchestrator-registration"),
            DummyContainer("orchestrator-health"),
            DummyContainer("orchestrator-edge-rotator"),
        ],
    )

    class DummyExecutor:
        def __init__(self):
            self.commands = []

        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            self.commands.append(cmd)
            git_prefix_a = ["git", "-C", "/tmp/repo"]
            git_prefix_b = ["git", "-c", "safe.directory=/tmp/repo", "-C", "/tmp/repo"]

            if cmd[: len(git_prefix_a)] == git_prefix_a:
                git_cmd = cmd[len(git_prefix_a) :]
            elif cmd[: len(git_prefix_b)] == git_prefix_b:
                git_cmd = cmd[len(git_prefix_b) :]
            else:
                git_cmd = None

            if git_cmd is not None:
                if git_cmd[:3] == ["rev-parse", "--is-inside-work-tree"]:
                    return DummyResult(stdout="true\n")
                if git_cmd[:2] == ["status", "--porcelain"]:
                    return DummyResult(stdout="")
                if git_cmd[:3] == ["rev-parse", "--short", "HEAD"]:
                    return DummyResult(stdout="abc123\n")
                if git_cmd[:2] == ["fetch", "-q"]:
                    return DummyResult(stdout="")
                if git_cmd[:3] == ["pull", "-q", "--ff-only"]:
                    return DummyResult(stdout="")
                return DummyResult(stdout="")

            if cmd[:2] == ["docker", "compose"]:
                # Should still exclude self from regular pull/up. Self-recreate happens via a background job.
                assert "orchestrator-health" not in cmd
                assert "orchestrator-edge-rotator" not in cmd
                return DummyResult(stdout="")

            if cmd and cmd[0] == "python3":
                # Background recreate job (runs bash -lc "...pull orchestrator-health && ...up ... orchestrator-health")
                joined = " ".join(str(x) for x in cmd)
                assert "ops-recreate-orchestrator-health.log" in joined
                assert "orchestrator-health" in joined
                assert "bash" in cmd
                return DummyResult(stdout="scheduled\n")

            raise AssertionError(f"unexpected cmd: {cmd}")

    executor = DummyExecutor()
    monkeypatch.setattr(svc, "_cluster_executor_container", lambda: executor)
    monkeypatch.setattr(svc, "_cluster_project_dir", lambda: "/tmp/repo")

    resp = client.post("/ops/upgrade", json={"apply": True, "recreate_orchestrator_health": True})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    assert any(cmd and cmd[0] == "python3" for cmd in executor.commands)


def test_ops_rollout_execs_script(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_require_auth_strict", lambda _req: None)
    monkeypatch.setattr(svc, "_executor_disk_free_bytes", lambda *_args, **_kwargs: 999 * 1024 * 1024 * 1024)
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

    state_path = svc.ROLLOUT_STATE_FILE
    assert state_path.exists()
    state = json.loads(state_path.read_text())
    assert state["status"] in ("staged", "applied")


def test_meta_includes_rollout_and_verify(power_app):
    app, _svc = power_app
    client = TestClient(app)
    resp = client.get("/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert "rollout" in data
    assert "verify_last" in data


def test_meta_gpu_requires_allowlist(power_app):
    app, _svc = power_app
    client = TestClient(app)
    resp = client.get("/meta/gpu")
    assert resp.status_code == 403


def test_meta_gpu_returns_inventory(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app, client=("127.0.0.1", 12345))

    class DummyImage:
        id = "sha256:deadbeef"

    class DummyContainer:
        image = DummyImage()

    class DummyContainers:
        def get(self, name):  # noqa: ARG002
            return DummyContainer()

    monkeypatch.setattr(svc, "docker_client", type("DummyDocker", (), {"containers": DummyContainers()})())

    class DummyResult:
        exit_code = 0
        output = (b"0, GPU-123, NVIDIA RTX 4090, 24576, 535.104.12\n", b"")

    class DummyExecutor:
        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            assert cmd[:6] == ["docker", "run", "--rm", "--gpus", "all", "sha256:deadbeef"]
            assert "nvidia-smi" in cmd
            return DummyResult()

    monkeypatch.setattr(svc, "_cluster_executor_try_container", lambda: DummyExecutor())

    resp = client.get("/meta/gpu")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["gpus"][0]["name"] == "NVIDIA RTX 4090"
    assert data["gpus"][0]["memory_total_mib"] == 24576


def test_meta_gpu_returns_error_on_nvidia_smi_failure(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app, client=("127.0.0.1", 12345))

    class DummyImage:
        id = "sha256:deadbeef"

    class DummyContainer:
        image = DummyImage()

    class DummyContainers:
        def get(self, name):  # noqa: ARG002
            return DummyContainer()

    monkeypatch.setattr(svc, "docker_client", type("DummyDocker", (), {"containers": DummyContainers()})())

    class DummyResult:
        exit_code = 1
        output = (b"", b"nvidia-smi: command not found\n")

    class DummyExecutor:
        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            assert cmd[:6] == ["docker", "run", "--rm", "--gpus", "all", "sha256:deadbeef"]
            return DummyResult()

    monkeypatch.setattr(svc, "_cluster_executor_try_container", lambda: DummyExecutor())

    resp = client.get("/meta/gpu")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"] == "nvidia-smi failed"


def test_meta_gpu_stats_requires_allowlist(power_app):
    app, _svc = power_app
    client = TestClient(app)
    resp = client.get("/meta/gpu/stats")
    assert resp.status_code == 403


def test_meta_gpu_stats_returns_stats(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app, client=("127.0.0.1", 12345))

    svc._META_GPU_STATS_CACHE = None
    svc._META_GPU_STATS_CACHE_CAPTURED_MONO = None

    class DummyImage:
        id = "sha256:deadbeef"

    class DummyContainer:
        image = DummyImage()

    class DummyContainers:
        def get(self, name):  # noqa: ARG002
            return DummyContainer()

    monkeypatch.setattr(svc, "docker_client", type("DummyDocker", (), {"containers": DummyContainers()})())

    class DummyResult:
        exit_code = 0
        output = (b"0, GPU-123, 17, 3, 0, 100, 24576, 55, 150.5, 250.0\n", b"")

    class DummyExecutor:
        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            assert cmd[:6] == ["docker", "run", "--rm", "--gpus", "all", "sha256:deadbeef"]
            assert "nvidia-smi" in cmd
            return DummyResult()

    monkeypatch.setattr(svc, "_cluster_executor_try_container", lambda: DummyExecutor())

    resp = client.get("/meta/gpu/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["cached"] is False
    assert data["gpus"][0]["utilization_gpu_pct"] == 17
    assert data["gpus"][0]["memory_total_mib"] == 24576
    assert data["gpus"][0]["power_draw_w"] == 150.5
    assert "captured_at" in data


def test_meta_gpu_stats_cache(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app, client=("127.0.0.1", 12345))

    monkeypatch.setenv("META_GPU_STATS_TTL_SECONDS", "60")
    svc._META_GPU_STATS_CACHE = None
    svc._META_GPU_STATS_CACHE_CAPTURED_MONO = None

    class DummyImage:
        id = "sha256:deadbeef"

    class DummyContainer:
        image = DummyImage()

    class DummyContainers:
        def get(self, name):  # noqa: ARG002
            return DummyContainer()

    monkeypatch.setattr(svc, "docker_client", type("DummyDocker", (), {"containers": DummyContainers()})())

    calls = {"count": 0}

    class DummyResult:
        exit_code = 0
        output = (b"0, GPU-123, 17, 3, 0, 100, 24576, 55, 150.5, 250.0\n", b"")

    class DummyExecutor:
        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            calls["count"] += 1
            assert cmd[:6] == ["docker", "run", "--rm", "--gpus", "all", "sha256:deadbeef"]
            return DummyResult()

    monkeypatch.setattr(svc, "_cluster_executor_try_container", lambda: DummyExecutor())

    resp1 = client.get("/meta/gpu/stats")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["cached"] is False

    resp2 = client.get("/meta/gpu/stats")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["cached"] is True
    assert data2["captured_at"] == data1["captured_at"]
    assert calls["count"] == 1


def test_ops_pull_image_execs_docker_pull(ops_app, monkeypatch):
    app, svc = ops_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_require_auth_strict", lambda _req: None)

    class DummyResult:
        exit_code = 0
        output = (b"pulled\n", b"")

    class DummyExecutor:
        def exec_run(self, cmd, environment=None, demux=False):  # noqa: ARG002
            assert cmd == ["docker", "pull", "ghcr.io/example/image:latest"]
            return DummyResult()

    monkeypatch.setattr(svc, "_cluster_executor_container", lambda: DummyExecutor())

    resp = client.post("/ops/pull-image", json={"image": "ghcr.io/example/image:latest"})
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


def test_cluster_deploy_rejects_invalid_override_paths(cluster_app, monkeypatch):
    app, svc = cluster_app
    client = TestClient(app)

    monkeypatch.setattr(svc, "_docker_port_conflicts", lambda _ports, **_kwargs: {})

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
        status = "running"

        def reload(self) -> None:  # pragma: no cover - used by service code
            return None

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
