"""Airspace encroachment monitor for protecting your own RC/UAS operation.

Centered on the receiver's home position (store.home_lat/home_lon), which
under line-of-sight rules is where your model is flying. Evaluates every
live aircraft each tick and assigns an alert level with hysteresis, a
closest-point-of-approach prediction, and lost-contact tracking.

Pure Python, no Qt: testable on its own.
"""
import json
import math
import time
from dataclasses import dataclass, asdict, field
from enum import IntEnum
from pathlib import Path
from typing import Optional

ALERTS_PATH = Path("alerts.json")
FT_PER_NM = 6076.12


class Level(IntEnum):
    NONE = 0
    ADVISORY = 1
    WARNING = 2
    ALERT = 3
    LOST = 4          # was inside advisory, then stopped reporting


@dataclass
class AlertSettings:
    enabled: bool = True
    # Site + pressure correction (SBS altitude is pressure altitude @ 29.92)
    site_elev_ft: Optional[float] = None    # ft MSL; auto-set from a 3D GPS fix
    altimeter_inhg: float = 29.92           # auto-derived from traffic, or set by hand
    auto_site_elev: bool = True             # take site elevation from GPS
    auto_altimeter: bool = True             # derive altimeter from aircraft baro/geom
    aircraft_json_url: str = "http://127.0.0.1/tar1090/data/aircraft.json"
    # Advisory ring
    advisory_nm: float = 3.0
    advisory_agl_ft: float = 2000.0
    # Warning ring
    warning_nm: float = 1.5
    warning_agl_ft: float = 1000.0
    # Alert ring
    alert_nm: float = 0.5
    alert_agl_ft: float = 700.0
    # Predictive: warn if CPA inside this distance within this many seconds
    cpa_nm: float = 0.5
    cpa_horizon_s: float = 90.0
    # TIS-B ('~' hex) targets are radar-derived: widen their rings
    tisb_radius_mult: float = 1.5
    # Hysteresis: must clear radius*exit_mult (and ceiling+exit_ft) to downgrade
    exit_mult: float = 1.2
    exit_ft: float = 200.0
    # Lost contact handling
    lost_after_s: float = 10.0      # no update for this long inside advisory -> LOST
    lost_hold_s: float = 60.0       # keep showing last-known position this long
    # Audio
    sound: bool = True
    alert_repeat_s: float = 3.0


