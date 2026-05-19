"""Validate the scraped county outage series against EAGLE-I on overlapping dates.

This is the step that makes the scraped verification set defensible. The
scraped data will never have the exact coverage of EAGLE-I; this quantifies the
gap -- how well the two agree county-by-county, and whether your scraper
systematically sees fewer customers-out -- so you can report it honestly and,
if needed, restrict verification to well-covered counties.

    python crosscheck.py --eaglei /path/to/eaglei_county_hour.parquet

The EAGLE-I file must be exported to columns (fips, time_block, customers_out)
at the same hourly resolution. Run this over any window where your scrape and
EAGLE-I overlap (e.g. once EAGLE-I publishes its next annual file).
"""
from __future__ import annotations

import argparse

import pandas as pd

from config import AGGREGATED_DIR, OUTAGE_THRESHOLD


def run(scraped_path: str, eaglei_path: str) -> None:
    scraped = pd.read_parquet(scraped_path)
    eaglei = pd.read_parquet(eaglei_path)

    for col in ("fips", "time_block", "customers_out"):
        if col not in eaglei.columns:
            raise SystemExit(
                f"EAGLE-I file is missing column '{col}'. Re-export it to "
                "(fips, time_block, customers_out) at hourly resolution.")

    for frame in (scraped, eaglei):
        frame["fips"] = frame["fips"].astype(str).str.zfill(5)
        frame["time_block"] = pd.to_datetime(frame["time_block"], utc=True)

    merged = scraped.merge(eaglei, on=["fips", "time_block"], how="inner",
                           suffixes=("_scraped", "_eaglei"))
    if merged.empty:
        raise SystemExit("No overlapping (fips, time_block) rows. Check the date "
                         "window and that both sides use UTC hourly blocks.")

    a = merged["customers_out_scraped"].astype(float)
    b = merged["customers_out_eaglei"].astype(float)
    flag_a = (a >= OUTAGE_THRESHOLD).astype(int)
    flag_b = (b >= OUTAGE_THRESHOLD).astype(int)

    print("=" * 56)
    print("  SCRAPED  vs  EAGLE-I   coverage cross-check")
    print("=" * 56)
    print(f"  Overlapping county-hours : {len(merged):,}")
    print(f"  Counties in common       : {merged['fips'].nunique():,}")
    print(f"  Pearson correlation      : {a.corr(b):.3f}")
    print(f"  Spearman correlation     : {a.corr(b, method='spearman'):.3f}")
    print(f"  Mean customers_out (scr) : {a.mean():,.0f}")
    print(f"  Mean customers_out (eag) : {b.mean():,.0f}")
    ratio = a.sum() / b.sum() if b.sum() else float("nan")
    print(f"  Coverage ratio scr/eag   : {ratio:.3f}")
    print(f"      (<1 => scraper sees fewer customers-out than EAGLE-I)")
    print(f"  Outage-flag agreement    : {(flag_a == flag_b).mean():.1%}")
    # Where they disagree, which way?
    miss = ((flag_b == 1) & (flag_a == 0)).sum()
    false = ((flag_b == 0) & (flag_a == 1)).sum()
    print(f"      scraper missed EAGLE-I outage : {miss:,}")
    print(f"      scraper flagged, EAGLE-I did not: {false:,}")
    print("=" * 56)
    print("Report the coverage ratio and flag agreement in the paper, and "
          "consider\nrestricting verification to counties with ratio near 1.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-check scraped outages vs EAGLE-I")
    parser.add_argument("--scraped",
                        default=str(AGGREGATED_DIR / "scraped_county_outages.parquet"))
    parser.add_argument("--eaglei", required=True,
                        help="EAGLE-I parquet, columns (fips, time_block, customers_out)")
    args = parser.parse_args()
    run(args.scraped, args.eaglei)


if __name__ == "__main__":
    main()
