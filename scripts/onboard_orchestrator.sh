#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Interactive orchestrator onboarding (encrypted game image flow).

If you run this script with no flags, it launches a CLI wizard that:
  - checks prerequisites (and can install missing deps on Ubuntu/Debian)
  - asks for the admin-provided inputs (token + artifact URL + IDs)
  - writes/updates `.env` + generates `.env.turn`
  - loads the encrypted game image via a Payments lease
  - starts `docker-compose.unreal.yml` and registers the orchestrator

Usage:
  # Recommended (wizard)
  ./scripts/onboard_orchestrator.sh

  # Non-interactive
  ./scripts/onboard_orchestrator.sh --non-interactive \
    --orchestrator-id <id> \
    --orchestrator-address <0x...> \
    --artifact-url <https://...tar.zst.age> \
    (--orch-token-file <path> | --orch-token-env <ENV> | --orch-token <value>)

Common options:
  --payments-api-url <url>    (default: http://3.141.111.200:8081)
  --image-ref <ref>           (default: ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1)
  --forwarder-ip <ip>         (default: 3.150.172.153)
  --public-ip <ip|auto>       (default: auto; tries EC2 IMDSv2 then ipify)

Host paths (written into .env):
  --session-dir <path>        (default: <target-home>/vtuber_sessions)
  --recordings-dir <path>     (default: <target-home>/recordings)

Behavior flags:
  --interactive               Force the CLI wizard (even if flags are provided)
  --non-interactive           Never prompt; error if required values are missing
  --install-deps              Attempt apt-get install of curl/jq/zstd/age/python3 (Ubuntu/Debian only)
  --install-docker            Attempt apt-get install of docker + compose plugin (Ubuntu/Debian only)
  --install-nvidia-driver     Attempt to install the NVIDIA driver (Ubuntu/Debian only; requires reboot)
  --install-nvidia-toolkit    Attempt to install nvidia-container-toolkit (Ubuntu/Debian only)
  --rotate-turn               Regenerate .env.turn even if present
  --no-pull                   Skip docker compose pull
  --skip-rollout              Skip encrypted image rollout; just docker compose up -d
  --skip-registration         Skip running orchestrator-registration
  --no-verify                 Skip rollout health checks
  --force-env                 Overwrite .env (otherwise upsert keys)
  --config-only               Only write `.env`/`.env.turn` and exit (no docker actions)

Examples:
  # Recommended: store the license token in a file (admin provides it)
  mkdir -p ~/.embody && chmod 700 ~/.embody
  printf '%s' '<ORCH_TOKEN>' > ~/.embody/orch-license-token.txt && chmod 600 ~/.embody/orch-license-token.txt

  git clone https://github.com/its-DeFine/Unreal_Vtuber.git && cd Unreal_Vtuber && ./scripts/onboard_orchestrator.sh
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

note() {
  echo "[onboard] $*" >&2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing dependency: $1"
}

is_tty() {
  [[ -t 0 && -t 1 ]]
}

prompt_default() {
  local label="$1" default="$2" out
  if [[ -n "$default" ]]; then
    read -r -p "${label} [${default}]: " out
  else
    read -r -p "${label}: " out
  fi
  if [[ -z "$out" ]]; then
    echo "$default"
  else
    echo "$out"
  fi
}

prompt_secret() {
  local label="$1" out
  read -r -s -p "${label}: " out
  echo >&2
  echo "$out"
}

prompt_yes_no() {
  local label="$1" default="${2:-y}" out
  local hint="[y/N]"
  if [[ "$default" == "y" ]]; then
    hint="[Y/n]"
  fi
  read -r -p "${label} ${hint}: " out
  out="${out:-$default}"
  case "$out" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

read_env_value() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || return 1
  awk -v k="$key" -F= '
    $1 == k {
      sub(k "=", "", $0)
      print $0
      exit
    }
  ' "$file"
}

is_valid_eth_address() {
  local addr="$1"
  [[ "$addr" =~ ^0x[0-9a-fA-F]{40}$ ]]
}

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ORIGINAL_ARGS=("$@")

ENV_FILE="$REPO_ROOT/.env"
TURN_ENV_FILE="$REPO_ROOT/.env.turn"
COMPOSE_FILE="$REPO_ROOT/docker-compose.unreal.yml"
ENV_TEMPLATE="$REPO_ROOT/orchestrator.env.example"

PAYMENTS_API_URL="http://3.141.111.200:8081"
IMAGE_REF="ghcr.io/its-define/unreal_vtuber/embody-ue-ps:enc-v1"
FORWARDER_IP="3.150.172.153"
PUBLIC_IP="auto"

ORCH_ID=""
ORCH_ADDRESS=""
ARTIFACT_URL=""
ORCH_TOKEN=""
ORCH_TOKEN_FILE=""
ORCH_TOKEN_ENV=""

SESSION_DIR=""
RECORDINGS_DIR=""

INSTALL_DEPS="0"
INSTALL_DOCKER="0"
INSTALL_NVIDIA_DRIVER="0"
INSTALL_NVIDIA_TOOLKIT="0"
ROTATE_TURN="0"
NO_PULL="0"
SKIP_ROLLOUT="0"
SKIP_REGISTRATION="0"
NO_VERIFY="0"
FORCE_ENV="0"
CONFIG_ONLY="0"

INTERACTIVE="auto"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --interactive)
      INTERACTIVE="1"
      shift 1
      ;;
    --non-interactive)
      INTERACTIVE="0"
      shift 1
      ;;
    --payments-api-url)
      PAYMENTS_API_URL="${2:-}"
      shift 2
      ;;
    --image-ref)
      IMAGE_REF="${2:-}"
      shift 2
      ;;
    --forwarder-ip)
      FORWARDER_IP="${2:-}"
      shift 2
      ;;
    --public-ip)
      PUBLIC_IP="${2:-}"
      shift 2
      ;;
    --orchestrator-id)
      ORCH_ID="${2:-}"
      shift 2
      ;;
    --orchestrator-address)
      ORCH_ADDRESS="${2:-}"
      shift 2
      ;;
    --artifact-url)
      ARTIFACT_URL="${2:-}"
      shift 2
      ;;
    --orch-token)
      ORCH_TOKEN="${2:-}"
      shift 2
      ;;
    --orch-token-file)
      ORCH_TOKEN_FILE="${2:-}"
      shift 2
      ;;
    --orch-token-env)
      ORCH_TOKEN_ENV="${2:-}"
      shift 2
      ;;
    --session-dir)
      SESSION_DIR="${2:-}"
      shift 2
      ;;
    --recordings-dir)
      RECORDINGS_DIR="${2:-}"
      shift 2
      ;;
    --install-deps)
      INSTALL_DEPS="1"
      shift 1
      ;;
    --install-docker)
      INSTALL_DOCKER="1"
      shift 1
      ;;
    --install-nvidia-driver)
      INSTALL_NVIDIA_DRIVER="1"
      shift 1
      ;;
    --install-nvidia-toolkit)
      INSTALL_NVIDIA_TOOLKIT="1"
      shift 1
      ;;
    --rotate-turn)
      ROTATE_TURN="1"
      shift 1
      ;;
    --no-pull)
      NO_PULL="1"
      shift 1
      ;;
    --skip-rollout)
      SKIP_ROLLOUT="1"
      shift 1
      ;;
    --skip-registration)
      SKIP_REGISTRATION="1"
      shift 1
      ;;
    --no-verify)
      NO_VERIFY="1"
      shift 1
      ;;
    --force-env)
      FORCE_ENV="1"
      shift 1
      ;;
    --config-only)
      CONFIG_ONLY="1"
      shift 1
      ;;
    *)
      die "unknown arg: $1 (run with --help)"
      ;;
  esac
