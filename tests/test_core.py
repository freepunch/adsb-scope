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




def test_parse_gpsd_tpv():
    from adsb_scope.gps_client import parse_gpsd_line
    good = '{"class":"TPV","mode":3,"lat":45.4642,"lon":9.1900}'
    assert parse_gpsd_line(good) == (45.4642, 9.1900)
    assert parse_gpsd_line('{"class":"TPV","mode":1}') is None      # no fix
    assert parse_gpsd_line('{"class":"SKY"}') is None               # wrong class
    assert parse_gpsd_line('not json at all') is None


def test_set_home_recomputes():
    store = AircraftStore(40.0, -76.0, stale_seconds=30)
    store.update("abc123", lat=41.0, lon=-76.0)
    d_before = store.snapshot()[0].dist_nm
    store.set_home(42.0, -76.0)   # jump home north of the aircraft
    ac = store.snapshot()[0]
    assert abs(ac.bearing - 180.0) < 0.5           # aircraft now due south
    assert abs(ac.dist_nm - d_before) < 1.0        # still ~60 nm away


def test_polar_to_xy_cardinals():
    from adsb_scope.hittest import polar_to_xy
    # due north at full range -> straight up from centre
    x, y = polar_to_xy(100, 100, 50, 60, 0, 60)
    assert abs(x - 100) < 0.01 and abs(y - 50) < 0.01
    # due east at half range -> right of centre
    x, y = polar_to_xy(100, 100, 50, 60, 90, 30)
    assert abs(x - 125) < 0.01 and abs(y - 100) < 0.01


def test_hit_test_picks_nearest_within_tolerance():
    from adsb_scope.hittest import hit_test
    positions = {"aaa": (100.0, 100.0), "bbb": (140.0, 100.0)}
    assert hit_test(103, 102, positions) == "aaa"
    assert hit_test(138, 101, positions) == "bbb"
    assert hit_test(300, 300, positions) is None      # far from everything


def test_hit_test_tolerance_is_touch_sized():
    from adsb_scope.hittest import hit_test
    positions = {"aaa": (100.0, 100.0)}
    assert hit_test(118, 100, positions) == "aaa"     # 18px off still hits
    assert hit_test(160, 100, positions) is None      # 60px off does not


def test_range_steps_snap_and_zoom():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from adsb_scope.ui.scope_view import ScopeView, RANGE_STEPS
    from adsb_scope.aircraft import AircraftStore
    app = QApplication.instance() or QApplication([])
    store = AircraftStore(40.0, -76.0)

    # a configured 100 nm snaps onto the 100 step
    sv = ScopeView(store, 100.0, 15)
    assert sv.max_range_nm == 100.0

    # an odd configured value snaps to the nearest step
    sv2 = ScopeView(store, 60.0, 15)
    assert sv2.max_range_nm == 50.0

    # zoom in tightens, zoom out widens
    start = sv.max_range_nm
    sv.zoom_in()
    assert sv.max_range_nm < start
    sv.zoom_out()
    assert sv.max_range_nm == start

    # clamps at both ends rather than running off the list
    for _ in range(20):
        sv.zoom_in()
    assert sv.max_range_nm == float(RANGE_STEPS[0])
    for _ in range(20):
        sv.zoom_out()
    assert sv.max_range_nm == float(RANGE_STEPS[-1])


def test_range_filter_hides_distant_aircraft():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from adsb_scope.ui.detail_panel import DetailPanel
    from adsb_scope.aircraft import AircraftStore
    app = QApplication.instance() or QApplication([])
    store = AircraftStore(40.0, -76.0)
    store.update("near1", lat=40.1, lon=-76.0)    # ~6 nm
    store.update("far1", lat=41.0, lon=-76.0)     # ~60 nm

    panel = DetailPanel(store)
    panel.set_range_filter(200)
    assert panel.table.rowCount() == 2
    panel.set_range_filter(25)
    assert panel.table.rowCount() == 1             # far one filtered out


def test_chiptune_waveform():
    """The boot chime must be the right length, audible, and actually square."""
    import struct, wave
    from pathlib import Path
    from adsb_scope.audio import make_chiptune, STARTUP_NOTES, RATE

    out = Path("/tmp/_test_chime.wav")
    if out.exists():
        out.unlink()
    make_chiptune(out, STARTUP_NOTES)
    with wave.open(str(out)) as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2
        assert w.getframerate() == RATE
        n = w.getnframes()
        samples = struct.unpack(f"<{n}h", w.readframes(n))

    expected_s = sum(ms for _, ms in STARTUP_NOTES) / 1000
    assert abs(n / RATE - expected_s) < 0.02

    peak = max(abs(s) for s in samples)
    assert 5000 < peak < 32767          # audible, not clipping

    # the rest between the arpeggio and the final note issilence
    rest_at = sum(ms for _, ms in STARTUP_NOTES[:6]) / 1000
    i0, i1 = int(rest_at * RATE) + 50, int((rest_at + 0.04) * RATE) - 50
    assert max(abs(s) for s in samples[i0:i1]) == 0

    # sustain portion sits at the rails: square, not sine
    note_n = int(RATE * STARTUP_NOTES[0][1] / 1000)
    sustain = samples[200:int(note_n * 0.45)]
    peak_s = max(abs(x) for x in sustain)
    assert sum(1 for s in sustain if abs(s) > 0.9 * peak_s) / len(sustain) > 0.95
    out.unlink()


def test_splash_respects_sound_flag():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from adsb_scope.ui.splash import SplashScreen
    app = QApplication.instance() or QApplication([])
    s = SplashScreen(sound=False)
    assert s.sound_played is False
    s.skip()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
