"""Radar scope: range rings, sweep, aircraft glyphs, click selection."""
import math

from PySide6.QtCore import Qt, QPointF, QTimer, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QPolygonF
from PySide6.QtWidgets import QWidget

from ..hittest import polar_to_xy, hit_test

BG = QColor(6, 10, 8)
RING = QColor(0, 80, 0)
RING_TEXT = QColor(0, 235, 120)      # neon green, readable on black
SWEEP = QColor(0, 210, 0)
TEXT = QColor(255, 255, 255)         # aircraft labels: white
SELECTED = QColor(255, 190, 60)

# altitude bands -> colour (ft, colour); warm = low, cool = high
ALT_BANDS = [
    (5000,   QColor(255, 110, 90)),
    (12000,  QColor(255, 180, 70)),
    (22000,  QColor(120, 230, 140)),
    (32000,  QColor(90, 200, 255)),
    (99000,  QColor(160, 150, 255)),
]


def altitude_color(alt_ft) -> QColor:
    if not alt_ft:
        return QColor(160, 160, 160)
    for ceiling, colour in ALT_BANDS:
        if alt_ft < ceiling:
            return colour
    return ALT_BANDS[-1][1]


class ScopeView(QWidget):
    """Emits the hex id of a tapped aircraft."""

    aircraft_clicked = Signal(str)

    def __init__(self, store, max_range_nm: float, render_fps: int = 25, parent=None):
        super().__init__(parent)
        self.store = store
        self.max_range_nm = max_range_nm
        self.sweep_angle = 0.0
        self.selected_hex: str | None = None
        self._positions: dict[str, tuple[float, float]] = {}
        fps = max(5, min(render_fps, 60))
        self._step = 60.0 / fps          # constant 60 deg/sec regardless of fps
        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(int(1000 / fps))

    def set_selected(self, hex_id: str | None):
        self.selected_hex = hex_id
        self.update()

    def _tick(self):
        self.sweep_angle = (self.sweep_angle + self._step) % 360
        self.update()

    def mousePressEvent(self, event):
        pos = event.position()
        hit = hit_test(pos.x(), pos.y(), self._positions)
        if hit:
            self.aircraft_clicked.emit(hit)

    def _draw_aircraft(self, p: QPainter, x: float, y: float,
                       track: float | None, colour: QColor, selected: bool):
        """A small plane glyph pointing along its track (north up = 0 deg)."""
        p.save()
        p.translate(x, y)
        p.rotate(track if track is not None else 0.0)
        body = QPolygonF([
            QPointF(0, -9),      # nose
            QPointF(2.2, -2),
            QPointF(9, 3),       # right wingtip
            QPointF(9, 5),
            QPointF(2.2, 2.5),
            QPointF(2.0, 7),
            QPointF(4.5, 9),     # right tailplane
            QPointF(4.5, 10.5),
            QPointF(0, 9),
            QPointF(-4.5, 10.5), # left tailplane
            QPointF(-4.5, 9),
            QPointF(-2.0, 7),
            QPointF(-2.2, 2.5),
            QPointF(-9, 5),      # left wingtip
            QPointF(-9, 3),
            QPointF(-2.2, -2),
        ])
        if selected:
            p.setPen(QPen(SELECTED, 2))
            p.setBrush(SELECTED)
        else:
            p.setPen(QPen(colour, 1))
            p.setBrush(colour)
        p.drawPolygon(body)
        p.restore()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), BG)

        # keep the scope square and fully inside the pane, centred
        side = min(self.width(), self.height())
        cx, cy = self.width() / 2, self.height() / 2
        radius = side / 2 - 18

        font = QFont()
        font.setPointSize(8)
        p.setFont(font)

        # range rings, crosshair, ring labels, cardinal marks
        p.setPen(QPen(RING, 1))
        for frac in (1/3, 2/3, 1.0):
            p.drawEllipse(QPointF(cx, cy), radius * frac, radius * frac)
        p.drawLine(QPointF(cx, cy - radius), QPointF(cx, cy + radius))
        p.drawLine(QPointF(cx - radius, cy), QPointF(cx + radius, cy))
        p.setPen(RING_TEXT)
        for frac in (1/3, 2/3, 1.0):
            p.drawText(QPointF(cx + 4, cy - radius * frac + 12),
                       f"{self.max_range_nm * frac:.0f}")
        for deg, name in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
            rad = math.radians(deg)
            p.drawText(QPointF(cx + (radius + 6) * math.sin(rad) - 4,
                               cy - (radius + 6) * math.cos(rad) + 4), name)

        # sweep
        rad = math.radians(self.sweep_angle)
        p.setPen(QPen(SWEEP, 2))
        p.drawLine(QPointF(cx, cy),
                   QPointF(cx + radius * math.sin(rad), cy - radius * math.cos(rad)))

        # aircraft
        self._positions = {}
        for ac in self.store.snapshot():
            if not ac.has_position or ac.dist_nm is None:
                continue
            if ac.dist_nm > self.max_range_nm:
                continue
            x, y = polar_to_xy(cx, cy, radius, self.max_range_nm,
                               ac.bearing, ac.dist_nm)
            self._positions[ac.hex_id] = (x, y)
            selected = (ac.hex_id == self.selected_hex)
            self._draw_aircraft(p, x, y, ac.track_deg,
                                altitude_color(ac.altitude_ft), selected)
            p.setPen(SELECTED if selected else TEXT)
            label = ac.callsign or ac.hex_id.upper()
            p.drawText(QPointF(x + 12, y - 6), label)
            if ac.altitude_ft:
                p.drawText(QPointF(x + 12, y + 6), f"{ac.altitude_ft // 100:03d}")
        p.end()
