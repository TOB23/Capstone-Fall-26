"""Aggregate raw outage snapshots into county-level, EAGLE-I-shaped labels.

The output columns deliberately match the EAGLE-I outage table so the scraped
verification set is directly comparable to the model's training labels:

    fips, time_block, customers_out, outage_flag

    python county_aggregate.py                       # all snapshots
    python county_aggregate.py --start 2026-09-01    # a date window

Point-geometry records are spatially joined to county polygons. Records with no
geometry (a utility that reports only a service-area name) need a per-utility
area->FIPS crosswalk; until you supply one they are reported and dropped, so
the coverage gap is visible rather than silent.
"""
from __future__ import annotations

import argparse

import pandas as pd
import geopandas as gpd

from config import (SNAPSHOT_DIR, AGGREGATED_DIR, COUNTY_SHAPEFILE,
                    OUTAGE_THRESHOLD, TIME_BLOCK)


def load_snapshots(start: str | None = None, end: str | None = None) -> pd.DataFrame:
    frames = [pd.read_parquet(f) for f in sorted(SNAPSHOT_DIR.glob("snapshot_*.parquet"))]
    if not frames:
        raise SystemExit("No snapshots found. Run collector.py first.")
    df = pd.concat(frames, ignore_index=True)
    df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True)
    if start:
        df = df[df["observed_at"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        df = df[df["observed_at"] <= pd.Timestamp(end, tz="UTC")]
    return df


def place_in_counties(df: pd.DataFrame) -> pd.DataFrame:
    """Spatial-join point records to county FIPS codes."""
    if not COUNTY_SHAPEFILE.exists():
        raise SystemExit(
            f"County shapefile not found at {COUNTY_SHAPEFILE}.\n"
            "Download the Census cartographic county boundaries "
            "(cb_2023_us_county_500k) and unzip into that folder.")

    counties = gpd.read_file(COUNTY_SHAPEFILE)[["GEOID", "geometry"]]
    counties = counties.rename(columns={"GEOID": "fips"}).to_crs(4326)

    points = df.dropna(subset=["latitude", "longitude"]).copy()
    no_geom = len(df) - len(points)
    if no_geom:
        print(f"  note: {no_geom} records had no point geometry "
              f"(service-area-only utilities) and were not placed.")

    gdf = gpd.GeoDataFrame(
        points,
        geometry=gpd.points_from_xy(points["longitude"], points["latitude"]),
        crs=4326,
    )
    joined = gpd.sjoin(gdf, counties, how="inner", predicate="within")
    outside = len(points) - len(joined)
    if outside:
        print(f"  note: {outside} points fell outside US county polygons.")
    return pd.DataFrame(joined.drop(columns=["geometry", "index_right"],
                                    errors="ignore"))


def aggregate_to_county_hour(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse placed records to one row per (county, hour)."""
    df = df.copy()
    df["time_block"] = df["observed_at"].dt.floor(TIME_BLOCK)
    # A utility may post several snapshots within one hour; take the peak
    # customers-out per utility per county, then sum across utilities so two
    # utilities serving the same county add up rather than overwrite.
    per_utility = (df.groupby(["fips", "time_block", "utility_id"])["customers_out"]
                     .max().reset_index())
    county = (per_utility.groupby(["fips", "time_block"])["customers_out"]
                         .sum().reset_index())
    county["outage_flag"] = (county["customers_out"] >= OUTAGE_THRESHOLD).astype(int)
    return county


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate scraped outages to county-hour")
    parser.add_argument("--start", help="ISO date, inclusive")
    parser.add_argument("--end", help="ISO date, inclusive")
    args = parser.parse_args()

    raw = load_snapshots(args.start, args.end)
    print(f"Loaded {len(raw):,} raw records from {SNAPSHOT_DIR}")
    placed = place_in_counties(raw)
    county = aggregate_to_county_hour(placed)

    out_path = AGGREGATED_DIR / "scraped_county_outages.parquet"
    county.to_parquet(out_path, index=False)
    print(f"Wrote {len(county):,} county-hour rows -> {out_path}")
    if not county.empty:
        share = county["outage_flag"].mean()
        print(f"Positive-label rate: {share:.3f}  "
              f"(EAGLE-I climatology is ~0.136 nationally)")


if __name__ == "__main__":
    main()
