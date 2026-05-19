"""Heuristic classifier for a utility's outage map: KUBRA, ArcGIS, or unknown.

Given an outage-map URL, this fetches the page and scans the HTML/JS for vendor
signatures and any embedded endpoint URLs. It is a FIRST-PASS aid, not magic:
the precise KUBRA tile template is usually assembled in JavaScript at runtime
and still has to be confirmed with browser DevTools (Network tab). Use this to
classify a utility quickly and to harvest candidate URLs, then verify.

    python discover.py https://outagemap.some-utility.com
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from base import build_session
from config import REQUEST_TIMEOUT

KUBRA_SIGNATURES = ("kubra.io", "kubra", "stormcenter")
ARCGIS_SIGNATURES = ("arcgis", "/featureserver", "/mapserver")
URL_RE = re.compile(r"https?://[^\s\"'<>()]+", re.IGNORECASE)


@dataclass
class Discovery:
    url: str
    platform: str = "unknown"            # "kubra" | "arcgis" | "unknown"
    confidence: str = "low"              # "low" | "medium"
    candidate_urls: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"URL        : {self.url}",
            f"Platform   : {self.platform}  ({self.confidence} confidence)",
        ]
        if self.candidate_urls:
            lines.append("Candidate endpoints found in the page source:")
            lines += [f"  - {u}" for u in self.candidate_urls]
        lines += [f"Note: {n}" for n in self.notes]
        return "\n".join(lines)


def classify_outage_map(url: str, session=None) -> Discovery:
    """Fetch an outage-map page and guess its vendor platform."""
    session = session or build_session()
    result = Discovery(url=url)
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        result.notes.append(f"could not fetch page: {type(exc).__name__}: {exc}")
        return result

    low = html.lower()
    found = set(URL_RE.findall(html))

    if any(sig in low for sig in KUBRA_SIGNATURES):
        result.platform = "kubra"
        result.confidence = "medium" if "kubra.io" in low else "low"
        result.candidate_urls = sorted(u for u in found if "kubra" in u.lower())
        result.notes.append(
            "KUBRA detected. The exact tile_url_template is built in JS - open "
            "DevTools > Network, filter 'kubra', refresh, and copy the metadata "
            "and tile (cluster) request URLs into the registry entry.")
    elif any(sig in low for sig in ARCGIS_SIGNATURES):
        result.platform = "arcgis"
        result.candidate_urls = sorted(
            u for u in found
            if "/featureserver" in u.lower() or "/mapserver" in u.lower())
        result.confidence = "medium" if result.candidate_urls else "low"
        result.notes.append(
            "ArcGIS detected. service_url is a layer URL ending in "
            "/FeatureServer/<n> or /MapServer/<n> (everything before /query).")
    else:
        result.notes.append(
            "No KUBRA or ArcGIS signature in the initial HTML. The map may load "
            "its vendor via JS, or use another platform - inspect with DevTools, "
            "and if it is a new platform, add an OutageAdapter subclass for it.")
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("usage: python discover.py <outage-map-url>")
        raise SystemExit(1)
    print(classify_outage_map(sys.argv[1]).summary())
