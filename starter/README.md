# Starter utility list — top ~100 US electric utilities

Two files, both generated from the same ranked roster:

- **`top_utilities.csv`** — human-readable, sorted by approximate customer
  count. Open in Excel/VS Code to plan your work.
- **`registry_starter.json`** — the same 104 utilities in real `registry.json`
  shape, **every entry `enabled: false`** with `config` fields stubbed
  `FILL-ME`. This is your worklist, not a finished registry.

## What this is — and is not

It **is** a prioritized roster: the ~104 largest US electric operating
utilities (not holding companies — ComEd and PECO are listed separately, not
"Exelon"), ordered so you register the highest-customer utilities first.
Together they cover roughly 118 million customers — the large majority of US
electricity customers.

It is **not** a ready-to-run registry. Two fields are deliberately unverified:

- **`customers_served`** is approximate. Operating-utility counts shift yearly
  and no single free source ranks all 100 cleanly. It is good enough to set
  priority order; do not cite it as data.
- **`platform`** is a *guess* (mostly `kubra`, the dominant US outage-map
  vendor). The `config` endpoints are all `FILL-ME`. Every entry must be
  confirmed in notebook 01 before it is enabled.

## How to use it

1. Copy `registry_starter.json` to the repo root as `registry.json`
   (or merge it into your existing one).
2. Open `01_build_registry.ipynb`. Work **top-down by rank** — rank 1 is the
   biggest utility, so it buys the most coverage per hour of effort.
3. For each utility: open its `_outage_map_url`, use DevTools → Network to
   capture the real endpoints, fill the `config`, test-fetch, then flip
   `enabled` to `true`. The notebook walks through this.
4. Re-run as you go. You do **not** need all 104 before collecting — enable the
   first 10–20, schedule the collector, and keep adding. Coverage grows; data
   starts accruing immediately.

## Notes on specific entries

- **FirstEnergy** operates ~10 named utilities sharing one outage-map system —
  once you crack the FirstEnergy endpoint, the territory differs per utility
  but the platform pattern repeats.
- **Duke**, **AEP**, **Entergy**, **Exelon**, **Eversource**, **Avangrid**,
  **National Grid**, **Xcel** similarly share infrastructure across their
  subsidiaries — solving one usually accelerates its siblings.
- **Municipal/public-power** utilities (LADWP, SRP, SMUD, Austin Energy,
  Seattle City Light, JEA, OPPD, NPPD) more often run **ArcGIS** feature
  layers than KUBRA — flagged `arcgis` here, but still verify.
- This list is electric IOUs, large munis, and a few big co-ops. The ~800 small
  rural co-ops are intentionally excluded — long-tail, low coverage-per-effort.

Re-run `build_starter.py` (in the repo parent folder) to regenerate both files
if you edit the roster.
