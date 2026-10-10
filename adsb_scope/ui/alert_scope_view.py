"""ScopeView plus alert rings and threat highlights. Subclasses the existing
ScopeView so nothing in the original file changes."""
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPen, QColor

from .scope_view import ScopeView
from ..alerts import Level

COLORS = {Level.ADVISORY: QColor(240, 224, 64), Level.WARNING: QColor(255, 160, 48),
          Level.ALERT: QColor(255, 80, 80), Level.LOST: QColor(176, 176, 255)}


class AlertScopeView(ScopeView):
    def __init__(self, store, max_range_nm, monitor, render_fps: int = 25, parent=None):
        super().__init__(store, max_range_nm, render_fps, parent)
        self.monitor = monitor

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # same geometry the base class drew with, so rings line up with glyphs
        cx, cy, radius = self.scope_geometry()
        k = radius / self.max_range_nm
        s = self.monitor.settings

        dash = QPen(QColor(255, 160, 48, 160), 1, Qt.DashLine)
        for nm, col in ((s.advisory_nm, COLORS[Level.ADVISORY]),
                        (s.warning_nm, COLORS[Level.WARNING]),
                        (s.alert_nm, COLORS[Level.ALERT])):
            r_px = nm * k
            if r_px > radius * 1.05:
                continue          # ring is off-scope at this zoom; skip it
            dash.setColor(QColor(col.red(), col.green(), col.blue(), 150))
            p.setPen(dash)
            p.drawEllipse(QPointF(cx, cy), r_px, r_px)

        for t in self.monitor.threats:
            x, y = cx + t.east_nm * k, cy - t.north_nm * k
            pen = QPen(COLORS[t.level], 2,
                       Qt.DotLine if t.level == Level.LOST else Qt.SolidLine)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRect(int(x - 8), int(y - 8), 16, 16)
        p.end()