done

if [[ ! -f "$COMPOSE_FILE" ]]; then
  die "compose file not found: $COMPOSE_FILE (are you in the repo?)"
fi

maybe_rerun_with_sudo_for_docker() {
  if [[ "$(id -u)" == "0" ]]; then
    return
  fi
  if ! command -v docker >/dev/null 2>&1; then
    return
  fi
  if docker info >/dev/null 2>&1; then
    return
  fi
  if ! command -v sudo >/dev/null 2>&1; then
    die "docker is installed but not accessible (and sudo is missing). Run as root or add your user to the docker group."
  fi
  if ! sudo -n docker info >/dev/null 2>&1; then
    if is_tty && prompt_yes_no "Docker requires sudo on this host. Re-run this script with sudo?" "y"; then
      exec sudo -E bash "$SCRIPT_PATH" "$@"
    fi
    die "docker daemon not reachable (re-run with sudo, or add your user to the docker group)"
  fi
  if is_tty && prompt_yes_no "Docker requires sudo on this host. Re-run this script with sudo?" "y"; then
    exec sudo -E bash "$SCRIPT_PATH" "$@"
  fi
  die "docker daemon not reachable (re-run with sudo, or add your user to the docker group)"
}

maybe_rerun_with_sudo_for_docker "${ORIGINAL_ARGS[@]}"

