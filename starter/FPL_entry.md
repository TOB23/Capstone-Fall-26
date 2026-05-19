# FPL registry entry — countyjson platform

FPL turned out NOT to be KUBRA. Its outage map (`https://www.fplmaps.com/`)
publishes a single JSON document already aggregated by county — handled by the
new `countyjson` adapter (`countyjson.py`).

## FPL registry entry

Paste this into `registry.json` (replace the `FPL` placeholder entry, or add
it). The `feed_url` is filled in and verified — `enabled` is already `true`:

```json
{
  "utility_id": "FPL",
  "utility_name": "Florida Power & Light",
  "platform": "countyjson",
  "states": ["FL"],
  "customers_served": 5800000,
  "enabled": true,
  "_priority_rank": 1,
  "_outage_map_url": "https://www.fplmaps.com/",
  "config": {
    "feed_url": "https://www.fplmaps.com/customer/outage/CountyOutages.json",
    "records_key": "outages",
    "county_field": "County Name",
    "customers_field": "Customers Out",
    "served_field": "Customers Served",
    "state": "FL"
  }
}
```

Note `FPL` here is FPL's main peninsula territory. FPL's Northwest Florida
region (the old Gulf Power area) has a separate map at
`https://www.fplmaps.com/northwest` — that is the `GULF_POWER` starter entry;
inspect it the same way when you reach it.

## The countyjson platform — reuse

`countyjson` handles any utility that serves outages as a JSON array of
county-name + customers-out records. Config keys:

  feed_url        the JSON endpoint
  records_key     key for the record list      (FPL: "outages")
  county_field    key for county name          (FPL: "County Name")
  customers_field key for customers-out         (FPL: "Customers Out")
  served_field    optional customers-served key (FPL: "Customers Served")
  state           2-letter state — REQUIRED, county names resolve per-state

County names are mapped to FIPS by `county_fips.CountyResolver`, which builds
an authoritative lookup from the Census county shapefile (so the shapefile
must be in place — see config.COUNTY_SHAPEFILE). Names that do not resolve are
printed loudly during collection, never dropped silently.

Expect to reuse `countyjson` for other utilities — a county-name JSON feed is
a common pattern. When you meet one, just add a registry entry; no new code.
