#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  produce.sh --image <docker-image-ref> (--recipient <age1...> | --recipients-file <path> | --recipient-env <ENV>) [--out <path>]

Options:
  --image               Docker image ref to export (tag or digest)
  --out                 Write encrypted artifact to this path (default: stdout)
  --recipient           age recipient (public key, "age1...")
  --recipients-file     Path to recipients file (-R), one recipient per line
  --recipient-env       Read recipient public key from env var name
  --zstd-level          Zstd compression level (default: 15)
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

image=""
out=""
recipient=""
recipients_file=""
recipient_env=""
zstd_level="15"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image)
      image="${2:-}"
      shift 2
      ;;
    --out)
      out="${2:-}"
      shift 2
      ;;
    --recipient)
      recipient="${2:-}"
      shift 2
      ;;
    --recipients-file)
      recipients_file="${2:-}"
      shift 2
      ;;
    --recipient-env)
      recipient_env="${2:-}"
      shift 2
      ;;
    --zstd-level)
      zstd_level="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown arg: $1"
      ;;
  esac
done

[[ -n "$image" ]] || die "--image is required"

command -v docker >/dev/null 2>&1 || die "missing dependency: docker"
command -v zstd >/dev/null 2>&1 || die "missing dependency: zstd"
command -v age >/dev/null 2>&1 || die "missing dependency: age"

if [[ -n "$recipient_env" ]]; then
  recipient="${!recipient_env:-}"
fi

if [[ -n "$recipients_file" ]]; then
  [[ -f "$recipients_file" ]] || die "--recipients-file not found: $recipients_file"
fi

if [[ -z "$recipient" && -z "$recipients_file" ]]; then
  die "recipient required (use --recipient, --recipients-file, or --recipient-env)"
fi

zstd_flags=(-T0 -q -c "-${zstd_level}")

if [[ -n "$out" ]]; then
  mkdir -p "$(dirname "$out")"
  docker save "$image" \
    | zstd "${zstd_flags[@]}" \
    | if [[ -n "$recipients_file" ]]; then age -R "$recipients_file"; else age -r "$recipient"; fi \
    > "$out"
else
  docker save "$image" \
    | zstd "${zstd_flags[@]}" \
    | if [[ -n "$recipients_file" ]]; then age -R "$recipients_file"; else age -r "$recipient"; fi
fi
