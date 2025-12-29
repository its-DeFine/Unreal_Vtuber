#!/usr/bin/env python3
from __future__ import annotations

import ipaddress
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"[edge-rotator {ts}] {msg}", flush=True)


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")


@dataclass(frozen=True)
class PortRule:
    proto: str  # tcp|udp
    start: int
    end: int

    def __str__(self) -> str:
        if self.start == self.end:
            return f"{self.start}/{self.proto}"
        return f"{self.start}-{self.end}/{self.proto}"


def _parse_ports(raw: str) -> list[PortRule]:
    out: list[PortRule] = []
    for token in (raw or "").split(","):
        token = token.strip()
        if not token:
            continue
        if "/" in token:
            port_part, proto = token.split("/", 1)
            proto = proto.strip().lower()
        else:
            port_part, proto = token, "tcp"
        if proto not in ("tcp", "udp"):
            raise ValueError(f"invalid protocol in EDGE_ALLOW_PORTS entry: {token!r}")
        if "-" in port_part:
            a, b = port_part.split("-", 1)
            start, end = int(a), int(b)
        else:
            start = end = int(port_part)
        if not (1 <= start <= 65535 and 1 <= end <= 65535 and start <= end):
            raise ValueError(f"invalid port range in EDGE_ALLOW_PORTS entry: {token!r}")
        out.append(PortRule(proto=proto, start=start, end=end))
    if not out:
        out = [
            PortRule(proto="tcp", start=8080, end=8080),
            PortRule(proto="tcp", start=8888, end=8888),
            PortRule(proto="tcp", start=8889, end=8889),
            PortRule(proto="tcp", start=9090, end=9090),
            PortRule(proto="tcp", start=9877, end=9877),
            PortRule(proto="tcp", start=3478, end=3478),
            PortRule(proto="udp", start=3478, end=3478),
            PortRule(proto="udp", start=49160, end=49200),
        ]
    # de-dupe (preserve order)
    seen: set[tuple[str, int, int]] = set()
    deduped: list[PortRule] = []
    for r in out:
        key = (r.proto, r.start, r.end)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def _run(
    args: list[str],
    *,
    check: bool = True,
    env: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    _log("+ " + " ".join(shlex.quote(a) for a in args))
    return subprocess.run(args, check=check, capture_output=True, text=True, env=env)


def _iptables(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return _run(["iptables", *args], check=check)


def _ensure_jump(parent_chain: str, rule_spec: list[str]) -> None:
    while True:
        cp = _iptables(["-D", parent_chain, *rule_spec], check=False)
        if cp.returncode != 0:
            break
    _iptables(["-I", parent_chain, "1", *rule_spec], check=False)


def _ensure_iptables_chain(chain: str) -> None:
    cp = _iptables(["-N", chain], check=False)
    if cp.returncode != 0:
        _iptables(["-F", chain], check=False)

    # Hook early in INPUT (host-network services) and DOCKER-USER (docker-mapped ports).
    _ensure_jump("INPUT", ["-j", chain])

    # Avoid breaking intra-docker traffic (container-to-container) on the same ports.
    _ensure_jump(
        "DOCKER-USER",
        ["!", "-i", "docker0", "!", "-i", "br+", "!", "-i", "veth+", "-j", chain],
    )

    _iptables(["-F", chain], check=False)


def _translate_docker_ports(ports: list[PortRule]) -> list[PortRule]:
    translated: list[PortRule] = []
    for rule in ports:
        translated.append(rule)
        # docker-compose exposes "8080:80" for signaling; once DNAT'd, the dport is 80.
        if rule.proto == "tcp" and rule.start == 8080 and rule.end == 8080:
            translated.append(PortRule(proto="tcp", start=80, end=80))

    # de-dupe (preserve order)
    seen: set[tuple[str, int, int]] = set()
    out: list[PortRule] = []
    for r in translated:
        key = (r.proto, r.start, r.end)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _apply_firewall(chain: str, *, cidrs: list[str], ports: list[PortRule], enforce_exclusive: bool) -> None:
    _ensure_iptables_chain(chain)

    ports = _translate_docker_ports(ports)

    # Always preserve loopback access to avoid breaking local checks.
    allow = ["127.0.0.1/32", *cidrs]
    allow_deduped: list[str] = []
    seen = set()
    for c in allow:
        if c in seen:
            continue
        seen.add(c)
        allow_deduped.append(c)

    for rule in ports:
        for cidr in allow_deduped:
            args = ["-A", chain, "-p", rule.proto, "-s", cidr]
            if rule.start == rule.end:
                args += ["--dport", str(rule.start)]
            else:
                args += ["--dport", f"{rule.start}:{rule.end}"]
            args += ["-j", "ACCEPT"]
            _iptables(args, check=False)

        if enforce_exclusive:
            args = ["-A", chain, "-p", rule.proto]
            if rule.start == rule.end:
                args += ["--dport", str(rule.start)]
            else:
                args += ["--dport", f"{rule.start}:{rule.end}"]
            args += ["-j", "DROP"]
            _iptables(args, check=False)


def _http_get_json(url: str, *, token: str) -> dict:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")  # noqa: S310
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
        data = resp.read().decode("utf-8")
    parsed = json.loads(data)
    if not isinstance(parsed, dict):
        raise ValueError("control plane returned non-object JSON")
    return parsed


def _resolve_a_records(host: str) -> list[str]:
    ips: list[str] = []
    try:
        infos = socket.getaddrinfo(host, None, family=socket.AF_INET, type=socket.SOCK_STREAM)
        for info in infos:
            addr = info[4][0]
            if addr and addr not in ips:
                ips.append(addr)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"failed to resolve edge_host {host!r}: {exc}") from exc
    return ips


def _as_cidrs(payload: dict) -> list[str]:
    cidrs: list[str] = []

    raw = payload.get("edge_cidrs")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip():
                cidrs.append(item.strip())

    raw_ip = payload.get("edge_ip")
    if isinstance(raw_ip, str) and raw_ip.strip():
        cidrs.append(f"{raw_ip.strip()}/32")

    raw_ips = payload.get("edge_ips")
    if isinstance(raw_ips, list):
        for item in raw_ips:
            if isinstance(item, str) and item.strip():
                cidrs.append(f"{item.strip()}/32")

    raw_host = payload.get("edge_host")
    if isinstance(raw_host, str) and raw_host.strip():
        for ip in _resolve_a_records(raw_host.strip()):
            cidrs.append(f"{ip}/32")

    out: list[str] = []
    seen = set()
    for token in cidrs:
        token = token.strip()
        if not token:
            continue
        try:
            net = ipaddress.ip_network(token, strict=False)
        except ValueError:
            continue
        if net.version != 4:
            continue
        normalized = str(net)
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _parse_cidrs_csv(raw: str) -> list[str]:
    cidrs: list[str] = []
    for token in (raw or "").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            net = ipaddress.ip_network(token, strict=False)
        except ValueError:
            continue
        if net.version != 4:
            continue
        cidrs.append(str(net))

    out: list[str] = []
    seen = set()
    for token in cidrs:
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _cidrs_to_ips(cidrs: list[str]) -> list[str]:
    ips: list[str] = []
    seen: set[str] = set()
    for token in cidrs:
        token = (token or "").strip()
        if not token:
            continue
        try:
            net = ipaddress.ip_network(token, strict=False)
        except ValueError:
            continue
        if net.version != 4:
            continue
        if getattr(net, "prefixlen", 32) != 32:
            continue
        ip = str(net.network_address)
        if ip in seen:
            continue
        seen.add(ip)
        ips.append(ip)
    return ips


def _read_env_value(env_path: Path, key: str) -> str:
    if not env_path.exists():
        return ""
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].lstrip()
        if not stripped.startswith(f"{key}="):
            continue
        return stripped.split("=", 1)[1]
    return ""


