"""Live traffic table, nearest aircraft first."""
import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

COLUMNS = ["Callsign", "Hex", "Alt ft", "GS kt", "Track", "Dist nm", "Brg", "Age s"]


class TableView(QTableWidget):
    def __init__(self, store, parent=None):
        super().__init__(0, len(COLUMNS), parent)
        self.store = store
        self.setHorizontalHeaderLabels(COLUMNS)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.verticalHeader().setVisible(False)
        timer = QTimer(self)
        timer.timeout.connect(self.refresh)
        timer.start(1000)

    @staticmethod
    def _fmt(value, spec="{}"):
        return spec.format(value) if value is not None else "—"

    def refresh(self):
        aircraft = self.store.snapshot()
        now = time.time()
        self.setRowCount(len(aircraft))
        for row, ac in enumerate(aircraft):
            cells = [
                ac.callsign or "—",
                ac.hex_id,
                self._fmt(ac.altitude_ft, "{:,}"),
                self._fmt(ac.ground_speed_kt),
                self._fmt(ac.track_deg, "{:.0f}"),
                self._fmt(ac.dist_nm, "{:.1f}"),
                self._fmt(ac.bearing, "{:.0f}"),
                f"{now - ac.last_seen:.0f}",
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(str(text))
                if col >= 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.setItem(row, col, item)
