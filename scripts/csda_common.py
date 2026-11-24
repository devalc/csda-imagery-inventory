"""Shared, metadata-only CSDA helpers. No order, tasking, or download functions."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from httpx import BasicAuth
from shapely.geometry import shape
from shapely.ops import unary_union

STAC_URL = "https://csdap.earthdata.nasa.gov/stac"
SECRET_PATTERN = re.compile(r"authorization|token|cookie|password|username", re.I)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_env(path: Path | None = None) -> dict[str, str]:
    path = path or project_root() / ".env"
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key not in {"EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"}:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1].replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        values[key] = value
    return values


def credentials() -> tuple[str, str]:
    values = load_env()
    username = values.get("EARTHDATA_USERNAME") or os.getenv("EARTHDATA_USERNAME", "")
    password = values.get("EARTHDATA_PASSWORD") or os.getenv("EARTHDATA_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("Earthdata credentials are missing; run scripts/setup_credentials.py")
    return username, password


def authenticated_account_summary() -> dict[str, Any]:
    """Return a sanitized entitlement summary from the authenticated CSDA profile."""
    from csda_client import CsdaClient
    username, password = credentials()
    with CsdaClient.open(BasicAuth(username=username, password=password)) as client:
        client.verify()
        profile = client.profile(username).model_dump(mode="json")
    return sanitize({
        "authentication": "SUCCESS",
        "reduced_latency_data": profile.get("reduced_latency_data"),
        "vendors": [{k: row.get(k) for k in ("vendor", "slug", "approved", "preview_approved", "expiration_date", "quota", "quota_unit")} for row in profile.get("vendors", [])],
    })


def load_aoi(path: Path):
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("type") == "FeatureCollection":
        geometries = [shape(x["geometry"]) for x in document.get("features", []) if x.get("geometry")]
    elif document.get("type") == "Feature":
        geometries = [shape(document["geometry"])]
    else:
        geometries = [shape(document)]
    geometry = unary_union(geometries)
    if geometry.is_empty:
        raise ValueError(f"AOI contains no geometry: {path}")
    return geometry


def collections() -> list[dict[str, Any]]:
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        response = client.get(f"{STAC_URL}/collections")
        response.raise_for_status()
        return response.json().get("collections", [])


def search(collection: str, bbox: tuple[float, float, float, float], date_range: str, max_items: int) -> tuple[list[dict], dict]:
    params: dict[str, Any] | None = {"collections": collection, "bbox": ",".join(map(str, bbox)), "datetime": date_range, "limit": min(1000, max_items)}
    url, items, pages, truncated = f"{STAC_URL}/search", [], 0, False
    with httpx.Client(follow_redirects=True, timeout=180, headers={"User-Agent": "reusable-csda-inventory/1.0"}) as client:
        while url and len(items) < max_items:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json(); pages += 1
            features = payload.get("features", []); room = max_items - len(items)
            items.extend(features[:room])
            nxt = next((x for x in payload.get("links", []) if x.get("rel") == "next" and x.get("method", "GET").upper() == "GET"), None)
            truncated = truncated or len(features) > room or bool(nxt and len(items) >= max_items)
            url, params = (nxt.get("href"), None) if nxt and len(items) < max_items else (None, None)
    deduped = list({(x.get("collection"), x.get("id")): x for x in items}.values())
    return deduped, {"collection": collection, "pages": pages, "items": len(deduped), "truncated": truncated, "max_items": max_items}


def safe_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items() if not SECRET_PATTERN.search(str(k))}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return safe_url(value)
    return value

