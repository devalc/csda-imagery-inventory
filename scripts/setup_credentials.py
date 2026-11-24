#!/usr/bin/env python3
"""Safely create the repository-local .env file."""
from __future__ import annotations
import getpass
import os
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"


def quoted(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def main() -> int:
    if ENV.exists() and input("A .env file exists. Overwrite it? [y/N]: ").strip().lower() not in {"y", "yes"}:
        print("Existing .env was not changed."); return 0
    username = input("NASA Earthdata username: ").strip()
    password = getpass.getpass("NASA Earthdata password: ")
    if not username or not password:
        print("Credentials were not saved: both values are required."); return 1
    fd = os.open(ENV, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(f"EARTHDATA_USERNAME={quoted(username)}\nEARTHDATA_PASSWORD={quoted(password)}\n")
    try: os.chmod(ENV, 0o600)
    except OSError: pass
    print("CSDA/Earthdata credentials saved locally to .env")
    return 0


if __name__ == "__main__": raise SystemExit(main())

