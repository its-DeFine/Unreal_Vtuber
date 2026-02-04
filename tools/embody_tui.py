#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request

LOCAL_POWER_URL = "http://127.0.0.1:9090/power"
LOCAL_META_URL = "http://127.0.0.1:9090/meta"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_token_file(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def fetch_json(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def safe_fetch(url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        return fetch_json(url, {}), None
    except Exception as exc:
        return None, str(exc)


def fetch_local_power() -> Tuple[str, Optional[str]]:
    data, err = safe_fetch(LOCAL_POWER_URL)
    if not data:
        return "unknown", err
    state = str(data.get("state") or "unknown").strip().lower()
    return state or "unknown", None


def fetch_local_meta() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    data, err = safe_fetch(LOCAL_META_URL)
    if not data:
        return [], err
    containers = data.get("containers")
    if isinstance(containers, list):
        out: List[Dict[str, Any]] = []
        for item in containers:
            if isinstance(item, dict):
                out.append(item)
        return out, None
    return [], None


def fetch_orchestrators(base_url: str, viewer_token: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    headers = {}
    if viewer_token:
        headers["X-Admin-Token"] = viewer_token
    url = f"{base_url.rstrip('/')}/api/orchestrators"
    try:
        data = fetch_json(url, headers)
        rows = data.get("orchestrators")
        if isinstance(rows, list):
            return rows, None
        return [], None
    except error.HTTPError as exc:
        return [], f"HTTP {exc.code}"
    except Exception as exc:
        return [], str(exc)


def fetch_orchestrator_me(base_url: str, orch_token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    headers = {}
    if orch_token:
        headers["X-Orchestrator-Token"] = orch_token
    url = f"{base_url.rstrip('/')}/api/orchestrators/me"
    try:
        data = fetch_json(url, headers)
        return data, None
    except error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except Exception as exc:
        return None, str(exc)


def fmt_decimal(value: str, places: int = 4) -> str:
    try:
        return f"{Decimal(value):.{places}f}"
    except Exception:
        return value


def truncate(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return value[: width - 3] + "..."


def bar(value: float, max_value: float, width: int = 16) -> str:
    if max_value <= 0:
        return "".ljust(width)
    ratio = max(0.0, min(1.0, value / max_value))
    filled = int(ratio * width)
    return "#" * filled + "." * (width - filled)


def parse_int(raw: Any, default: int = 0) -> int:
    try:
        return int(str(raw).strip())
    except Exception:
        return default


def fetch_gpu_stats() -> List[Dict[str, Any]]:
    if not shutil.which("nvidia-smi"):
        return []
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,name,utilization.gpu,temperature.gpu,memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return []
    rows: List[Dict[str, Any]] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 6:
            continue
        rows.append(
            {
                "index": parse_int(parts[0], 0),
                "name": parts[1],
                "util": parse_int(parts[2], 0),
                "temp": parse_int(parts[3], 0),
                "mem_used": parse_int(parts[4], 0),
                "mem_total": parse_int(parts[5], 0),
            }
        )
    return rows


def cosmo_available() -> bool:
    return shutil.which("cosmo") is not None


def graph_path(default_path: Optional[str]) -> Path:
    if default_path:
        return Path(default_path)
    base = Path.home() / ".embody" / "graphs"
    base.mkdir(parents=True, exist_ok=True)
    return base / "orchestrators.json"


def write_graph(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_cosmo(path: Path) -> Optional[str]:
    binary = shutil.which("cosmo")
    if not binary:
        return "cosmo CLI not found on PATH"
    subprocess.run([binary, "--file", str(path)], check=False)
    return None


def graph_payload_global(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = [{"id": "payments", "value": "payments"}]
    edges: List[Dict[str, Any]] = []
    for row in rows:
        orch_id = str(row.get("orchestrator_id", ""))
        if not orch_id:
            continue
        balance = fmt_decimal(str(row.get("balance_eth", "0")), places=3)
        active = "active" if row.get("active") else "idle"
        nodes.append({"id": orch_id, "value": f"{orch_id} | {balance} | {active}"})
        edges.append({"id": f"payments-{orch_id}", "source": "payments", "target": orch_id})
    return {"nodes": nodes, "edges": edges}


def graph_payload_self(orch_id: str, containers: List[Dict[str, Any]], power_state: str) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = [{"id": orch_id, "value": orch_id}]
    edges: List[Dict[str, Any]] = []
    nodes.append({"id": "power", "value": f"power:{power_state}"})
    edges.append({"id": f"{orch_id}-power", "source": orch_id, "target": "power"})
    for idx, item in enumerate(containers[:12]):
        name = str(item.get("name") or item.get("project") or f"svc-{idx}")
        node_id = f"svc-{idx}"
        nodes.append({"id": node_id, "value": name})
        edges.append({"id": f"{orch_id}-{node_id}", "source": orch_id, "target": node_id})
    return {"nodes": nodes, "edges": edges}


def detect_mode(viewer_token: str, orch_token: str, mode_arg: str) -> str:
    if mode_arg in {"global", "self", "local"}:
        return mode_arg
    if viewer_token:
        return "global"
    if orch_token:
        return "self"
    return "local"


def render_once(args: argparse.Namespace) -> int:
    mode = detect_mode(args.viewer_token, args.orch_token, args.mode)
    power_state, _ = fetch_local_power()
    containers, _ = fetch_local_meta()
    gpu_stats = fetch_gpu_stats()
    print(f"Embody TUI snapshot | {args.api} | {utc_now()} | mode={mode}")
    print(f"local power: {power_state} | local containers: {len(containers)} | gpus: {len(gpu_stats)}")

    if mode == "global":
        rows, err = fetch_orchestrators(args.api, args.viewer_token)
        if err:
            print(f"fetch error: {err}")
            return 1
        rows.sort(key=lambda r: Decimal(str(r.get("balance_eth", "0"))), reverse=True)
        max_bal = max((Decimal(str(r.get("balance_eth", "0"))) for r in rows), default=Decimal("0"))
        print("rank  orch_id           bal_eth     active  bar")
        for idx, row in enumerate(rows, start=1):
            orch_id = truncate(str(row.get("orchestrator_id", "")), 16)
            bal = Decimal(str(row.get("balance_eth", "0")))
            bal_fmt = fmt_decimal(str(bal), places=4)
            active = "yes" if row.get("active") else "no"
            bar_str = bar(float(bal), float(max_bal), width=12)
            print(f"{idx:>4}  {orch_id:<16}  {bal_fmt:>9}  {active:<6}  {bar_str}")
        return 0

    if mode == "self":
        me, err = fetch_orchestrator_me(args.api, args.orch_token)
        if err:
            print(f"fetch error: {err}")
            return 1
        if not me:
            print("no orchestrator record")
            return 1
        orch_id = me.get("orchestrator_id") or "unknown"
        bal = fmt_decimal(str(me.get("balance_eth", "0")), places=4)
        active = "yes" if me.get("active") else "no"
        in_use = "yes" if me.get("in_use") else "no"
        print(f"orch: {orch_id}")
        print(f"balance: {bal} | active: {active} | in_use: {in_use}")
        if gpu_stats:
            print("gpu stats:")
            for gpu in gpu_stats:
                util_bar = bar(float(gpu["util"]), 100.0, width=10)
                mem_bar = bar(float(gpu["mem_used"]), float(gpu["mem_total"] or 1), width=10)
                print(
                    f"  gpu{gpu['index']} {gpu['name']} | util {gpu['util']:>3}% {util_bar} | mem {gpu['mem_used']}/{gpu['mem_total']} {mem_bar} | temp {gpu['temp']}c"
                )
        return 0

    print("local-only mode (no tokens available)")
    if gpu_stats:
        print("gpu stats:")
        for gpu in gpu_stats:
            util_bar = bar(float(gpu["util"]), 100.0, width=10)
            mem_bar = bar(float(gpu["mem_used"]), float(gpu["mem_total"] or 1), width=10)
            print(
                f"  gpu{gpu['index']} {gpu['name']} | util {gpu['util']:>3}% {util_bar} | mem {gpu['mem_used']}/{gpu['mem_total']} {mem_bar} | temp {gpu['temp']}c"
            )
    return 0


def run_tui(args: argparse.Namespace) -> int:
    import curses

    mode = detect_mode(args.viewer_token, args.orch_token, args.mode)
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.nodelay(True)
    stdscr.keypad(True)

    last_error: Optional[str] = None
    next_refresh = 0.0
    rows: List[Dict[str, Any]] = []
    me: Optional[Dict[str, Any]] = None
    power_state = "unknown"
    containers: List[Dict[str, Any]] = []
    gpu_stats: List[Dict[str, Any]] = []

    try:
        while True:
            now = time.time()
            if now >= next_refresh:
                power_state, _ = fetch_local_power()
                containers, _ = fetch_local_meta()
                gpu_stats = fetch_gpu_stats()
                if mode == "global":
                    rows, last_error = fetch_orchestrators(args.api, args.viewer_token)
                    if rows:
                        rows.sort(key=lambda r: Decimal(str(r.get("balance_eth", "0"))), reverse=True)
                elif mode == "self":
                    me, last_error = fetch_orchestrator_me(args.api, args.orch_token)
                else:
                    last_error = None
                next_refresh = now + args.interval

            stdscr.erase()
            height, width = stdscr.getmaxyx()
            header = f"Embody TUI | {args.api} | {utc_now()} | mode={mode}"
            stdscr.addnstr(0, 0, header, width - 1)
            status = f"local power: {power_state} | local containers: {len(containers)} | gpus: {len(gpu_stats)}"
            stdscr.addnstr(1, 0, status, width - 1)
            if last_error:
                stdscr.addnstr(2, 0, f"fetch error: {last_error}", width - 1)
            else:
                stdscr.addnstr(2, 0, "q=quit  r=refresh  g=cosmo", width - 1)

            row = 4
            if mode == "global":
                stdscr.addnstr(3, 0, "rank  orch_id           bal_eth     active  bar", width - 1)
                max_bal = max((Decimal(str(r.get("balance_eth", "0"))) for r in rows), default=Decimal("0"))
                for idx, r in enumerate(rows, start=1):
                    if row >= height - 1:
                        break
                    orch_id = truncate(str(r.get("orchestrator_id", "")), 16)
                    bal = Decimal(str(r.get("balance_eth", "0")))
                    bal_fmt = fmt_decimal(str(bal), places=4)
                    active = "yes" if r.get("active") else "no"
                    bar_str = bar(float(bal), float(max_bal), width=12)
                    line = f"{idx:>4}  {orch_id:<16}  {bal_fmt:>9}  {active:<6}  {bar_str}"
                    stdscr.addnstr(row, 0, line, width - 1)
                    row += 1
            elif mode == "self":
                stdscr.addnstr(3, 0, "orchestrator stats", width - 1)
                if me:
                    orch_id = str(me.get("orchestrator_id", ""))
                    bal = fmt_decimal(str(me.get("balance_eth", "0")), places=4)
                    active = "yes" if me.get("active") else "no"
                    in_use = "yes" if me.get("in_use") else "no"
                    stdscr.addnstr(row, 0, f"id: {orch_id}", width - 1)
                    row += 1
                    stdscr.addnstr(row, 0, f"balance: {bal}", width - 1)
                    row += 1
                    stdscr.addnstr(row, 0, f"active: {active} | in_use: {in_use}", width - 1)
                    row += 1
                row += 1
                stdscr.addnstr(row, 0, "local containers:", width - 1)
                row += 1
                for item in containers[: max(0, height - row - 1)]:
                    name = str(item.get("name") or item.get("project") or "")
                    status = str(item.get("status") or "")
                    stdscr.addnstr(row, 0, f"- {name} [{status}]", width - 1)
                    row += 1
                if gpu_stats and row < height - 1:
                    row += 1
                    stdscr.addnstr(row, 0, "gpu stats:", width - 1)
                    row += 1
                    for gpu in gpu_stats[: max(0, height - row - 1)]:
                        util_bar = bar(float(gpu["util"]), 100.0, width=10)
                        mem_bar = bar(float(gpu["mem_used"]), float(gpu["mem_total"] or 1), width=10)
                        line = (
                            f"gpu{gpu['index']} {gpu['name']} | util {gpu['util']:>3}% {util_bar} | "
                            f"mem {gpu['mem_used']}/{gpu['mem_total']} {mem_bar} | temp {gpu['temp']}c"
                        )
                        stdscr.addnstr(row, 0, line, width - 1)
                        row += 1
            else:
                stdscr.addnstr(3, 0, "local-only mode (no tokens available)", width - 1)
                if gpu_stats and row < height - 1:
                    row += 1
                    stdscr.addnstr(row, 0, "gpu stats:", width - 1)
                    row += 1
                    for gpu in gpu_stats[: max(0, height - row - 1)]:
                        util_bar = bar(float(gpu["util"]), 100.0, width=10)
                        mem_bar = bar(float(gpu["mem_used"]), float(gpu["mem_total"] or 1), width=10)
                        line = (
                            f"gpu{gpu['index']} {gpu['name']} | util {gpu['util']:>3}% {util_bar} | "
                            f"mem {gpu['mem_used']}/{gpu['mem_total']} {mem_bar} | temp {gpu['temp']}c"
                        )
                        stdscr.addnstr(row, 0, line, width - 1)
                        row += 1

            stdscr.refresh()

            try:
                key = stdscr.getch()
            except Exception:
                key = -1
            if key in (ord("q"), 27):
                break
            if key == ord("r"):
                next_refresh = 0.0
            if key == ord("g"):
                if mode == "global":
                    payload = graph_payload_global(rows)
                else:
                    orch_id = str((me or {}).get("orchestrator_id") or os.environ.get("ORCHESTRATOR_ID") or "orch")
                    payload = graph_payload_self(orch_id, containers, power_state)
                path = graph_path(args.graph_out)
                write_graph(path, payload)
                curses.endwin()
                err = run_cosmo(path)
                if err:
                    print(err)
                    print(f"graph saved: {path}")
                    input("Press Enter to return to TUI...")
                stdscr = curses.initscr()
                curses.noecho()
                curses.cbreak()
                stdscr.nodelay(True)
                stdscr.keypad(True)
            time.sleep(0.1)
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Embody orchestrator TUI + cosmo graph export")
    parser.add_argument("--api", default=os.environ.get("PAYMENTS_API_URL", "http://3.141.111.200:8081"))
    parser.add_argument("--viewer-token", default=os.environ.get("PAYMENTS_VIEWER_TOKEN", ""))
    parser.add_argument("--orchestrator-token", dest="orch_token", default=os.environ.get("ORCHESTRATOR_TOKEN", ""))
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--mode", default="auto", help="auto|global|self|local")
    parser.add_argument("--graph-out", default=os.environ.get("EMBODY_TUI_GRAPH_PATH", ""))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--cosmo", action="store_true")
    args = parser.parse_args()

    if args.cosmo:
        mode = detect_mode(args.viewer_token, args.orch_token, args.mode)
        power_state, _ = fetch_local_power()
        containers, _ = fetch_local_meta()
        if mode == "global":
            rows, err = fetch_orchestrators(args.api, args.viewer_token)
            if err:
                print(f"fetch error: {err}")
                return 1
            payload = graph_payload_global(rows)
        else:
            orch_id = str(os.environ.get("ORCHESTRATOR_ID") or "orch")
            payload = graph_payload_self(orch_id, containers, power_state)
        path = graph_path(args.graph_out)
        write_graph(path, payload)
        err = run_cosmo(path)
        if err:
            print(err)
            print(f"graph saved: {path}")
        return 0
    if args.once:
        return render_once(args)
    return run_tui(args)


if __name__ == "__main__":
    raise SystemExit(main())
