"""Adapter for utilities whose outage maps run on KUBRA "Storm Center".

KUBRA is the most common US outage-map vendor, so this single adapter unlocks
a large share of national coverage. KUBRA serves outage data as tiled JSON
keyed by Bing-style quadkeys: a coarse tile lists 'clusters'; you recurse into
the four child tiles until a tile lists individual outages (a leaf) or returns
404 (an empty branch).

Endpoint paths differ between KUBRA deployments and versions, so the URL
templates live per-utility in registry.json, NOT here. To discover them for a
new utility: open its public outage map, open browser DevTools -> Network,
filter for 'kubra' or '.json', trigger a refresh, and read the request URLs.
The reusable intellectual property in this file is the descent algorithm and
the defensive parsing -- the URLs are data.

Reference implementations worth reading: open-austin/energy-outage (kubra_scraper.py)
and danp/nspoweroutages (documents the metadata.json -> directory -> tile schema).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from Code.base import OutageAdapter, OutageRecord, decode_polyline


def quadkey_children(quadkey: str) -> list[str]:
    """The four child quadkeys one zoom level deeper."""
    return [quadkey + d for d in "0123"]


class KubraAdapter(OutageAdapter):
    platform = "kubra"

    def fetch(self, utility_id: str, cfg: dict[str, Any]) -> list[OutageRecord]:
        # 1. Resolve the current data directory. KUBRA rotates this path on
        #    every refresh, so it must be re-read each pass.
        meta = self._get_json(cfg["metadata_url"])
        data_dir = meta.get("directory")
        if not data_dir and isinstance(meta.get("data"), dict):
            data_dir = meta["data"].get("directory")
        if not data_dir:
            raise ValueError(f"{utility_id}: could not resolve KUBRA data directory "
                             f"from {cfg['metadata_url']}")

        tile_template = cfg["tile_url_template"]          # uses {data_dir} and {quadkey}
        max_zoom = int(cfg.get("max_zoom", 14))
        # seed_quadkeys should be the utility's service territory (tighter = faster).
        # Default is the four zoom-1 world tiles; empty branches 404 quickly.
        seeds = cfg.get("seed_quadkeys") or list("0123")

        observed_at = datetime.now(timezone.utc).isoformat()
        records: list[OutageRecord] = []
        visited: set[str] = set(seeds)
        stack: list[str] = list(seeds)

        while stack:
            quadkey = stack.pop()
            url = tile_template.format(data_dir=data_dir, quadkey=quadkey)
            try:
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 404:
                    continue                              # empty branch
                resp.raise_for_status()
                payload = resp.json()
            except Exception:
                continue                                  # skip a bad tile, keep going

            for item in _extract_items(payload):
                is_cluster = _is_cluster(item)
                if is_cluster and len(quadkey) < max_zoom:
                    for child in quadkey_children(quadkey):
                        if child not in visited:
                            visited.add(child)
                            stack.append(child)
                else:
                    # Leaf outage, or a cluster at max zoom: count it either way
                    # so customers are never silently dropped.
                    rec = _parse_item(utility_id, item, observed_at)
                    if rec is not None:
                        records.append(rec)
        return records


def _extract_items(payload: Any) -> list[dict]:
    """Pull the list of outage/cluster dicts out of a KUBRA tile payload.
    Tile structure varies by deployment, so try the known shapes in order."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("file_data", "data", "clusters", "outages"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                for inner in ("clusters", "outages"):
                    if isinstance(value.get(inner), list):
                        return value[inner]
    return []


def _is_cluster(item: dict) -> bool:
    desc = item.get("desc", item)
    if isinstance(desc, dict):
        if desc.get("cluster") is True:
            return True
        if "n_out" in desc:                               # cluster member count
            return True
    return False


def _parse_item(utility_id: str, item: dict, observed_at: str) -> OutageRecord | None:
    desc = item.get("desc", item)
    cust = desc.get("cust_a")
    customers = cust.get("val") if isinstance(cust, dict) else cust
    if customers is None:
        # fall back across the field names different deployments use
        for alt in ("cust_aff", "numberOut", "customers", "custOut"):
            if desc.get(alt) is not None:
                customers = desc[alt]
                break
    if customers is None:
        return None

    lat = lon = None
    geom = item.get("geom")
    if isinstance(geom, dict) and geom.get("p"):
        encoded = geom["p"][0] if isinstance(geom["p"], list) else geom["p"]
        try:
            points = decode_polyline(encoded)
            if points:
                lat, lon = points[0]
        except Exception:
            pass

    try:
        customers = int(float(customers))
    except (TypeError, ValueError):
        return None

    return OutageRecord(
        utility_id=utility_id,
        observed_at=observed_at,
        customers_out=customers,
        latitude=lat,
        longitude=lon,
        area_name=desc.get("title"),
        source_platform="kubra",
        raw_id=str(item.get("id", "")),
    )
