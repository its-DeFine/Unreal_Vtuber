#!/usr/bin/env bash
set -euo pipefail

USE_COLOR="0"
USE_FX="0"
COLOR_MODE="auto"
FX_MODE="auto"

STYLE_RESET=""
STYLE_BOLD=""
STYLE_DIM=""
STYLE_RED=""
STYLE_GRN=""
STYLE_YLW=""
STYLE_BLU=""
STYLE_CYN=""

usage() {
  cat <<'EOF'
Interactive orchestrator onboarding (encrypted game image flow).

If you run this script with no flags, it launches a CLI wizard that:
  - checks prerequisites (and can install missing deps on Ubuntu/Debian)
  - asks for the required inputs (orchestrator ID/address + token + artifact URL)
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
  --advanced                  Prompt for optional settings (Payments URL, forwarder IP, paths)
  --no-color                  Disable ANSI colors
  --no-fx                     Disable transition effects
  --install-deps              Attempt apt-get install of curl/jq/zstd/age/python3 (Ubuntu/Debian only)
  --install-docker            Attempt apt-get install of docker + compose plugin (Ubuntu/Debian only)
  --install-nvidia-driver     Attempt to install the NVIDIA driver (Ubuntu/Debian only; requires reboot)
  --install-nvidia-toolkit    Attempt to install nvidia-container-toolkit (Ubuntu/Debian only)
  --rotate-turn               Regenerate .env.turn even if present
  --no-pull                   Skip docker compose pull
  --skip-registration         Skip running orchestrator-registration
  --no-verify                 Skip rollout health checks
  --apply-firewall            Attempt to apply inbound allowlist rules (default: on for interactive wizard)
  --no-apply-firewall         Do not modify firewall / security group rules
  --force-env                 Overwrite .env (otherwise upsert keys)

Examples:
  # Recommended: store the license token in a file (admin provides it)
  mkdir -p ~/.embody && chmod 700 ~/.embody
  printf '%s' '<ORCH_TOKEN>' > ~/.embody/orch-license-token.txt && chmod 600 ~/.embody/orch-license-token.txt

  git clone https://github.com/its-DeFine/Unreal_Vtuber.git && cd Unreal_Vtuber && ./scripts/onboard_orchestrator.sh
EOF
}

die() {
  echo "${STYLE_RED}error:${STYLE_RESET} $*" >&2
  exit 1
}

note() {
  echo "${STYLE_CYN}[onboard]${STYLE_RESET} $*" >&2
}

warn() {
  echo "${STYLE_YLW}[warn]${STYLE_RESET} $*" >&2
}

ok() {
  echo "${STYLE_GRN}[ok]${STYLE_RESET} $*" >&2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing dependency: $1"
}

is_tty() {
  [[ -t 0 && -t 1 ]]
}

supports_color() {
  is_tty || return 1
  [[ "${TERM:-}" != "dumb" ]] || return 1
  [[ -z "${NO_COLOR:-}" ]] || return 1
  return 0
}

supports_fx() {
  is_tty || return 1
  [[ "${TERM:-}" != "dumb" ]] || return 1
  [[ -z "${CI:-}" ]] || return 1
  return 0
}

init_ui() {
  case "$COLOR_MODE" in
    always) USE_COLOR="1" ;;
    never) USE_COLOR="0" ;;
    auto)
      if supports_color; then USE_COLOR="1"; else USE_COLOR="0"; fi
      ;;
    *) USE_COLOR="0" ;;
  esac

  case "$FX_MODE" in
    always) USE_FX="1" ;;
    never) USE_FX="0" ;;
    auto)
      if supports_fx && [[ "$INTERACTIVE" != "0" ]]; then USE_FX="1"; else USE_FX="0"; fi
      ;;
    *) USE_FX="0" ;;
  esac

  if [[ "$USE_COLOR" == "1" ]]; then
    STYLE_RESET=$'\033[0m'
    STYLE_BOLD=$'\033[1m'
    STYLE_DIM=$'\033[2m'
    STYLE_RED=$'\033[31m'
    STYLE_GRN=$'\033[32m'
    STYLE_YLW=$'\033[33m'
    STYLE_BLU=$'\033[34m'
    STYLE_CYN=$'\033[36m'
  fi
}

divider() {
  printf '%s\n' "------------------------------------------------------------" >&2
}

section() {
  echo >&2
  echo "${STYLE_BOLD}${STYLE_BLU}==> $*${STYLE_RESET}" >&2
}

banner() {
  divider
  echo "${STYLE_BOLD}${STYLE_CYN}Embody Unreal Vtuber${STYLE_RESET} ${STYLE_DIM}— Orchestrator Onboarding${STYLE_RESET}" >&2
  echo "${STYLE_DIM}Press Ctrl+C anytime to abort.${STYLE_RESET}" >&2
  divider
}

