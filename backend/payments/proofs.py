"""Verification helpers for orchestrator-submitted proofs.

These helpers currently perform structural validation and compute stable hashes
of the submitted proof payloads. They should be replaced with real zk-proof
verification once integrated with the chosen proof system.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


class ProofVerificationError(Exception):
    """Raised when a proof payload is invalid."""


def _require_dict(value: Any, *, field: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ProofVerificationError(f"{field} must be an object")
    return value


def _hash_payload(data: Dict[str, Any]) -> str:
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_script_proof(
    proof: Dict[str, Any],
    *,
    script_root: str,
    asset_root: Optional[str],
    frame_root: str,
    command_root: str,
    nonce: str,
) -> Dict[str, Any]:
    """Validate the submitted proof payload.

    The placeholder implementation ensures the payload contains the expected
    public input values and returns a deterministic hash for auditing. Real zk
    verification logic should be wired in here.
    """

    proof_payload = _require_dict(proof, field="proof")

    public_inputs = proof_payload.get("public_inputs")
    if public_inputs is None:
        raise ProofVerificationError("proof.public_inputs missing")
    public_inputs = _require_dict(public_inputs, field="proof.public_inputs")

    def _ensure_match(key: str, expected: Optional[str]) -> None:
        if expected is None:
            return
        value = public_inputs.get(key)
        if value != expected:
            raise ProofVerificationError(f"proof public input mismatch for {key}")

    _ensure_match("script_root", script_root)
    _ensure_match("asset_root", asset_root)
    _ensure_match("frame_root", frame_root)
    _ensure_match("command_root", command_root)
    _ensure_match("nonce", nonce)

    status = proof_payload.get("status")
    if status not in {"ok", "valid", True}:
        raise ProofVerificationError("proof.status indicates failure")

    proof_hash = _hash_payload(proof_payload)
    return {
        "proof_hash": proof_hash,
        "public_inputs": public_inputs,
    }


__all__ = ["ProofVerificationError", "verify_script_proof"]
