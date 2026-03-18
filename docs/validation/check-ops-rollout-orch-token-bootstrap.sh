#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVICE_FILE="$REPO_ROOT/orchestrator-health/orchestrator_health/remote_health_service.py"
TEST_FILE="$REPO_ROOT/orchestrator-health/tests/test_power_api.py"
CONSUME_SCRIPT="$REPO_ROOT/tools/encrypted-game-image/consume.sh"
CANARY_DOC="$REPO_ROOT/docs/ops-rollout-orch-token-bootstrap-canary.md"
PYTHON_BIN="python3"
if [[ -x "$REPO_ROOT/orchestrator-health/.venv_test/bin/python" ]]; then
  PYTHON_BIN="$REPO_ROOT/orchestrator-health/.venv_test/bin/python"
fi
PY_COMPILE_CMD="cd $REPO_ROOT && $PYTHON_BIN -m py_compile orchestrator-health/orchestrator_health/remote_health_service.py orchestrator-health/tests/test_power_api.py"
PYTEST_CMD="cd $REPO_ROOT/orchestrator-health && $PYTHON_BIN -m pytest tests/test_power_api.py -k 'ops_rollout_execs_script or orch_token'"

printf 'task_id=UVT-ROLL-BOOTSTRAP-20260306\nts_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

for required in "$SERVICE_FILE" "$TEST_FILE" "$CONSUME_SCRIPT" "$CANARY_DOC"; do
  if [[ ! -f "$required" ]]; then
    echo "status=blocked"
    echo "blocker=missing_required_file:$required"
    echo "next_exact_command=cd $REPO_ROOT && ls -la $(dirname "$required")"
    exit 0
  fi
done

consume_supports_env_token="no"
if rg -q -- '--orch-token-env' "$CONSUME_SCRIPT"; then
  consume_supports_env_token="yes"
fi

service_uses_file_token="no"
if rg -q -- '--orch-token-file' "$SERVICE_FILE"; then
  service_uses_file_token="yes"
fi

request_has_orch_token="no"
if rg -q -- 'orch_token:' "$SERVICE_FILE"; then
  request_has_orch_token="yes"
fi

tests_cover_orch_token="no"
if rg -q -- 'orch_token' "$TEST_FILE"; then
  tests_cover_orch_token="yes"
fi

printf 'consume_supports_orch_token_env=%s\n' "$consume_supports_env_token"
printf 'ops_rollout_uses_file_token=%s\n' "$service_uses_file_token"
printf 'ops_rollout_request_has_orch_token=%s\n' "$request_has_orch_token"
printf 'tests_cover_orch_token=%s\n' "$tests_cover_orch_token"
printf 'canary_doc=%s\n' "$CANARY_DOC"
printf 'syntax_check_command=%s\n' "$PY_COMPILE_CMD"
printf 'local_test_command=%s\n' "$PYTEST_CMD"

set +e
PY_COMPILE_OUTPUT="$("$PYTHON_BIN" -m py_compile "$SERVICE_FILE" "$TEST_FILE" 2>&1)"
PY_COMPILE_RC=$?
set -e

printf 'py_compile_exit_code=%s\n' "$PY_COMPILE_RC"
echo "py_compile_output_begin"
printf '%s\n' "$PY_COMPILE_OUTPUT" | sed -n '1,40p'
echo "py_compile_output_end"

if [[ "$PY_COMPILE_RC" -ne 0 ]]; then
  echo "status=blocked"
  echo "summary=python_syntax_check_failed"
  echo "next_exact_command=$PY_COMPILE_CMD"
  exit 0
fi

if ! "$PYTHON_BIN" -m pytest --version >/dev/null 2>&1; then
  echo "pytest_available=no"
  echo "status=blocked"
  if [[ "$consume_supports_env_token" == "yes" && "$request_has_orch_token" == "yes" && "$tests_cover_orch_token" == "yes" ]]; then
    echo "summary=orch_token_bridge_present_but_pytest_not_installed"
  else
    echo "summary=env_token_bridge_still_missing_and_pytest_not_installed"
  fi
  echo "next_exact_command=$PYTEST_CMD"
  exit 0
fi

echo "pytest_available=yes"
printf 'python_bin=%s\n' "$PYTHON_BIN"

if [[ "$consume_supports_env_token" == "yes" && "$service_uses_file_token" == "yes" && "$request_has_orch_token" == "no" ]]; then
  echo "status=blocked"
  echo "summary=api_layer_still_missing_env_token_bridge"
  echo "next_exact_command=$PYTEST_CMD"
  exit 0
fi

set +e
PYTEST_OUTPUT="$(cd "$REPO_ROOT/orchestrator-health" && "$PYTHON_BIN" -m pytest tests/test_power_api.py -k 'ops_rollout_execs_script or orch_token' 2>&1)"
PYTEST_RC=$?
set -e

printf 'pytest_exit_code=%s\n' "$PYTEST_RC"
echo "pytest_output_begin"
printf '%s\n' "$PYTEST_OUTPUT" | sed -n '1,120p'
echo "pytest_output_end"

if [[ "$PYTEST_RC" -eq 0 ]]; then
  echo "status=pass"
  echo "summary=focused_ops_rollout_tests_passed"
  echo "next_exact_command=cd $REPO_ROOT && sed -n '1,220p' $CANARY_DOC"
  exit 0
fi

echo "status=blocked"
echo "summary=focused_ops_rollout_tests_failed"
echo "next_exact_command=$PYTEST_CMD"
exit 0
