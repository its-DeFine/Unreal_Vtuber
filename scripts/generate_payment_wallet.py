#!/usr/bin/env python3
"""Generate a fresh Ethereum wallet and inject it into the payments .env file."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple

from eth_account import Account

DEFAULT_ENV = Path(__file__).resolve().parent.parent / ".env"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV,
        help="Path to the .env file to update (default: ./ .env)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing PAYMENT_PRIVATE_KEY/ORCHESTRATOR_ADDRESS without prompting",
    )
    parser.add_argument(
        "--keep-dry-run",
        action="store_true",
        help="Do not modify PAYMENT_DRY_RUN (default behaviour sets it to false).",
    )
    return parser.parse_args()


def load_env_lines(env_path: Path) -> List[str]:
    if not env_path.exists():
        raise FileNotFoundError(f"Env file not found: {env_path}")
    return env_path.read_text().splitlines()


def already_has_values(lines: List[str]) -> Tuple[bool, bool]:
    key_present = False
    addr_present = False
    for line in lines:
        if line.startswith("PAYMENT_PRIVATE_KEY=") and line.strip() != "PAYMENT_PRIVATE_KEY=":
            key_present = True
        if line.startswith("ORCHESTRATOR_ADDRESS=") and line.strip() != "ORCHESTRATOR_ADDRESS=":
            addr_present = True
    return key_present, addr_present


def inject_values(lines: List[str], address: str, private_key: str, force: bool) -> List[str]:
    updated: List[str] = []
    found_key = False
    found_addr = False
    for line in lines:
        stripped = line.strip()
        if line.startswith("ORCHESTRATOR_ADDRESS="):
            if not force and stripped != "ORCHESTRATOR_ADDRESS=":
                raise ValueError("ORCHESTRATOR_ADDRESS already populated; rerun with --force to overwrite.")
            updated.append(f"ORCHESTRATOR_ADDRESS={address}")
            found_addr = True
        elif line.startswith("PAYMENT_PRIVATE_KEY="):
            if not force and stripped != "PAYMENT_PRIVATE_KEY=":
                raise ValueError("PAYMENT_PRIVATE_KEY already populated; rerun with --force to overwrite.")
            updated.append(f"PAYMENT_PRIVATE_KEY={private_key}")
            found_key = True
        elif stripped.startswith("#") and "PAYMENT_PRIVATE_KEY=" in stripped and not found_key:
            updated.append(f"PAYMENT_PRIVATE_KEY={private_key}")
            found_key = True
        else:
            updated.append(line)

    if not found_addr:
        updated.append(f"ORCHESTRATOR_ADDRESS={address}")
    if not found_key:
        updated.append(f"PAYMENT_PRIVATE_KEY={private_key}")
    return updated


def ensure_dry_run_line(lines: List[str], keep_true: bool) -> List[str]:
    if keep_true:
        return lines
    updated: List[str] = []
    replaced = False
    for line in lines:
        if line.startswith("PAYMENT_DRY_RUN=") and not replaced:
            updated.append("PAYMENT_DRY_RUN=false")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append("PAYMENT_DRY_RUN=false")
    return updated


def write_env(env_path: Path, original: List[str], new_lines: List[str]) -> None:
    backup_path = env_path.with_suffix(env_path.suffix + ".bak")
    original_text = "\n".join(original) + "\n"
    new_text = "\n".join(new_lines) + "\n"
    if not backup_path.exists():
        backup_path.write_text(original_text)
    env_path.write_text(new_text)


def main() -> int:
    args = parse_args()
    env_path = args.env_file

    try:
        original_lines = load_env_lines(env_path)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    key_present, addr_present = already_has_values(original_lines)
    if (key_present or addr_present) and not args.force:
        print("Existing wallet details detected. Use --force to overwrite.", file=sys.stderr)
        return 1

    acct = Account.create()
    address = acct.address
    private_key = acct.key.hex()

    try:
        new_lines = inject_values(original_lines, address, private_key, args.force)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    new_lines = ensure_dry_run_line(new_lines, args.keep_dry_run)
    write_env(env_path, original_lines, new_lines)

    print("Generated new wallet:")
    print(f"  Address: {address}")
    print(f"  Private key stored in: {env_path}")
    print("A backup of the previous .env (if any) is saved beside the original.")
    print("Remember to fund the address on Arbitrum One before disabling dry run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