def load_settings() -> AlertSettings:
    if ALERTS_PATH.exists():
        try:
            data = json.loads(ALERTS_PATH.read_text())
            return AlertSettings(**{k: v for k, v in data.items()
                                    if k in AlertSettings.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError):
            pass
    s = AlertSettings()
    ALERTS_PATH.write_text(json.dumps(asdict(s), indent=2))
    return s


def save_settings(s: AlertSettings) -> bool:
    """Write settings back to alerts.json. Returns False if the write failed
    (read-only overlay filesystem, wrong owner), so the UI can say so rather
    than silently pretending it saved."""
    try:
        ALERTS_PATH.write_text(json.dumps(asdict(s), indent=2))
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- geometry

def to_local_nm(home_lat, home_lon, lat, lon):
    """Flat-earth east/north offset in nm. Accurate to <0.5% inside ~50 nm."""
    north = (lat - home_lat) * 60.0
    east = (lon - home_lon) * 60.0 * math.cos(math.radians(home_lat))
    return east, north


def velocity_nm_s(gs_kt, track_deg):
    if gs_kt is None or track_deg is None:
        return 0.0, 0.0
    v = gs_kt / 3600.0
    t = math.radians(track_deg)
    return v * math.sin(t), v * math.cos(t)


def closest_approach(px, py, vx, vy, horizon_s):
    """Return (cpa_nm, t_cpa_s) for a target at p moving at v, observer at origin.
    t is clamped to [0, horizon]."""
    v2 = vx * vx + vy * vy
    if v2 < 1e-12:
        return math.hypot(px, py), 0.0
    t = -(px * vx + py * vy) / v2
    t = max(0.0, min(t, horizon_s))
    return math.hypot(px + vx * t, py + vy * t), t


def height_agl_ft(pressure_alt_ft, settings: AlertSettings):
    """Pressure altitude -> approx height above the site. None if unknown."""
    if pressure_alt_ft is None:
        return None
    msl = pressure_alt_ft + (settings.altimeter_inhg - 29.92) * 1000.0
    return msl - (settings.site_elev_ft or 0.0)


# ---------------------------------------------------------------- monitor

@dataclass
class Threat:
    hex_id: str
    label: str
    level: Level
    dist_nm: float
    agl_ft: Optional[float]
    cpa_nm: float
    t_cpa_s: float
    tisb: bool
    east_nm: float
    north_nm: float
    last_seen: float
    reasons: list = field(default_factory=list)

    def summary(self) -> str:
        alt = "alt ?" if self.agl_ft is None else f"{self.agl_ft:+.0f} ft AGL"
        s = f"{self.label}  {self.dist_nm:.1f} nm  {alt}"
        if self.level == Level.LOST:
            return s + "  LOST CONTACT (last known)"
        if self.t_cpa_s > 0 and self.cpa_nm < self.dist_nm:
            s += f"  CPA {self.cpa_nm:.1f} nm in {self.t_cpa_s:.0f}s"
        if self.tisb:
            s += "  [TIS-B]"
        return s


class AlertMonitor:
    def __init__(self, store, settings: Optional[AlertSettings] = None):
        self.store = store
        self.settings = settings or load_settings()
        self._held: dict[str, Level] = {}
        self._last: dict[str, Threat] = {}
        self.threats: list[Threat] = []

    # level for one aircraft given thresholds scaled by mult / offset
    def _level(self, dist, agl, cpa, t_cpa, mult, ft_add, tisb):
        s = self.settings
        r = mult * (s.tisb_radius_mult if tisb else 1.0)
        low = lambda ceiling: agl is None or agl <= ceiling + ft_add
        reasons = []
        if dist <= s.alert_nm * r and low(s.alert_agl_ft):
            return Level.ALERT, ["inside alert ring"]
        if dist <= s.warning_nm * r and low(s.warning_agl_ft):
            reasons.append("inside warning ring")
        if (t_cpa > 0 and cpa <= s.cpa_nm * r and t_cpa <= s.cpa_horizon_s
                and low(s.warning_agl_ft)):
            reasons.append(f"projected CPA {cpa:.1f} nm in {t_cpa:.0f}s")
        if reasons:
            return Level.WARNING, reasons
        if dist <= s.advisory_nm * r and low(s.advisory_agl_ft):
            return Level.ADVISORY, ["inside advisory ring"]
        return Level.NONE, []

    def update(self, now: Optional[float] = None) -> list[Threat]:
        s = self.settings
        now = now or time.time()
        if not s.enabled:
            self.threats = []
            return self.threats
        hlat, hlon = self.store.home_lat, self.store.home_lon
        seen = set()
        out: list[Threat] = []

        for ac in self.store.snapshot():
            if ac.lat is None or ac.lon is None:
                continue
            seen.add(ac.hex_id)
            tisb = ac.hex_id.startswith("~")
            e, n = to_local_nm(hlat, hlon, ac.lat, ac.lon)
            dist = math.hypot(e, n)
            vx, vy = velocity_nm_s(ac.ground_speed_kt, ac.track_deg)
            cpa, t_cpa = closest_approach(e, n, vx, vy, s.cpa_horizon_s)
            agl = height_agl_ft(ac.altitude_ft, s)

            lvl, why = self._level(dist, agl, cpa, t_cpa, 1.0, 0.0, tisb)
            held = self._held.get(ac.hex_id, Level.NONE)
            if held in (Level.LOST,):
                held = Level.NONE
            if lvl < held:   # hysteresis: only downgrade once clear of exit thresholds
                exit_lvl, _ = self._level(dist, agl, cpa, t_cpa,
                                          s.exit_mult, s.exit_ft, tisb)
                if exit_lvl > lvl:
                    lvl, why = min(held, exit_lvl), why or ["holding (hysteresis)"]

            stale = now - ac.last_seen > s.lost_after_s
            if stale and lvl >= Level.ADVISORY:
                lvl = Level.LOST

            self._held[ac.hex_id] = lvl
            if lvl > Level.NONE:
                t = Threat(ac.hex_id, ac.callsign or ac.hex_id, lvl, dist, agl,
                           cpa, t_cpa, tisb, e, n, ac.last_seen, why)
                self._last[ac.hex_id] = t
                out.append(t)
            else:
                self._last.pop(ac.hex_id, None)

        # aircraft that vanished from the store while threatening -> LOST
        for hex_id, t in list(self._last.items()):
            if hex_id in seen:
                continue
            if now - t.last_seen <= s.lost_hold_s:
                t.level = Level.LOST
                out.append(t)
            else:
                self._last.pop(hex_id, None)
                self._held.pop(hex_id, None)

        out.sort(key=lambda t: (-int(t.level == Level.ALERT), -int(t.level), t.dist_nm))
        self.threats = out
        return out

    def max_level(self) -> Level:
        live = [t.level for t in self.threats if t.level != Level.LOST]
        top = max(live, default=Level.NONE)
        if top == Level.NONE and any(t.level == Level.LOST for t in self.threats):
            return Level.LOST
        return top
