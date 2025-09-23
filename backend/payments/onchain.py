"""Utility helpers for read-only contract queries."""
from __future__ import annotations

from typing import Any, Iterable

from web3 import Web3


def fetch_top_entries(
    web3: Web3,
    contract_address: str,
    abi: Iterable[dict[str, Any]],
    function_name: str = "getTop",
    limit: int = 100,
) -> Any:
    """Call a view function that returns the top entries from a contract.

    The helper assumes the contract exposes a callable `function_name` that
    accepts a single integer argument specifying how many entries to return.
    """
    contract = web3.eth.contract(address=contract_address, abi=list(abi))
    fn = contract.get_function_by_name(function_name)
    return fn(limit).call()
