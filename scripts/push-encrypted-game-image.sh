#!/usr/bin/env bash
set -euo pipefail

# Push an encrypted game image to GHCR as a FROM-scratch Docker image.
#
# The encrypted blob is useless without the age private key, so it is safe
# to host on a public/private GHCR repo. Orchestrators pull via standard
# docker-pull (CDN-cached, resumable) and decrypt locally.
#
# Prerequisites: docker, zstd, age, and GHCR auth (docker login ghcr.io).

usage() {
  cat <<'EOF'
Usage:
  push-encrypted-game-image.sh --image <docker-image-ref> --recipient <age1...> [OPTIONS]

Required:
  --image         Local Docker image ref to encrypt (e.g., embody-ue-ps:kokoro-v3)
  --recipient     age public key for encryption (age1...)

Options:
  --tag           GHCR tag for the encrypted image (default: <date>-enc)
  --ghcr-repo     GHCR repo (default: ghcr.io/its-define/unreal_vtuber/embody-ue-ps)
  --zstd-level    Zstd compression level 1-19 (default: 3)
  --keep-tmp      Do not delete the temporary build directory on exit

Example:
  push-encrypted-game-image.sh \
    --image embody-ue-ps:kokoro-v3 \
    --recipient age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p \
    --tag kokoro-v3-enc
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

image=""
recipient=""
tag=""
ghcr_repo="ghcr.io/its-define/unreal_vtuber/embody-ue-ps"
zstd_level="3"
keep_tmp="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image)      image="${2:-}";      shift 2 ;;
    --recipient)  recipient="${2:-}";  shift 2 ;;
    --tag)        tag="${2:-}";        shift 2 ;;
    --ghcr-repo)  ghcr_repo="${2:-}";  shift 2 ;;
    --zstd-level) zstd_level="${2:-}"; shift 2 ;;
    --keep-tmp)   keep_tmp="1";        shift 1 ;;
    -h|--help)    usage; exit 0 ;;
    *)            die "unknown arg: $1" ;;
  esac
done

[[ -n "$image" ]]     || die "--image is required"
[[ -n "$recipient" ]] || die "--recipient is required"

command -v docker >/dev/null 2>&1 || die "missing dependency: docker"
command -v zstd   >/dev/null 2>&1 || die "missing dependency: zstd"
command -v age    >/dev/null 2>&1 || die "missing dependency: age"

# Default tag includes timestamp to avoid collisions
if [[ -z "$tag" ]]; then
  tag="$(date +%Y%m%d-%H%M%S)-enc"
fi

full_ref="${ghcr_repo}:${tag}"
tmpdir="$(mktemp -d)"

cleanup() {
  if [[ "$keep_tmp" != "1" ]]; then
    rm -rf "$tmpdir"
  else
    echo "Temporary files kept at: $tmpdir" >&2
  fi
}
trap cleanup EXIT

echo "==> Exporting Docker image: $image" >&2
echo "==> Compressing with zstd (level $zstd_level) and encrypting with age" >&2

docker save "$image" \
  | zstd "-${zstd_level}" -T0 \
  | age -r "$recipient" \
  -o "${tmpdir}/image.age"

encrypted_size="$(stat -f%z "${tmpdir}/image.age" 2>/dev/null || stat -c%s "${tmpdir}/image.age" 2>/dev/null)"
echo "==> Encrypted artifact: ${encrypted_size} bytes" >&2

# Build a minimal FROM-scratch image containing only the encrypted blob.
# This makes it pullable via standard docker pull (CDN, resumable, layer caching).
cat > "${tmpdir}/Dockerfile" <<'DOCKERFILE'
FROM scratch
COPY image.age /image.age
DOCKERFILE

echo "==> Building GHCR image: $full_ref" >&2
docker build -t "$full_ref" "$tmpdir"

echo "==> Pushing to GHCR: $full_ref" >&2
docker push "$full_ref"

echo "==> Done. Encrypted image pushed to: $full_ref" >&2
echo "$full_ref"
