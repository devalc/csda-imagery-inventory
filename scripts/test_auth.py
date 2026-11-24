#!/usr/bin/env python3
"""Verify CSDA authentication without exposing secrets or downloading data."""
from __future__ import annotations
import re
from csda_common import authenticated_account_summary


def main() -> int:
    try:
        result = authenticated_account_summary()
    except BaseException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        reason = f"HTTP {status}" if isinstance(status, int) else re.sub(r"[^A-Za-z0-9_]", "", type(exc).__name__)
        print("CSDA authentication: FAILED"); print(f"Reason: {reason}"); return 1
    print("CSDA authentication: SUCCESS")
    print(f"Vendor entitlement records: {len(result.get('vendors', []))}")
    print(f"Reduced-latency data flag: {result.get('reduced_latency_data')}")
    print("No imagery was downloaded or ordered.")
    return 0


if __name__ == "__main__": raise SystemExit(main())

