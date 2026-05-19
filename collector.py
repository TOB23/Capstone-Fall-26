"""Run one collection pass over the utility registry.

Designed to run on a schedule -- cron, or a GitHub Actions workflow (see
README and .github/workflows/collect.yml). A single pass writes one
timestamped parquet snapshot to data/snapshots/. Use --loop only if you are
running it as a long-lived process rather than on an external scheduler.

    python collector.py            # one pass, then exit  (use with cron)
    python collector.py --loop     # run forever, one pass every COLLECTION_INTERVAL

Only requests + pandas + pyarrow are needed to run the collector; geopandas is
needed later, by county_aggregate.py.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd

from config import (REGISTRY_PATH, SNAPSHOT_DIR, MIN_DELAY_PER_HOST,
                    COLLECTION_INTERVAL)
from Code.base import build_session
from kubra import KubraAdapter
from Code.arcgis import ArcGISAdapter

# Register new platform adapters here.
ADAPTERS = {"kubra": KubraAdapter, "arcgis": ArcGISAdapter}

SNAPSHOT_COLUMNS = ["utility_id", "observed_at", "customers_out", "latitude",
                    "longitude", "area_name", "source_platform", "raw_id"]


def load_registry() -> list[dict]:
    """Return the enabled registry entries."""
    with open(REGISTRY_PATH) as fh:
        entries = json.load(fh)
    return [e for e in entries if e.get("enabled")]


def _host_of(cfg: dict) -> str:
    for key in ("metadata_url", "service_url"):
        if cfg.get(key):
            return urlparse(cfg[key]).netloc
    return ""


def collect_once() -> str:
    """Run one full pass; return the path of the snapshot written."""
    session = build_session()
    adapters = {name: cls(session=session) for name, cls in ADAPTERS.items()}
    registry = load_registry()
    print(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}Z  "
          f"collecting {len(registry)} utilities")

    last_hit: dict[str, float] = defaultdict(float)
    rows: list[dict] = []
    n_ok = n_fail = 0

    for entry in registry:
        utility_id = entry["utility_id"]
        platform = entry.get("platform", "").strip().lower()
        if platform not in adapters:
            print(f"  [skip] {utility_id}: unknown platform '{platform}'")
            continue
        cfg = entry.get("config", {}) or {}

        # Per-host politeness: never issue back-to-back requests to one server.
        host = _host_of(cfg)
        wait = MIN_DELAY_PER_HOST - (time.monotonic() - last_hit[host])
        if wait > 0:
            time.sleep(wait)

        try:
            records = adapters[platform].fetch(utility_id, cfg)
            rows.extend(r.as_dict() for r in records)
            n_ok += 1
            print(f"  [ok]   {utility_id}: {len(records)} records")
        except Exception as exc:                       # one utility must not abort the pass
            n_fail += 1
            print(f"  [fail] {utility_id}: {type(exc).__name__}: {exc}")
        finally:
            last_hit[host] = time.monotonic()

    df = pd.DataFrame(rows, columns=SNAPSHOT_COLUMNS)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = SNAPSHOT_DIR / f"snapshot_{stamp}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"  -> {len(df)} records, {n_ok} ok / {n_fail} failed, wrote {out_path}")
    return str(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="National outage collector")
    parser.add_argument("--loop", action="store_true",
                        help="run continuously instead of a single pass")
    args = parser.parse_args()

    if args.loop:
        print(f"Looping: one pass every {COLLECTION_INTERVAL}s. Ctrl-C to stop.")
        while True:
            try:
                collect_once()
            except Exception as exc:
                print(f"  pass failed: {type(exc).__name__}: {exc}")
            time.sleep(COLLECTION_INTERVAL)
    else:
        collect_once()


if __name__ == "__main__":
    main()