fx_dots() {
  local msg="$1"
  if [[ "$USE_FX" != "1" ]]; then
    note "$msg"
    return
  fi
  printf "%s" "${STYLE_DIM}${msg}${STYLE_RESET}" >&2
  for _ in 1 2 3; do
    sleep 0.15
    printf "." >&2
  done
  printf "\n" >&2
}

prompt_default() {
  local label="$1" default="$2" out
  if [[ -n "$default" ]]; then
    read -r -p "${STYLE_BOLD}${label}${STYLE_RESET} [${STYLE_DIM}${default}${STYLE_RESET}]: " out
  else
    read -r -p "${STYLE_BOLD}${label}${STYLE_RESET}: " out
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
  read -r -p "${STYLE_BOLD}${label}${STYLE_RESET} ${STYLE_DIM}${hint}${STYLE_RESET}: " out
  out="${out:-$default}"
  case "$out" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

trim_whitespace() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

strip_inline_comment() {
  local s="$1"
  s="${s%%#*}"
  trim_whitespace "$s"
}

redact_url() {
  local url="$1"
  url="${url%%\?*}"
  if [[ ${#url} -gt 96 ]]; then
    echo "${url:0:93}..."
  else
    echo "$url"
  fi
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

is_zero_eth_address() {
  local addr="$1"
  [[ "$addr" == "0x0000000000000000000000000000000000000000" ]]
}

is_valid_orchestrator_id() {
  local id="$1"
  [[ "$id" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$ ]]
}

is_valid_email() {
  local email="$1"
  [[ "$email" == *"@"* ]] || return 1
  [[ "$email" != "@"* ]] || return 1
  [[ "$email" != *"@" ]] || return 1
  return 0
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
ORCH_CONTACT_EMAIL=""
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
SKIP_REGISTRATION="0"
NO_VERIFY="0"
FORCE_ENV="0"
APPLY_FIREWALL="auto"

INTERACTIVE="auto"
ADVANCED="0"

SESSION_DIR_SET="0"
RECORDINGS_DIR_SET="0"

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
    --advanced)
      ADVANCED="1"
      shift 1
      ;;
    --no-color)
      COLOR_MODE="never"
      shift 1
      ;;
    --no-fx)
      FX_MODE="never"
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
      SESSION_DIR_SET="1"
      shift 2
      ;;
    --recordings-dir)
      RECORDINGS_DIR="${2:-}"
      RECORDINGS_DIR_SET="1"
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
    --skip-registration)
      SKIP_REGISTRATION="1"
      shift 1
      ;;
    --no-verify)
      NO_VERIFY="1"
      shift 1
      ;;
    --apply-firewall)
      APPLY_FIREWALL="1"
      shift 1
      ;;
    --no-apply-firewall)
      APPLY_FIREWALL="0"
      shift 1
      ;;
    --force-env)
      FORCE_ENV="1"
      shift 1
      ;;
    *)
      die "unknown arg: $1 (run with --help)"
      ;;
  esac
done

init_ui

if [[ ! -f "$COMPOSE_FILE" ]]; then
  die "compose file not found: $COMPOSE_FILE (are you in the repo?)"
fi

cd "$REPO_ROOT"

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
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --batch --yes --dearmor -o "$keyring"
    curl -fsSL "https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list" \
      | sed "s#deb https://#deb [signed-by=${keyring}] https://#g" \
      > /etc/apt/sources.list.d/nvidia-container-toolkit.list
  else
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
      | sudo gpg --batch --yes --dearmor -o "$keyring"
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

extract_host_from_url() {
  local url="$1" hostport host
  hostport="${url#*://}"
  hostport="${hostport%%/*}"
  host="${hostport%%:*}"
  echo "$host"
}

is_ipv4() {
  local ip="$1"
  [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]
}

imds_get() {
  local path="$1" token
  token="$(curl -fsS --max-time 2 -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)"
  if [[ -n "$token" ]]; then
    curl -fsS --max-time 2 -H "X-aws-ec2-metadata-token: $token" \
      "http://169.254.169.254/latest/${path}" 2>/dev/null || true
  else
    curl -fsS --max-time 2 "http://169.254.169.254/latest/${path}" 2>/dev/null || true
  fi
}

is_ec2() {
  local iid
  iid="$(imds_get meta-data/instance-id || true)"
  [[ -n "$iid" ]]
}

run_as_target_user() {
  if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
    sudo -u "$SUDO_USER" -E "$@"
  else
    "$@"
  fi
}

