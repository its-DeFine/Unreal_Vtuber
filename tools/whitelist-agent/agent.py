import ipaddress
import json
import os
import subprocess
import sys
import time
from typing import List, Tuple, Optional
from urllib import request, parse

CHAIN_NAME = "WHITELIST_AGENT"
POLL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))
FAIL_OPEN = os.environ.get("FAIL_OPEN", "true").lower() == "true"
CONTROL_PLANE_URL = os.environ.get("CONTROL_PLANE_URL", "").strip()
API_TOKEN = os.environ.get("API_TOKEN", "").strip()
NODE_ID = os.environ.get("NODE_ID", "").strip()


def run_cmd(args: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.Popen([str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    return proc.returncode, out.strip(), err.strip()


def parse_ports(raw: str):
    ports = []
    for token in [p.strip() for p in raw.split(",") if p.strip()]:
        proto = None
        port_part = token
        if "/" in token:
            port_part, proto = token.split("/", 1)
            proto = proto.lower()
        # range support
        if "-" in port_part:
            start, end = port_part.split("-", 1)
            ports.append((start, end, proto))
        else:
            ports.append((port_part, port_part, proto))
    return ports


def parse_cidrs(raw: str):
    cidrs = []
    for token in [c.strip() for c in raw.split(",") if c.strip()]:
        try:
            cidrs.append(ipaddress.ip_network(token, strict=False))
        except ValueError:
            print(f"[whitelist-agent] skipping invalid CIDR: {token}", file=sys.stderr)
    return cidrs


def ensure_chain():
    code, _, _ = run_cmd(["iptables", "-N", CHAIN_NAME])
    if code != 0:
        run_cmd(["iptables", "-F", CHAIN_NAME])
    # flush any existing jump rules
    run_cmd(["iptables", "-D", "INPUT", "-j", CHAIN_NAME])
    run_cmd(["iptables", "-I", "INPUT", "1", "-j", CHAIN_NAME])
    # default: allow established
    run_cmd(["iptables", "-F", CHAIN_NAME])
    run_cmd(["iptables", "-A", CHAIN_NAME, "-m", "conntrack", "--ctstate", "ESTABLISHED,RELATED", "-j", "ACCEPT"])


def apply_rules(cidrs, ports):
    ensure_chain()
    if not cidrs:
        print("[whitelist-agent] no allowlist provided")
        if FAIL_OPEN:
            print("[whitelist-agent] fail-open enabled; not dropping traffic")
            return
    for start, end, proto in ports:
        target_protos = [proto] if proto else ["tcp"]
        for p in target_protos:
            for net in cidrs:
                args = ["iptables", "-A", CHAIN_NAME]
                if p:
                    args += ["-p", p]
                args += ["-s", str(net)]
                args += ["--dport", f"{start}:{end}"] if start != end else ["--dport", start]
                args += ["-j", "ACCEPT"]
                code, out, err = run_cmd(args)
                if code != 0:
                    print(f"[whitelist-agent] iptables add ACCEPT failed ({args}): {err}", file=sys.stderr)
            # default drop for this port/range/proto
            args = ["iptables", "-A", CHAIN_NAME]
            if p:
                args += ["-p", p]
            args += ["--dport", f"{start}:{end}"] if start != end else ["--dport", start]
            args += ["-j", "DROP"]
            code, out, err = run_cmd(args)
            if code != 0:
                print(f"[whitelist-agent] iptables add DROP failed ({args}): {err}", file=sys.stderr)


def fetch_control_plane():
    if not CONTROL_PLANE_URL:
        return None
    try:
        url = CONTROL_PLANE_URL
        if NODE_ID:
            q = parse.urlencode({"node_id": NODE_ID})
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{q}"
        headers = {}
        if API_TOKEN:
            headers["Authorization"] = f"Bearer {API_TOKEN}"
        req = request.Request(url, headers=headers, method="GET")
        with request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            cidrs = data.get("cidrs") or []
            ports = data.get("ports") or []
            # Normalize to comma-separated strings to reuse parsers
            cidr_str = ",".join(cidrs) if isinstance(cidrs, list) else str(cidrs)
            port_str = ",".join(ports) if isinstance(ports, list) else str(ports)
            return cidr_str, port_str
    except Exception as e:
        print(f"[whitelist-agent] control plane fetch failed: {e}", file=sys.stderr)
        return None


def loop():
    base_ports = os.environ.get("WHITELIST_PORTS", "8080,8888,8889,7777,9877,3478,49160-49200/udp")
    base_cidrs = os.environ.get("WHITELIST_CIDRS", "")
    print(f"[whitelist-agent] fail_open={FAIL_OPEN} poll={POLL_SECONDS}s control_plane={bool(CONTROL_PLANE_URL)}")
    last_sig = None
    while True:
        ctrl = fetch_control_plane()
        raw_cidrs, raw_ports = (ctrl if ctrl else (base_cidrs, base_ports))
        ports = parse_ports(raw_ports)
        cidrs = parse_cidrs(raw_cidrs)
        sig = (tuple(ports), tuple(str(c) for c in cidrs))
        print(f"[whitelist-agent] applying ports={ports} cidrs={[str(c) for c in cidrs]}")
        apply_rules(cidrs, ports)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[whitelist-agent] must run as root (NET_ADMIN)", file=sys.stderr)
        sys.exit(1)
    loop()