def _upsert_env_value(env_path: Path, key: str, value: str) -> bool:
    """Returns True if the file was changed."""
    env_path.parent.mkdir(parents=True, exist_ok=True)
    original = env_path.read_text().splitlines() if env_path.exists() else []
    out: list[str] = []
    found = False
    changed = False

    for line in original:
        stripped = line.strip()
        candidate = stripped
        prefix = ""
        if candidate.startswith("export "):
            prefix = "export "
            candidate = candidate[len("export ") :].lstrip()
        if candidate.startswith(f"{key}="):
            found = True
            new_line = f"{prefix}{key}={value}"
            if line != new_line:
                changed = True
            out.append(new_line)
        else:
            out.append(line)

    if not found:
        out.append(f"{key}={value}")
        changed = True

    if not changed:
        return False

    tmp = env_path.with_suffix(env_path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text("\n".join(out) + "\n")
    try:
        if env_path.exists():
            tmp.chmod(env_path.stat().st_mode)
        else:
            tmp.chmod(0o600)
    except Exception:
        pass
    tmp.replace(env_path)
    return True


_MATCHMAKER_ARGS_RE = re.compile(
    r"--use_matchmaker\s+--matchmaker_address\s+\S+\s+--matchmaker_port\s+\d+\s+--public_port\s+\d+"
)


def _strip_known_matchmaker_args(raw: str) -> str:
    """Best-effort removal of previously injected matchmaker args from a flag string."""
    if not raw:
        return ""
    cleaned = _MATCHMAKER_ARGS_RE.sub("", raw)
    return " ".join(cleaned.split()).strip()


def _read_power_state(power_state_path: Path) -> tuple[str, Optional[datetime]]:
    if not power_state_path.exists():
        return ("awake", None)
    try:
        payload = json.loads(power_state_path.read_text())
        state = str(payload.get("state") or "awake")
        updated_at_raw = payload.get("updated_at")
        updated_at = None
        if isinstance(updated_at_raw, str) and updated_at_raw:
            # Power API writes ISO8601; best-effort parse.
            updated_at = datetime.fromisoformat(updated_at_raw.replace("Z", "+00:00"))
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
        return (state, updated_at)
    except Exception:
        return ("awake", None)


def _compose(
    *,
    project_dir: str,
    env_file: str,
    compose_file: str,
    args: list[str],
    check: bool = True,
) -> subprocess.CompletedProcess:
    cmd = [
        "docker",
        "compose",
        "--project-directory",
        project_dir,
        "--env-file",
        env_file,
        "-f",
        compose_file,
        *args,
    ]
    env = dict(os.environ)
    # The rotator container itself consumes the host `.env` via `env_file: .env`.
    # When we update `.env` and then invoke `docker compose` from inside the rotator,
    # stale process env values can override `--env-file` and cause the recreated
    # containers to keep the *previous* values (breaking edge rotation).
    for key in ("SIGNALING_EXTRA_ARGS", "SIGNALING_MATCHMAKER_ARGS", "VTUBER_ALLOWED_ADDRESSES"):
        env.pop(key, None)
    return _run(cmd, check=check, env=env)


def _write_csv_file(path: Path, values: list[str], *, mode: int = 0o600) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ",".join(values) + "\n"
    try:
        if path.exists() and path.read_text() == content:
            return False
    except Exception:
        pass

    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(content)
    try:
        tmp.chmod(mode)
    except Exception:
        pass
    tmp.replace(path)
    return True


def _write_json_file(path: Path, payload: dict, *, mode: int = 0o600) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, sort_keys=True) + "\n"
    try:
        if path.exists() and path.read_text() == content:
            return False
    except Exception:
        pass

    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(content)
    try:
        tmp.chmod(mode)
    except Exception:
        pass
    tmp.replace(path)
    return True


