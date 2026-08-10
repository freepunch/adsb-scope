"""Live aircraft state, keyed by ICAO 24-bit hex address.

SBS messages are partial: one carries a callsign, another a position,
another speed/track. Each updates only the fields it has; this store
merges them into one record per aircraft and expires stale ones.
"""
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

from .geo import haversine_nm, bearing_deg


@dataclass
class Aircraft:
    hex_id: str
    callsign: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    altitude_ft: Optional[int] = None
    ground_speed_kt: Optional[int] = None
    track_deg: Optional[float] = None
    last_seen: float = field(default_factory=time.time)
    dist_nm: Optional[float] = None
    bearing: Optional[float] = None

    @property
    def has_position(self) -> bool:
        return self.lat is not None and self.lon is not None


class AircraftStore:
    """Thread-safe store: the network thread writes, the UI thread reads."""

    def __init__(self, home_lat: float, home_lon: float, stale_seconds: float = 30.0):
        self._aircraft: dict[str, Aircraft] = {}
        self._lock = Lock()
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.stale_seconds = stale_seconds
        self.message_count = 0

    def set_home(self, lat: float, lon: float):
        """Move the reference position (e.g. a GPS fix) and recompute
        range/bearing for everything currently tracked."""
        with self._lock:
            self.home_lat = lat
            self.home_lon = lon
            for ac in self._aircraft.values():
                if ac.has_position:
                    ac.dist_nm = haversine_nm(lat, lon, ac.lat, ac.lon)
                    ac.bearing = bearing_deg(lat, lon, ac.lat, ac.lon)

    def update(self, hex_id: str, **fields) -> Aircraft:
        with self._lock:
            ac = self._aircraft.setdefault(hex_id, Aircraft(hex_id=hex_id))
            for key, value in fields.items():
                if value is not None:
                    setattr(ac, key, value)
            ac.last_seen = time.time()
            if ac.has_position:
                ac.dist_nm = haversine_nm(self.home_lat, self.home_lon, ac.lat, ac.lon)
                ac.bearing = bearing_deg(self.home_lat, self.home_lon, ac.lat, ac.lon)
            self.message_count += 1
            return ac

    def snapshot(self) -> list[Aircraft]:
        """Expire stale aircraft and return the rest, nearest first."""
        now = time.time()
        with self._lock:
            self._aircraft = {
                h: a for h, a in self._aircraft.items()
                if now - a.last_seen < self.stale_seconds
            }
            live = list(self._aircraft.values())
        live.sort(key=lambda a: a.dist_nm if a.dist_nm is not None else 1e9)
        return live
