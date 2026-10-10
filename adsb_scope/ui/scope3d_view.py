"""Real-time 3D scope using pyqtgraph's OpenGL widgets.

Local frame: x = east nm, y = north nm, z = height AGL scaled by
`vexag` (default 5x) so low traffic is readable. Draws ground grid, range
rings, alert cylinder, aircraft colored by alert level, drop lines to the
ground, and short trails. Falls back to a message if OpenGL/pyqtgraph is
unavailable (e.g. a Pi without GL drivers).
"""
import math
from collections import deque

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from ..alerts import Level, to_local_nm, height_agl_ft, FT_PER_NM

# numpy is imported inside the guard as well: on a Pi with no 3D deps
# installed, an unguarded import here would break the whole app, not
# just this tab.
try:
    import numpy as np
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
    GL_OK = True
except Exception as exc:          # ImportError or GL init failure
    GL_OK, GL_ERR = False, str(exc)

LEVEL_RGBA = {Level.NONE: (0.2, 0.9, 0.9, 1), Level.ADVISORY: (0.94, 0.88, 0.25, 1),
              Level.WARNING: (1.0, 0.63, 0.19, 1), Level.ALERT: (1.0, 0.3, 0.3, 1),
              Level.LOST: (0.7, 0.7, 1.0, 0.6)}


class Scope3DView(QWidget):
    def __init__(self, store, monitor, view_range_nm=15.0, vexag=5.0,
                 trail_len=45, parent=None):
        super().__init__(parent)
        self.store, self.monitor = store, monitor
        self.range_nm, self.vexag = view_range_nm, vexag
        self.trails: dict[str, deque] = {}
        self.trail_len = trail_len
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if not GL_OK:
            layout.addWidget(QLabel(f"3D view unavailable: {GL_ERR}\n"
                                    "pip install pyqtgraph PyOpenGL"))
            return

        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor((8, 12, 8))
        self.view.setCameraPosition(distance=self.range_nm * 2.2, elevation=25, azimuth=-90)
        layout.addWidget(self.view)

        grid = gl.GLGridItem()
        grid.setSize(self.range_nm * 2, self.range_nm * 2)
        grid.setSpacing(1, 1)
        grid.setColor((0, 90, 0, 120))
        self.view.addItem(grid)

        # range rings every 5 nm
        for r in np.arange(5, self.range_nm + 0.1, 5):
            a = np.linspace(0, 2 * np.pi, 120)
            ring = np.column_stack([r * np.sin(a), r * np.cos(a), np.zeros_like(a)])
            self.view.addItem(gl.GLLinePlotItem(pos=ring, color=(0, 0.6, 0, 0.8), width=1))

        # north tick
        self.view.addItem(gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, self.range_nm, 0]]), color=(0, 0.6, 0, 0.6)))

        self._add_alert_cylinders()

        self.points = gl.GLScatterPlotItem(pos=np.zeros((1, 3)), size=9, pxMode=True)
        self.view.addItem(self.points)
        self.drops = gl.GLLinePlotItem(pos=np.zeros((2, 3)), mode="lines",
                                       color=(0.3, 0.8, 0.8, 0.5), width=1)
        self.view.addItem(self.drops)
        self.trail_item = gl.GLLinePlotItem(pos=np.zeros((2, 3)), mode="lines",
                                            color=(0.3, 0.9, 0.9, 0.35), width=1)
        self.view.addItem(self.trail_item)
        self.labels = []

        timer = QTimer(self)
        timer.timeout.connect(self.refresh)
        timer.start(1000)

    def _z(self, agl_ft):
        return max(agl_ft or 0.0, 0.0) / FT_PER_NM * self.vexag

    def _add_alert_cylinders(self):
        s = self.monitor.settings
        for nm, ceil, rgba in ((s.advisory_nm, s.advisory_agl_ft, (0.94, 0.88, 0.25, 0.10)),
                               (s.alert_nm, s.alert_agl_ft, (1.0, 0.3, 0.3, 0.18))):
            md = gl.MeshData.cylinder(rows=1, cols=48, radius=[nm, nm],
                                      length=self._z(ceil))
            item = gl.GLMeshItem(meshdata=md, smooth=True, color=rgba,
                                 shader=None, glOptions="additive", drawEdges=False)
            self.view.addItem(item)

    def refresh(self):
        s = self.monitor.settings
        levels = {t.hex_id: t.level for t in self.monitor.threats}
        pos, cols, drops, trails = [], [], [], []
        for lab in self.labels:
            self.view.removeItem(lab)
        self.labels = []

        live = set()
        for ac in self.store.snapshot():
            if ac.lat is None or ac.lon is None:
                continue
            e, n = to_local_nm(self.store.home_lat, self.store.home_lon, ac.lat, ac.lon)
            if math.hypot(e, n) > self.range_nm:
                continue
            live.add(ac.hex_id)
            z = self._z(height_agl_ft(ac.altitude_ft, s))
            p = (e, n, z)
            pos.append(p)
            cols.append(LEVEL_RGBA.get(levels.get(ac.hex_id, Level.NONE)))
            drops += [p, (e, n, 0.0)]
            tr = self.trails.setdefault(ac.hex_id, deque(maxlen=self.trail_len))
            tr.append(p)
            pts = list(tr)
            for a, b in zip(pts, pts[1:]):
                trails += [a, b]
            if hasattr(gl, "GLTextItem"):
                agl = height_agl_ft(ac.altitude_ft, s)
                txt = (ac.callsign or ac.hex_id) + ("" if agl is None else f" {agl:.0f}")
                lab = gl.GLTextItem(pos=(e, n, z + 0.15), text=txt,
                                    color=(220, 220, 220, 255))
                self.view.addItem(lab)
                self.labels.append(lab)

        for h in list(self.trails):
            if h not in live:
                del self.trails[h]

        if pos:
            self.points.setData(pos=np.array(pos), color=np.array(cols))
            self.drops.setData(pos=np.array(drops))
        else:
            self.points.setData(pos=np.zeros((0, 3)))
            self.drops.setData(pos=np.zeros((2, 3)))
        self.trail_item.setData(pos=np.array(trails) if trails else np.zeros((2, 3)))
