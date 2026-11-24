#!/usr/bin/env python3
"""Filter generated inventories against configurable pre/during/post event windows."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from csda_common import project_root


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",default="config/event_windows.json"); parser.add_argument("--inventory-root",default="outputs")
    args=parser.parse_args(); root=project_root(); config=json.loads((root/args.config).read_text()); inv_root=root/args.inventory_root
    imagery=set(config.get("imagery_collections",[])); summaries=[]; candidates=[]
    for area_id,windows in config["areas"].items():
        frame=pd.read_csv(inv_root/area_id/"inventory.csv",low_memory=False)
        frame["datetime"]=pd.to_datetime(frame.acquisition_datetime,format="mixed",errors="coerce",utc=True)
        frame=frame[frame.collection.isin(imagery)&frame.datetime.notna()].copy()
        for window in windows:
            start=pd.Timestamp(window["start"],tz="UTC"); end=pd.Timestamp(window["end"]+" 23:59:59",tz="UTC")
            inside=frame[frame.datetime.between(start,end)].copy()
            summaries.append({"area_id":area_id,"window":window["name"],"start":window["start"],"end":window["end"],"description":window.get("description"),"records":len(inside),"collections":"; ".join(f"{k}: {v}" for k,v in inside.collection.value_counts().items())})
            relations=[("in_window",inside.sort_values(["cloud_cover_percent","aoi_coverage_percent","datetime"],ascending=[True,False,False],na_position="last").head(50)),("nearest_before",frame[frame.datetime<start].sort_values("datetime",ascending=False).head(5)),("nearest_after",frame[frame.datetime>end].sort_values("datetime").head(5))]
            for relation,subset in relations:
                for _,row in subset.iterrows():
                    delta=0 if relation=="in_window" else ((start-row.datetime).days if relation=="nearest_before" else (row.datetime-end).days)
                    record=row.drop(labels=["datetime"]).to_dict(); record.update({"area_id":area_id,"window":window["name"],"relation":relation,"days_from_window":int(delta)}); candidates.append(record)
    pd.DataFrame(summaries).to_csv(inv_root/"event_window_summary.csv",index=False)
    pd.DataFrame(candidates).to_csv(inv_root/"event_window_candidates.csv",index=False)
    print(pd.DataFrame(summaries).to_string(index=False)); return 0


if __name__ == "__main__": raise SystemExit(main())

