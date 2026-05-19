"""Resolve US county NAMES to 5-digit FIPS codes.

Several utilities publish outages keyed by county *name* ("Miami-Dade",
"St Lucie") rather than FIPS. This module builds an authoritative
name -> FIPS lookup straight from the Census county shapefile you already
downloaded (config.COUNTY_SHAPEFILE), so there is no hand-typed county table to
get wrong, and it stays correct if the shapefile is ever updated.

Matching is the hard part: utilities spell county names inconsistently. The
resolver normalizes aggressively (case, punctuation, "Saint"/"St", the word
"County", "Parish", "Borough") so "St. Lucie", "St Lucie", and "Saint Lucie
County" all collapse to one key.

Usage:
    from county_fips import CountyResolver
    resolver = CountyResolver()                 # builds from the shapefile
    fips = resolver.lookup("Miami-Dade", "FL")  # -> "12086"  (None if no match)

The state argument is required: county names are NOT unique nationally
(dozens of states have a "Washington" county), so a name only resolves
within a known state.
"""
from __future__ import annotations

import re

from config import COUNTY_SHAPEFILE

# US state / territory postal code -> 2-digit state FIPS prefix.
STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56", "PR": "72",
}


def normalize_county(name: str) -> str:
    """Collapse a county name to a comparison key.

    Lower-cases; turns "Saint"/"Ste" into "st"; drops the words county,
    parish, borough, municipality, census area; strips punctuation and
    spaces. So "St. Lucie", "St Lucie", "Saint Lucie County" -> "stlucie",
    and "DeSoto" / "De Soto" -> "desoto".
    """
    s = name.strip().lower()
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\bste\b", "st", s)
    # remove generic county-equivalent suffixes
    for word in ("county", "parish", "borough", "municipality",
                 "census area", "city and borough", "planning region"):
        s = s.replace(word, "")
    # drop everything that is not a letter or digit
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


class CountyResolver:
    """Builds a (state_fips, normalized_name) -> 5-digit FIPS map from the
    Census county shapefile."""

    def __init__(self, shapefile_path=None):
        self._map: dict[tuple[str, str], str] = {}
        self._build(shapefile_path or COUNTY_SHAPEFILE)

    def _build(self, shapefile_path) -> None:
        if not shapefile_path.exists():
            raise FileNotFoundError(
                f"County shapefile not found at {shapefile_path}. "
                "Download the Census cb_2025_us_county_500k file and unzip it "
                "into that folder (see config.COUNTY_SHAPEFILE).")
        # geopandas is heavy; import here so importing this module stays cheap.
        import geopandas as gpd

        gdf = gpd.read_file(shapefile_path)
        # Census county shapefile columns: GEOID = 5-digit FIPS,
        # NAME = bare county name, STATEFP = 2-digit state FIPS.
        for _, row in gdf.iterrows():
            geoid = str(row["GEOID"]).zfill(5)
            state_fp = str(row["STATEFP"]).zfill(2)
            key = (state_fp, normalize_county(str(row["NAME"])))
            self._map[key] = geoid

    def lookup(self, county_name: str, state: str) -> str | None:
        """Return the 5-digit FIPS for a county name within a state.

        `state` may be a postal code ("FL") or a 2-digit state FIPS ("12").
        Returns None if the name does not resolve - callers should treat a
        None as a skipped record and log it, never guess.
        """
        state = state.strip().upper()
        state_fp = STATE_FIPS.get(state, state if state.isdigit() else None)
        if state_fp is None:
            return None
        return self._map.get((state_fp.zfill(2), normalize_county(county_name)))

    def __len__(self) -> int:
        return len(self._map)