target_user="${SUDO_USER:-$USER}"
target_home=""
if command -v getent >/dev/null 2>&1; then
  target_home="$(getent passwd "$target_user" | cut -d: -f6 || true)"
fi
if [[ -z "$target_home" ]]; then
  target_home="$(eval echo "~${target_user}" 2>/dev/null || true)"
fi
if [[ -z "$target_home" ]]; then
  target_home="$HOME"
fi

if [[ -z "$SESSION_DIR" ]]; then
  SESSION_DIR="$target_home/vtuber_sessions"
fi
if [[ -z "$RECORDINGS_DIR" ]]; then
  RECORDINGS_DIR="$target_home/recordings"
fi

APT_UPDATED="0"

apt_install() {
  local pkgs=("$@")
  if ! command -v apt-get >/dev/null 2>&1; then
    die "apt-get not found; install deps manually: ${pkgs[*]}"
  fi
  if [[ "$(id -u)" != "0" ]]; then
    require_cmd sudo
  fi
  if [[ "$APT_UPDATED" != "1" ]]; then
    note "apt-get update"
    if [[ "$(id -u)" == "0" ]]; then
      DEBIAN_FRONTEND=noninteractive apt-get update -y
    else
      sudo DEBIAN_FRONTEND=noninteractive apt-get update -y
    fi
    APT_UPDATED="1"
  fi
  note "apt-get install: ${pkgs[*]}"
  if [[ "$(id -u)" == "0" ]]; then
    NEEDRESTART_MODE=a DEBIAN_FRONTEND=noninteractive \
      apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
      "${pkgs[@]}"
  else
    sudo NEEDRESTART_MODE=a DEBIAN_FRONTEND=noninteractive \
      apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
      "${pkgs[@]}"
  fi
}

install_deps_if_requested() {
  if [[ "$INSTALL_DEPS" != "1" ]]; then
    return
  fi
  apt_install curl jq zstd age python3
}

install_docker_if_requested() {
  if [[ "$INSTALL_DOCKER" != "1" ]]; then
    return
  fi
  apt_install docker.io

  # Prefer the v2 compose plugin when available, but fall back to the classic
  # `docker-compose` package on distros that don't ship the plugin.
  if apt-cache show docker-compose-plugin >/dev/null 2>&1; then
    apt_install docker-compose-plugin
  elif apt-cache show docker-compose >/dev/null 2>&1; then
    apt_install docker-compose
  else
    die "Docker Compose not available via apt on this host; install it manually"
  fi

  if command -v systemctl >/dev/null 2>&1; then
    if [[ "$(id -u)" == "0" ]]; then
      systemctl enable --now docker >/dev/null 2>&1 || true
    else
      sudo systemctl enable --now docker >/dev/null 2>&1 || true
    fi
  fi
}

install_nvidia_driver_if_requested() {
  if [[ "$INSTALL_NVIDIA_DRIVER" != "1" ]]; then
    return
  fi
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    note "NVIDIA driver already installed (nvidia-smi OK); skipping."
    return
  fi

  note "Installing NVIDIA driver (Ubuntu/Debian)"
  apt_install ubuntu-drivers-common

  if command -v ubuntu-drivers >/dev/null 2>&1; then
    ubuntu-drivers devices || true
    ubuntu-drivers autoinstall || true
  else
    die "ubuntu-drivers not available after install; install NVIDIA driver manually"
  fi

  note "NVIDIA driver install complete, but a reboot is usually required."
  if [[ "$INTERACTIVE" != "0" ]] && is_tty; then
    if prompt_yes_no "Reboot now?" "y"; then
      if [[ "$(id -u)" == "0" ]]; then
        reboot
      else
        sudo reboot
      fi
      exit 0
    fi
  fi
  die "reboot required; run 'sudo reboot' then rerun ./scripts/onboard_orchestrator.sh"
}

