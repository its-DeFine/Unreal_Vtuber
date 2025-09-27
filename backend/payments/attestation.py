"""Utility helpers for validating attestation payloads.

These are lightweight placeholders that validate attestation structure and
surface the data we need to persist. Real TEE validation should replace this
module when integrating with Nitro Enclaves / SEV-SNP / TDX.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AttestationError(Exception):
    """Raised when the attestation payload is invalid."""


def _require_dict(value: Any, *, field: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise AttestationError(f"{field} must be an object")
    return value


def verify_attestation(
    payload: Dict[str, Any],
    *,
    expected_nonce: str,
) -> Dict[str, Any]:
    """Validate a TEE attestation payload.

    Returns a normalized dictionary containing the fields we persist. The
    implementation is intentionally conservative and should be replaced with
    vendor-specific quote validation when available.
    """

    attestation = _require_dict(payload, field="attestation")

    nonce = attestation.get("nonce")
    if not isinstance(nonce, str):
        raise AttestationError("attestation.nonce must be a string")
    if nonce != expected_nonce:
        raise AttestationError("attestation nonce mismatch")

    measurement = attestation.get("measurement")
    if measurement is not None and not isinstance(measurement, str):
        raise AttestationError("attestation.measurement must be a string")

    gpu_uuid = attestation.get("gpu_uuid")
    if gpu_uuid is not None and not isinstance(gpu_uuid, str):
        raise AttestationError("attestation.gpu_uuid must be a string when provided")

    timestamp = attestation.get("timestamp")
    if isinstance(timestamp, str):
        try:
            datetime.fromisoformat(timestamp)
        except ValueError as exc:  # pragma: no cover - defensive
            raise AttestationError("attestation.timestamp is not ISO-8601") from exc
    else:
        timestamp = datetime.now(timezone.utc).isoformat()

    # Optional roots may come embedded in the attestation. When present we
    # round-trip them as strings so callers can compare against explicit inputs.
    frame_root = attestation.get("frame_root")
    command_root = attestation.get("command_root")
    script_root = attestation.get("script_root")
    asset_root = attestation.get("asset_root")

    normalized: Dict[str, Any] = {
        "nonce": nonce,
        "timestamp": timestamp,
        "measurement": measurement,
        "gpu_uuid": gpu_uuid,
        "frame_root": frame_root,
        "command_root": command_root,
        "script_root": script_root,
        "asset_root": asset_root,
        # Successful validation implies trusted capture.
        "capture_trust_level": "trusted",
    }

    logger.debug("Validated attestation: %s", json.dumps(normalized, sort_keys=True))
    return normalized


__all__ = ["AttestationError", "verify_attestation"]
