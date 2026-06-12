"""Entry point: python -m adsb_scope"""
import sys

from PySide6.QtWidgets import QApplication

from . import config
from .aircraft import AircraftStore
from .coverage import CoverageTracker
from .sbs_client import SBSClient
from .ui.main_window import MainWindow


def main():
    cfg = config.load()
    store = AircraftStore(cfg.home_lat, cfg.home_lon, cfg.stale_seconds)
    tracker = CoverageTracker(cfg.coverage_bucket_deg)
    client = SBSClient(cfg.host, cfg.port, store)
    client.start()

    app = QApplication(sys.argv)
    window = MainWindow(store, client, tracker, cfg)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