install_nvidia_toolkit_if_requested() {
  if [[ "$INSTALL_NVIDIA_TOOLKIT" != "1" ]]; then
    return
  fi
  if ! command -v /usr/bin/nvidia-smi >/dev/null 2>&1 && ! command -v nvidia-smi >/dev/null 2>&1; then
    note "NVIDIA driver not detected (nvidia-smi missing). Install the NVIDIA driver first, reboot, then rerun."
    return
  fi

  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release || true
  fi
  local distribution="${ID:-ubuntu}${VERSION_ID:-22.04}"

  apt_install ca-certificates curl gnupg

  local keyring="/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg"
  note "Adding NVIDIA container toolkit apt repo (${distribution})"
  if [[ "$(id -u)" == "0" ]]; then
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o "$keyring"
    curl -fsSL "https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list" \
      | sed "s#deb https://#deb [signed-by=${keyring}] https://#g" \
      > /etc/apt/sources.list.d/nvidia-container-toolkit.list
  else
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
      | sudo gpg --dearmor -o "$keyring"
    curl -fsSL "https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list" \
      | sed "s#deb https://#deb [signed-by=${keyring}] https://#g" \
      | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
  fi

  APT_UPDATED="0"
  apt_install nvidia-container-toolkit

  if command -v nvidia-ctk >/dev/null 2>&1; then
    note "Configuring NVIDIA runtime for Docker"
    if [[ "$(id -u)" == "0" ]]; then
      nvidia-ctk runtime configure --runtime=docker >/dev/null 2>&1 || true
    else
      sudo nvidia-ctk runtime configure --runtime=docker >/dev/null 2>&1 || true
    fi
  fi

  if command -v systemctl >/dev/null 2>&1; then
    note "Restarting Docker"
    if [[ "$(id -u)" == "0" ]]; then
      systemctl restart docker >/dev/null 2>&1 || true
    else
      sudo systemctl restart docker >/dev/null 2>&1 || true
    fi
  fi
}

detect_public_ip() {
  local token ip
  token="$(curl -fsS --max-time 2 -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)"
  if [[ -n "$token" ]]; then
    ip="$(curl -fsS --max-time 2 -H "X-aws-ec2-metadata-token: $token" \
      "http://169.254.169.254/latest/meta-data/public-ipv4" 2>/dev/null || true)"
  else
    ip="$(curl -fsS --max-time 2 "http://169.254.169.254/latest/meta-data/public-ipv4" 2>/dev/null || true)"
  fi
  if [[ -n "${ip:-}" ]]; then
    echo "$ip"
    return 0
  fi
  curl -fsS --max-time 3 https://api.ipify.org 2>/dev/null || true
}

ensure_env_file_exists() {
  if [[ -f "$ENV_FILE" ]]; then
    return
  fi
  if [[ -f "$ENV_TEMPLATE" ]]; then
    note "Creating $ENV_FILE from orchestrator.env.example"
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    return
  fi
  note "Creating empty $ENV_FILE"
  cat >"$ENV_FILE" <<'EOF_ENV'
# Generated by scripts/onboard_orchestrator.sh
EOF_ENV
}

upsert_env_kv() {
  local file="$1" key="$2" value="$3"
  local tmp
  tmp="$(mktemp)"

  ensure_env_file_exists

  awk -v key="$key" -v value="$value" '
    BEGIN { found=0 }
    $0 ~ ("^" key "=") {
      print key "=" value
      found=1
      next
    }
    { print }
    END { if (!found) print key "=" value }
  ' "$file" >"$tmp"
  mv "$tmp" "$file"
}

write_token_file_if_needed() {
  if [[ -n "$ORCH_TOKEN_FILE" || -n "$ORCH_TOKEN_ENV" ]]; then
    return
  fi
  if [[ -z "$ORCH_TOKEN" ]]; then
    return
  fi

  local token_dir token_file
  token_dir="$target_home/.embody"
  token_file="$token_dir/orch-license-token.txt"

  note "Writing orchestrator token to $token_file"
  mkdir -p "$token_dir"
  chmod 700 "$token_dir" || true
  printf '%s' "$ORCH_TOKEN" >"$token_file"
  chmod 600 "$token_file" || true
  if [[ "$(id -u)" == "0" && -n "$SUDO_USER" ]]; then
    chown "$SUDO_USER":"$SUDO_USER" "$token_dir" "$token_file" || true
  fi
  ORCH_TOKEN_FILE="$token_file"
  ORCH_TOKEN=""
}

