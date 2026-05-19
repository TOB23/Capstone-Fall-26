"""Batch-probe every utility in the starter list and produce a triage worklist.

The slow part of building the registry is not the copy-paste of entries - it is
deciding which utility to investigate and how. This script does that triage in
one run: it hits every utility's outage-map URL, records whether the URL is
alive, and pre-classifies the platform (KUBRA / ArcGIS / unknown) with
discover.py.

    python batch_check.py                       # check the whole starter list
    python batch_check.py --limit 20            # just the top 20 by rank
    python batch_check.py --registry registry.json   # check a different file

Input : starter/registry_starter.json by default (or --registry).
Output: starter/url_triage.csv  - one row per utility, sorted by priority rank.

The CSV columns:
    rank, utility_id, utility_name, states, customers_k,
    url, http_status, url_alive, platform_guess, confidence, candidate_urls, note

How to use the output:
  * url_alive == False  -> the starter URL is stale (like FPL's was). Search
    "<utility> outage map" for the current URL before investigating.
  * platform_guess == kubra / arcgis -> batch these; same DevTools moves each.
  * platform_guess == unknown -> needs a real investigation; may be a new
    platform (like FPL's countyjson).

This does NOT register anything and does NOT replace the DevTools step. It
tells you where the real work is so you are not investigating blind.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from urllib.parse import urlparse

from config import REGISTRY_PATH, MIN_DELAY_PER_HOST, ROOT
from base import build_session
from discover import classify_outage_map

STARTER_REGISTRY = ROOT / "starter" / "registry_starter.json"
TRIAGE_CSV = ROOT / "starter" / "url_triage.csv"


def load_entries(registry_path: Path) -> list[dict]:
    entries = json.loads(registry_path.read_text(encoding="utf-8"))
    # Sort by priority rank when present so the worklist is biggest-first.
    entries.sort(key=lambda e: e.get("_priority_rank", 9999))
    return entries


def probe_one(entry: dict, session) -> dict:
    """Probe a single utility: is the URL alive, and what platform is it?"""
    uid = entry.get("utility_id", "?")
    url = entry.get("_outage_map_url") or entry.get("config", {}).get("feed_url", "")
    row = {
        "rank": entry.get("_priority_rank", ""),
        "utility_id": uid,
        "utility_name": entry.get("utility_name", ""),
        "states": ",".join(entry.get("states", [])),
        "customers_k": entry.get("customers_served", 0) // 1000,
        "url": url,
        "http_status": "",
        "url_alive": False,
        "platform_guess": "unknown",
        "confidence": "low",
        "candidate_urls": "",
        "note": "",
    }
    if not url:
        row["note"] = "no URL in starter list"
        return row

    # Step 1: a lightweight reachability check.
    try:
        resp = session.get(url, timeout=30, allow_redirects=True)
        row["http_status"] = resp.status_code
        row["url_alive"] = resp.ok
        if not resp.ok:
            row["note"] = f"URL returned {resp.status_code} - find current URL"
            return row
    except Exception as exc:
        row["http_status"] = "ERR"
        row["note"] = f"could not reach: {type(exc).__name__}"
        return row

    # Step 2: platform classification (reuses discover.py).
    try:
        disc = classify_outage_map(url, session=session)
        row["platform_guess"] = disc.platform
        row["confidence"] = disc.confidence
        row["candidate_urls"] = " | ".join(disc.candidate_urls[:3])
        if disc.platform == "unknown":
            row["note"] = "platform not identifiable from HTML - DevTools needed"
        else:
            row["note"] = f"{disc.platform} detected - confirm endpoints in DevTools"
    except Exception as exc:
        row["note"] = f"classify failed: {type(exc).__name__}"
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-probe starter utility URLs")
    parser.add_argument("--registry", default=None,
                        help="registry JSON to check (default: starter/registry_starter.json)")
    parser.add_argument("--limit", type=int, default=None,
                        help="only check the top N by rank")
    args = parser.parse_args()

    registry_path = Path(args.registry) if args.registry else STARTER_REGISTRY
    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    entries = load_entries(registry_path)
    if args.limit:
        entries = entries[:args.limit]

    print(f"Probing {len(entries)} utilities from {registry_path.name}")
    print("(one HTTP request per utility, polite delay between hosts)\n")

    session = build_session()
    last_hit: dict[str, float] = {}
    rows = []
    for i, entry in enumerate(entries, 1):
        url = entry.get("_outage_map_url", "")
        host = urlparse(url).netloc if url else ""
        if host in last_hit:
            wait = MIN_DELAY_PER_HOST - (time.monotonic() - last_hit[host])
            if wait > 0:
                time.sleep(wait)
        row = probe_one(entry, session)
        last_hit[host] = time.monotonic()
        rows.append(row)
        flag = "ok  " if row["url_alive"] else "DEAD"
        print(f"  [{i:>3}/{len(entries)}] {flag} {row['utility_id']:<20} "
              f"{row['platform_guess']:<9} {row['note']}")

    # Write the triage CSV.
    with open(TRIAGE_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Summary so you know the shape of the work at a glance.
    alive = sum(r["url_alive"] for r in rows)
    dead = len(rows) - alive
    by_platform: dict[str, int] = {}
    for r in rows:
        if r["url_alive"]:
            by_platform[r["platform_guess"]] = by_platform.get(r["platform_guess"], 0) + 1

    print("\n" + "=" * 56)
    print("  TRIAGE SUMMARY")
    print("=" * 56)
    print(f"  Utilities checked   : {len(rows)}")
    print(f"  URL alive           : {alive}")
    print(f"  URL dead/unreachable: {dead}  (need a fresh URL)")
    print("  Platform guesses (alive URLs only):")
    for plat, n in sorted(by_platform.items(), key=lambda kv: -kv[1]):
        print(f"      {plat:<10} {n}")
    print("=" * 56)
    print(f"Worklist written -> {TRIAGE_CSV}")
    print("Next: open it, batch the 'kubra' rows, find new URLs for the dead "
          "ones,\nand investigate the 'unknown' rows in DevTools.")


if __name__ == "__main__":
    main()
