import json
import os
import subprocess
import sys
import time
from typing import List, Sequence

DEFAULT_PORTS = [80, 8888, 8889, 9877]
DEFAULT_CHAIN = "WHITELIST_AGENT"


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_ports(raw: str | None) -> List[int]:
    if not raw:
        return DEFAULT_PORTS
    ports: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ports.append(int(part))
        except ValueError:
            log(f"skipping invalid port '{part}'")
    return ports or DEFAULT_PORTS


def fetch_allowlist() -> List[str]:
    """Fetch allowed CIDRs/IPs from control-plane; fall back to static env."""
    static = os.environ.get("WHITELIST_STATIC_CIDRS", "")
    control_url = os.environ.get("CONTROL_PLANE_URL")
    token = os.environ.get("API_TOKEN") or os.environ.get("CONTROL_PLANE_TOKEN")
    node_id = os.environ.get("NODE_ID") or os.environ.get("AGENT_NODE_ID")
    headers = {}

    if control_url:
        url = control_url
        if "{node_id}" in url and node_id:
            url = url.format(node_id=node_id)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            import urllib.request

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            for key in ("allowed_ips", "allowlist", "allow"):
                if key in payload and isinstance(payload[key], list):
                    return [str(x).strip() for x in payload[key] if str(x).strip()]
            log("control-plane response missing allowlist keys; falling back to static list")
        except Exception as exc:
            log(f"control-plane fetch failed: {exc}; falling back to static list")

    return [cidr.strip() for cidr in static.split(",") if cidr.strip()]


def run_iptables(args: Sequence[str]) -> None:
    base = ["iptables", "-w", "5"]
    try:
        subprocess.run(base + list(args), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        err = exc.stderr.decode() if exc.stderr else str(exc)
        log(f"iptables error for {args}: {err}")
        raise


def ensure_chain(chain: str) -> None:
    try:
        run_iptables(["-N", chain])
    except Exception:
        # Chain likely exists; continue.
        pass
    run_iptables(["-F", chain])


def ensure_jump(chain: str) -> None:
    try:
        run_iptables(["-C", "INPUT", "-j", chain])
    except Exception:
        run_iptables(["-I", "INPUT", "1", "-j", chain])


def apply_allowlist(chain: str, ports: List[int], allowlist: List[str], fail_open: bool) -> None:
    if not ports:
        ports = DEFAULT_PORTS

    ensure_chain(chain)
    ensure_jump(chain)

    # Always allow loopback and established flows to avoid self-inflicted outages.
    run_iptables(["-A", chain, "-i", "lo", "-j", "RETURN"])
    run_iptables(["-A", chain, "-m", "conntrack", "--ctstate", "ESTABLISHED,RELATED", "-j", "RETURN"])

    if allowlist:
        for cidr in allowlist:
            run_iptables(
                [
                    "-A",
                    chain,
                    "-s",
                    cidr,
                    "-p",
                    "tcp",
                    "-m",
                    "multiport",
                    "--dports",
                    ",".join(str(p) for p in ports),
                    "-j",
                    "RETURN",
                ]
            )
        drop_msg = f"enforcing drop for ports {ports} (allow: {allowlist})"
    else:
        if fail_open:
            log("no allowlist available; fail-open active (no drops applied)")
            return
        drop_msg = f"empty allowlist; fail-closed drop on ports {ports}"

    run_iptables(
        ["-A", chain, "-p", "tcp", "-m", "multiport", "--dports", ",".join(str(p) for p in ports), "-j", "DROP"]
    )
    log(drop_msg)


def main() -> None:
    ports = parse_ports(os.environ.get("WHITELIST_PORTS"))
    chain = os.environ.get("WHITELIST_CHAIN", DEFAULT_CHAIN)
    poll_seconds = int(os.environ.get("POLL_INTERVAL_SECONDS", "5"))
    fail_open = os.environ.get("FAIL_OPEN", "true").lower() not in ("0", "false", "no")

    log(f"whitelist-agent starting: ports={ports}, chain={chain}, poll={poll_seconds}s, fail_open={fail_open}")

    last_applied: list[str] = []
    while True:
        allowlist = fetch_allowlist()
        if allowlist != last_applied or not last_applied:
            try:
                apply_allowlist(chain, ports, allowlist, fail_open)
                last_applied = allowlist
            except Exception as exc:
                log(f"failed to apply rules: {exc}")
        time.sleep(poll_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