def _read_state_key(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict):
            return ""
        key = payload.get("last_applied_key")
        return key if isinstance(key, str) else ""
    except Exception:
        return ""


def _container_env_value(container: str, key: str) -> str:
    cp = _run(
        ["docker", "inspect", container, "--format", "{{range .Config.Env}}{{println .}}{{end}}"],
        check=False,
    )
    if cp.returncode != 0:
        return ""
    prefix = f"{key}="
    for line in (cp.stdout or "").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return ""


def _normalize_ws(s: str) -> str:
    return " ".join((s or "").split()).strip()


def main() -> int:
    control_plane_url = (os.environ.get("EDGE_CONFIG_URL") or "").strip()
    if not control_plane_url:
        _log("EDGE_CONFIG_URL is unset; sleeping (disabled)")
        while True:
            time.sleep(60)

    edge_config_token = (os.environ.get("EDGE_CONFIG_TOKEN") or "").strip()
    poll_s = int(os.environ.get("EDGE_POLL_INTERVAL_SECONDS", "15"))

    project_dir = (os.environ.get("EDGE_PROJECT_DIR") or "/home/ubuntu/Unreal_Vtuber").strip()
    env_file = Path(project_dir) / ".env"
    env_turn = Path(project_dir) / ".env.turn"
    compose_file = Path(project_dir) / "docker-compose.unreal.yml"
    power_state = Path("/var/lib/vtuber/power-state/power_state.json")

    chain = (os.environ.get("EDGE_IPTABLES_CHAIN") or "EMBODY_EDGE_ALLOWLIST").strip()
    ports = _parse_ports(os.environ.get("EDGE_ALLOW_PORTS", ""))
    enforce = _env_bool("EDGE_ENFORCE_EXCLUSIVE", default=True)
    wake_settle_s = int(os.environ.get("EDGE_WAKE_SETTLE_SECONDS", "60"))
    update_turn = _env_bool("EDGE_UPDATE_TURN", default=False)
    extra_firewall_cidrs = _parse_cidrs_csv(os.environ.get("EDGE_FIREWALL_EXTRA_CIDRS", ""))
    extra_power_cidrs = _parse_cidrs_csv(os.environ.get("EDGE_POWER_EXTRA_CIDRS", ""))
    power_allowed_file_raw = (os.environ.get("EDGE_POWER_ALLOWED_IPS_FILE") or "").strip()
    power_allowed_file = Path(power_allowed_file_raw) if power_allowed_file_raw else None
    local_allowlist = (os.environ.get("EDGE_LOCAL_ALLOWLIST") or "127.0.0.1,::1,172.17.0.1,172.18.0.1").strip()

    public_port = int(os.environ.get("EDGE_SIGNALING_PUBLIC_PORT", "8080"))
    default_mm_port = int(os.environ.get("EDGE_MATCHMAKER_DEFAULT_PORT", "8889"))

    state_file_raw = (os.environ.get("EDGE_STATE_FILE") or "").strip()
    state_file = Path(state_file_raw) if state_file_raw else Path("/var/lib/vtuber/power-state/edge_rotator_state.json")
    last_applied_key = _read_state_key(state_file)

    _log(
        f"init project_dir={project_dir} poll={poll_s}s chain={chain} ports={[str(p) for p in ports]} enforce={enforce} state_file={state_file}"
    )

    while True:
        try:
            orch_id = (os.environ.get("ORCHESTRATOR_ID") or "").strip() or _read_env_value(env_file, "ORCHESTRATOR_ID").strip()
            if not orch_id:
                raise RuntimeError("ORCHESTRATOR_ID is missing (set env or .env)")

            url = control_plane_url
            q = urllib.parse.urlencode({"orchestrator_id": orch_id})
            url = f"{url}{'&' if '?' in url else '?'}{q}"
            desired = _http_get_json(url, token=edge_config_token)

            cidrs = _as_cidrs(desired)
            if not cidrs:
                raise RuntimeError("control plane response did not include any edge IPs/cidrs (edge_cidrs/edge_ip/edge_ips/edge_host)")

            mm_host = (
                (desired.get("matchmaker_host") if isinstance(desired.get("matchmaker_host"), str) else None)
                or (desired.get("matchmaker_address") if isinstance(desired.get("matchmaker_address"), str) else None)
                or ""
            ).strip()
            if not mm_host:
                raise RuntimeError("control plane response missing matchmaker_host/matchmaker_address")
            mm_port = desired.get("matchmaker_port")
            if isinstance(mm_port, int) and 1 <= mm_port <= 65535:
                pass
            else:
                mm_port = default_mm_port

            args = f"--use_matchmaker --matchmaker_address {mm_host} --matchmaker_port {mm_port} --public_port {public_port}"

            # stable key to suppress no-op churn
            apply_key = json.dumps({"cidrs": cidrs, "ports": [str(p) for p in ports], "mm": args}, sort_keys=True)
            desired_changed = apply_key != last_applied_key
            if desired_changed:
                _log(f"desired edge_id={desired.get('edge_id')!r} matchmaker={mm_host}:{mm_port} cidrs={cidrs}")

            firewall_cidrs = [*cidrs, *extra_firewall_cidrs]
            _apply_firewall(chain, cidrs=firewall_cidrs, ports=ports, enforce_exclusive=enforce)

            if power_allowed_file:
                allow = ["127.0.0.1/32", *cidrs, *extra_power_cidrs]
                deduped: list[str] = []
                seen = set()
                for token in allow:
                    token = token.strip()
                    if not token or token in seen:
                        continue
                    seen.add(token)
                    deduped.append(token)
                _write_csv_file(power_allowed_file, deduped)

            env_changed = False
            # We intentionally write the effective matchmaker flags into SIGNALING_EXTRA_ARGS.
            #
            # Reason: the edge-rotator container currently ships with an older docker compose v2.x
            # binary, and we observed that relying on composing multiple env-substitutions inside
            # docker-compose.unreal.yml could result in matchmaker flags being dropped on recreate.
            #
            # By writing the full args into SIGNALING_EXTRA_ARGS, the compose file only needs to
            # interpolate a single variable for the container env (and swaps remain reliable).
            existing_extra = _read_env_value(env_file, "SIGNALING_EXTRA_ARGS").strip()
            existing_extra = _strip_known_matchmaker_args(existing_extra)
            combined = " ".join([token for token in [existing_extra, args] if token]).strip()
            env_changed = _upsert_env_value(env_file, "SIGNALING_EXTRA_ARGS", combined) or env_changed

            # Prevent accidental double-injection in stacks that still concatenate
            # SIGNALING_EXTRA_ARGS + SIGNALING_MATCHMAKER_ARGS.
            env_changed = _upsert_env_value(env_file, "SIGNALING_MATCHMAKER_ARGS", "") or env_changed

            # Ensure runner/recorder allowlists follow the selected edge. This allowlist is consumed
            # by services that do strict string matching on client IP (no CIDR support), so only
            # /32 edge CIDRs can be reflected here.
            desired_allowed_csv = ""
            edge_ips = _cidrs_to_ips(cidrs)
            if edge_ips:
                base = [t.strip() for t in local_allowlist.split(",") if t.strip()]
                allow_tokens = [*base, *edge_ips]
                deduped: list[str] = []
                seen = set()
                for token in allow_tokens:
                    if token in seen:
                        continue
                    seen.add(token)
                    deduped.append(token)
                desired_allowed_csv = ",".join(deduped)
                env_changed = _upsert_env_value(env_file, "VTUBER_ALLOWED_ADDRESSES", desired_allowed_csv) or env_changed

            if update_turn:
                turn_ip: str | None = None
                raw_turn = desired.get("turn_external_ip")
                if isinstance(raw_turn, str) and raw_turn.strip():
                    turn_ip = raw_turn.strip()
                else:
                    # When the orchestrator sits behind an edge/gateway DNAT, TURN must advertise the edge/gateway IP.
                    # If the control plane doesn't provide an explicit turn_external_ip, fall back to the selected edge IP
                    # when it is an unambiguous single /32.
                    edge_ips = _cidrs_to_ips(cidrs)
                    if len(edge_ips) == 1:
                        turn_ip = edge_ips[0]

                if turn_ip:
                    env_changed = _upsert_env_value(env_turn, "TURN_EXTERNAL_IP", turn_ip) or env_changed
                    env_changed = _upsert_env_value(env_turn, "TURN_SERVER", f"{turn_ip}:3478") or env_changed

            state, updated_at = _read_power_state(power_state)
            now = datetime.now(timezone.utc)
            recently_changed = False
            if updated_at is not None:
                recently_changed = abs((now - updated_at).total_seconds()) < wake_settle_s

            drifted = False
            if desired_allowed_csv:
                runner_allowed = _container_env_value("vtuber-script-runner", "VTUBER_ALLOWED_ADDRESSES")
                recorder_allowed = _container_env_value("vtuber-recorder-control", "VTUBER_ALLOWED_ADDRESSES")
                if runner_allowed and runner_allowed != desired_allowed_csv:
                    drifted = True
                if recorder_allowed and recorder_allowed != desired_allowed_csv:
                    drifted = True

            signaling_args = _container_env_value("vtuber-unreal-signaling", "SIGNALING_EXTRA_ARGS")
            if signaling_args and _normalize_ws(args) not in _normalize_ws(signaling_args):
                drifted = True

            needs_recreate = desired_changed or env_changed or drifted

            if needs_recreate:
                # If sleeping, recreate without starting so /power wake starts with the new config.
                # If we're in the first moments of a wake transition, avoid fighting the wake sequence.
                reason = "config changed" if env_changed else ("edge changed" if desired_changed else "drift detected")

                if state != "sleeping" and recently_changed:
                    _log(f"{reason}; state={state} recently_changed={recently_changed} -> deferring recreate")
                else:
                    if state == "sleeping":
                        _log(f"{reason}; state={state} recently_changed={recently_changed} -> docker compose up --no-start")
                        cp = _compose(
                            project_dir=project_dir,
                            env_file=str(env_file),
                            compose_file=str(compose_file),
                            args=[
                                "up",
                                "--no-start",
                                "--force-recreate",
                                "unreal-signaling",
                                "turn-server",
                                "vtuber-script-runner",
                                "recorder-control",
                            ],
                            check=False,
                        )
                    else:
                        _log(f"{reason}; recreating signaling/turn/runner/recorder")
                        cp = _compose(
                            project_dir=project_dir,
                            env_file=str(env_file),
                            compose_file=str(compose_file),
                            args=[
                                "up",
                                "-d",
                                "--force-recreate",
                                "unreal-signaling",
                                "turn-server",
                                "vtuber-script-runner",
                                "recorder-control",
                            ],
                            check=False,
                        )
                    if cp.returncode != 0:
                        stderr = (cp.stderr or "").strip()
                        if stderr:
                            stderr = "\n".join(stderr.splitlines()[-5:]).strip()
                            raise RuntimeError(f"docker compose failed (rc={cp.returncode}): {stderr}")
                        raise RuntimeError(f"docker compose failed (rc={cp.returncode})")

                    last_applied_key = apply_key
                    _write_json_file(
                        state_file,
                        {
                            "last_applied_key": last_applied_key,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
            else:
                # Keep state persisted so restarts don't trigger unnecessary recreates.
                if last_applied_key != apply_key:
                    last_applied_key = apply_key
                    _write_json_file(
                        state_file,
                        {
                            "last_applied_key": last_applied_key,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
        except Exception as exc:  # noqa: BLE001
            _log(f"error: {exc}")

        time.sleep(max(5, poll_s))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
