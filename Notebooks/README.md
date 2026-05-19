# National Outage Collector

A framework for building a **national, near-real-time power-outage observation
set** by aggregating public utility outage maps — for verifying the Capstone2026
48-hour outage forecast. It produces county-hour labels in the **same shape as
EAGLE-I**, so scraped verification data is directly comparable to the model's
training labels.

This exists because there is no free single national real-time feed. EAGLE-I is
an annual archive (no live verification), ODIN is live but partial coverage, and
the commercial aggregators charge for access. The only free path to national
live data is to do what those services do internally: aggregate the utility
maps yourself.

This is its **own repository**, separate from the main Capstone2026 model code,
so the scraper and the model evolve independently and a problem in one cannot
touch the other.

---

## The method

You do **not** scrape ~900 utilities one at a time. Almost every US utility
outage map runs on one of a few vendor platforms. Write one adapter per
**platform**, then keep a **registry** mapping each utility to its platform and
endpoints. Two adapters cover a large share of the country:

- **KUBRA "Storm Center"** — the dominant vendor. Serves outages as tiled JSON
  keyed by quadkeys; you recurse from coarse tiles into finer ones. (`kubra.py`)
- **ArcGIS feature layers** — second most common. A stable REST `/query`
  endpoint returns outage features as JSON. (`arcgis.py`)

Adding a third platform is just another `OutageAdapter` subclass.

```
collector.py         one polite pass over the registry -> a timestamped snapshot
  ├── kubra.py        KUBRA Storm Center adapter (quadkey tile descent)
  └── arcgis.py       ArcGIS FeatureServer/MapServer adapter
county_aggregate.py  snapshots -> (fips, time_block, customers_out, outage_flag)
crosscheck.py        compare the scraped series against EAGLE-I; quantify the gap
discover.py          heuristic: classify a utility's outage map (KUBRA vs ArcGIS)
check_coverage.py    audit whether the scheduler ran every pass (gap detector)
run_collector.bat    Windows wrapper: one logged pass (called by Task Scheduler)
register_task.ps1    one-time: register the collector as a Windows scheduled task
base.py / config.py  shared types, polite HTTP session, settings
registry.json        which utility uses which platform, with endpoint config
notebooks/           the hands-on VS Code surface (these import the modules above)
  ├── 00_setup.ipynb                 verify dependencies, imports, config
  ├── 01_build_registry.ipynb        discover + test utilities, grow the registry
  └── 02_aggregate_and_verify.ipynb  aggregate to county, map, cross-check
```

The engine is plain `.py` modules on purpose: the collector runs unattended on a
scheduler, so it must be importable script code — a notebook cannot be cron'd or
imported cleanly. The `notebooks/` folder is your interactive surface in VS Code;
each notebook imports these modules and drives them. This is the standard layout
for a notebook-based project: logic in modules, notebooks orchestrate and plot.

## Quick start

```bash
pip install -r requirements.txt
# edit config.py: set CONTACT_EMAIL
# edit registry.json: add real utilities (see "Populating the registry")
python collector.py                 # one pass -> data/snapshots/snapshot_*.parquet
python county_aggregate.py          # -> data/county/scraped_county_outages.parquet
python crosscheck.py --eaglei eaglei_county_hour.parquet   # once data overlaps
```

`county_aggregate.py` needs the Census cartographic county boundaries
(`cb_2023_us_county_500k`) unzipped into `data/counties/`.

**Working interactively in VS Code:** open the `notebooks/` folder and run them
in order — `00_setup.ipynb` to verify the environment, `01_build_registry.ipynb`
to discover, test, and register utilities, and `02_aggregate_and_verify.ipynb`
to aggregate to county and cross-check against EAGLE-I with maps. The notebooks
import the modules above, so the command-line steps and the notebooks do the
same work either way. The numbering (00/01/02) is this repo's own sequence —
separate from the main Capstone2026 model notebooks.

## Populating the registry

The framework is the mechanism; the registry is the coverage, and it is the
real ongoing work. For each utility you add:

