#!/usr/bin/env python3
"""Create AOI-specific, metadata-only CSDA inventories from a JSON config."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pyproj import Geod
from shapely.geometry import shape

from csda_common import authenticated_account_summary, collections, load_aoi, project_root, sanitize, search

GEOD = Geod(ellps="WGS84")
INVENTORY_COLUMNS = (
    "provider", "collection", "product", "scene_id", "acquisition_datetime",
    "platform", "cloud_cover_percent", "gsd_m", "intersection_area_km2",
    "aoi_coverage_percent", "asset_count", "asset_keys", "asset_statuses",
    "total_asset_size_bytes",
)


def area_km2(geometry) -> float:
    return abs(GEOD.geometry_area_perimeter(geometry)[0]) / 1_000_000


def item_row(item: dict, aoi) -> dict:
    props, assets = item.get("properties", {}), item.get("assets", {})
    footprint = shape(item["geometry"]) if item.get("geometry") else None
    overlap = footprint.intersection(aoi) if footprint and footprint.is_valid else None
    overlap_area = area_km2(overlap) if overlap and not overlap.is_empty else 0.0
    statuses = sorted({str(x.get("status")) for x in assets.values() if x.get("status")})
    sizes = [x.get("file:size") or x.get("file_size") for x in assets.values()]
    return {
        "provider": props.get("provider") or props.get("constellation") or item.get("collection"),
        "collection": item.get("collection"), "product": props.get("pl:item_type") or props.get("csda:item_type") or props.get("processing:level"),
        "scene_id": item.get("id"), "acquisition_datetime": props.get("datetime") or props.get("start_datetime"),
        "platform": props.get("platform") or props.get("constellation"),
        "cloud_cover_percent": props.get("eo:cloud_cover", props.get("pl:cloud_percent")), "gsd_m": props.get("gsd", props.get("eo:gsd")),
        "intersection_area_km2": round(overlap_area, 6), "aoi_coverage_percent": round(100 * overlap_area / area_km2(aoi), 3),
        "asset_count": len(assets), "asset_keys": ";".join(sorted(assets)), "asset_statuses": ";".join(statuses),
        "total_asset_size_bytes": sum(x for x in sizes if isinstance(x, (int, float))),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/areas.json")
    parser.add_argument("--output", default="outputs")
    args = parser.parse_args(); root = project_root()
    config_path = (root / args.config).resolve(); config = json.loads(config_path.read_text())
    output = (root / args.output).resolve(); output.mkdir(parents=True, exist_ok=True)
    account = authenticated_account_summary()
    (output / "account_access_summary.json").write_text(json.dumps(account, indent=2), encoding="utf-8")
    advertised = collections(); advertised_ids = {x["id"] for x in advertised}
    selected = config.get("collections") or sorted(advertised_ids)
    date_range = f"{config.get('search_start', '2000-01-01T00:00:00Z')}/{config['as_of']}"
    max_items = int(config.get("max_items_per_collection", 5000))
    for spec in config["areas"]:
        aoi_path = (root / spec["geojson"]).resolve(); aoi = load_aoi(aoi_path)
        rows, audits = [], []
        for collection_id in selected:
            if collection_id not in advertised_ids:
                audits.append({"collection": collection_id, "not_run": True, "reason": "not advertised"}); continue
            items, audit = search(collection_id, aoi.bounds, date_range, max_items); audits.append(audit)
            rows.extend(item_row(item, aoi) for item in items if item.get("geometry") and shape(item["geometry"]).intersects(aoi))
        area_out = output / spec["id"]; area_out.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(rows, columns=INVENTORY_COLUMNS)
        frame.to_csv(area_out / "inventory.csv", index=False)
        summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "area_id": spec["id"], "area_name": spec["name"], "aoi": spec["geojson"], "date_range": date_range, "records": len(frame), "collections": dict(Counter(frame.collection)) if not frame.empty else {}, "metadata_only": True}
        (area_out / "summary.json").write_text(json.dumps(sanitize(summary), indent=2), encoding="utf-8")
        (area_out / "pagination_audit.json").write_text(json.dumps(audits, indent=2), encoding="utf-8")
        print(spec["id"], len(frame), "records")
    return 0


if __name__ == "__main__": raise SystemExit(main())

