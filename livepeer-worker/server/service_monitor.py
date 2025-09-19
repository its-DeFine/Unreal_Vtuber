"""
Service Monitor for BYOB Pixel Streaming stack
Tracks uptime/health of core services to determine BYOC payment eligibility.
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Any

import asyncio
import docker

logger = logging.getLogger(__name__)


class ServiceMonitor:
    """Monitors Docker containers that make up the VTuber runtime."""

    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except Exception:
            self.docker_client = docker.DockerClient(base_url="unix://var/run/docker.sock")

        # Containers that must remain available for BYOB payouts
        self.monitored_services = [
            "vtuber-unreal-game",
            "vtuber-unreal-signaling",
            "vtuber-turn-server",
            "livepeer-worker",
            "vtuber-ollama",
            "nginx_rtmp",
            "management_agent",
            "prometheus",
            "grafana",
            "node_exporter",
            "cadvisor",
            "ollama_exporter",
            "nginx_exporter",
        ]

        self.service_stats: Dict[str, Dict[str, Any]] = {}
        self.check_interval = 10
        self.uptime_window = 60
        self.last_check = None

    def check_services(self) -> Dict[str, Any]:
        """Return health information for all monitored services."""
        try:
            containers = {c.name: c for c in self.docker_client.containers.list(all=True)}
            current_time = time.time()
            services_status: Dict[str, Dict[str, Any]] = {}

            for name in self.monitored_services:
                container = containers.get(name)
                stats = self.service_stats.setdefault(
                    name,
                    {
                        "checks": [],
                        "uptime_percentage": 0.0,
                        "last_status": "missing",
                    },
                )

                if container is None:
                    stats["last_status"] = "missing"
                    stats["uptime_percentage"] = 0.0
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

            return {
                "timestamp": datetime.now().isoformat(),
                "services": services_status,
                "monitored_count": len(self.monitored_services),
                "summary": self.get_summary(),
            }

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(f"Error checking services: {exc}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(exc),
                "services": {},
                "monitored_count": 0,
            }

    def get_summary(self) -> Dict[str, Any]:
        total_services = len(self.monitored_services)
        if total_services == 0:
            return {
                "overall_uptime": 0.0,
                "services_up": 0,
                "services_down": 0,
                "total_services": 0,
                "eligible_for_payment": False,
                "min_uptime_required": float(os.environ.get("MIN_SERVICE_UPTIME", "80.0")),
            }

        total_uptime = sum(self.service_stats.get(name, {}).get("uptime_percentage", 0.0) for name in self.monitored_services)
        overall_uptime = total_uptime / total_services if total_services else 0.0

        services_up = sum(
            1 for name in self.monitored_services if self.service_stats.get(name, {}).get("last_status") == "running"
        )
        services_down = total_services - services_up

        min_uptime_threshold = float(os.environ.get("MIN_SERVICE_UPTIME", "80.0"))
        eligible = overall_uptime >= min_uptime_threshold

        return {
            "overall_uptime": overall_uptime,
            "services_up": services_up,
            "services_down": services_down,
            "total_services": total_services,
            "eligible_for_payment": eligible,
            "min_uptime_required": min_uptime_threshold,
        }

    async def start_monitoring(self):
        while True:
            self.check_services()
            await asyncio.sleep(self.check_interval)


service_monitor = ServiceMonitor()
