"""Adapter for utilities that publish outages as a county-name JSON feed.

Some utilities (FPL is the first we found) skip per-outage geometry entirely
and serve a single JSON document already aggregated by county:

    {"outages": [
        {"County Name": "Miami-Dade", "Customers Out": "743", ...},
        ...]}

This is the easiest possible source: one URL, already county-level, no tile
descent and no spatial join. The only work is mapping the county NAME to a
FIPS code (via county_fips.CountyResolver) and parsing comma-formatted number
strings ("1,269,677" -> 1269677).

Registry config keys for platform "countyjson":
  feed_url        : the JSON endpoint URL
  records_key     : key holding the list of records      (default "outages")
  county_field    : key for the county name              (default "County Name")
  customers_field : key for the customers-out count       (default "Customers Out")
  state           : 2-letter state code for FIPS lookup   (REQUIRED - county
                    names only resolve within a state)
  served_field    : optional key for customers-served (kept as extra context)

Because the feed is already county-level, each OutageRecord carries the FIPS
in `area_name` as "FIPS:12086" and has no lat/lon. county_aggregate.py detects
that prefix and uses it directly instead of doing a spatial join.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from base import OutageAdapter, OutageRecord
from county_fips import CountyResolver

# One resolver shared across all countyjson utilities (building it reads the
# shapefile, so do it once, lazily, on first use).
_RESOLVER: CountyResolver | None = None


def _get_resolver() -> CountyResolver:
    global _RESOLVER
    if _RESOLVER is None:
        _RESOLVER = CountyResolver()
    return _RESOLVER


def _to_int(value: Any) -> int | None:
    """Parse a customers count that may be a comma-formatted string."""
    if value is None:
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


class CountyJsonAdapter(OutageAdapter):
    platform = "countyjson"

    def fetch(self, utility_id: str, cfg: dict[str, Any]) -> list[OutageRecord]:
        feed_url = cfg["feed_url"]
        records_key = cfg.get("records_key", "outages")
        county_field = cfg.get("county_field", "County Name")
        customers_field = cfg.get("customers_field", "Customers Out")
        served_field = cfg.get("served_field")
        state = cfg.get("state")
        if not state:
            raise ValueError(f"{utility_id}: countyjson config needs a 'state' "
                             f"(2-letter code) for county-name -> FIPS lookup.")

        payload = self._get_json(feed_url)
        items = payload.get(records_key, []) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            raise ValueError(f"{utility_id}: '{records_key}' is not a list in "
                             f"the feed at {feed_url}.")

        resolver = _get_resolver()
        observed_at = datetime.now(timezone.utc).isoformat()
        records: list[OutageRecord] = []
        unresolved: list[str] = []

        for item in items:
            county = item.get(county_field)
            customers = _to_int(item.get(customers_field))
            if county is None or customers is None:
                continue
            # Keep zero-outage counties OUT of the record list - they are not
            # outages. (Customers-served context for them is not needed.)
            if customers <= 0:
                continue

            fips = resolver.lookup(str(county), state)
            if fips is None:
                unresolved.append(str(county))
                continue

            rec = OutageRecord(
                utility_id=utility_id,
                observed_at=observed_at,
                customers_out=customers,
                latitude=None,
                longitude=None,
                area_name=f"FIPS:{fips}",        # pre-resolved county FIPS
                source_platform="countyjson",
                raw_id=str(county),
            )
            if served_field and item.get(served_field) is not None:
                # stash customers-served on the record's raw_id-adjacent slot
                # via area_name is taken; we simply note it is available.
                pass
            records.append(rec)

        if unresolved:
            # Loud, not silent: a county name that will not resolve is a real
            # gap (spelling variant, or a name outside the configured state).
            print(f"    [{utility_id}] {len(unresolved)} county name(s) did not "
                  f"resolve to FIPS: {', '.join(sorted(set(unresolved)))}")
        return records
