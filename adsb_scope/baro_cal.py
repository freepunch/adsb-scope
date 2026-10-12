"""Derive the local altimeter setting from the aircraft themselves.

Knowing your own elevation does not give you the pressure correction: the
correction is a property of today's atmosphere, not of your position. But
the aircraft overhead are already telling us. Most ADS-B equipment
broadcasts two altitudes:

    alt_baro   pressure altitude, referenced to the 29.92 inHg standard datum
    alt_geom   geometric altitude from GNSS, height above the WGS84 ellipsoid

The gap between them encodes the pressure correction, once the geoid
separation is removed:

    MSL  = alt_geom - geoid_sep
    MSL  = alt_baro + (altimeter - 29.92) * 1000

    => altimeter = 29.92 + (alt_geom - geoid_sep - alt_baro) / 1000

Geoid separation comes from our own GPS receiver, which reports it
directly. Around York PA it is roughly -105 ft, so ignoring it would bias
the derived setting by about 0.10 inHg, i.e. 100 ft of AGL error.

The SBS stream on port 30003 carries only barometric altitude, so this
reads readsb's aircraft.json over HTTP instead. Taking the median across
several aircraft rejects the odd mis-equipped airframe.

Honest limits: this is an estimate, typically good to a few hundredths of
an inHg with a handful of aircraft in view. It is not a METAR. With no
traffic in view it produces nothing at all and the previous value stands.
"""
import json
import statistics
import threading
import time
import urllib.request
from typing import Callable, Optional

STANDARD_INHG = 29.92
FT_PER_INHG = 1000.0

# plausibility gate: sea level pressure essentially never leaves this band
MIN_INHG, MAX_INHG = 27.50, 31.50
# a single aircraft disagreeing with the rest by more than this is dropped
OUTLIER_FT = 600.0
MIN_SAMPLES = 3


def estimate_altimeter(aircraft: list[dict],
                       geoid_sep_ft: float = 0.0) -> Optional[float]:
    """Median altimeter setting implied by aircraft reporting both altitudes.

    `aircraft` is the list from readsb's aircraft.json. Returns None when
    too few aircraft carry both altitudes, or the result is implausible.
    """
    deltas = []
    for ac in aircraft:
        baro, geom = ac.get("alt_baro"), ac.get("alt_geom")
        # "ground" appears in place of a number for aircraft on the surface
        if not isinstance(baro, (int, float)) or not isinstance(geom, (int, float)):
            continue
        deltas.append(float(geom) - geoid_sep_ft - float(baro))

    if len(deltas) < MIN_SAMPLES:
        return None

    med = statistics.median(deltas)
    kept = [d for d in deltas if abs(d - med) <= OUTLIER_FT]
    if len(kept) < MIN_SAMPLES:
        return None

    inhg = STANDARD_INHG + statistics.median(kept) / FT_PER_INHG
    if not (MIN_INHG <= inhg <= MAX_INHG):
        return None
    return round(inhg, 2)


def fetch_aircraft(url: str, timeout: float = 4.0) -> list[dict]:
    """Read readsb's aircraft.json. Returns [] on any failure."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")).get("aircraft", [])
    except Exception:
        return []


class BaroCalibrator(threading.Thread):
    """Polls aircraft.json and reports a derived altimeter setting."""

    daemon = True

    def __init__(self, url: str, on_estimate: Callable[[float, int], None],
                 interval_s: float = 60.0):
        super().__init__(name="baro-cal")
        self.url = url
        self.on_estimate = on_estimate
        self.interval_s = interval_s
        self.geoid_sep_ft = 0.0      # updated by the GPS client
        self.last_estimate: Optional[float] = None
        self.last_sample_count = 0
        self._stop = threading.Event()

    def set_geoid_sep(self, ft: Optional[float]):
        if ft is not None:
            self.geoid_sep_ft = ft

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            aircraft = fetch_aircraft(self.url)
            usable = sum(
                1 for ac in aircraft
                if isinstance(ac.get("alt_baro"), (int, float))
                and isinstance(ac.get("alt_geom"), (int, float)))
            est = estimate_altimeter(aircraft, self.geoid_sep_ft)
            if est is not None:
                self.last_estimate = est
                self.last_sample_count = usable
                self.on_estimate(est, usable)
            self._stop.wait(self.interval_s)
