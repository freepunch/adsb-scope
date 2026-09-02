"""Right-hand data panel: live traffic list, or detail on one aircraft.

Two stacked pages. The list is always the default; tapping an aircraft
(here or on the scope) swaps to detail, and Back returns.
"""
import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QHeaderView, QGridLayout)

HEADER_CSS = "color:#9ae6a0; font-weight:bold; letter-spacing:1px;"
VALUE_CSS = "color:#e6ece6; font-size:15px;"
KEY_CSS = "color:#7f8c7f; font-size:11px;"


class DetailPanel(QWidget):
    """Emits hex ids when the user picks an aircraft from the list."""

    aircraft_selected = Signal(str)
    selection_cleared = Signal()

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.selected_hex: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_list_page())
        self.stack.addWidget(self._build_detail_page())
        root.addWidget(self.stack)

        timer = QTimer(self)
        timer.timeout.connect(self.refresh)
        timer.start(1000)

    # ---------- pages ----------

    def _build_list_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)

        self.list_header = QLabel("TRAFFIC")
        self.list_header.setStyleSheet(HEADER_CSS)
        lay.addWidget(self.list_header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Callsign", "Alt", "Dist", "Brg"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)  # touch-friendly rows
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(self._on_row_clicked)
        lay.addWidget(self.table)
        return page

    def _build_detail_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        self.back_btn = QPushButton("‹  Back")
        self.back_btn.setMinimumHeight(38)          # touch target
        self.back_btn.clicked.connect(self.show_list)
        top.addWidget(self.back_btn)
        top.addStretch()
        lay.addLayout(top)

        self.detail_call = QLabel("—")
        self.detail_call.setStyleSheet(
            "color:#ffbe3c; font-size:26px; font-weight:bold;")
        lay.addWidget(self.detail_call)

        self.detail_hex = QLabel("")
        self.detail_hex.setStyleSheet(KEY_CSS)
        lay.addWidget(self.detail_hex)

        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        self.fields: dict[str, QLabel] = {}
        labels = [
            ("Altitude", "alt"), ("Vertical", "vert"),
            ("Ground speed", "gs"), ("Track", "track"),
            ("Distance", "dist"), ("Bearing", "brg"),
            ("Latitude", "lat"), ("Longitude", "lon"),
            ("Last seen", "age"), ("", ""),
        ]
        for i, (title, key) in enumerate(labels):
            if not key:
                continue
            row, col = divmod(i, 2)
            box = QVBoxLayout()
            k = QLabel(title.upper())
            k.setStyleSheet(KEY_CSS)
            v = QLabel("—")
            v.setStyleSheet(VALUE_CSS)
            box.addWidget(k)
            box.addWidget(v)
            holder = QWidget()
            holder.setLayout(box)
            grid.addWidget(holder, row, col)
            self.fields[key] = v
        lay.addLayout(grid)
        lay.addStretch()
        return page

    # ---------- behaviour ----------

    def _on_row_clicked(self, row, _col):
        item = self.table.item(row, 0)
        if item is None:
            return
        hex_id = item.data(Qt.UserRole)
        if hex_id:
            self.select(hex_id)
            self.aircraft_selected.emit(hex_id)

    def select(self, hex_id: str):
        self.selected_hex = hex_id
        self.stack.setCurrentIndex(1)
        self.refresh()

    def show_list(self):
        self.selected_hex = None
        self.stack.setCurrentIndex(0)
        self.selection_cleared.emit()
        self.refresh()

    @staticmethod
    def _fmt(value, spec="{}", suffix=""):
        return f"{spec.format(value)}{suffix}" if value is not None else "—"

    def refresh(self):
        aircraft = self.store.snapshot()
        if self.selected_hex is not None:
            self._refresh_detail(aircraft)
        else:
            self._refresh_list(aircraft)

    def _refresh_list(self, aircraft):
        self.list_header.setText(f"TRAFFIC   ({len(aircraft)})")
        self.table.setRowCount(len(aircraft))
        for row, ac in enumerate(aircraft):
            cells = [
                ac.callsign or ac.hex_id.upper(),
                self._fmt(ac.altitude_ft, "{:,}"),
                self._fmt(ac.dist_nm, "{:.1f}"),
                self._fmt(ac.bearing, "{:.0f}"),
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(str(text))
                if col == 0:
                    item.setData(Qt.UserRole, ac.hex_id)
                else:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, item)

    def _refresh_detail(self, aircraft):
        ac = next((a for a in aircraft if a.hex_id == self.selected_hex), None)
        if ac is None:
            self.detail_call.setText("LOST")
            self.detail_hex.setText(f"{self.selected_hex.upper()}  no longer tracked")
            for v in self.fields.values():
                v.setText("—")
            return
        self.detail_call.setText(ac.callsign or "(no callsign)")
        self.detail_hex.setText(f"ICAO {ac.hex_id.upper()}")
        vert = None
        self.fields["alt"].setText(self._fmt(ac.altitude_ft, "{:,}", " ft"))
        self.fields["vert"].setText(self._fmt(vert, "{}", " fpm"))
        self.fields["gs"].setText(self._fmt(ac.ground_speed_kt, "{}", " kt"))
        self.fields["track"].setText(self._fmt(ac.track_deg, "{:.0f}", "°"))
        self.fields["dist"].setText(self._fmt(ac.dist_nm, "{:.1f}", " nm"))
        self.fields["brg"].setText(self._fmt(ac.bearing, "{:.0f}", "°"))
        self.fields["lat"].setText(self._fmt(ac.lat, "{:.4f}"))
        self.fields["lon"].setText(self._fmt(ac.lon, "{:.4f}"))
        self.fields["age"].setText(f"{time.time() - ac.last_seen:.0f} s ago")
