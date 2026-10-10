"""Tests for the alert logic (no Qt). Run: python tests/test_alerts.py"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adsb_scope.alerts import (AlertMonitor, AlertSettings, Level,
                               closest_approach, height_agl_ft, to_local_nm)


class FakeAc:
    def __init__(self, hex_id, lat, lon, alt, gs=None, trk=None, seen=None):
        self.hex_id, self.lat, self.lon, self.altitude_ft = hex_id, lat, lon, alt
        self.ground_speed_kt, self.track_deg = gs, trk
        self.callsign, self.last_seen = "", seen or time.time()


class FakeStore:
    home_lat, home_lon = 40.0, -76.7
    def __init__(self): self.ac = []
    def snapshot(self): return list(self.ac)


def settings():
    return AlertSettings(site_elev_ft=400, altimeter_inhg=29.92, sound=False)


def nm_north(nm): return 40.0 + nm / 60.0


def test_cpa_head_on():
    cpa, t = closest_approach(0.0, 2.0, 0.0, -120 / 3600, 300)   # 2 nm north, 120 kt south
    assert cpa < 1e-6 and abs(t - 60) < 0.5


def test_cpa_moving_away_is_now():
    cpa, t = closest_approach(0.0, 2.0, 0.0, 120 / 3600, 300)
    assert t == 0.0 and abs(cpa - 2.0) < 1e-9


def test_pressure_correction():
    s = settings(); s.altimeter_inhg = 29.62          # low pressure day
    assert abs(height_agl_ft(1400, s) - 700) < 1e-6  # 1400 PA -> 1100 MSL -> 700 AGL


def test_levels_by_ring():
    st = FakeStore(); m = AlertMonitor(st, settings())
    st.ac = [FakeAc("a", nm_north(0.3), -76.7, 900),      # 500 AGL, 0.3 nm -> ALERT
             FakeAc("b", nm_north(1.0), -76.7, 1200),     # 800 AGL, 1 nm -> WARNING
             FakeAc("c", nm_north(2.5), -76.7, 2000),     # 1600 AGL -> ADVISORY
             FakeAc("d", nm_north(2.5), -76.7, 9000)]     # too high -> NONE
    got = {t.hex_id: t.level for t in m.update()}
    assert got == {"a": Level.ALERT, "b": Level.WARNING, "c": Level.ADVISORY}


def test_predictive_warning():
    st = FakeStore(); m = AlertMonitor(st, settings())
    st.ac = [FakeAc("p", nm_north(2.8), -76.7, 1100, gs=120, trk=180)]  # inbound
    t = m.update()[0]
    assert t.level == Level.WARNING and t.t_cpa_s > 0


def test_tisb_rings_wider():
    st = FakeStore(); m = AlertMonitor(st, settings())
    st.ac = [FakeAc("~t1", nm_north(2.0), -76.7, 1200)]   # 2 nm: outside 1.5, inside 2.25
    assert m.update()[0].level == Level.WARNING


def test_hysteresis_holds_then_releases():
    st = FakeStore(); m = AlertMonitor(st, settings())
    st.ac = [FakeAc("h", nm_north(1.4), -76.7, 1200)]
    assert m.update()[0].level == Level.WARNING
    st.ac = [FakeAc("h", nm_north(1.6), -76.7, 1200)]     # just outside 1.5 -> held
    assert m.update()[0].level == Level.WARNING
    st.ac = [FakeAc("h", nm_north(1.9), -76.7, 1200)]     # past 1.8 exit -> drops
    assert m.update()[0].level == Level.ADVISORY


def test_lost_contact():
    st = FakeStore(); m = AlertMonitor(st, settings())
    now = time.time()
    st.ac = [FakeAc("l", nm_north(1.0), -76.7, 1200, seen=now)]
    m.update(now)
    st.ac = []                                            # vanished from store
    t = m.update(now + 5)[0]
    assert t.level == Level.LOST
    assert m.update(now + 120) == []                      # released after hold time


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for f in fns:
        f(); print("ok ", f.__name__)
    print(f"\n{len(fns)} tests passed")
