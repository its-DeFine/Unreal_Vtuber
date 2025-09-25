"""Ethereum payment helper built on web3.py."""
from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)

WEI_PER_ETH = Decimal(10) ** 18


class PaymentClient:
    def __init__(
        self,
        rpc_url: str,
        chain_id: int,
        private_key: Optional[str] = None,
        keystore_path: Optional[Path] = None,
        keystore_password: Optional[str] = None,
        dry_run: bool = True,
    ) -> None:
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        # Ensure compatibility with Arbitrum / rollups that use Clique-like consensus
        self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self.chain_id = chain_id
        self.dry_run = dry_run
        self._account: Optional[LocalAccount] = None

        if private_key:
            self._account = Account.from_key(private_key)
        elif keystore_path and keystore_password:
            try:
                with Path(keystore_path).expanduser().open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                decrypted = Account.decrypt(data, keystore_password)
                self._account = Account.from_key(decrypted)
            except Exception as exc:
                logger.error("Failed to decrypt keystore %s: %s", keystore_path, exc)
        else:
            logger.info("Payment client running without signing key (dry-run=%s)", dry_run)

    @property
    def sender(self) -> Optional[str]:
        if isinstance(self._account, LocalAccount):
            return self._account.address
        return None

    def send_payment(self, recipient: str, amount_eth: Decimal) -> Optional[str]:
        wei_amount = int(amount_eth * WEI_PER_ETH)
        if wei_amount <= 0:
            logger.info("Skipping zero-value payment to %s", recipient)
            return None

        if not self._account or self.dry_run:
            logger.info(
                "Dry-run payment: would send %s wei to %s (sender=%s)",
                wei_amount,
                recipient,
                self.sender,
            )
            return None

        sender = self.sender
        try:
            recipient_checksum = Web3.to_checksum_address(recipient)
        except ValueError as exc:
            raise RuntimeError(f"Invalid recipient address {recipient}") from exc

        gas_price = self.web3.eth.gas_price
        nonce = self.web3.eth.get_transaction_count(sender, block_identifier="pending")
        estimate_payload = {
            "from": sender,
            "to": recipient_checksum,
            "value": wei_amount,
        }
        try:
            gas_limit = int(self.web3.eth.estimate_gas(estimate_payload))
        except Exception:  # pragma: no cover - estimation failures fall back to base gas
            gas_limit = 21_000
        gas_limit = max(21_000, gas_limit)
        tx = {
            "chainId": self.chain_id,
            "nonce": nonce,
            "to": recipient_checksum,
            "value": wei_amount,
            "gas": gas_limit,
        }

        max_priority_fee = getattr(self.web3.eth, "max_priority_fee", None)
        if callable(max_priority_fee):
            try:
                priority_fee = max_priority_fee()
            except Exception:  # pragma: no cover - fallback to gas price
                priority_fee = gas_price
            max_fee = max(gas_price, priority_fee) * 2
            tx.update(
                {
                    "maxPriorityFeePerGas": priority_fee,
                    "maxFeePerGas": max_fee,
                }
            )
        else:
            tx["gasPrice"] = gas_price * 2

        signed = self.web3.eth.account.sign_transaction(tx, self._account.key)
        raw_tx = getattr(signed, "rawTransaction", None) or getattr(
            signed, "raw_transaction", None
        )
        if raw_tx is None:  # pragma: no cover - defensive, should not happen
            raise RuntimeError("Signed transaction missing raw data")
        tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
        logger.info("Submitted payment tx %s to %s (%s eth)", tx_hash.hex(), recipient_checksum, amount_eth)
        return tx_hash.hex()