1. Open the utility's public outage map in a browser.
2. Open DevTools → Network, filter for `.json` (or `kubra`), refresh the map.
3. Read the request URLs. KUBRA maps fetch a `metadata.json` then tile JSON;
   ArcGIS maps hit a `.../query` endpoint. Copy those into a `registry.json`
   entry (`TEMPLATE_KUBRA` / `TEMPLATE_ARCGIS` show the fields).
4. Set `enabled: true` and run `collector.py` once to confirm it returns records.

**Prioritize by customers served.** US utility size is heavily Pareto — the
largest ~100–150 utilities cover the large majority of customers. Add the
biggest first; do not chase every rural co-op. Full parity with a commercial
aggregator is not a capstone-sized task, and you should not aim for it.

Prior art worth reading before extending the adapters:
- `open-austin/energy-outage` — a KUBRA scraper (quadkey logic)
- `danp/nspoweroutages` — documents the KUBRA `metadata.json` → tile schema
- `GateHouseMedia/power-outages` — multi-utility scraping with county rollups
- `simonw/pge-outages` — a long-running single-utility scraper worth reading

## Running it continuously (Windows)

Verification data only accrues **forward in time** — you cannot retroactively
scrape last week's live map. The collector must be running well before you
evaluate forecasts, on a schedule.

On Windows, use the built-in **Task Scheduler** — no third-party software:

1. Edit `run_collector.bat` — set `REPO_DIR` (the folder with `collector.py`)
   and `PYTHON` (full path to your project env's `python.exe`; find it by
   activating the env and running `where python`).
2. Open PowerShell, `cd` into the repo, and run:
   `powershell -ExecutionPolicy Bypass -File register_task.ps1`
   That registers a task named **OutageCollector** that runs hourly. For the
   15-minute EAGLE-I cadence instead: add `-IntervalMinutes 15`.
3. Test it immediately: `Start-ScheduledTask -TaskName "OutageCollector"`,
   then check `logs\collector_<date>.log`.

The task is configured to start a missed run as soon as possible
(`StartWhenAvailable`), to wake the machine from **sleep** to run (`WakeToRun`),
and to keep collecting on battery. It runs while you are logged in; to collect
while logged off, re-register with a stored credential (see comments in the
`.ps1`).

**The one real limit:** Task Scheduler cannot run a machine that is powered
**off** — only nothing can. Every pass missed while the machine is off is
outage data lost for good. If your machine is not reliably on, prefer an
always-on lab/desktop machine, or accept and document the gaps. Run
`python check_coverage.py` every few days — it reports how many passes actually
landed and flags any gaps, so a silently-stopped scheduler does not go unnoticed.

## Keeping the EAGLE-I labels comparable

The verification labels must be defined **identically** to the training labels:
customers-out summed to county, the `OUTAGE_THRESHOLD` (100) applied, snapped to
hourly blocks. `county_aggregate.py` does exactly this. Then run `crosscheck.py`
on any window where the scrape overlaps EAGLE-I and **report the coverage ratio
and flag agreement** — that is what makes the scraped verification defensible.

## Being a good citizen

This collects public, unauthenticated, aggregate data — the same data EAGLE-I
and ODIN collect. Keep it that way: the honest `User-Agent` with a contact
address (set it in `config.py`), the per-host delay, and retry/backoff are all
built in. If a specific utility actively blocks automated access, **skip it** —
do not try to defeat the block. Since this is academic work, a quick check with
your advisor on institutional data-use norms is worth the five minutes.

## Limitations — read this

- **Coverage is partial and you must report it as such.** "National" really
  means "the share of US customers your registry covers." `crosscheck.py`
  measures that share against EAGLE-I; weight or restrict verification
  accordingly.
- **Endpoints drift.** Utilities redesign maps; adapters will need maintenance.
- **Don't let this be your only verification.** The guaranteed result is
  *retrospective* verification — archived HRRR 48 h forecasts vs EAGLE-I 2025,
  all data already exists, cannot fail. This live collector is the operational
  layer **on top of** that, not underneath it.
