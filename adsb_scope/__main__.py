"""Entry point: python -m adsb_scope"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from . import config
from .aircraft import AircraftStore
from .coverage import CoverageTracker
from .baro_cal import BaroCalibrator
from .gps_client import GPSClient
from .sbs_client import SBSClient
from .ui.main_window import MainWindow
from .ui.splash import SplashScreen


def main():
    cfg = config.load()
    store = AircraftStore(cfg.home_lat, cfg.home_lon, cfg.stale_seconds)
    tracker = CoverageTracker(cfg.coverage_bucket_deg)
    client = SBSClient(cfg.host, cfg.port, store)
    client.start()

    # The alert monitor is created by the UI, but auto-calibration has to be
    # wired to the same settings object, so build the pieces here and hand
    # them in. Both are best-effort: no GPS or no traffic simply means the
    # stored values stand.
    gps = None
    calibrator = None

    def _on_gps_altitude(elev_ft, geoid_sep_ft):
        if calibrator is not None:
            calibrator.set_geoid_sep(geoid_sep_ft)
        app_state["site_elev_ft"] = elev_ft

    app_state = {"site_elev_ft": None}

    if cfg.gps_enabled:
        gps = GPSClient(on_fix=store.set_home, on_altitude=_on_gps_altitude)
        gps.start()

    app = QApplication(sys.argv)
    if cfg.hide_cursor:
        app.setOverrideCursor(Qt.BlankCursor)

    window = MainWindow(store, client, tracker, cfg, gps=gps)

    settings = window.monitor.settings
    if settings.auto_altimeter:
        calibrator = BaroCalibrator(
            settings.aircraft_json_url,
            on_estimate=window.on_altimeter_estimate)
        calibrator.start()
        window.calibrator = calibrator

    def _apply_gps_elevation():
        elev = app_state.get("site_elev_ft")
        if elev is not None and settings.auto_site_elev:
            window.on_site_elevation(elev)

    from PySide6.QtCore import QTimer
    _elev_timer = QTimer(window)
    _elev_timer.timeout.connect(_apply_gps_elevation)
    _elev_timer.start(5000)
    window._elev_timer = _elev_timer
    fullscreen = cfg.fullscreen or "--fullscreen" in sys.argv

    def show_main():
        if fullscreen:
            window.showFullScreen()
        else:
            window.show()

    if cfg.splash:
        # Built and shown first so the deck has something on screen while
        # the receiver connects. Keep a reference or it is garbage collected.
        splash = SplashScreen(sound=window.monitor.settings.sound)
        app._splash = splash
        if fullscreen:
            splash.showFullScreen()
        else:
            splash.resize(window.size())
            splash.show()

        def done():
            show_main()
            splash.close()
            app._splash = None

        splash.finished.connect(done)
    else:
        show_main()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
