"""Configuration for the national outage collector.

Edit CONTACT_EMAIL before running. Identifying yourself in the User-Agent is
both an academic courtesy and the single most effective way to avoid being
blocked: a utility that sees an honest research UA with a contact address is
far less likely to firewall you than one that sees an anonymous bot.
"""
from pathlib import Path

# --- Identify yourself. Replace with real values. ---
# This is a standalone repo, separate from Capstone2026. Set PROJECT_URL to the
# new repo once it exists.
CONTACT_EMAIL = "tob3@illinois.edu"
PROJECT_URL = "https://github.com/TOB23/Capstone-Fall-26"
USER_AGENT = (
    f"Capstone2026-OutageVerification/1.0 "
    f"(academic research; {PROJECT_URL}; mailto:{CONTACT_EMAIL})"
)

# --- Politeness / robustness ---
REQUEST_TIMEOUT = 30           # seconds per HTTP request
MAX_RETRIES = 3                # retries on 429/5xx, with exponential backoff
MIN_DELAY_PER_HOST = 1.0       # min seconds between consecutive hits to one host
COLLECTION_INTERVAL = 900      # seconds between passes when run with --loop (15 min)

# --- Outage label definition (MUST match the EAGLE-I training labels) ---
# A county-hour is a positive ("outage") label when total customers-out >= this.
OUTAGE_THRESHOLD = 100
TIME_BLOCK = "1h"              # pandas offset alias; 1h to match the HRRR cadence

# --- Paths ---
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"        # raw per-pass scrapes (parquet)
AGGREGATED_DIR = DATA_DIR / "county"         # county-aggregated, EAGLE-I-shaped
REGISTRY_PATH = ROOT / "registry.json"
# Census cartographic county boundaries (download + unzip into data/counties/).
COUNTY_SHAPEFILE = DATA_DIR / "counties" / "cb_2023_us_county_500k.shp"

for _d in (DATA_DIR, SNAPSHOT_DIR, AGGREGATED_DIR):
    _d.mkdir(parents=True, exist_ok=True)
