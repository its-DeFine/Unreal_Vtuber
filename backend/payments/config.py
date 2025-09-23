"""Settings loader for the payments backend."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LedgerPaths(BaseModel):
    balances: Path = Field(default=Path("/app/data/balances.json"))


class RegistryPaths(BaseModel):
    registry: Path = Field(default=Path("/app/data/registry.json"))


class PaymentSettings(BaseSettings):
    orchestrator_id: str = Field(default="local-orchestrator", env="ORCHESTRATOR_ID")
    orchestrator_address: str = Field(..., env="ORCHESTRATOR_ADDRESS")

    payment_interval_seconds: int = Field(default=60, env="PAYMENT_INTERVAL_SECONDS")
    payment_increment_eth: Decimal = Field(default=Decimal("0.00001"), env="PAYMENT_INCREMENT_ETH")
    payout_threshold_eth: Decimal = Field(default=Decimal("0.001"), env="PAYMENT_PAYOUT_THRESHOLD_ETH")

    eth_rpc_url: str = Field(..., env="ETH_RPC_URL")
    chain_id: int = Field(default=42161, env="ETH_CHAIN_ID")

    payment_private_key: Optional[str] = Field(default=None, env="PAYMENT_PRIVATE_KEY")
    payment_keystore_path: Optional[Path] = Field(default=None, env="PAYMENT_KEYSTORE_PATH")
    payment_keystore_password: Optional[str] = Field(default=None, env="PAYMENT_KEYSTORE_PASSWORD")

    payment_dry_run: bool = Field(default=True, env="PAYMENT_DRY_RUN")

    ledger: LedgerPaths = Field(default_factory=LedgerPaths)
    registry_paths: RegistryPaths = Field(default_factory=RegistryPaths)

    top_contract_address: Optional[str] = Field(default=None, env="TOP_CONTRACT_ADDRESS")
    top_contract_function: str = Field(default="getTop", env="TOP_CONTRACT_FUNCTION")
    top_contract_abi_path: Optional[Path] = Field(default=None, env="TOP_CONTRACT_ABI_PATH")
    top_contract_abi_json: Optional[str] = Field(default=None, env="TOP_CONTRACT_ABI_JSON")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("orchestrator_address")
    def validate_orchestrator_address(cls, value: str) -> str:
        if not value:
            raise ValueError("ORCHESTRATOR_ADDRESS must be set")
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

    @field_validator("payment_interval_seconds")
    def validate_interval(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("PAYMENT_INTERVAL_SECONDS must be positive")
        return value


settings = PaymentSettings()
