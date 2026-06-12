"""Radar scope widget: range rings, sweep, blips, velocity vectors."""
import math

from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QWidget

BG = QColor(8, 12, 8)
RING = QColor(0, 90, 0)
SWEEP = QColor(0, 200, 0)
BLIP = QColor(0, 220, 220)
TEXT = QColor(220, 220, 220)


class ScopeView(QWidget):
    def __init__(self, store, max_range_nm: float, parent=None):
        super().__init__(parent)
        self.store = store
        self.max_range_nm = max_range_nm
        self.sweep_angle = 0.0
        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(40)  # ~25 fps

    def _tick(self):
        self.sweep_angle = (self.sweep_angle + 2.4) % 360
        self.update()

    def _polar_to_xy(self, cx, cy, radius, bearing, dist_nm):
        frac = min(dist_nm / self.max_range_nm, 1.0)
        rad = math.radians(bearing)
        return (cx + radius * frac * math.sin(rad),
                cy - radius * frac * math.cos(rad))

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), BG)

        cx, cy = self.width() / 2, self.height() / 2
        radius = min(cx, cy) - 10

        # rings + crosshair + ring labels
        p.setPen(QPen(RING, 1))
        for frac in (1/3, 2/3, 1.0):
            p.drawEllipse(QPointF(cx, cy), radius * frac, radius * frac)
            label = f"{self.max_range_nm * frac:.0f}"
            p.drawText(QPointF(cx + 4, cy - radius * frac + 14), label)
        p.drawLine(QPointF(cx, cy - radius), QPointF(cx, cy + radius))
        p.drawLine(QPointF(cx - radius, cy), QPointF(cx + radius, cy))

        # sweep
        rad = math.radians(self.sweep_angle)
        p.setPen(QPen(SWEEP, 2))
        p.drawLine(QPointF(cx, cy),
                   QPointF(cx + radius * math.sin(rad), cy - radius * math.cos(rad)))

        # aircraft
        font = QFont("Menlo", 9)
        font.setStyleHint(QFont.Monospace)
        p.setFont(font)
        for ac in self.store.snapshot():
            if not ac.has_position or ac.dist_nm is None:
                continue
            if ac.dist_nm > self.max_range_nm:
                continue
            x, y = self._polar_to_xy(cx, cy, radius, ac.bearing, ac.dist_nm)
            p.setPen(Qt.NoPen)
            p.setBrush(BLIP)
            p.drawEllipse(QPointF(x, y), 3.5, 3.5)
            # velocity vector: a short line ahead along the track
            if ac.track_deg is not None and ac.ground_speed_kt:
                vec = 6 + min(ac.ground_speed_kt, 600) / 40
                trad = math.radians(ac.track_deg)
                p.setPen(QPen(BLIP, 1))
                p.drawLine(QPointF(x, y),
                           QPointF(x + vec * math.sin(trad), y - vec * math.cos(trad)))
            p.setPen(TEXT)
            label = ac.callsign or ac.hex_id
            if ac.altitude_ft:
                label += f" {ac.altitude_ft // 100:03d}"
            p.drawText(QPointF(x + 7, y - 5), label)
        p.end()
