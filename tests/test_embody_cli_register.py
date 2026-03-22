from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI_SOURCE = ROOT / "scripts" / "embody_cli.sh"


def _make_repo(tmp_path: Path, env_text: str | None = None, include_register_script: bool = True) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "embody_cli.sh").write_text(CLI_SOURCE.read_text())
    (repo / "docker-compose.unreal.yml").write_text("services:\n")
    if env_text is not None:
        (repo / ".env").write_text(env_text)

    if include_register_script:
        (scripts_dir / "register_orchestrator.py").write_text(
            "#!/usr/bin/env python3\n"
            "import json\n"
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            "\n"
            "log_path = os.environ.get('EMBODY_TEST_REGISTER_LOG')\n"
            "if log_path:\n"
            "    path = Path(log_path)\n"
            "    entries = []\n"
            "    if path.exists():\n"
            "        entries = json.loads(path.read_text())\n"
            "    entries.append(sys.argv[1:])\n"
            "    path.write_text(json.dumps(entries))\n"
            "stdout = os.environ.get('EMBODY_TEST_REGISTER_STDOUT', '')\n"
            "stderr = os.environ.get('EMBODY_TEST_REGISTER_STDERR', '')\n"
            "if stdout:\n"
            "    print(stdout)\n"
            "if stderr:\n"
            "    print(stderr, file=sys.stderr)\n"
            "raise SystemExit(int(os.environ.get('EMBODY_TEST_REGISTER_EXIT_CODE', '0')))\n"
        )

    home = tmp_path / "home"
    (home / ".embody").mkdir(parents=True)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "curl").write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "from pathlib import Path\n"
        "\n"
        "fixtures_path = os.environ['EMBODY_TEST_CURL_FIXTURES']\n"
        "state_path = Path(os.environ['EMBODY_TEST_CURL_STATE'])\n"
        "fixtures = json.loads(Path(fixtures_path).read_text())\n"
        "state = json.loads(state_path.read_text()) if state_path.exists() else {}\n"
        "url = ''\n"
        "for arg in reversed(sys.argv[1:]):\n"
        "    if arg.startswith('http://') or arg.startswith('https://'):\n"
        "        url = arg\n"
        "        break\n"
        "entry = fixtures.get(url) or fixtures.get('*') or [{'http_code': '000', 'body': ''}]\n"
        "if isinstance(entry, dict):\n"
        "    entry = [entry]\n"
        "index = state.get(url, 0)\n"
        "payload = entry[index] if index < len(entry) else entry[-1]\n"
        "state[url] = index + 1\n"
        "state_path.write_text(json.dumps(state))\n"
        "fmt = ''\n"
        "if '-w' in sys.argv:\n"
        "    fmt = sys.argv[sys.argv.index('-w') + 1]\n"
        "sys.stdout.write(str(payload.get('body', '')))\n"
        "if fmt:\n"
        "    sys.stdout.write(fmt.replace('%{http_code}', str(payload.get('http_code', '000'))))\n"
        "stderr = payload.get('stderr', '')\n"
        "if stderr:\n"
        "    sys.stderr.write(str(stderr))\n"
        "raise SystemExit(int(payload.get('exit_code', 0)))\n"
    )
    os.chmod(bin_dir / "curl", 0o755)

    return repo, home, bin_dir


def _write_token(home: Path) -> None:
    (home / ".embody" / "orch-license-token.txt").write_text("test-token\n")


