#!/usr/bin/env python3
"""Register an orchestrator with the central payments backend."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request

try:  # Prefer requests for better HTTPS/redirect handling
    import requests  # type: ignore
except ImportError:  # pragma: no cover - environment without requests
    requests = None  # type: ignore

DEFAULT_RETRY_SECONDS = 5.0
DEFAULT_RETRY_MULTIPLIER = 1.8
DEFAULT_MAX_RETRY_SECONDS = 300.0
DEFAULT_TIMEOUT_SECONDS = 15.0
METADATA_BASE = "http://169.254.169.254/latest"


def env_default(key: str, fallback: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(key)
    if value is not None and value.strip() == "":
        return fallback
    return value if value is not None else fallback


def detect_public_ip(timeout: float = 1.0) -> Optional[str]:
    """Best-effort fetch of this host's public IPv4 from EC2 metadata."""

    def _request(path: str, method: str = "GET", headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        req = request.Request(path, method=method, headers=headers or {})
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8").strip()
        except Exception:
            return None

    # Try IMDSv2 token first
    token = _request(
        f"{METADATA_BASE}/api/token",
        method="PUT",
        headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
    )
    headers = {"X-aws-ec2-metadata-token": token} if token else None
    ip = _request(f"{METADATA_BASE}/meta-data/public-ipv4", headers=headers)
    return ip or None


def parse_service_list(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    items = [item.strip() for item in raw.split(",")]
    cleaned = [item for item in items if item]
    return cleaned or None


def parse_optional_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=env_default("PAYMENTS_API_URL"), help="Base URL for the payments backend (e.g., https://backend.example.com)")
    parser.add_argument("--orchestrator-id", default=env_default("ORCHESTRATOR_ID"), help="Unique orchestrator identifier")
    parser.add_argument("--orchestrator-address", default=env_default("ORCHESTRATOR_ADDRESS"), help="Ethereum address for payouts")
    parser.add_argument("--capability", default=env_default("ORCHESTRATOR_CAPABILITY"), help="Optional capability label")
    parser.add_argument("--contact-email", default=env_default("ORCHESTRATOR_CONTACT_EMAIL"), help="Optional contact email")
    parser.add_argument("--host-name", default=env_default("ORCHESTRATOR_HOST_NAME"), help="Optional host name metadata")
    parser.add_argument("--host-public-ip", default=env_default("ORCHESTRATOR_HOST_PUBLIC_IP"), help="Optional public IP metadata")
    parser.add_argument("--health-url", default=env_default("ORCHESTRATOR_HEALTH_URL"), help="Optional override for the orchestrator health endpoint URL")
    parser.add_argument(
        "--health-port",
        type=int,
        default=int(env_default("ORCHESTRATOR_HEALTH_PORT", "9090")),
        help="Health endpoint port used when guessing the URL (default: 9090)",
    )
    parser.add_argument(
        "--health-timeout",
        type=float,
        default=parse_optional_float(env_default("ORCHESTRATOR_HEALTH_TIMEOUT", None)),
        help="Health endpoint timeout reported to the backend",
    )
    parser.add_argument(
        "--monitored-services",
        default=env_default("ORCHESTRATOR_MONITORED_SERVICES"),
        help="Comma-separated service names to report for monitoring",
    )
    parser.add_argument(
        "--min-service-uptime",
        type=float,
        default=parse_optional_float(env_default("ORCHESTRATOR_MIN_SERVICE_UPTIME", None)),
        help="Minimum uptime percentage required for eligibility",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(env_default("PAYMENTS_API_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS))),
        help="HTTP request timeout in seconds",
    )
    parser.add_argument("--retry-seconds", type=float, default=float(env_default("PAYMENTS_REGISTRATION_RETRY_SECONDS", str(DEFAULT_RETRY_SECONDS))), help="Initial retry delay in seconds")
    parser.add_argument("--retry-multiplier", type=float, default=float(env_default("PAYMENTS_REGISTRATION_RETRY_MULTIPLIER", str(DEFAULT_RETRY_MULTIPLIER))), help="Exponential backoff multiplier")
    parser.add_argument("--max-retry-seconds", type=float, default=float(env_default("PAYMENTS_REGISTRATION_MAX_SECONDS", str(DEFAULT_MAX_RETRY_SECONDS))), help="Maximum total time to keep retrying")
    parser.add_argument("--once", action="store_true", help="Send a single request without retrying on failures")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    missing = []
    if not args.api_url:
        missing.append("PAYMENTS_API_URL")
    if not args.orchestrator_id:
        missing.append("ORCHESTRATOR_ID")
    if not args.orchestrator_address:
        missing.append("ORCHESTRATOR_ADDRESS")
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required configuration: {joined}")

    address = args.orchestrator_address.strip()
    if not (address.startswith("0x") and len(address) == 42):
        raise ValueError("ORCHESTRATOR_ADDRESS must be a 42-character hex string")


def build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "orchestrator_id": args.orchestrator_id,
        "address": args.orchestrator_address,
    }
    if args.capability:
        payload["capability"] = args.capability
    if args.contact_email:
        payload["contact_email"] = args.contact_email
    if args.host_name:
        payload["host_name"] = args.host_name
    host_ip = args.host_public_ip or detect_public_ip()
    if host_ip:
        payload["host_public_ip"] = host_ip

    health_url = args.health_url
    if not health_url and host_ip:
        health_url = f"http://{host_ip}:{args.health_port}/health"
    if health_url:
        payload["health_url"] = health_url

    if args.health_timeout is not None:
        payload["health_timeout"] = args.health_timeout
    services = parse_service_list(args.monitored_services)
    if services:
        payload["monitored_services"] = services
    if args.min_service_uptime is not None:
        payload["min_service_uptime"] = args.min_service_uptime
    return payload


def attempt_registration(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    url = args.api_url.rstrip("/") + "/api/orchestrators/register"
    payload_dict = build_payload(args)

    if requests is not None:  # type: ignore
        try:
            response = requests.post(  # type: ignore
                url,
                json=payload_dict,
                timeout=args.timeout,
                allow_redirects=True,
            )
            try:
                body = response.json()
            except ValueError:
                body = {"detail": response.text}
            return response.status_code, body
        except requests.RequestException:  # type: ignore
            return _attempt_with_curl(url, payload_dict, timeout=args.timeout)

    payload = json.dumps(payload_dict).encode("utf-8")
    status, body = _attempt_with_urllib(url, payload, timeout=args.timeout)
    if status == 307:
        redirect_url = body.get("Location") if isinstance(body, dict) else None
        if redirect_url:
            return _attempt_with_urllib(redirect_url, payload, timeout=args.timeout)
    if status is not None and status != 0:
        return status, body

    return _attempt_with_curl(url, payload_dict, timeout=args.timeout)

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_args(args)
    except ValueError as exc:
        print(f"[registrar] configuration error: {exc}", file=sys.stderr)
        print(
            "[registrar] Ensure PAYMENTS_API_URL, ORCHESTRATOR_ID, and ORCHESTRATOR_ADDRESS are set (typically via `.env`).",
            file=sys.stderr,
        )
        print(
            "[registrar] Tip: on a fresh host, run `./scripts/embody_cli.sh setup` to generate `.env` / `.env.turn`.",
            file=sys.stderr,
        )
        return 2

    start = time.time()
    delay = max(args.retry_seconds, 0.5)
    attempt = 0

    while True:
        attempt += 1
        try:
            status, body = attempt_registration(args)
        except (error.URLError, TimeoutError) as exc:
            print(f"[registrar] network error on attempt {attempt}: {exc}", file=sys.stderr)
            status = None
            body = {"detail": str(exc)}
        else:
            if status == 200:
                message = body.get("message", "registered")
                balance = body.get("balance_eth", "0")
                print(
                    f"[registrar] registration succeeded (attempt {attempt}): {message}, balance={balance}"
                )
                return 0
            if status is None or status == 0:
                detail = body.get("detail") or body
                print(
                    f"[registrar] network/timeout on attempt {attempt}: {detail}",
                    file=sys.stderr,
                )
            else:
                detail = body.get("detail") or body
                print(
                    f"[registrar] backend rejected registration (status {status}): {detail}",
                    file=sys.stderr,
                )
                if status is not None and status < 500:
                    return 0

        if args.once:
            return 0

        elapsed = time.time() - start
        if elapsed >= args.max_retry_seconds:
            print(
                f"[registrar] giving up after {elapsed:.1f}s of retries; exiting",
                file=sys.stderr,
            )
            return 0

        time.sleep(delay)
        delay = min(delay * args.retry_multiplier, 60.0)


def _attempt_with_urllib(url: str, payload: bytes, *, timeout: float) -> Tuple[Optional[int], Dict[str, Any]]:
    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8") or "{}"
            return resp.status, json.loads(body)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8") or "{}"
        try:
            data = json.loads(detail)
        except Exception:
            data = {"detail": detail}
        if exc.code in (307, 308):
            location = exc.headers.get("Location")
            if location:
                return 307, {"Location": location}
        return exc.code, data
    except TimeoutError as exc:
        return None, {"detail": str(exc) or "timed out"}
    except error.URLError as exc:
        return None, {"detail": str(exc)}


def _attempt_with_curl(url: str, payload: Dict[str, Any], *, timeout: float) -> Tuple[int, Dict[str, Any]]:
    connect_timeout = min(max(timeout, 1.0), 5.0)
    cmd = [
        "curl",
        "-sS",
        "-L",
        "--connect-timeout",
        str(connect_timeout),
        "--max-time",
        str(timeout),
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(payload),
        url,
        "-o",
        "-",
        "-w",
        "\n%{http_code}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or f"curl exited with {result.returncode}"
        return 0, {"detail": detail, "curl_exit_code": result.returncode}
    stdout = result.stdout.rstrip("\n")
    if "\n" in stdout:
        body_text, status_text = stdout.rsplit("\n", 1)
    else:
        body_text, status_text = "", stdout
    try:
        status_code = int(status_text)
    except ValueError:
        status_code = 0
    try:
        body = json.loads(body_text or "{}")
    except json.JSONDecodeError:
        body = {"detail": body_text}
    return status_code, body


if __name__ == "__main__":
    sys.exit(main())
