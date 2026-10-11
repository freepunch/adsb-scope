"""Entry point: python -m adsb_scope"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from . import config
from .aircraft import AircraftStore
from .coverage import CoverageTracker
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

    gps = None
    if cfg.gps_enabled:
        gps = GPSClient(on_fix=store.set_home)
        gps.start()

    app = QApplication(sys.argv)
    if cfg.hide_cursor:
        app.setOverrideCursor(Qt.BlankCursor)

    window = MainWindow(store, client, tracker, cfg, gps=gps)
    fullscreen = cfg.fullscreen or "--fullscreen" in sys.argv

    def show_main():
        if fullscreen:
            window.showFullScreen()
        else:
            window.show()

    if cfg.splash:
        # Built and shown first so the deck has something on screen while
        # the receiver connects. Keep a reference or it is garbage collected.
        splash = SplashScreen()
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
