"""HTTP API for orchestrator self-registration and admin visibility."""
from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from .config import PaymentSettings
from .ledger import Ledger
from .registry import Registry, RegistryError


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._events: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            queue = self._events.setdefault(key, deque())
            cutoff = now - self.window_seconds
            while queue and queue[0] < cutoff:
                queue.popleft()
            if len(queue) >= self.max_calls:
                return False
            queue.append(now)
            return True


class RegistrationPayload(BaseModel):
    orchestrator_id: str = Field(min_length=1, max_length=128)
    address: str = Field(pattern=r"^0x[a-fA-F0-9]{40}$")
    capability: Optional[str] = Field(default=None, max_length=128)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    host_public_ip: Optional[str] = Field(default=None, max_length=64)
    host_name: Optional[str] = Field(default=None, max_length=128)
    services_healthy: Optional[bool] = Field(default=None)
    health_url: Optional[str] = Field(default=None, max_length=512)
    health_timeout: Optional[float] = Field(default=None, ge=0.1, le=60.0)
    monitored_services: Optional[List[str]] = Field(default=None)
    min_service_uptime: Optional[float] = Field(default=None, ge=0.0, le=100.0)

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        candidate = value.strip()
        if not candidate:
            return None
        if "@" not in candidate or candidate.startswith("@") or candidate.endswith("@"):
            raise ValueError("contact_email must include '@'")
        return candidate

    @field_validator("monitored_services")
    @classmethod
    def validate_services(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        cleaned: List[str] = []
        for item in value:
            if not item:
                continue
            candidate = item.strip()
            if not candidate:
                continue
            cleaned.append(candidate)
        if not cleaned:
            return None
        if len(cleaned) > 25:
            raise ValueError("monitored_services limit is 25 entries")
        return cleaned


class RegistrationResponse(BaseModel):
    orchestrator_id: str
    address: str
    balance_eth: str
    eligible_for_payments: bool
    is_top_100: bool
    registration_count: int
    cooldown_expires_at: Optional[str]
    message: str


class OrchestratorRecord(BaseModel):
    orchestrator_id: str
    address: str
    balance_eth: str
    eligible_for_payments: bool
    is_top_100: bool
    cooldown_expires_at: Optional[str]
    cooldown_active: bool
    first_seen: Optional[str]
    last_seen: Optional[str]
    registration_count: int
    contact_email: Optional[str]
    capability: Optional[str]
    host_public_ip: Optional[str]
    host_name: Optional[str]
    last_seen_ip: Optional[str]
    last_missed_all_services: Optional[str]
    last_healthy_at: Optional[str]
    last_cooldown_started_at: Optional[str]
    last_cooldown_cleared_at: Optional[str]
    health_url: Optional[str]
    health_timeout: Optional[float]
    monitored_services: Optional[List[str]]
    min_service_uptime: Optional[float]


class OrchestratorsResponse(BaseModel):
    orchestrators: List[OrchestratorRecord]


def create_app(registry: Registry, ledger: Ledger, settings: PaymentSettings) -> FastAPI:
    app = FastAPI(title="Embody Payments", version="1.0.0")

    per_minute_limiter = RateLimiter(
        max_calls=settings.registration_rate_limit_per_minute,
        window_seconds=60,
    )
    burst_limiter = RateLimiter(
        max_calls=settings.registration_rate_limit_burst,
        window_seconds=10,
    )

    async def require_admin(request: Request) -> None:
        token = settings.api_admin_token
        if not token:
            return
        provided = request.headers.get("X-Admin-Token")
        if provided != token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin token required")

    @app.exception_handler(RegistryError)
    async def registry_error_handler(_: Request, exc: RegistryError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @app.post("/api/orchestrators/register", response_model=RegistrationResponse)
    async def register(payload: RegistrationPayload, request: Request) -> RegistrationResponse:
        client_ip = request.client.host if request.client else None
        limiter_keys = [f"id:{payload.orchestrator_id}"]
        if client_ip:
            limiter_keys.append(f"ip:{client_ip}")

        for key in limiter_keys:
            if not per_minute_limiter.allow(key) or not burst_limiter.allow(key):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many registration attempts; slow down",
                )

        metadata = {
            "capability": payload.capability,
            "contact_email": payload.contact_email,
            "host_public_ip": payload.host_public_ip,
            "host_name": payload.host_name,
            "request_ip": client_ip,
            "services_healthy": payload.services_healthy,
        }
        if payload.health_url:
            metadata["health_url"] = payload.health_url
        if payload.health_timeout is not None:
            metadata["health_timeout"] = payload.health_timeout
        if payload.monitored_services:
            metadata["monitored_services"] = payload.monitored_services
        if payload.min_service_uptime is not None:
            metadata["min_service_uptime"] = payload.min_service_uptime

        result = registry.register(
            orchestrator_id=payload.orchestrator_id,
            address=payload.address,
            metadata=metadata,
        )
        balance = ledger.get_balance(payload.orchestrator_id)

        return RegistrationResponse(
            orchestrator_id=result.orchestrator_id,
            address=result.address,
            balance_eth=str(balance),
            eligible_for_payments=result.eligible_for_payments,
            is_top_100=result.is_top_100,
            registration_count=result.registration_count,
            cooldown_expires_at=result.cooldown_expires_at,
            message=result.message,
        )

    @app.get("/api/orchestrators", response_model=OrchestratorsResponse)
    async def list_orchestrators(_: Any = Depends(require_admin)) -> OrchestratorsResponse:
        records = registry.all_records()
        response: List[OrchestratorRecord] = []
        now = datetime.now(timezone.utc)
        for orchestrator_id, record in records.items():
            balance = ledger.get_balance(orchestrator_id)
            cooldown_expires_at = record.get("cooldown_expires_at")
            cooldown_active = False
            if isinstance(cooldown_expires_at, str):
                try:
                    expires = datetime.fromisoformat(cooldown_expires_at)
                    cooldown_active = expires > now
                except ValueError:
                    cooldown_active = False
            response.append(
                OrchestratorRecord(
                    orchestrator_id=orchestrator_id,
                    address=record.get("address", ""),
                    balance_eth=str(balance),
                    eligible_for_payments=bool(record.get("eligible_for_payments", False)),
                    is_top_100=bool(record.get("is_top_100", False)),
                    cooldown_expires_at=cooldown_expires_at,
                    cooldown_active=cooldown_active,
                    first_seen=record.get("first_seen"),
                    last_seen=record.get("last_seen"),
                    registration_count=int(record.get("registration_count", 0)),
                    contact_email=record.get("contact_email"),
                    capability=record.get("capability"),
                    host_public_ip=record.get("host_public_ip"),
                    host_name=record.get("host_name"),
                    last_seen_ip=record.get("last_seen_ip"),
                    last_missed_all_services=record.get("last_missed_all_services"),
                    last_healthy_at=record.get("last_healthy_at"),
                    last_cooldown_started_at=record.get("last_cooldown_started_at"),
                    last_cooldown_cleared_at=record.get("last_cooldown_cleared_at"),
                    health_url=record.get("health_url"),
                    health_timeout=record.get("health_timeout"),
                    monitored_services=record.get("monitored_services"),
                    min_service_uptime=record.get("min_service_uptime"),
                )
            )

        return OrchestratorsResponse(orchestrators=response)

    @app.get("/api/orchestrators/{orchestrator_id}", response_model=OrchestratorRecord)
    async def get_orchestrator(orchestrator_id: str, _: Any = Depends(require_admin)) -> OrchestratorRecord:
        record = registry.get_record(orchestrator_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        balance = ledger.get_balance(orchestrator_id)
        cooldown_expires_at = record.get("cooldown_expires_at")
        cooldown_active = False
        if isinstance(cooldown_expires_at, str):
            try:
                expires = datetime.fromisoformat(cooldown_expires_at)
                cooldown_active = expires > datetime.now(timezone.utc)
            except ValueError:
                cooldown_active = False
        return OrchestratorRecord(
            orchestrator_id=orchestrator_id,
            address=record.get("address", ""),
            balance_eth=str(balance),
            eligible_for_payments=bool(record.get("eligible_for_payments", False)),
            is_top_100=bool(record.get("is_top_100", False)),
            cooldown_expires_at=cooldown_expires_at,
            cooldown_active=cooldown_active,
            first_seen=record.get("first_seen"),
            last_seen=record.get("last_seen"),
            registration_count=int(record.get("registration_count", 0)),
            contact_email=record.get("contact_email"),
            capability=record.get("capability"),
            host_public_ip=record.get("host_public_ip"),
            host_name=record.get("host_name"),
            last_seen_ip=record.get("last_seen_ip"),
            last_missed_all_services=record.get("last_missed_all_services"),
            last_healthy_at=record.get("last_healthy_at"),
            last_cooldown_started_at=record.get("last_cooldown_started_at"),
            last_cooldown_cleared_at=record.get("last_cooldown_cleared_at"),
        )

    return app


def run_api(app: FastAPI, settings: PaymentSettings) -> None:
    """Run the FastAPI app using uvicorn."""
    import uvicorn  # Imported lazily to avoid mandatory dependency in tests

    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
        root_path=settings.api_root_path,
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = False
    server.run()


__all__ = ["create_app", "run_api"]
