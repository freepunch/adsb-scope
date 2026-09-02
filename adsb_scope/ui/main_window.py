"""Main window: split scope + data panel, with coverage on a second view."""
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QSplitter, QPushButton, QStackedWidget)

from .scope_view import ScopeView
from .detail_panel import DetailPanel
from .coverage_view import CoverageView

DARK = "background-color:#0a0e0b;"


class MainWindow(QMainWindow):
    def __init__(self, store, client, tracker, cfg, gps=None):
        super().__init__()
        self.store = store
        self.client = client
        self.tracker = tracker
        self.gps = gps
        self.setWindowTitle("adsb-scope")
        self.resize(1024, 600)
        self.setStyleSheet(DARK)

        self.scope = ScopeView(store, cfg.max_range_nm, cfg.render_fps)
        self.panel = DetailPanel(store)

        # scope click -> panel detail; panel row click -> scope highlight
        self.scope.aircraft_clicked.connect(self._on_scope_click)
        self.panel.aircraft_selected.connect(self.scope.set_selected)
        self.panel.selection_cleared.connect(lambda: self.scope.set_selected(None))

        split = QSplitter(Qt.Horizontal)
        split.addWidget(self.scope)
        split.addWidget(self.panel)
        split.setStretchFactor(0, 3)     # scope gets ~60% of 1024px
        split.setStretchFactor(1, 2)
        split.setSizes([600, 424])

        radar_page = QWidget()
        radar_layout = QVBoxLayout(radar_page)
        radar_layout.setContentsMargins(0, 0, 0, 0)
        radar_layout.addWidget(split)

        self.pages = QStackedWidget()
        self.pages.addWidget(radar_page)                 # 0
        self.pages.addWidget(CoverageView(tracker))      # 1

        # bottom bar: view switch, touch-sized
        bar = QHBoxLayout()
        self.radar_btn = QPushButton("RADAR")
        self.cov_btn = QPushButton("COVERAGE")
        for btn in (self.radar_btn, self.cov_btn):
            btn.setMinimumHeight(40)
            btn.setCheckable(True)
        self.radar_btn.setChecked(True)
        self.radar_btn.clicked.connect(lambda: self._show_page(0))
        self.cov_btn.clicked.connect(lambda: self._show_page(1))
        bar.addWidget(self.radar_btn)
        bar.addWidget(self.cov_btn)
        bar.addStretch()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.pages, stretch=1)
        layout.addLayout(bar)
        self.setCentralWidget(central)

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(1000)
        self._save_timer = QTimer(self)
        self._save_timer.timeout.connect(self.tracker.save)
        self._save_timer.start(30_000)
        self._feed_timer = QTimer(self)
        self._feed_timer.timeout.connect(self._feed_coverage)
        self._feed_timer.start(1000)

    def _show_page(self, index: int):
        self.pages.setCurrentIndex(index)
        self.radar_btn.setChecked(index == 0)
        self.cov_btn.setChecked(index == 1)

    def _on_scope_click(self, hex_id: str):
        self.scope.set_selected(hex_id)
        self.panel.select(hex_id)

    def _feed_coverage(self):
        for ac in self.store.snapshot():
            if ac.has_position and ac.dist_nm is not None:
                self.tracker.record(ac.bearing, ac.dist_nm)

    def _update_status(self):
        state = "connected" if self.client.connected else "reconnecting…"
        gps_state = ""
        if self.gps is not None:
            gps_state = "   GPS: fix" if self.gps.has_fix else "   GPS: searching…"
        self.statusBar().showMessage(
            f"{self.client.host}:{self.client.port}  [{state}]   "
            f"aircraft: {len(self.store.snapshot())}   "
            f"messages: {self.store.message_count:,}"
            f"{gps_state}   "
            f"pos: {self.store.home_lat:.3f}, {self.store.home_lon:.3f}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
        elif event.key() == Qt.Key_Escape:
            if self.panel.selected_hex is not None:
                self.panel.show_list()      # Esc backs out of detail first
            elif self.isFullScreen():
                self.showNormal()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.tracker.save()
        self.client.stop()
        if self.gps is not None:
            self.gps.stop()
        super().closeEvent(event)
