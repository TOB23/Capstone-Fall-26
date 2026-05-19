"""Audit collection coverage: did the scheduler actually run every pass?

A missed pass is outage data you can never recover, and a stopped scheduler can
fail silently. Run this every few days to confirm snapshots are landing at the
expected cadence and to see any gaps.

    python check_coverage.py                 # assume hourly cadence
    python check_coverage.py --interval 15   # if collecting every 15 min
"""
from __future__ import annotations

import argparse
import re
from datetime import timedelta

import pandas as pd

from config import SNAPSHOT_DIR

STAMP_RE = re.compile(r"snapshot_(\d{8}T\d{6}Z)\.parquet$")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit outage snapshot coverage")
    parser.add_argument("--interval", type=int, default=60,
                        help="expected minutes between passes (default 60)")
    parser.add_argument("--tolerance", type=float, default=0.5,
                        help="gap counts as missed if larger than "
                             "interval * (1 + tolerance); default 0.5")
    args = parser.parse_args()

    files = sorted(SNAPSHOT_DIR.glob("snapshot_*.parquet"))
    stamps = []
    for f in files:
        m = STAMP_RE.search(f.name)
        if m:
            stamps.append(pd.Timestamp(m.group(1)))
    if not stamps:
        raise SystemExit(f"No snapshots found in {SNAPSHOT_DIR}.")

    stamps = pd.Series(sorted(stamps))
    span = stamps.iloc[-1] - stamps.iloc[0]
    expected = int(span / timedelta(minutes=args.interval)) + 1
    actual = len(stamps)

    print("=" * 56)
    print("  OUTAGE SNAPSHOT COVERAGE AUDIT")
    print("=" * 56)
    print(f"  First snapshot : {stamps.iloc[0]}")
    print(f"  Last snapshot  : {stamps.iloc[-1]}")
    print(f"  Span           : {span}")
    print(f"  Snapshots      : {actual}  (expected ~{expected} at "
          f"{args.interval}-min cadence)")
    print(f"  Coverage       : {actual / expected:.1%}")

    # Find gaps larger than the tolerance.
    gaps = stamps.diff().dropna()
    limit = timedelta(minutes=args.interval * (1 + args.tolerance))
    big = gaps[gaps > limit]
    if big.empty:
        print("  Gaps           : none beyond tolerance - scheduler healthy.")
    else:
        print(f"  Gaps           : {len(big)} gap(s) beyond {limit}:")
        for idx, gap in big.items():
            start = stamps.iloc[idx - 1]
            missed = int(gap / timedelta(minutes=args.interval)) - 1
            print(f"      after {start}  -> gap of {gap}  (~{missed} missed)")
    print("=" * 56)
    if not big.empty:
        print("Investigate gaps: machine was off/asleep, or the task stopped.")
        print("Check logs\\collector_<date>.log and Task Scheduler history.")


if __name__ == "__main__":
    main()
