import ipaddress
import os
import subprocess
import sys
import time
from typing import List, Tuple

CHAIN_NAME = "WHITELIST_AGENT"
POLL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))
FAIL_OPEN = os.environ.get("FAIL_OPEN", "true").lower() == "true"


def run_cmd(args: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
        for net in cidrs:
            args = ["iptables", "-A", CHAIN_NAME]
            if proto:
                args += ["-p", proto]
            args += ["-s", str(net)]
            args += ["--dport", f"{start}:{end}"] if start != end else ["--dport", start]
            args += ["-j", "ACCEPT"]
            run_cmd(args)
        # default drop for this port/range
        args = ["iptables", "-A", CHAIN_NAME]
        if proto:
            args += ["-p", proto]
        args += ["--dport", f"{start}:{end}"] if start != end else ["--dport", start]
        args += ["-j", "DROP"]
        run_cmd(args)


def loop():
    raw_ports = os.environ.get(
        "WHITELIST_PORTS",
        "8080,8888,8889,7777,9877,3478,49160-49200/udp",
    )
    raw_cidrs = os.environ.get("WHITELIST_CIDRS", "")
    ports = parse_ports(raw_ports)
    cidrs = parse_cidrs(raw_cidrs)

    print(f"[whitelist-agent] ports={ports} cidrs={[str(c) for c in cidrs]} fail_open={FAIL_OPEN} poll={POLL_SECONDS}s")
    while True:
        apply_rules(cidrs, ports)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[whitelist-agent] must run as root (NET_ADMIN)", file=sys.stderr)
        sys.exit(1)
    loop()
