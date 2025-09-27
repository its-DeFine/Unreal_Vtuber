from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import requests


def upload(
    file_path: Path,
    storage_url: str,
    session_id: str,
    orchestrator_id: Optional[str] = None,
    token: Optional[str] = None,
) -> None:
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    headers = {"X-Storage-Token": token} if token else {}
    with file_path.open("rb") as fh:
        files = {"file": (file_path.name, fh, "video/webm")}
        data = {"session_id": session_id}
        if orchestrator_id:
            data["orchestrator_id"] = orchestrator_id
        resp = requests.post(f"{storage_url.rstrip('/')}/api/captures", files=files, data=data, headers=headers, timeout=60)
        resp.raise_for_status()
        print(resp.json())


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a capture to the storage service")
    parser.add_argument("file", type=Path)
    parser.add_argument("session_id")
    parser.add_argument("storage_url")
    parser.add_argument("--orchestrator-id")
    parser.add_argument("--token")
    args = parser.parse_args()

    upload(args.file, args.storage_url, args.session_id, args.orchestrator_id, args.token)


if __name__ == "__main__":
    main()