should_apply_firewall() {
  case "$APPLY_FIREWALL" in
    1) return 0 ;;
    0) return 1 ;;
    auto)
      if [[ "$INTERACTIVE" != "0" ]] && is_tty; then
        return 0
      fi
      return 1
      ;;
    *) return 1 ;;
  esac
}

ensure_ufw_rules_best_effort() {
  if ! command -v ufw >/dev/null 2>&1; then
    return 0
  fi
  if ! ufw status 2>/dev/null | grep -qi "Status: active"; then
    return 0
  fi

  local ufw_cmd=(ufw)
  if [[ "$(id -u)" != "0" ]]; then
    ufw_cmd=(sudo ufw)
  fi

  local payments_host payments_ip
  payments_host="$(extract_host_from_url "$PAYMENTS_API_URL")"
  if is_ipv4 "$payments_host"; then
    payments_ip="$payments_host"
  else
    payments_ip=""
  fi

  note "UFW detected (active); applying inbound allowlist rules"

  local forwarder_cidr="${FORWARDER_IP}/32"
  "${ufw_cmd[@]}" allow from "$forwarder_cidr" to any port 8080 proto tcp >/dev/null 2>&1 || true
  "${ufw_cmd[@]}" allow from "$forwarder_cidr" to any port 8888 proto tcp >/dev/null 2>&1 || true
  "${ufw_cmd[@]}" allow from "$forwarder_cidr" to any port 8889 proto tcp >/dev/null 2>&1 || true
  "${ufw_cmd[@]}" allow from "$forwarder_cidr" to any port 9877 proto tcp >/dev/null 2>&1 || true
  "${ufw_cmd[@]}" allow from "$forwarder_cidr" to any port 3478 proto udp >/dev/null 2>&1 || true
  "${ufw_cmd[@]}" allow from "$forwarder_cidr" to any port 49160:49200 proto udp >/dev/null 2>&1 || true

  if [[ -n "$payments_ip" ]]; then
    "${ufw_cmd[@]}" allow from "${payments_ip}/32" to any port 9090 proto tcp >/dev/null 2>&1 || true
  fi

  "${ufw_cmd[@]}" reload >/dev/null 2>&1 || true
}

ensure_ec2_sg_rules_best_effort() {
  if ! is_ec2; then
    return 0
  fi

  local region instance_id
  instance_id="$(imds_get meta-data/instance-id || true)"
  region="$(imds_get dynamic/instance-identity/document | jq -r '.region // empty' 2>/dev/null || true)"
  if [[ -z "$instance_id" || -z "$region" ]]; then
    return 0
  fi

  if ! command -v aws >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      if [[ "$INTERACTIVE" != "0" ]] && is_tty; then
        if prompt_yes_no "AWS CLI not found. Install awscli to auto-apply EC2 security group rules?" "y"; then
          note "Installing awscli (best-effort)"
          if [[ "$(id -u)" == "0" ]]; then
            DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1 || true
            NEEDRESTART_MODE=a DEBIAN_FRONTEND=noninteractive apt-get install -y awscli >/dev/null 2>&1 || true
          else
            sudo DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1 || true
            sudo NEEDRESTART_MODE=a DEBIAN_FRONTEND=noninteractive apt-get install -y awscli >/dev/null 2>&1 || true
          fi
        fi
      fi
    fi
  fi

  if ! command -v aws >/dev/null 2>&1; then
    warn "AWS CLI not available; cannot auto-apply EC2 security group rules (install awscli + provide credentials/instance role)."
    return 0
  fi

  if ! run_as_target_user aws sts get-caller-identity --output json >/dev/null 2>&1; then
    warn "AWS credentials/permissions not available on this host; cannot auto-apply EC2 security group rules."
    return 0
  fi

  local sg_json sg_count selected_idx sg_id
  sg_json="$(run_as_target_user aws ec2 describe-instances --region "$region" --instance-ids "$instance_id" --output json \
    --query 'Reservations[0].Instances[0].SecurityGroups' 2>/dev/null || true)"
  sg_count="$(echo "$sg_json" | jq 'length' 2>/dev/null || echo 0)"
  if [[ "$sg_count" -le 0 ]]; then
    warn "Could not determine EC2 security groups for instance $instance_id"
    return 0
  fi

  selected_idx="0"
  if [[ "$sg_count" -gt 1 && "$INTERACTIVE" != "0" ]] && is_tty; then
    note "Security groups attached to this instance:"
    echo "$sg_json" | jq -r 'to_entries[] | "  [\(.key+1)] \(.value.GroupId) (\(.value.GroupName))"' >&2
    local picked
    picked="$(prompt_default "Select security group to modify" "1")"
    if [[ "$picked" =~ ^[0-9]+$ ]] && ((picked >= 1 && picked <= sg_count)); then
      selected_idx="$((picked - 1))"
    fi
  fi

  sg_id="$(echo "$sg_json" | jq -r ".[${selected_idx}].GroupId // empty" 2>/dev/null || true)"
  if [[ -z "$sg_id" ]]; then
    warn "Could not select a security group to modify"
    return 0
  fi

  local payments_host payments_ip
  payments_host="$(extract_host_from_url "$PAYMENTS_API_URL")"
  if is_ipv4 "$payments_host"; then
    payments_ip="$payments_host"
  else
    payments_ip=""
  fi

  note "Ensuring EC2 security group ingress rules on $sg_id (region $region)"

  aws_authorize_ingress() {
    local proto="$1" port="$2" cidr="$3" out
    out="$(run_as_target_user aws ec2 authorize-security-group-ingress --region "$region" \
      --group-id "$sg_id" --protocol "$proto" --port "$port" --cidr "$cidr" 2>&1)" || true
    if [[ -z "$out" ]]; then
      ok "SG rule ensured: $proto $port from $cidr"
      return 0
    fi
    if echo "$out" | grep -q "InvalidPermission.Duplicate"; then
      ok "SG rule present: $proto $port from $cidr"
      return 0
    fi
    if echo "$out" | grep -qi "UnauthorizedOperation\\|AccessDenied"; then
      warn "AWS denied updating SG rules: $proto $port from $cidr"
      warn "  $out"
      return 0
    fi
    # Some AWS CLI versions print JSON on success; treat non-error as ok.
    if echo "$out" | grep -q "\"Return\"[[:space:]]*:[[:space:]]*true"; then
      ok "SG rule ensured: $proto $port from $cidr"
      return 0
    fi
    warn "Failed to ensure SG rule: $proto $port from $cidr"
    warn "  $out"
    return 0
  }

  local forwarder_cidr="${FORWARDER_IP}/32"
  aws_authorize_ingress tcp 8080 "$forwarder_cidr"
  aws_authorize_ingress tcp 8888 "$forwarder_cidr"
  aws_authorize_ingress tcp 8889 "$forwarder_cidr"
  aws_authorize_ingress tcp 9877 "$forwarder_cidr"
  aws_authorize_ingress udp 3478 "$forwarder_cidr"
  aws_authorize_ingress udp 49160-49200 "$forwarder_cidr"

  if [[ -n "$payments_ip" ]]; then
    aws_authorize_ingress tcp 9090 "${payments_ip}/32"
  else
    warn "Payments API host is not an IPv4; skipping SG rule for TCP 9090 (health monitoring)."
  fi
}

