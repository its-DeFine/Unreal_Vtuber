import json
import os
import stat
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "scripts" / "embody_cli.sh"
PRIVATE_DESTINATION = "rtmps://stream.example.test/live/a-secret-stream-key?token=private-token"


FAKE_DOCKER = r'''#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

state_path = Path(os.environ["FAKE_DOCKER_STATE"])
try:
    state = json.loads(state_path.read_text(encoding="utf-8"))
except Exception:
    state = {"container": "absent", "network": False, "up_count": 0, "calls": []}

args = sys.argv[1:]
state["calls"].append(
    {
        "args": args,
        "mode": os.environ.get("EMBODY_BROADCAST_MODE"),
        "destination_file": os.environ.get("EMBODY_BROADCAST_RTMP_URL_FILE"),
    }
)

def save():
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")

if args == ["info"]:
    save()
    raise SystemExit(0)
if args[:2] == ["compose", "version"]:
    save()
    print("Docker Compose version fake")
    raise SystemExit(0)
if args[:2] == ["network", "inspect"]:
    save()
    raise SystemExit(0 if state.get("network") else 1)
if args[:2] == ["network", "create"]:
    state["network"] = True
    save()
    print(args[-1])
    raise SystemExit(0)
if args and args[0] == "compose":
    if "up" in args:
        state["container"] = "running"
        state["up_count"] = state.get("up_count", 0) + 1
        state_dir = Path(os.environ["EMBODY_BROADCAST_STATE_DIR"])
        state_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        (state_dir / "state.json").write_text(
            json.dumps(
                {
                    "status": "streaming",
                    "connected": True,
                    "attempts": state["up_count"],
                    "started_at": now,
                    "heartbeat_at": now,
                    "updated_at": now,
                }
            ),
            encoding="utf-8",
        )
    elif "down" in args:
        state["container"] = "absent"
    save()
    raise SystemExit(0)
if args and args[0] == "inspect":
    save()
    if state.get("container") == "running":
        print("running|healthy")
        raise SystemExit(0)
    raise SystemExit(1)
if args and args[0] == "logs":
    save()
    print("sanitized fake bridge log")
    raise SystemExit(0)

save()
print("unsupported fake docker call: " + repr(args), file=sys.stderr)
raise SystemExit(2)
'''


@pytest.fixture
def cli_env(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(FAKE_DOCKER, encoding="utf-8")
    fake_docker.chmod(0o755)

    home = tmp_path / "home"
    home.mkdir()
    state = tmp_path / "fake-docker-state.json"
    broadcast_dir = tmp_path / "operator-state" / "broadcast"
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "FAKE_DOCKER_STATE": str(state),
        "EMBODY_BROADCAST_DIR": str(broadcast_dir),
        "EMBODY_BROADCAST_START_WAIT_SECONDS": "0",
        "EMBODY_CLI_NO_AUTO_UPDATE": "1",
        "NO_COLOR": "1",
    }
    return env, state, broadcast_dir


def run_cli(env, *args, check=True, input_text=None):
    return subprocess.run(
        [str(CLI), "broadcast", *args],
        cwd=REPO_ROOT,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        check=check,
    )


def test_fake_mode_exercises_start_status_stop_and_recover(cli_env):
    env, docker_state_path, _broadcast_dir = cli_env

    configured = run_cli(env, "configure", "--test")
    assert "local test mode" in configured.stdout

    started = run_cli(env, "start")
    assert "started" in started.stdout
    assert "fake sink" in started.stdout

    status_result = run_cli(env, "status", "--json")
    status_payload = json.loads(status_result.stdout)
    assert status_payload["enabled"] is True
    assert status_payload["mode"] == "test"
    assert status_payload["container"]["status"] == "running"
    assert status_payload["bridge"]["status"] == "streaming"

    stopped = run_cli(env, "stop")
    assert "WebRTC/signaling and recorder services were not changed" in stopped.stdout
    stopped_status = run_cli(env, "status", "--json", check=False)
    assert stopped_status.returncode == 1
    assert json.loads(stopped_status.stdout)["container"]["status"] == "absent"

    recovered = run_cli(env, "recover")
    assert "recreated" in recovered.stdout
    docker_state = json.loads(docker_state_path.read_text(encoding="utf-8"))
    assert docker_state["up_count"] == 2

    disabled = run_cli(env, "configure", "--disable")
    assert "Broadcast disabled" in disabled.stdout
    disabled_status = run_cli(env, "status", "--json")
    assert json.loads(disabled_status.stdout)["enabled"] is False


def test_real_destination_is_private_and_never_reaches_argv_env_or_status(cli_env, tmp_path):
    env, docker_state_path, broadcast_dir = cli_env
    source = tmp_path / "input-url"
    source.write_text(PRIVATE_DESTINATION, encoding="utf-8")
    source.chmod(0o600)

    configured = run_cli(env, "configure", "--url-file", str(source))
    assert PRIVATE_DESTINATION not in configured.stdout
    assert PRIVATE_DESTINATION not in configured.stderr

    destination_file = broadcast_dir / "rtmp-url"
    config_file = broadcast_dir / "config.json"
    assert destination_file.read_text(encoding="utf-8") == PRIVATE_DESTINATION
    assert stat.S_IMODE(destination_file.stat().st_mode) == 0o600
    assert PRIVATE_DESTINATION not in config_file.read_text(encoding="utf-8")

    started = run_cli(env, "start")
    assert PRIVATE_DESTINATION not in started.stdout
    assert PRIVATE_DESTINATION not in started.stderr

    status_result = run_cli(env, "status", "--json")
    assert PRIVATE_DESTINATION not in status_result.stdout
    assert "a-secret-stream-key" not in status_result.stdout
    payload = json.loads(status_result.stdout)
    assert payload["destination_configured"] is True

    docker_state = json.loads(docker_state_path.read_text(encoding="utf-8"))
    serialized_calls = json.dumps(docker_state["calls"])
    assert PRIVATE_DESTINATION not in serialized_calls
    assert "a-secret-stream-key" not in serialized_calls
    # The mounted private file path is expected; its contents are not.
    assert any(call.get("destination_file") == str(destination_file) for call in docker_state["calls"])

    run_cli(env, "configure", "--disable")
    assert not destination_file.exists()


def test_cli_refuses_destination_as_a_command_line_argument(cli_env):
    env, _docker_state_path, _broadcast_dir = cli_env
    result = run_cli(env, "configure", "--url", PRIVATE_DESTINATION, check=False)
    assert result.returncode != 0
    assert "refusing destination credentials on the command line" in result.stderr
    # The shell supplied the value, but the CLI must not reflect it back.
    assert PRIVATE_DESTINATION not in result.stdout
    assert PRIVATE_DESTINATION not in result.stderr
