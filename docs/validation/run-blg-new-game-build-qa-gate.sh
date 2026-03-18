#!/usr/bin/env bash
set -u -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
REMOTE_HELPER="$WS_ROOT/bin/gpu-remote.sh"
DRIVE_URL="https://drive.google.com/drive/folders/1xRKfSfs2_OUAEdzfMcX0PJvhPz2C0GwX?usp=sharing"
NEXT_CMD="cd /home/node/.openclaw/workspace-engineer && bin/gpu-remote.sh \"rm -rf \\\$HOME/new_build_drop_probe && ~/.local/bin/gdown --folder --fuzzy '$DRIVE_URL' -O \\\$HOME/new_build_drop_probe && find \\\$HOME/new_build_drop_probe -type f | grep -Ei '\\\\.zip$|\\\\.pak$|\\\\.utoc$|\\\\.ucas$|LinuxNoEditor' | sed -n '1,120p'\""

printf 'task_id=BLG-NEW-GAME-BUILD-QA\nts_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ ! -x "$REMOTE_HELPER" ]]; then
  echo "status=blocked"
  echo "blocker=missing_remote_helper:$REMOTE_HELPER"
  echo "next_exact_command=ls -la $WS_ROOT/bin"
  exit 0
fi

REMOTE_CMD=$(cat <<'RCMD'
rm -rf "$HOME/new_build_drop_probe"
~/.local/bin/gdown --folder --fuzzy 'https://drive.google.com/drive/folders/1xRKfSfs2_OUAEdzfMcX0PJvhPz2C0GwX?usp=sharing' -O "$HOME/new_build_drop_probe" >/tmp/blg_gdown.log 2>&1 || { echo REMOTE_ERROR=gdown_failed; sed -n '1,40p' /tmp/blg_gdown.log; exit 11; }
find "$HOME/new_build_drop_probe" -type f | awk 'BEGIN{IGNORECASE=1;c=0} /(\\.zip|\\.pak|\\.utoc|\\.ucas)$|LinuxNoEditor/ {print; c++} END{print "MATCH_COUNT=" c}'
echo TOP_FILES_BEGIN
find "$HOME/new_build_drop_probe" -type f -printf '%s %p\\n' | sort -nr | sed -n '1,10p'
RCMD
)

PROBE_OUTPUT="$($REMOTE_HELPER "$REMOTE_CMD" 2>&1)"
RC=$?

if [[ $RC -ne 0 ]]; then
  echo "status=blocked"
  echo "blocker=remote_probe_exec_failed:$RC"
  echo "evidence_begin"
  printf '%s\n' "$PROBE_OUTPUT" | sed -n '1,120p'
  echo "evidence_end"
  echo "next_exact_command=$NEXT_CMD"
  exit 0
fi

MATCH_COUNT=$(printf '%s\n' "$PROBE_OUTPUT" | awk -F= '/^MATCH_COUNT=/{print $2}' | tail -n1)
if [[ -z "${MATCH_COUNT:-}" ]]; then
  MATCH_COUNT=0
fi

echo "match_count=$MATCH_COUNT"
if [[ "$MATCH_COUNT" -gt 0 ]]; then
  echo "status=pass"
  echo "summary=payload_candidates_found"
  echo "evidence_begin"
  printf '%s\n' "$PROBE_OUTPUT" | sed -n '1,120p'
  echo "evidence_end"
  echo "next_exact_command=cd /home/node/.openclaw/workspace-engineer/Unreal_Vtuber && ./docs/validation/run-blg-new-game-build-qa-gate.sh"
  exit 0
fi

echo "status=blocked"
echo "summary=drive_folder_docs_only_no_linux_payload"
echo "request_id=REQUEST-0002"
echo "evidence_begin"
printf '%s\n' "$PROBE_OUTPUT" | sed -n '1,120p'
echo "evidence_end"
echo "next_exact_command=$NEXT_CMD"
exit 0
