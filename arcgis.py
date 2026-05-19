"""Adapter for utilities whose outage maps are ArcGIS feature layers.

The second most common pattern after KUBRA. An ArcGIS FeatureServer or
MapServer layer exposes a documented, stable REST '/query' endpoint that
returns outage features as JSON -- far simpler and more robust than KUBRA
tile descent.

To find the layer for a new utility: open its outage map, DevTools -> Network,
look for requests to '.../FeatureServer/<n>/query' or '.../MapServer/<n>/query'.
The 'service_url' in registry.json is everything up to (not including) '/query'.

Registry config keys:
  service_url      : layer URL ending in /FeatureServer/<n> or /MapServer/<n>
  customers_field  : attribute name holding the customers-affected count
  where            : optional SQL filter (default "1=1")
  area_field       : optional attribute name for a service-area label
  id_field         : optional unique-id attribute (default "OBJECTID")
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from Code.base import OutageAdapter, OutageRecord


class ArcGISAdapter(OutageAdapter):
    platform = "arcgis"

    def fetch(self, utility_id: str, cfg: dict[str, Any]) -> list[OutageRecord]:
        service_url = cfg["service_url"].rstrip("/")
        cust_field = cfg.get("customers_field", "CustomersAffected")
        area_field = cfg.get("area_field", "")
        id_field = cfg.get("id_field", "OBJECTID")
        observed_at = datetime.now(timezone.utc).isoformat()

        records: list[OutageRecord] = []
        offset, page_size = 0, 2000
        while True:
            params = {
                "where": cfg.get("where", "1=1"),
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",            # request WGS84 lat/lon
                "f": "json",
                "resultOffset": offset,
                "resultRecordCount": page_size,
            }
            payload = self._get_json(f"{service_url}/query", params=params)
            features = payload.get("features", [])
            for feature in features:
                rec = _parse_feature(utility_id, feature, observed_at,
                                     cust_field, area_field, id_field)
                if rec is not None:
                    records.append(rec)
            # ArcGIS pages results; keep going only while more remain.
            if not features or not payload.get("exceededTransferLimit"):
                break
            offset += page_size
        return records


def _parse_feature(utility_id, feature, observed_at,
                   cust_field, area_field, id_field) -> OutageRecord | None:
    attrs = feature.get("attributes", {}) or {}
    customers = attrs.get(cust_field)
    if customers in (None, ""):
        return None
    try:
        customers = int(float(customers))
    except (TypeError, ValueError):
        return None

    geom = feature.get("geometry") or {}
    lat, lon = geom.get("y"), geom.get("x")
    # Polygon features have 'rings' rather than x/y; leave coords None and let
    # the aggregation step fall back to an area crosswalk for those utilities.

    return OutageRecord(
        utility_id=utility_id,
        observed_at=observed_at,
        customers_out=customers,
        latitude=lat,
        longitude=lon,
        area_name=attrs.get(area_field) if area_field else None,
        source_platform="arcgis",
        raw_id=str(attrs.get(id_field, "")),
    )