def _run_cli(
    repo: Path,
    home: Path,
    bin_dir: Path,
    args: list[str],
    fixtures: dict[str, object],
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    fixtures_path = repo / "curl-fixtures.json"
    fixtures_path.write_text(json.dumps(fixtures))
    state_path = repo / "curl-state.json"
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PATH": f"{bin_dir}:{env['PATH']}",
            "EMBODY_CLI_NO_AUTO_UPDATE": "1",
            "EMBODY_TEST_CURL_FIXTURES": str(fixtures_path),
            "EMBODY_TEST_CURL_STATE": str(state_path),
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(repo / "scripts" / "embody_cli.sh"), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_register_status_shows_registration_state_and_services(tmp_path: Path) -> None:
    repo, home, bin_dir = _make_repo(
        tmp_path,
        env_text=(
            "PAYMENTS_API_URL=http://payments.test\n"
            "ORCHESTRATOR_ID=orch-1\n"
            "ORCHESTRATOR_ADDRESS=0x1111111111111111111111111111111111111111\n"
        ),
    )
    _write_token(home)

    result = _run_cli(
        repo,
        home,
        bin_dir,
        ["register", "--status"],
        fixtures={
            "http://payments.test/api/orchestrators/me": {
                "http_code": "200",
                "body": json.dumps(
                    {
                        "orchestrator_id": "orch-1",
                        "active": True,
                        "last_seen": "2026-03-22T10:00:00Z",
                        "eligible_for_payments": True,
                    }
                ),
            },
            "http://127.0.0.1:9090/health": {
                "http_code": "200",
                "body": json.dumps(
                    {
                        "summary": {
                            "status_message": "All required services online",
                            "services_up": 3,
                            "total_services": 3,
                            "missing_services": [],
                        }
                    }
                ),
            },
        },
    )

    assert result.returncode == 0
    assert "Registered" in result.stdout
    assert "yes" in result.stdout
    assert "2026-03-22T10:00:00Z" in result.stdout
    assert "All required services online" in result.stdout
    assert "Payment eligible" in result.stdout


def test_register_missing_script_tells_operator_to_git_pull(tmp_path: Path) -> None:
    repo, home, bin_dir = _make_repo(
        tmp_path,
        env_text=(
            "PAYMENTS_API_URL=http://payments.test\n"
            "ORCHESTRATOR_ID=orch-1\n"
            "ORCHESTRATOR_ADDRESS=0x1111111111111111111111111111111111111111\n"
        ),
        include_register_script=False,
    )

    result = _run_cli(repo, home, bin_dir, ["register"], fixtures={})

    assert result.returncode == 1
    assert "git pull" in result.stderr
    assert "register_orchestrator.py" in result.stderr


def test_register_lists_missing_env_fields(tmp_path: Path) -> None:
    repo, home, bin_dir = _make_repo(tmp_path, env_text=None)

    result = _run_cli(repo, home, bin_dir, ["register"], fixtures={})

    assert result.returncode == 1
    assert ".env not found" in result.stderr
    assert "PAYMENTS_API_URL" in result.stderr
    assert "ORCHESTRATOR_ID" in result.stderr
    assert "ORCHESTRATOR_ADDRESS" in result.stderr


def test_register_active_orchestrator_requires_force_in_non_tty(tmp_path: Path) -> None:
    repo, home, bin_dir = _make_repo(
        tmp_path,
        env_text=(
            "PAYMENTS_API_URL=http://payments.test\n"
            "ORCHESTRATOR_ID=orch-1\n"
            "ORCHESTRATOR_ADDRESS=0x1111111111111111111111111111111111111111\n"
        ),
    )
    _write_token(home)
    register_log = repo / "register-log.json"

    result = _run_cli(
        repo,
        home,
        bin_dir,
        ["register"],
        fixtures={
            "http://payments.test/api/orchestrators/me": {
                "http_code": "200",
                "body": json.dumps(
                    {
                        "orchestrator_id": "orch-1",
                        "active": True,
                        "last_seen": "2026-03-22T10:00:00Z",
                        "eligible_for_payments": True,
                    }
                ),
            },
            "http://127.0.0.1:9090/health": {
                "http_code": "200",
                "body": json.dumps(
                    {
                        "summary": {
                            "status_message": "All required services online",
                            "services_up": 3,
                            "total_services": 3,
                            "missing_services": [],
                        }
                    }
                ),
            },
        },
        extra_env={"EMBODY_TEST_REGISTER_LOG": str(register_log)},
    )

    assert result.returncode == 0
    assert "Use --force to re-register" in result.stderr
    assert not register_log.exists()


def test_register_inactive_orchestrator_forces_reregistration_and_verifies_visibility(tmp_path: Path) -> None:
    repo, home, bin_dir = _make_repo(
        tmp_path,
        env_text=(
            "PAYMENTS_API_URL=http://payments.test\n"
            "ORCHESTRATOR_ID=orch-1\n"
            "ORCHESTRATOR_ADDRESS=0x1111111111111111111111111111111111111111\n"
        ),
    )
    _write_token(home)
    register_log = repo / "register-log.json"

    result = _run_cli(
        repo,
        home,
        bin_dir,
        ["register"],
        fixtures={
            "http://payments.test/api/orchestrators/me": [
                {
                    "http_code": "200",
                    "body": json.dumps(
                        {
                            "orchestrator_id": "orch-1",
                            "active": False,
                            "last_seen": "2026-03-20T10:00:00Z",
                            "eligible_for_payments": False,
                        }
                    ),
                },
                {
                    "http_code": "200",
                    "body": json.dumps(
                        {
                            "orchestrator_id": "orch-1",
                            "active": True,
                            "last_seen": "2026-03-22T10:05:00Z",
                            "eligible_for_payments": True,
                        }
                    ),
                },
            ],
            "http://127.0.0.1:9090/health": {
                "http_code": "200",
                "body": json.dumps(
                    {
                        "summary": {
                            "status_message": "All required services online",
                            "services_up": 3,
                            "total_services": 3,
                            "missing_services": [],
                        }
                    }
                ),
            },
        },
        extra_env={"EMBODY_TEST_REGISTER_LOG": str(register_log)},
    )

    assert result.returncode == 0
    assert "registered but inactive" in result.stderr
    assert "fleet visibility" in result.stdout
    log_entries = json.loads(register_log.read_text())
    assert "--force" in log_entries[0]


def test_register_reports_unreachable_payments_backend(tmp_path: Path) -> None:
    repo, home, bin_dir = _make_repo(
        tmp_path,
        env_text=(
            "PAYMENTS_API_URL=http://payments.test\n"
            "ORCHESTRATOR_ID=orch-1\n"
            "ORCHESTRATOR_ADDRESS=0x1111111111111111111111111111111111111111\n"
        ),
    )
    _write_token(home)

    result = _run_cli(
        repo,
        home,
        bin_dir,
        ["register"],
        fixtures={
            "http://payments.test/api/orchestrators/me": {
                "http_code": "000",
                "body": "",
            },
            "http://127.0.0.1:9090/health": {
                "http_code": "200",
                "body": json.dumps({"summary": {"status_message": "All required services online"}}),
            },
        },
    )

    assert result.returncode == 1
    assert "Payments backend unreachable at http://payments.test" in result.stderr
