"""Settings loader for the payments backend."""
from __future__ import annotations

import os
import re
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LedgerPaths(BaseModel):
    balances: Path = Field(default=Path("/app/data/balances.json"))


class RegistryPaths(BaseModel):
    registry: Path = Field(default=Path("/app/data/registry.json"))


class BootstrapOrchestrator(BaseModel):
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


class PaymentSettings(BaseSettings):
    orchestrator_id: Optional[str] = Field(default=None, env="ORCHESTRATOR_ID")
    orchestrator_address: Optional[str] = Field(default=None, env="ORCHESTRATOR_ADDRESS")
    orchestrator_health_url: Optional[str] = Field(default=None, env="ORCHESTRATOR_HEALTH_URL")
    orchestrator_health_timeout: Optional[float] = Field(default=None, env="ORCHESTRATOR_HEALTH_TIMEOUT")

    payment_interval_seconds: int = Field(default=60, env="PAYMENT_INTERVAL_SECONDS")
    payment_increment_eth: Decimal = Field(default=Decimal("0.00001"), env="PAYMENT_INCREMENT_ETH")
    payout_threshold_eth: Decimal = Field(default=Decimal("0.001"), env="PAYMENT_PAYOUT_THRESHOLD_ETH")

    eth_rpc_url: str = Field(default="http://localhost:8545", env="ETH_RPC_URL")
    chain_id: int = Field(default=42161, env="ETH_CHAIN_ID")

    payment_private_key: Optional[str] = Field(default=None, env="PAYMENT_PRIVATE_KEY")
    payment_keystore_path: Optional[Path] = Field(default=None, env="PAYMENT_KEYSTORE_PATH")
    payment_keystore_password: Optional[str] = Field(default=None, env="PAYMENT_KEYSTORE_PASSWORD")

    payment_dry_run: bool = Field(default=True, env="PAYMENT_DRY_RUN")

    ledger: LedgerPaths = Field(default_factory=LedgerPaths)
    registry_paths: RegistryPaths = Field(default_factory=RegistryPaths)

    bootstrap_orchestrators_path: Optional[Path] = Field(
        default=Path("/app/data/orchestrators.json"),
        env="PAYMENTS_BOOTSTRAP_ORCHESTRATORS_PATH",
    )
    bootstrap_orchestrators_inline: Optional[str] = Field(
        default=None,
        env="PAYMENTS_BOOTSTRAP_ORCHESTRATORS",
    )
    bootstrap_skip_rank_validation: bool = Field(
        default=True,
        env="PAYMENTS_BOOTSTRAP_SKIP_RANK_VALIDATION",
    )

    top_contract_address: Optional[str] = Field(default=None, env="TOP_CONTRACT_ADDRESS")
    top_contract_function: str = Field(default="getTop", env="TOP_CONTRACT_FUNCTION")
    top_contract_abi_path: Optional[Path] = Field(default=None, env="TOP_CONTRACT_ABI_PATH")
    top_contract_abi_json: Optional[str] = Field(default=None, env="TOP_CONTRACT_ABI_JSON")
    top_cache_ttl_seconds: int = Field(default=300, env="TOP_CACHE_TTL_SECONDS")

    api_host: str = Field(default="0.0.0.0", env="PAYMENTS_API_HOST")
    api_port: int = Field(default=8081, env="PAYMENTS_API_PORT")
    api_root_path: str = Field(default="", env="PAYMENTS_API_ROOT_PATH")
    api_admin_token: Optional[str] = Field(default=None, env="PAYMENTS_API_ADMIN_TOKEN")

    registration_rate_limit_per_minute: int = Field(
        default=5, env="PAYMENTS_REGISTRATION_PER_MINUTE"
    )
    registration_rate_limit_burst: int = Field(
        default=5, env="PAYMENTS_REGISTRATION_BURST"
    )

    single_orchestrator_mode: bool = Field(
        default=True, env="PAYMENTS_SINGLE_ORCHESTRATOR_MODE"
    )
    payment_miss_threshold: int = Field(default=3, env="PAYMENTS_MISS_THRESHOLD")
    payment_cooldown_seconds: int = Field(default=3600, env="PAYMENTS_COOLDOWN_SECONDS")

    default_health_timeout: float = Field(default=5.0, env="PAYMENTS_DEFAULT_HEALTH_TIMEOUT")
    default_min_service_uptime: float = Field(default=80.0, env="PAYMENTS_DEFAULT_MIN_SERVICE_UPTIME")
    audit_log_path: Path = Field(default=Path("/app/data/audit/registry.log"), env="PAYMENTS_AUDIT_LOG_PATH")
    address_denylist: List[str] = Field(default_factory=list, env="PAYMENTS_ADDRESS_DENYLIST")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("orchestrator_address")
    def validate_orchestrator_address(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not value.startswith("0x") or len(value) != 42:
            raise ValueError("ORCHESTRATOR_ADDRESS must be a 42-character hex string")
        return value

    @field_validator("payment_increment_eth", "payout_threshold_eth", mode="before")
    def coerc_decimal(cls, value):  # type: ignore[override]
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid decimal value: {value}") from exc

    @field_validator(
        "payment_interval_seconds",
        "api_port",
        "registration_rate_limit_per_minute",
        "registration_rate_limit_burst",
        "payment_miss_threshold",
        "payment_cooldown_seconds",
        "top_cache_ttl_seconds",
    )
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Value must be positive")
        return value

    @field_validator(
        "default_health_timeout",
        "default_min_service_uptime",
        "orchestrator_health_timeout",
    )
    def validate_positive_float(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return value
        if value <= 0:
            raise ValueError("Value must be positive")
        return value

    @field_validator("address_denylist", mode="before")
    @classmethod
    def parse_address_denylist(cls, value):  # type: ignore[override]
        if value is None:
            return []
        if isinstance(value, str):
            parts = re.split(r"[\s,]+", value.strip())
            return [part for part in parts if part]
        return value

    @field_validator("address_denylist")
    @classmethod
    def normalize_address_denylist(cls, value: List[str]) -> List[str]:
        normalized: List[str] = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("address_denylist entries must be strings")
            candidate = item.strip()
            if not candidate:
                continue
            if not candidate.startswith("0x") or len(candidate) != 42:
                raise ValueError("address_denylist entries must be 42-character hex strings")
            candidate_lower = candidate.lower()
            if not all(ch in "0123456789abcdef" for ch in candidate_lower[2:]):
                raise ValueError("address_denylist entries must be valid hex strings")
            if candidate_lower in seen:
                continue
            seen.add(candidate_lower)
            normalized.append(candidate_lower)
        return normalized

    @model_validator(mode="after")
    def populate_denylist_and_validate(self) -> "PaymentSettings":
        if not self.address_denylist:
            raw = os.environ.get("PAYMENTS_ADDRESS_DENYLIST")
            if raw:
                parts = self.parse_address_denylist(raw)
                self.address_denylist = self.normalize_address_denylist(parts)
        if self.single_orchestrator_mode:
            if not self.orchestrator_id:
                raise ValueError(
                    "ORCHESTRATOR_ID must be set when PAYMENTS_SINGLE_ORCHESTRATOR_MODE is enabled"
                )
            if not self.orchestrator_address:
                raise ValueError(
                    "ORCHESTRATOR_ADDRESS must be set when PAYMENTS_SINGLE_ORCHESTRATOR_MODE is enabled"
                )
        return self


settings = PaymentSettings()
payout_override = os.environ.get("PAYMENT_PAYOUT_THRESHOLD_ETH")
if payout_override is not None:
    try:
        settings.payout_threshold_eth = Decimal(str(payout_override))
    except Exception:  # pragma: no cover - defensive
        pass
