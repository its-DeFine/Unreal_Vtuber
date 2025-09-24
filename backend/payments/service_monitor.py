"""Container health monitor reused by the payments backend."""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import docker
import requests

logger = logging.getLogger(__name__)


class ServiceMonitor:
    """Tracks Docker containers or remote health endpoints and computes uptime."""

    def __init__(
        self,
        services: Iterable[str] | None = None,
        check_interval: int = 10,
        uptime_window: int = 60,
        remote_health_url: Optional[str] = None,
        remote_health_timeout: float = 5.0,
    ) -> None:
        try:
            self.docker_client = docker.from_env()
        except Exception:  # pragma: no cover - fallback for custom sockets
            self.docker_client = docker.DockerClient(base_url="unix://var/run/docker.sock")

        env_services = os.environ.get("MONITORED_SERVICES")
        if env_services:
            services = [svc.strip() for svc in env_services.split(",") if svc.strip()]

        self.monitored_services: List[str] = list(
            services
            or [
                "vtuber-unreal-game",
                "vtuber-unreal-signaling",
                "vtuber-turn-server",
            ]
        )

        self.check_interval = check_interval
        self.uptime_window = uptime_window
        self.service_stats: Dict[str, Dict[str, Any]] = {}
        self._last_missing: set[str] = set()
        self.last_check: float | None = None

        self.remote_health_url = remote_health_url or os.environ.get("ORCHESTRATOR_HEALTH_URL")
        try:
            env_timeout = float(os.environ.get("ORCHESTRATOR_HEALTH_TIMEOUT", "5"))
        except ValueError:
            env_timeout = 5.0
        self.remote_health_timeout = (
            remote_health_timeout if remote_health_url else env_timeout
        )

    def check_services(self) -> Dict[str, Any]:
        """Return health information for monitored services."""
        if self.remote_health_url:
            remote = self._fetch_remote_health()
            if remote is not None:
                return remote

        containers = {c.name: c for c in self.docker_client.containers.list(all=True)}
        current_time = time.time()
        services_status: Dict[str, Dict[str, Any]] = {}

        for name in self.monitored_services:
            container = containers.get(name)
            stats = self.service_stats.setdefault(
                name,
                {"checks": [], "uptime_percentage": 0.0, "last_status": "missing"},
            )

            if container is None:
                stats.update({"last_status": "missing", "uptime_percentage": 0.0})
                services_status[name] = {
                    "status": "missing",
                    "running": False,
                    "uptime_percentage": 0.0,
                    "checks_count": len(stats["checks"]),
                    "health": "unknown",
                }
                continue

            is_running = container.status == "running"
            stats["checks"].append({"timestamp": current_time, "running": is_running})
            cutoff = current_time - self.uptime_window
            stats["checks"] = [chk for chk in stats["checks"] if chk["timestamp"] > cutoff]

            checks = stats["checks"]
            if checks:
                running_checks = sum(1 for chk in checks if chk["running"])
                uptime_pct = (running_checks / len(checks)) * 100
            else:
                uptime_pct = 0.0

            stats["uptime_percentage"] = uptime_pct
            stats["last_status"] = "running" if is_running else "stopped"

            services_status[name] = {
                "status": container.status,
                "running": is_running,
                "uptime_percentage": uptime_pct,
                "checks_count": len(checks),
                "health": container.attrs.get("State", {}).get("Health", {}).get("Status", "unknown"),
            }

        self.last_check = current_time
        summary = self.get_summary()

        return {
            "timestamp": datetime.now().isoformat(),
            "services": services_status,
            "monitored_count": len(self.monitored_services),
            "summary": summary,
        }

    def get_summary(self) -> Dict[str, Any]:
        total_services = len(self.monitored_services)
        if total_services == 0:
            return {
                "overall_uptime": 0.0,
                "calculated_uptime": 0.0,
                "services_up": 0,
                "services_down": 0,
                "total_services": 0,
                "eligible_for_payment": False,
                "min_uptime_required": float(os.environ.get("MIN_SERVICE_UPTIME", "80.0")),
                "missing_services": [],
                "running_services": [],
                "status_message": "No services configured",
            }

        total_uptime = sum(
            self.service_stats.get(name, {}).get("uptime_percentage", 0.0)
            for name in self.monitored_services
        )
        window_average = total_uptime / total_services if total_services else 0.0

        services_up = []
        services_down = []
        for name in self.monitored_services:
            if self.service_stats.get(name, {}).get("last_status") == "running":
                services_up.append(name)
            else:
                services_down.append(name)

        missing_set = set(services_down)
        status_message = "All required services online"
        if missing_set:
            missing_list = ", ".join(sorted(missing_set))
            status_message = (
                f"Offline services detected: {missing_list}"
                if missing_list
                else "Offline services detected"
            )
            if missing_set != self._last_missing:
                logger.warning(status_message)
        elif self._last_missing:
            logger.info("All required services restored")

        self._last_missing = missing_set
        overall_uptime = 100.0 if not missing_set else 0.0
        min_uptime_threshold = float(os.environ.get("MIN_SERVICE_UPTIME", "80.0"))
        eligible = not missing_set

        return {
            "overall_uptime": overall_uptime,
            "calculated_uptime": window_average,
            "services_up": len(services_up),
            "services_down": len(services_down),
            "total_services": total_services,
            "eligible_for_payment": eligible,
            "min_uptime_required": min_uptime_threshold,
            "missing_services": services_down,
            "running_services": services_up,
            "status_message": status_message,
        }

    def all_required_services_running(self) -> bool:
        """True if every monitored container is running."""
        summary = self.get_summary()
        return summary["eligible_for_payment"] and not summary["missing_services"]

    def _fetch_remote_health(self) -> Optional[Dict[str, Any]]:
        url = self.remote_health_url
        if not url:
            return None
        try:
            response = requests.get(
                url,
                timeout=self.remote_health_timeout,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or "summary" not in data:
                logger.warning("Remote health response malformed: %s", data)
                return None
            return data
        except requests.RequestException as exc:
            logger.warning("Remote health check failed (%s): %s", url, exc)
            return None


__all__ = ["ServiceMonitor"]