ensure_inbound_rules_best_effort() {
  if ! should_apply_firewall; then
    return 0
  fi
  note "Checking/applying inbound allowlist rules (best-effort)"

  # Try host-level firewall first (if present), then EC2 SG rules (if available).
  if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -qi "Status: active"; then
    ensure_ufw_rules_best_effort
  fi
  ensure_ec2_sg_rules_best_effort
}

verify_payments_registration_best_effort() {
  local url json
  url="${PAYMENTS_API_URL%/}/api/orchestrators"
  fx_dots "Verifying registration in Payments"

  for _ in $(seq 1 20); do
    json="$(curl -fsS --max-time 5 "$url" 2>/dev/null || true)"
    if [[ -n "$json" ]]; then
      if echo "$json" | jq -e --arg id "$ORCH_ID" '
        if type == "array" then
          any(.[]; (.orchestrator_id? == $id) or (.orchestratorId? == $id) or (.id? == $id))
        elif (.orchestrators? | type) == "array" then
          any(.orchestrators[]; (.orchestrator_id? == $id) or (.orchestratorId? == $id) or (.id? == $id))
        else
          false
        end
      ' >/dev/null 2>&1; then
        ok "Registration verified in Payments (orchestrator_id=$ORCH_ID)"
        return 0
      fi
    fi
    sleep 2
  done

  warn "Could not verify registration in Payments yet (orchestrator_id=$ORCH_ID)."
  warn "If this persists, check firewall rules (TCP 9090 from Payments, and forwarder allowlists) and rerun registration."
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
    if [[ -z "$ARTIFACT_URL" ]]; then
      need_prompt="1"
    fi
    if [[ -z "$ORCH_TOKEN" && -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" ]]; then
      need_prompt="1"
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

  banner
  fx_dots "Starting onboarding wizard"

  echo "${STYLE_DIM}You will need:${STYLE_RESET}" >&2
  echo "  - A unique orchestrator ID (you choose)" >&2
  echo "  - Payout wallet address (0x...)" >&2
  echo "  - License token + encrypted artifact URL (admin provides)" >&2
  echo "${STYLE_DIM}Tip:${STYLE_RESET} run with ${STYLE_BOLD}--advanced${STYLE_RESET} to override Payments URL, forwarder IP, or host paths." >&2

  local existing_orch_id existing_addr existing_payments existing_forwarder existing_session_dir existing_recordings_dir
  existing_orch_id="$(read_env_value "$ENV_FILE" "ORCHESTRATOR_ID" 2>/dev/null || true)"
  existing_addr="$(read_env_value "$ENV_FILE" "ORCHESTRATOR_ADDRESS" 2>/dev/null || true)"
  existing_orch_id="$(trim_whitespace "$existing_orch_id")"
  existing_addr="$(trim_whitespace "$existing_addr")"
  existing_payments="$(read_env_value "$ENV_FILE" "PAYMENTS_API_URL" 2>/dev/null || true)"
  if [[ -z "$existing_payments" ]]; then
    existing_payments="$(read_env_value "$ENV_TEMPLATE" "PAYMENTS_API_URL" 2>/dev/null || true)"
  fi

  existing_forwarder="$(read_env_value "$ENV_FILE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null | awk -F, '{print $3}' || true)"
  if [[ -z "$existing_forwarder" ]]; then
    existing_forwarder="$(read_env_value "$ENV_TEMPLATE" "VTUBER_ALLOWED_ADDRESSES" 2>/dev/null | awk -F, '{print $3}' || true)"
  fi

  existing_session_dir="$(read_env_value "$ENV_FILE" "VTUBER_SESSION_DIR" 2>/dev/null || true)"
  if [[ -z "$existing_session_dir" ]]; then
    existing_session_dir="$(read_env_value "$ENV_TEMPLATE" "VTUBER_SESSION_DIR" 2>/dev/null || true)"
  fi

  existing_recordings_dir="$(read_env_value "$ENV_FILE" "VTUBER_RECORDINGS_DIR" 2>/dev/null || true)"
  if [[ -z "$existing_recordings_dir" ]]; then
    existing_recordings_dir="$(read_env_value "$ENV_TEMPLATE" "VTUBER_RECORDINGS_DIR" 2>/dev/null || true)"
  fi

  if [[ -z "$PAYMENTS_API_URL" || "$PAYMENTS_API_URL" == "http://3.141.111.200:8081" ]]; then
    PAYMENTS_API_URL="${existing_payments:-$PAYMENTS_API_URL}"
  fi
  if [[ "$ADVANCED" == "1" || -z "$PAYMENTS_API_URL" ]]; then
    PAYMENTS_API_URL="$(prompt_default "Payments API URL" "$PAYMENTS_API_URL")"
  fi

  section "Identity"

  if [[ -z "$ORCH_ID" ]]; then
    if [[ -n "$existing_orch_id" ]] && is_valid_orchestrator_id "$existing_orch_id"; then
      ORCH_ID="$existing_orch_id"
    else
      note "Choose a unique orchestrator ID (1-64 chars; letters/numbers/dot/underscore/dash)."
      while [[ -z "$ORCH_ID" ]]; do
        ORCH_ID="$(prompt_default "Orchestrator ID (unique; you choose)" "")"
        ORCH_ID="$(trim_whitespace "$ORCH_ID")"
        if [[ -z "$ORCH_ID" ]]; then
          note "Orchestrator ID is required."
          continue
        fi
        if ! is_valid_orchestrator_id "$ORCH_ID"; then
          note "Invalid ID. Use 1-64 chars: letters/numbers/dot/underscore/dash (start with a letter/number)."
          ORCH_ID=""
        fi
      done
    fi
  fi

  while [[ -z "$ORCH_ADDRESS" ]]; do
    ORCH_ADDRESS="$(prompt_default "Orchestrator payout wallet address (0x...)" "${existing_addr:-}")"
    if ! is_valid_eth_address "$ORCH_ADDRESS"; then
      note "Wallet address must look like 0x + 40 hex chars"
      ORCH_ADDRESS=""
      continue
    fi
    if is_zero_eth_address "$ORCH_ADDRESS"; then
      note "Wallet address cannot be 0x0000000000000000000000000000000000000000"
      ORCH_ADDRESS=""
    fi
  done

  local existing_email
  existing_email="$(read_env_value "$ENV_FILE" "ORCHESTRATOR_CONTACT_EMAIL" 2>/dev/null || true)"
  if [[ -z "$existing_email" ]]; then
    existing_email="$(read_env_value "$ENV_TEMPLATE" "ORCHESTRATOR_CONTACT_EMAIL" 2>/dev/null || true)"
  fi
  existing_email="$(trim_whitespace "$existing_email")"
  existing_email="$(strip_inline_comment "$existing_email")"

  if [[ -z "$ORCH_CONTACT_EMAIL" ]]; then
    ORCH_CONTACT_EMAIL="$(prompt_default "Contact email (optional)" "$existing_email")"
    ORCH_CONTACT_EMAIL="$(trim_whitespace "$ORCH_CONTACT_EMAIL")"
    if [[ -n "$ORCH_CONTACT_EMAIL" ]] && ! is_valid_email "$ORCH_CONTACT_EMAIL"; then
      note "Contact email must include '@' (or leave blank)"
      ORCH_CONTACT_EMAIL=""
    fi
  fi

  section "Encrypted Build"

  note "You need the admin-provided license token + encrypted artifact URL to continue."
  note "If you don’t have them yet, press Ctrl+C and request them from your admin."

  ARTIFACT_URL="$(prompt_default "Encrypted artifact URL (.tar.zst.age)" "$ARTIFACT_URL")"
  while [[ -z "$ARTIFACT_URL" ]]; do
    ARTIFACT_URL="$(prompt_default "Encrypted artifact URL (.tar.zst.age)" "$ARTIFACT_URL")"
  done

  local default_token_file="$target_home/.embody/orch-license-token.txt"
  if [[ -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" && -z "$ORCH_TOKEN" ]]; then
    if [[ -s "$default_token_file" ]]; then
      if prompt_yes_no "Use token file at $default_token_file?" "y"; then
        ORCH_TOKEN_FILE="$default_token_file"
      else
        ORCH_TOKEN="$(prompt_secret "Paste orchestrator license token (hidden input)")"
      fi
    else
      ORCH_TOKEN="$(prompt_secret "Paste orchestrator license token (hidden input)")"
    fi
  fi

  if [[ -n "$ORCH_TOKEN" && -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" ]]; then
    note "We will save it to $default_token_file (chmod 600) so you don't have to paste again."
  fi

  if [[ -z "$ORCH_TOKEN" && -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" ]]; then
    die "orchestrator token required to load encrypted image"
  fi

  section "Network"

  if [[ -z "$FORWARDER_IP" || "$FORWARDER_IP" == "3.150.172.153" ]]; then
    FORWARDER_IP="${existing_forwarder:-$FORWARDER_IP}"
  fi
  if [[ "$ADVANCED" == "1" || -z "$FORWARDER_IP" ]]; then
    FORWARDER_IP="$(prompt_default "Forwarder IP (allowlisted for runner/recorder/power)" "$FORWARDER_IP")"
  fi

  if [[ "$PUBLIC_IP" == "auto" ]]; then
    fx_dots "Detecting public IP"
    local detected
    detected="$(detect_public_ip || true)"
    if [[ -n "$detected" ]]; then
      note "Detected public IP: $detected"
      if [[ "$ADVANCED" == "1" ]]; then
        PUBLIC_IP="$(prompt_default "Public IP" "$detected")"
      else
        PUBLIC_IP="$detected"
      fi
    else
      PUBLIC_IP="$(prompt_default "Public IP" "")"
    fi
  fi

  section "Storage"

  existing_session_dir="$(strip_inline_comment "$existing_session_dir")"
  existing_recordings_dir="$(strip_inline_comment "$existing_recordings_dir")"

  if [[ "$SESSION_DIR_SET" != "1" && -n "$existing_session_dir" ]]; then
    SESSION_DIR="$existing_session_dir"
  fi
  if [[ "$RECORDINGS_DIR_SET" != "1" && -n "$existing_recordings_dir" ]]; then
    RECORDINGS_DIR="$existing_recordings_dir"
  fi

  if [[ "$ADVANCED" == "1" || -z "$SESSION_DIR" ]]; then
    SESSION_DIR="$(prompt_default "Session dir (host path)" "$SESSION_DIR")"
  fi
  if [[ "$ADVANCED" == "1" || -z "$RECORDINGS_DIR" ]]; then
    RECORDINGS_DIR="$(prompt_default "Recordings dir (host path)" "$RECORDINGS_DIR")"
  fi

  section "Summary"
  divider
  echo "Orchestrator ID:     $ORCH_ID" >&2
  echo "Payout wallet:       $ORCH_ADDRESS" >&2
  if [[ -n "$ORCH_CONTACT_EMAIL" ]]; then
    echo "Contact email:       $ORCH_CONTACT_EMAIL" >&2
  fi
  echo "Public IP:           $PUBLIC_IP" >&2
  echo "Forwarder allowlist: $FORWARDER_IP" >&2
  echo "Session dir:         $SESSION_DIR" >&2
  echo "Recordings dir:      $RECORDINGS_DIR" >&2
  echo "Encrypted artifact:  $(redact_url "$ARTIFACT_URL")" >&2
  if [[ -n "$ORCH_TOKEN_FILE" ]]; then
    echo "License token:       file $(strip_inline_comment "$ORCH_TOKEN_FILE")" >&2
  elif [[ -n "$ORCH_TOKEN_ENV" ]]; then
    echo "License token:       env $ORCH_TOKEN_ENV" >&2
  else
    echo "License token:       provided (hidden)" >&2
  fi
  divider

  section "Preflight"
  local missing_deps=()
  for cmd in curl python3 jq zstd age; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing_deps+=("$cmd")
    fi
  done
  if ((${#missing_deps[@]})); then
    warn "Missing deps: ${missing_deps[*]}"
    if prompt_yes_no "Install missing deps now? (Ubuntu/Debian via apt-get)" "y"; then
      INSTALL_DEPS="1"
    fi
  else
    ok "Deps: OK (curl/python3/jq/zstd/age)"
  fi

  if ! command -v docker >/dev/null 2>&1; then
    warn "Docker: missing"
    if prompt_yes_no "Install Docker + Compose plugin now? (Ubuntu/Debian via apt-get)" "y"; then
      INSTALL_DOCKER="1"
    fi
  else
    ok "Docker: present"
    if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
      warn "Compose: missing"
      if prompt_yes_no "Install Compose plugin now? (Ubuntu/Debian via apt-get)" "y"; then
        INSTALL_DOCKER="1"
      fi
    else
      ok "Compose: present"
    fi
  fi

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    warn "GPU driver: nvidia-smi missing (cannot start the game container yet)."
    if prompt_yes_no "Install NVIDIA driver now? (Ubuntu/Debian via apt-get; requires reboot)" "y"; then
      INSTALL_NVIDIA_DRIVER="1"
    fi
  else
    ok "GPU driver: nvidia-smi present"
  fi

  if ! command -v docker >/dev/null 2>&1; then
    note "NVIDIA container runtime: will check after Docker is installed."
  elif ! command -v nvidia-smi >/dev/null 2>&1; then
    note "NVIDIA container runtime: will check after the GPU driver is installed."
  else
    local docker_runtimes=""
    if docker info >/dev/null 2>&1; then
      docker_runtimes="$(docker info --format '{{json .Runtimes}}' 2>/dev/null || true)"
    fi
    if echo "$docker_runtimes" | grep -qi "nvidia"; then
      ok "NVIDIA container runtime: configured"
    else
      warn "NVIDIA container runtime: missing"
      if prompt_yes_no "Install NVIDIA container toolkit to enable the Docker GPU runtime?" "y"; then
        INSTALL_NVIDIA_TOOLKIT="1"
      fi
    fi
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
ORCH_ID="$(trim_whitespace "$ORCH_ID")"
if ! is_valid_orchestrator_id "$ORCH_ID"; then
  die "ORCHESTRATOR_ID must be 1-64 chars: letters/numbers/dot/underscore/dash (start with a letter/number)"
fi
if [[ -z "$ORCH_ADDRESS" ]]; then
  die "--orchestrator-address is required (or run without --non-interactive to use the wizard)"
fi
ORCH_ADDRESS="$(trim_whitespace "$ORCH_ADDRESS")"
if ! is_valid_eth_address "$ORCH_ADDRESS"; then
  die "ORCHESTRATOR_ADDRESS must look like 0x + 40 hex chars"
fi
if is_zero_eth_address "$ORCH_ADDRESS"; then
  die "ORCHESTRATOR_ADDRESS cannot be 0x0000000000000000000000000000000000000000"
fi

[[ -n "$ARTIFACT_URL" ]] || die "--artifact-url is required"
if [[ -z "$ORCH_TOKEN" && -z "$ORCH_TOKEN_FILE" && -z "$ORCH_TOKEN_ENV" ]]; then
  die "orchestrator token required (use --orch-token-file or --orch-token-env)"
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
if [[ -n "$ORCH_CONTACT_EMAIL" ]]; then
  upsert_env_kv "$ENV_FILE" "ORCHESTRATOR_CONTACT_EMAIL" "$ORCH_CONTACT_EMAIL"
fi
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

# Docker Compose interpolates ${TURN_*} from .env (not from env_file).
# Sync TURN vars so Compose doesn't warn and the recorder can build RECORDER_TURN_URL.
turn_user="$(read_env_value "$TURN_ENV_FILE" "TURN_USER" 2>/dev/null || true)"
turn_pass="$(read_env_value "$TURN_ENV_FILE" "TURN_PASS" 2>/dev/null || true)"
turn_port="$(read_env_value "$TURN_ENV_FILE" "TURN_PORT" 2>/dev/null || true)"
turn_realm="$(read_env_value "$TURN_ENV_FILE" "TURN_REALM" 2>/dev/null || true)"
turn_external_ip="$(read_env_value "$TURN_ENV_FILE" "TURN_EXTERNAL_IP" 2>/dev/null || true)"
turn_min_port="$(read_env_value "$TURN_ENV_FILE" "TURN_MIN_PORT" 2>/dev/null || true)"
turn_max_port="$(read_env_value "$TURN_ENV_FILE" "TURN_MAX_PORT" 2>/dev/null || true)"
turn_server="$(read_env_value "$TURN_ENV_FILE" "TURN_SERVER" 2>/dev/null || true)"

if [[ -n "$turn_user" ]]; then upsert_env_kv "$ENV_FILE" "TURN_USER" "$turn_user"; fi
if [[ -n "$turn_pass" ]]; then upsert_env_kv "$ENV_FILE" "TURN_PASS" "$turn_pass"; fi
if [[ -n "$turn_port" ]]; then upsert_env_kv "$ENV_FILE" "TURN_PORT" "$turn_port"; fi
if [[ -n "$turn_realm" ]]; then upsert_env_kv "$ENV_FILE" "TURN_REALM" "$turn_realm"; fi
if [[ -n "$turn_external_ip" ]]; then upsert_env_kv "$ENV_FILE" "TURN_EXTERNAL_IP" "$turn_external_ip"; fi
if [[ -n "$turn_min_port" ]]; then upsert_env_kv "$ENV_FILE" "TURN_MIN_PORT" "$turn_min_port"; fi
if [[ -n "$turn_max_port" ]]; then upsert_env_kv "$ENV_FILE" "TURN_MAX_PORT" "$turn_max_port"; fi
if [[ -n "$turn_server" ]]; then upsert_env_kv "$ENV_FILE" "TURN_SERVER" "$turn_server"; fi

chmod 600 "$ENV_FILE" >/dev/null 2>&1 || true
if [[ "$(id -u)" == "0" && -n "${SUDO_USER:-}" ]]; then
  chown "$SUDO_USER":"$SUDO_USER" "$ENV_FILE" >/dev/null 2>&1 || true
fi

require_nvidia_prereqs() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    die "NVIDIA driver not detected (nvidia-smi missing). Install the NVIDIA driver and rerun."
  fi
  if ! nvidia-smi >/dev/null 2>&1; then
    die "NVIDIA driver detected but nvidia-smi failed. Fix the NVIDIA driver and rerun."
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
    die "install/configure nvidia-container-toolkit so Docker has an 'nvidia' runtime, then rerun."
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

ensure_inbound_rules_best_effort

if [[ "$SKIP_REGISTRATION" != "1" ]]; then
  note "Registering orchestrator with Payments"
  reg_args=(--api-url "$PAYMENTS_API_URL" --orchestrator-id "$ORCH_ID" --orchestrator-address "$ORCH_ADDRESS" --max-retry-seconds 120)
  if [[ -n "$ORCH_CONTACT_EMAIL" ]]; then
    reg_args+=(--contact-email "$ORCH_CONTACT_EMAIL")
  fi
  reg_args+=(--host-public-ip "$PUBLIC_IP" --health-url "http://$PUBLIC_IP:9090/health")
  python3 "$REPO_ROOT/scripts/register_orchestrator.py" "${reg_args[@]}" || true
  verify_payments_registration_best_effort || true
fi

note "Health checks (best-effort)"
curl -fsS --max-time 2 http://127.0.0.1:9877/health >/dev/null 2>&1 || true
curl -fsS --max-time 2 http://127.0.0.1:8080/healthz >/dev/null 2>&1 || true
curl -fsS --max-time 2 http://127.0.0.1:9090/health >/dev/null 2>&1 || true

cat >&2 <<EOF

[onboard] Done.

Next:
  1) Ensure inbound allowlists / firewall rules are set (the wizard can auto-apply on EC2 if AWS CLI + permissions are available):
     - Forwarder ${FORWARDER_IP} -> TCP 8080,8888,8889,9877 and UDP 3478,49160-49200
     - Payments backend -> TCP 9090 (health monitoring)

  2) Verify locally:
     - Signaling health:    curl http://127.0.0.1:8080/healthz
     - Runner health:       curl http://127.0.0.1:9877/health
     - Orchestrator health: curl http://127.0.0.1:9090/health

  3) If registration didn’t show up yet, rerun:
     PAYMENTS_API_URL="${PAYMENTS_API_URL}" ORCHESTRATOR_ID="${ORCH_ID}" ORCHESTRATOR_ADDRESS="${ORCH_ADDRESS}" \\
       python3 scripts/register_orchestrator.py
EOF
