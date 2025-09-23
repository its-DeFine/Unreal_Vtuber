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
from web3.middleware import geth_poa_middleware

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
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
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

        gas_price = self.web3.eth.gas_price
        nonce = self.web3.eth.get_transaction_count(self.sender)
        tx = {
            "chainId": self.chain_id,
            "nonce": nonce,
            "to": recipient,
            "value": wei_amount,
            "gas": 21_000,
            "gasPrice": gas_price,
        }

        signed = self._account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        logger.info("Submitted payment tx %s to %s (%s eth)", tx_hash.hex(), recipient, amount_eth)
        return tx_hash.hex()
