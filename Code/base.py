"""Core types and shared utilities for the national outage collector.

Everything platform-agnostic lives here:
  * OutageRecord  - the normalized record every adapter emits
  * build_session - a polite, retrying HTTP session
  * OutageAdapter - the base class every platform adapter extends
  * decode_polyline - Google-encoded-polyline decoder (KUBRA geometry uses it)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import USER_AGENT, REQUEST_TIMEOUT, MAX_RETRIES


@dataclass
class OutageRecord:
    """One observed outage (an individual outage or a cluster of them),
    normalized so records from any platform are interchangeable downstream."""
    utility_id: str
    observed_at: str               # ISO-8601 UTC; the collection timestamp
    customers_out: int
    latitude: float | None = None
    longitude: float | None = None
    area_name: str | None = None   # service-area / city label if no point geometry
    source_platform: str = ""
    raw_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_session() -> requests.Session:
    """A resilient, polite HTTP session: honest User-Agent, automatic retry
    with exponential backoff on rate-limit / server errors, Retry-After honored."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def decode_polyline(encoded: str, precision: int = 5) -> list[tuple[float, float]]:
    """Decode a Google-encoded-polyline string into [(lat, lon), ...].

    KUBRA outage maps store point and area geometry in this encoding
    (the 'geom.p' / 'geom.a' fields). Precision is 5 for standard polylines.
    """
    coords: list[tuple[float, float]] = []
    index = lat = lon = 0
    factor = 10 ** precision
    length = len(encoded)
    while index < length:
        for is_lon in (False, True):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lon:
                lon += delta
            else:
                lat += delta
        coords.append((lat / factor, lon / factor))
    return coords


class OutageAdapter(ABC):
    """Base class for platform adapters. Subclass once per outage-map vendor;
    register the subclass in collector.ADAPTERS."""

    platform: str = "base"

    def __init__(self, session: requests.Session | None = None):
        self.session = session or build_session()

    @abstractmethod
    def fetch(self, utility_id: str, cfg: dict[str, Any]) -> list[OutageRecord]:
        """Return the current outage records for one utility.

        `cfg` is that utility's `config` block from registry.json.
        Implementations should be defensive: skip a bad tile/feature rather
        than abort the whole utility.
        """
        raise NotImplementedError

    def _get_json(self, url: str, **kwargs: Any) -> Any:
        resp = self.session.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp.json()
