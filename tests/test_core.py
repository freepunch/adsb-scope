"""Tests for the non-GUI core: geometry, SBS parsing, store, coverage.
Run with: python -m pytest  (or python tests/test_core.py)"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adsb_scope.geo import haversine_nm, bearing_deg
from adsb_scope.sbs_client import parse_sbs_line
from adsb_scope.aircraft import AircraftStore
from adsb_scope.coverage import CoverageTracker


def test_haversine_known_distance():
    # JFK to LAX is ~2144 nm
    d = haversine_nm(40.6413, -73.7781, 33.9416, -118.4085)
    assert abs(d - 2144) < 15


def test_bearing_cardinal():
    assert abs(bearing_deg(40.0, -76.0, 41.0, -76.0) - 0.0) < 0.5      # due north
    assert abs(bearing_deg(40.0, -76.0, 40.0, -75.0) - 90.0) < 1.0     # ~east


def test_parse_position_message():
    line = "MSG,3,1,1,A1B2C3,1,2026/06/12,12:00:00.000,2026/06/12,12:00:00.000,,35000,,,40.1234,-76.5678,,,,,,"
    hex_id, fields = parse_sbs_line(line)
    assert hex_id == "a1b2c3"
    assert fields["altitude_ft"] == 35000
    assert abs(fields["lat"] - 40.1234) < 1e-9


def test_parse_ident_and_velocity():
    ident = "MSG,1,1,1,A1B2C3,1,2026/06/12,12:00:00.000,2026/06/12,12:00:00.000,UAL123 ,,,,,,,,,,,"
    hex_id, fields = parse_sbs_line(ident)
    assert fields["callsign"] == "UAL123"
    vel = "MSG,4,1,1,A1B2C3,1,2026/06/12,12:00:00.000,2026/06/12,12:00:00.000,,,450,275.5,,,,,,,,"
    hex_id, fields = parse_sbs_line(vel)
    assert fields["ground_speed_kt"] == 450
    assert abs(fields["track_deg"] - 275.5) < 1e-9


def test_parse_rejects_junk():
    assert parse_sbs_line("") is None
    assert parse_sbs_line("STA,,,,") is None
    assert parse_sbs_line("MSG,3,1,1,,1,a,b,c,d,,not_a_number,,,xx,yy,,,,,,") is None


def test_store_merges_partial_messages():
    store = AircraftStore(40.0, -76.0, stale_seconds=30)
    store.update("abc123", callsign="TEST1")
    store.update("abc123", lat=41.0, lon=-76.0, altitude_ft=30000)
    snap = store.snapshot()
    assert len(snap) == 1
    ac = snap[0]
    assert ac.callsign == "TEST1" and ac.has_position
    assert abs(ac.bearing - 0.0) < 0.5 and 59 < ac.dist_nm < 61  # 1 deg lat = 60 nm


def test_store_expires_stale():
    store = AircraftStore(40.0, -76.0, stale_seconds=0.05)
    store.update("abc123", callsign="GONE")
    time.sleep(0.1)
    assert store.snapshot() == []


def test_coverage_records_max(tmp_path=None):
    import adsb_scope.coverage as cov
    cov.COVERAGE_PATH = Path("/tmp/_test_coverage.json")
    if cov.COVERAGE_PATH.exists():
        cov.COVERAGE_PATH.unlink()
    t = CoverageTracker(bucket_deg=5)
    t.record(2.0, 50.0)
    t.record(3.0, 80.0)   # same bucket, larger -> wins
    t.record(3.0, 20.0)   # smaller -> ignored
    assert t.snapshot()[0] == 80.0
    t.save()
    t2 = CoverageTracker(bucket_deg=5)
    assert t2.snapshot()[0] == 80.0  # persisted and reloaded
    cov.COVERAGE_PATH.unlink()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