maybe_run_wizard() {
  local need_prompt="0"

  if [[ "$INTERACTIVE" == "0" ]]; then
    return
  fi
  if [[ "$INTERACTIVE" == "1" ]]; then
    need_prompt="1"
  fi
  if [[ "$need_prompt" != "1" ]]; then
    if [[ -z "$ORCH_ID" || -z "$ORCH_ADDRESS" ]]; then
      need_prompt="1"
    fi
    if [[ "$SKIP_ROLLOUT" != "1" ]]; then
      if [[ -z "$ARTIFACT_URL" ]]; then
        need_prompt="1"
      fi
      if [[ -z "$ORCH_TOKEN" && -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" ]]; then
        need_prompt="1"
      fi
    fi
  fi

  if [[ "$need_prompt" != "1" ]]; then
    return
  fi
  if ! is_tty; then
    die "missing required args and no TTY available (run with --help)"
  fi

  if [[ "$(id -u)" != "0" ]] && command -v sudo >/dev/null 2>&1; then
    note "This setup often needs sudo (install packages + run Docker)."
    if prompt_yes_no "Re-run with sudo (recommended)?" "y"; then
      exec sudo -E bash "$SCRIPT_PATH" "${ORIGINAL_ARGS[@]}"
    fi
  fi

  note "Starting onboarding wizard…"

  local existing_orch_id existing_addr existing_payments existing_forwarder existing_session_dir existing_recordings_dir
  existing_orch_id="$(read_env_value "$ENV_FILE" "ORCHESTRATOR_ID" 2>/dev/null || true)"
  existing_addr="$(read_env_value "$ENV_FILE" "ORCHESTRATOR_ADDRESS" 2>/dev/null || true)"
  existing_payments="$(read_env_value "$ENV_FILE" "PAYMENTS_API_URL" 2>/dev/null || true)"
  existing_forwarder="$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null | awk -F, '{print $3}' || true)"
  existing_session_dir="$(read_env_value "$ENV_FILE" "VTUBER_SESSION_DIR" 2>/dev/null || true)"
  existing_recordings_dir="$(read_env_value "$ENV_FILE" "VTUBER_RECORDINGS_DIR" 2>/dev/null || true)"

  if [[ -z "$PAYMENTS_API_URL" || "$PAYMENTS_API_URL" == "http://3.141.111.200:8081" ]]; then
    PAYMENTS_API_URL="${existing_payments:-$PAYMENTS_API_URL}"
  fi
  PAYMENTS_API_URL="$(prompt_default "Payments API URL" "$PAYMENTS_API_URL")"

  if [[ -z "$ORCH_ID" ]]; then
    local suggested_id="orch-$(hostname -s 2>/dev/null || hostname || echo 'orch-1')"
    ORCH_ID="$(prompt_default "Orchestrator ID (from admin)" "${existing_orch_id:-$suggested_id}")"
  fi

  while [[ -z "$ORCH_ADDRESS" ]]; do
    ORCH_ADDRESS="$(prompt_default "Orchestrator payout wallet (0x...)" "${existing_addr:-}")"
    if ! is_valid_eth_address "$ORCH_ADDRESS"; then
      note "Wallet address must look like 0x + 40 hex chars"
      ORCH_ADDRESS=""
    fi
  done

  if [[ "$SKIP_ROLLOUT" != "1" ]]; then
    if ! prompt_yes_no "Do you have the admin-provided token + artifact URL and want to load the encrypted game image now?" "y"; then
      SKIP_ROLLOUT="1"
    fi
  fi

  if [[ "$SKIP_ROLLOUT" != "1" ]]; then
    ARTIFACT_URL="$(prompt_default "Encrypted artifact URL (.tar.zst.age)" "$ARTIFACT_URL")"
    while [[ -z "$ARTIFACT_URL" ]]; do
      ARTIFACT_URL="$(prompt_default "Encrypted artifact URL (.tar.zst.age)" "$ARTIFACT_URL")"
    done

    local default_token_file="$target_home/.embody/orch-license-token.txt"
    if [[ -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" && -z "$ORCH_TOKEN" ]]; then
      if [[ -s "$default_token_file" ]]; then
        if prompt_yes_no "Use existing token file at $default_token_file?" "y"; then
          ORCH_TOKEN_FILE="$default_token_file"
        fi
      fi
    fi

    if [[ -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" && -z "$ORCH_TOKEN" ]]; then
      local token_file
      token_file="$(prompt_default "Token file path (leave blank to paste token)" "$default_token_file")"
      if [[ -n "$token_file" && -f "$token_file" ]]; then
        ORCH_TOKEN_FILE="$token_file"
      else
        ORCH_TOKEN="$(prompt_secret "Paste orchestrator license token (hidden input)")"
      fi
    fi

    if [[ -z "$ORCH_TOKEN" && -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" ]]; then
      die "orchestrator token required to load encrypted image"
    fi
  fi

  if [[ -z "$FORWARDER_IP" || "$FORWARDER_IP" == "3.150.172.153" ]]; then
    FORWARDER_IP="${existing_forwarder:-$FORWARDER_IP}"
  fi
  FORWARDER_IP="$(prompt_default "Forwarder IP (allowlisted for runner/recorder/power)" "$FORWARDER_IP")"

  if [[ "$PUBLIC_IP" == "auto" ]]; then
    local detected
    detected="$(detect_public_ip || true)"
    if [[ -n "$detected" ]]; then
      note "Detected public IP: $detected"
      if prompt_yes_no "Use detected public IP ($detected)?" "y"; then
        PUBLIC_IP="$detected"
      else
        PUBLIC_IP="$(prompt_default "Public IP" "")"
      fi
    else
      PUBLIC_IP="$(prompt_default "Public IP" "")"
    fi
  fi

  SESSION_DIR="$(prompt_default "Session dir (host path)" "${existing_session_dir:-$SESSION_DIR}")"
  RECORDINGS_DIR="$(prompt_default "Recordings dir (host path)" "${existing_recordings_dir:-$RECORDINGS_DIR}")"

  note "Preflight:"
  local missing_deps=()
  for cmd in python3 jq zstd age; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing_deps+=("$cmd")
    fi
  done
  if ((${#missing_deps[@]})); then
    note "Missing deps: ${missing_deps[*]}"
    if prompt_yes_no "Install missing deps now? (Ubuntu/Debian via apt-get)" "y"; then
      INSTALL_DEPS="1"
    fi
  else
    note "Deps: OK (python3/jq/zstd/age)"
  fi

  if ! command -v docker >/dev/null 2>&1; then
    note "Docker: missing"
    if prompt_yes_no "Install Docker + Compose plugin now? (Ubuntu/Debian via apt-get)" "y"; then
      INSTALL_DOCKER="1"
    fi
  else
    note "Docker: present"
    if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
      note "Compose: missing"
      if prompt_yes_no "Install Compose plugin now? (Ubuntu/Debian via apt-get)" "y"; then
        INSTALL_DOCKER="1"
      fi
    else
      note "Compose: present"
    fi
  fi

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    note "GPU driver: nvidia-smi missing (cannot start the game container yet)."
    if prompt_yes_no "Install NVIDIA driver now? (Ubuntu/Debian via apt-get; requires reboot)" "y"; then
      INSTALL_NVIDIA_DRIVER="1"
    fi
  else
    note "GPU driver: nvidia-smi present"
  fi
  if prompt_yes_no "Install NVIDIA container toolkit if GPU runtime is missing?" "y"; then
    INSTALL_NVIDIA_TOOLKIT="1"
  fi

  if prompt_yes_no "Proceed with setup now?" "y"; then
    return
  fi
  die "aborted"
}

maybe_run_wizard

if [[ -z "$ORCH_ID" ]]; then
  die "--orchestrator-id is required (or run without --non-interactive to use the wizard)"
fi
if [[ -z "$ORCH_ADDRESS" ]]; then
  die "--orchestrator-address is required (or run without --non-interactive to use the wizard)"
fi
if ! is_valid_eth_address "$ORCH_ADDRESS"; then
  die "ORCHESTRATOR_ADDRESS must look like 0x + 40 hex chars"
fi

if [[ "$SKIP_ROLLOUT" != "1" ]]; then
  [[ -n "$ARTIFACT_URL" ]] || die "--artifact-url is required unless --skip-rollout is set"
  if [[ -z "$ORCH_TOKEN" && -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" ]]; then
    die "orchestrator token required (use --orch-token-file or --orch-token-env)"
  fi
fi

install_docker_if_requested
install_deps_if_requested
install_nvidia_driver_if_requested
install_nvidia_toolkit_if_requested

if [[ "$INTERACTIVE" == "0" ]]; then
  maybe_rerun_with_sudo_for_docker "${ORIGINAL_ARGS[@]}"
fi

require_cmd docker
require_cmd curl
require_cmd python3

if ! docker info >/dev/null 2>&1; then
  note "Waiting for Docker daemon..."
  for _ in $(seq 1 15); do
    sleep 1
    if docker info >/dev/null 2>&1; then
      break
    fi
  done
fi
if ! docker info >/dev/null 2>&1; then
  die "docker daemon not reachable (try running with sudo, or add your user to the docker group)"
fi

compose_cmd=()
if docker compose version >/dev/null 2>&1; then
  compose_cmd=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  die "missing dependency: docker compose (or docker-compose)"
fi

if [[ "$PUBLIC_IP" == "auto" ]]; then
  note "Detecting public IP…"
  PUBLIC_IP="$(detect_public_ip || true)"
  [[ -n "$PUBLIC_IP" ]] || die "could not detect public IP; pass --public-ip <ip>"
fi

note "Using PUBLIC_IP=$PUBLIC_IP"
note "Using PAYMENTS_API_URL=$PAYMENTS_API_URL"

write_token_file_if_needed

if [[ "$FORCE_ENV" == "1" ]]; then
  note "Regenerating $ENV_FILE"
  rm -f "$ENV_FILE"
fi

ensure_env_file_exists

upsert_env_kv "$ENV_FILE" "PAYMENTS_API_URL" "$PAYMENTS_API_URL"
upsert_env_kv "$ENV_FILE" "ORCHESTRATOR_ID" "$ORCH_ID"
upsert_env_kv "$ENV_FILE" "ORCHESTRATOR_ADDRESS" "$ORCH_ADDRESS"
upsert_env_kv "$ENV_FILE" "PUBLIC_IP" "$PUBLIC_IP"
upsert_env_kv "$ENV_FILE" "ORCHESTRATOR_HOST_PUBLIC_IP" "$PUBLIC_IP"
upsert_env_kv "$ENV_FILE" "ORCHESTRATOR_HEALTH_URL" "http://$PUBLIC_IP:9090/health"
upsert_env_kv "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" "127.0.0.1,::1,$FORWARDER_IP"
upsert_env_kv "$ENV_FILE" "VTUBER_SESSION_DIR" "$SESSION_DIR"
upsert_env_kv "$ENV_FILE" "VTUBER_RECORDINGS_DIR" "$RECORDINGS_DIR"

chmod 600 "$ENV_FILE" >/dev/null 2>&1 || true
if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
  chown "$SUDO_USER":"$SUDO_USER" "$ENV_FILE" >/dev/null 2>&1 || true
fi

note "Ensuring host directories exist"
mkdir -p "$SESSION_DIR" "$RECORDINGS_DIR"
if [[ "$(id -u)" == "0" && -n "$SUDO_USER" ]]; then
  chown "$SUDO_USER":"$SUDO_USER" "$SESSION_DIR" "$RECORDINGS_DIR" || true
fi

note "Ensuring vtuber_network exists"
docker network create vtuber_network 2>/dev/null || true

if [[ "$ROTATE_TURN" == "1" || ! -s "$TURN_ENV_FILE" ]]; then
  note "Generating TURN credentials (.env.turn)"
  (cd "$REPO_ROOT" && PUBLIC_IP="$PUBLIC_IP" ./scripts/generate_turn_credentials.sh)
else
  note "Keeping existing $TURN_ENV_FILE (use --rotate-turn to regenerate)"
fi
if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
  chown "$SUDO_USER":"$SUDO_USER" "$TURN_ENV_FILE" >/dev/null 2>&1 || true
fi

if [[ "$CONFIG_ONLY" == "1" ]]; then
  note "Config-only mode; exiting after writing env files."
  exit 0
fi

require_nvidia_prereqs() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    note "NVIDIA driver not detected (nvidia-smi missing)."
    if [[ "$INTERACTIVE" != "0" ]] && is_tty && prompt_yes_no "Write config only and exit? (install GPU driver + NVIDIA Container Toolkit, then rerun)" "y"; then
      exit 0
    fi
    die "install NVIDIA driver (nvidia-smi) and rerun; or use --config-only"
  fi
  if ! nvidia-smi >/dev/null 2>&1; then
    note "NVIDIA driver detected but nvidia-smi failed."
    if [[ "$INTERACTIVE" != "0" ]] && is_tty && prompt_yes_no "Write config only and exit? (fix driver, then rerun)" "y"; then
      exit 0
    fi
    die "fix NVIDIA driver (nvidia-smi) and rerun; or use --config-only"
  fi

  # Compose file uses `runtime: nvidia`; ensure Docker knows about the runtime.
  local runtimes
  runtimes="$(docker info --format '{{json .Runtimes}}' 2>/dev/null || true)"
  if [[ -z "$runtimes" ]]; then
    runtimes="$(docker info 2>/dev/null | awk -F: '/Runtimes:/ {print $2}' | tr -d ' ' || true)"
  fi
  if ! echo "$runtimes" | grep -qi "nvidia"; then
    note "Docker NVIDIA runtime not configured (no 'nvidia' runtime in docker info)."
    if [[ "$INSTALL_NVIDIA_TOOLKIT" == "1" ]]; then
      note "Tried to install NVIDIA container toolkit; you may need to restart Docker and/or log out/in."
    fi
    if [[ "$INTERACTIVE" != "0" ]] && is_tty && prompt_yes_no "Write config only and exit? (install/configure nvidia-container-toolkit, then rerun)" "y"; then
      exit 0
    fi
    die "install/configure nvidia-container-toolkit so Docker has an 'nvidia' runtime; or use --config-only"
  fi
}

require_nvidia_prereqs

if [[ "$NO_PULL" != "1" ]]; then
  note "Pulling service images"
  "${compose_cmd[@]}" -f "$COMPOSE_FILE" pull \
    turn-server unreal-signaling \
    vtuber-script-runner vtuber-watchdog \
    orchestrator-registration orchestrator-health \
    vtuber-auto-updater recorder-control
fi

if [[ "$SKIP_ROLLOUT" == "1" ]]; then
  note "Starting compose stack (skipping encrypted rollout)"
  "${compose_cmd[@]}" -f "$COMPOSE_FILE" up -d
else
  require_cmd jq
  require_cmd zstd
  require_cmd age

  rollout_args=()
  if [[ "$NO_VERIFY" == "1" ]]; then
    rollout_args+=(--no-verify)
  fi

  note "Rolling out encrypted game image + starting compose stack"
  token_args=()
  if [[ -n "$ORCH_TOKEN_ENV" ]]; then
    token_args+=(--orch-token-env "$ORCH_TOKEN_ENV")
  elif [[ -n "$ORCH_TOKEN_FILE" ]]; then
    token_args+=(--orch-token-file "$ORCH_TOKEN_FILE")
  elif [[ -n "$ORCH_TOKEN" ]]; then
    token_args+=(--orch-token "$ORCH_TOKEN")
  fi
  "$REPO_ROOT/tools/encrypted-game-image/rollout.sh" \
    --payments-api-url "$PAYMENTS_API_URL" \
    --image-ref "$IMAGE_REF" \
    --artifact-url "$ARTIFACT_URL" \
    "${token_args[@]}" \
    "${rollout_args[@]}"
fi

if [[ "$SKIP_REGISTRATION" != "1" ]]; then
  note "Registering orchestrator with Payments (best-effort)"
  "${compose_cmd[@]}" -f "$COMPOSE_FILE" run --rm orchestrator-registration >/dev/null 2>&1 || true
fi

note "Health checks (best-effort)"
curl -fsS --max-time 2 http://127.0.0.1:9877/health >/dev/null 2>&1 || true
curl -fsS --max-time 2 http://127.0.0.1:8080/healthz >/dev/null 2>&1 || true
curl -fsS --max-time 2 http://127.0.0.1:9090/health >/dev/null 2>&1 || true

cat >&2 <<EOF

[onboard] Done.

Next:
  1) Ensure inbound allowlists / firewall rules are set:
     - Forwarder ${FORWARDER_IP} -> TCP 8080,8888,8889,9877 and UDP 3478,49160-49200
     - Payments backend -> TCP 9090 (health monitoring)

  2) Verify locally:
     - Signaling health:    curl http://127.0.0.1:8080/healthz
     - Runner health:       curl http://127.0.0.1:9877/health
     - Orchestrator health: curl http://127.0.0.1:9090/health

  3) If registration didn’t show up yet, rerun:
     ${compose_cmd[*]} -f docker-compose.unreal.yml run --rm orchestrator-registration
EOF
