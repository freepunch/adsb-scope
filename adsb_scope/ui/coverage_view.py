"""Polar plot of max reception range per bearing: the antenna's report card."""
import math

from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

BG = QColor(10, 10, 14)
RING = QColor(70, 70, 90)
FILL = QColor(0, 160, 220, 70)
EDGE = QColor(0, 200, 255)
TEXT = QColor(220, 220, 220)


class CoverageView(QWidget):
    def __init__(self, tracker, parent=None):
        super().__init__(parent)
        self.tracker = tracker
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.status = QLabel()
        reset_btn = QPushButton("Reset (new antenna test)")
        reset_btn.clicked.connect(self.tracker.reset)
        bar.addWidget(self.status)
        bar.addStretch()
        bar.addWidget(reset_btn)
        layout.addLayout(bar)
        self.plot = _CoveragePlot(tracker)
        layout.addWidget(self.plot, stretch=1)
        timer = QTimer(self)
        timer.timeout.connect(self._refresh)
        timer.start(1000)

    def _refresh(self):
        ranges = self.tracker.snapshot()
        best = max(ranges) if ranges else 0
        self.status.setText(
            f"positions logged: {self.tracker.total_positions:,}   "
            f"best range: {best:.0f} nm")
        self.plot.update()


class _CoveragePlot(QWidget):
    def __init__(self, tracker, parent=None):
        super().__init__(parent)
        self.tracker = tracker

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), BG)
        cx, cy = self.width() / 2, self.height() / 2
        radius = min(cx, cy) - 24

        ranges = self.tracker.snapshot()
        scale = max(max(ranges), 1.0) if ranges else 1.0

        p.setPen(QPen(RING, 1))
        for frac in (0.25, 0.5, 0.75, 1.0):
            p.drawEllipse(QPointF(cx, cy), radius * frac, radius * frac)
            p.drawText(QPointF(cx + 4, cy - radius * frac + 13),
                       f"{scale * frac:.0f} nm")
        for deg, name in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
            rad = math.radians(deg)
            p.drawText(QPointF(cx + (radius + 10) * math.sin(rad) - 4,
                               cy - (radius + 10) * math.cos(rad) + 4), name)

        if any(r > 0 for r in ranges):
            poly = QPolygonF()
            step = self.tracker.bucket_deg
            for i, r in enumerate(ranges):
                rad = math.radians(i * step + step / 2)
                frac = r / scale
                poly.append(QPointF(cx + radius * frac * math.sin(rad),
                                    cy - radius * frac * math.cos(rad)))
            p.setPen(QPen(EDGE, 2))
            p.setBrush(QBrush(FILL))
            p.drawPolygon(poly)

        p.setPen(TEXT)
        p.drawText(QPointF(10, 18), "Max range per bearing")
        p.end()
