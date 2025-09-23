"""Container health monitor reused by the payments backend."""
from __future__ import annotations

import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Iterable, List

import docker

logger = logging.getLogger(__name__)


class ServiceMonitor:
    """Tracks a fixed list of Docker containers and computes uptime metrics."""

    def __init__(
        self,
        services: Iterable[str] | None = None,
        check_interval: int = 10,
        uptime_window: int = 60,
    ) -> None:
        try:
            self.docker_client = docker.from_env()
        except Exception:  # pragma: no cover - fallback for custom sockets
            self.docker_client = docker.DockerClient(base_url="unix://var/run/docker.sock")

        env_services = os.environ.get("MONITORED_SERVICES")
        if env_services:
            services = [svc.strip() for svc in env_services.split(",") if svc.strip()]

        self.monitored_services: List[str] = list(services or [
            "vtuber-unreal-game",
            "vtuber-unreal-signaling",
            "vtuber-turn-server",
        ])

        self.check_interval = check_interval
        self.uptime_window = uptime_window
        self.service_stats: Dict[str, Dict[str, Any]] = {}
        self._last_missing: set[str] = set()
        self.last_check: float | None = None

    def check_services(self) -> Dict[str, Any]:
        """Return health information for monitored services."""
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
            status_message = f"Offline services detected: {missing_list}" if missing_list else "Offline services detected"
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


__all__ = ["ServiceMonitor"]
