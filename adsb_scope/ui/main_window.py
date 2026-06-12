"""Main window: status bar + tabs for scope, traffic table, and coverage."""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QTabWidget

from .scope_view import ScopeView
from .table_view import TableView
from .coverage_view import CoverageView


class MainWindow(QMainWindow):
    def __init__(self, store, client, tracker, cfg):
        super().__init__()
        self.store = store
        self.client = client
        self.tracker = tracker
        self.setWindowTitle("adsb-scope")
        self.resize(900, 700)

        tabs = QTabWidget()
        tabs.addTab(ScopeView(store, cfg.max_range_nm), "Scope")
        tabs.addTab(TableView(store), "Traffic")
        tabs.addTab(CoverageView(tracker), "Coverage")
        self.setCentralWidget(tabs)

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(1000)
        self._save_timer = QTimer(self)
        self._save_timer.timeout.connect(self.tracker.save)
        self._save_timer.start(30_000)  # persist coverage every 30 s
        self._feed_timer = QTimer(self)
        self._feed_timer.timeout.connect(self._feed_coverage)
        self._feed_timer.start(1000)

    def _feed_coverage(self):
        for ac in self.store.snapshot():
            if ac.has_position and ac.dist_nm is not None:
                self.tracker.record(ac.bearing, ac.dist_nm)

    def _update_status(self):
        state = "connected" if self.client.connected else "reconnecting…"
        self.statusBar().showMessage(
            f"{self.client.host}:{self.client.port}  [{state}]   "
            f"aircraft: {len(self.store.snapshot())}   "
            f"messages: {self.store.message_count:,}")

    def closeEvent(self, event):
        self.tracker.save()
        self.client.stop()
        super().closeEvent(event)
