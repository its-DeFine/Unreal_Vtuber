"""Helpers to retrieve orchestrator addresses from Livepeer APIs."""
from __future__ import annotations

import logging
from typing import Iterable, List, Sequence, Set

import requests
from eth_utils import is_address, to_checksum_address

logger = logging.getLogger(__name__)

EXPLORER_ENDPOINTS: Sequence[str] = (
    "https://explorer.livepeer.org/api/orchestrators",
    "https://api.livepeer.org/orchestrator",
)

SUBGRAPH_ENDPOINT = "https://api.thegraph.com/subgraphs/name/livepeer/livepeer"


def fetch_from_explorer() -> List[str]:
    addresses: List[str] = []
    for url in EXPLORER_ENDPOINTS:
        try:
            logger.debug("Fetching orchestrators from %s", url)
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                addresses.extend(_extract_addresses(data))
            elif isinstance(data, dict):
                orch = data.get("orchestrators") or data.get("data", {}).get("orchestrators")
                if isinstance(orch, list):
                    addresses.extend(_extract_addresses(orch))
            if addresses:
                break
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("Explorer request failed for %s: %s", url, exc)
    return addresses


def _extract_addresses(payload: Iterable[dict]) -> List[str]:
    acc: List[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        for key in ("address", "id", "serviceURI", "ethAddress"):
            value = item.get(key)
            if isinstance(value, str) and _looks_like_address(value):
                acc.append(value)
                break
    return acc


def fetch_from_subgraph(limit: int = 100) -> List[str]:
    query = """
    query ($limit: Int!) {
      transcoders(first: $limit, where: {active: true}) {
        id
      }
    }
    """
    try:
        resp = requests.post(
            SUBGRAPH_ENDPOINT,
            json={"query": query, "variables": {"limit": limit}},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        transcoders = data.get("data", {}).get("transcoders", [])
        return [t["id"] for t in transcoders if isinstance(t, dict) and "id" in t]
    except Exception as exc:  # pragma: no cover - network errors
        logger.warning("Subgraph request failed: %s", exc)
        return []


def fetch_orchestrator_addresses(limit: int = 100) -> List[str]:
    """Aggregate orchestrator addresses from available sources."""
    collected: Set[str] = set()

    for fetcher in (lambda: fetch_from_subgraph(limit=limit), fetch_from_explorer):
        results = fetcher()
        for addr in results:
            if _looks_like_address(addr):
                collected.add(to_checksum_address(addr))
        if len(collected) >= limit:
            break

    return list(list(collected)[:limit])


def _looks_like_address(value: str) -> bool:
    candidate = value.strip()
    if candidate.startswith("0x") and len(candidate) == 42:
        return is_address(candidate)
    return False


__all__ = [
    "fetch_orchestrator_addresses",
    "fetch_from_explorer",
    "fetch_from_subgraph",
]
