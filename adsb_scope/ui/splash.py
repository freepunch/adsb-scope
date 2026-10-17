"""AirAware boot sequence: an Atari-era startup animation.

Four phases over ~4 seconds, driven by one timer and plain QPainter
rectangles so it stays cheap on a Pi 3:

  0  COLOR BARS   broadcast test pattern wipes in from the left
  1  LOGO         AIRAWARE assembles letter by letter in a 5x7 pixel font
  2  SELF TEST    fake boot checklist types out under a radar sweep
  3  FADE         to black, then the main window takes over

Scanlines are drawn over everything. Any key or tap skips to the end.
"""
from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import QWidget

import math

from ..audio import play_startup_sound

# Period-correct palette: saturated, few colours, no gradients.
BARS = [
    QColor(192, 192, 192), QColor(192, 192, 0), QColor(0, 192, 192),
    QColor(0, 192, 0), QColor(192, 0, 192), QColor(192, 0, 0),
    QColor(0, 0, 192), QColor(16, 16, 16),
]
NEON = QColor(0, 255, 136)
AMBER = QColor(255, 176, 0)
WHITE = QColor(235, 245, 235)
BG = QColor(6, 10, 8)

# 5x7 bitmap font, only the glyphs AIRAWARE needs.
GLYPHS = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
}
LOGO = "AIRAWARE"

BOOT_LINES = [
    "RECEIVER ....... 1090 MHZ",
    "DECODER ........ READSB",
    "POSITION ....... GPS",
    "AIRSPACE ....... ARMED",
    "",
    "READY",
]


class SplashScreen(QWidget):
    """Emits finished() when the sequence completes or is skipped."""

    finished = Signal()

    # phase boundaries in ticks (50 ms each)
    BARS_END = 16      # 0.8 s
    LOGO_END = 52      # 1.8 s of letter assembly
    TEST_END = 88      # 1.8 s of boot lines
    FADE_END = 100     # 0.6 s fade

    def __init__(self, parent=None, sound: bool = True):
        super().__init__(parent)
        self.sound = sound
        self.sound_played = False
        self.setWindowTitle("AirAware")
        self.setStyleSheet("background:#060a08;")
        self.setFocusPolicy(Qt.StrongFocus)
        self.tick = 0
        self._done = False
        if self.sound:
            # best effort: no sound server simply means a silent boot
            self.sound_played = play_startup_sound()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(50)

    # ---------- lifecycle ----------

    def _advance(self):
        self.tick += 1
        if self.tick >= self.FADE_END:
            self._finish()
        self.update()

    def _finish(self):
        if self._done:
            return
        self._done = True
        self._timer.stop()
        self.finished.emit()

    def skip(self):
        """Jump straight to the end; used by any key press or tap."""
        self.tick = self.FADE_END
        self._finish()

    def keyPressEvent(self, _event):
        self.skip()

    def mousePressEvent(self, _event):
        self.skip()

    # ---------- drawing ----------

    def _draw_bars(self, p: QPainter, w: int, h: int, progress: float):
        bar_w = w / len(BARS)
        visible = w * progress
        for i, col in enumerate(BARS):
            x = i * bar_w
            if x > visible:
                break
            p.fillRect(QRectF(x, 0, min(bar_w, visible - x), h), col)

    def _logo_metrics(self, w: int, h: int):
        """(pixel size, left x, top y). Everything below the logo is laid
        out from its baseline so the subtitle can never collide with it."""
        cols = len(LOGO) * 6 - 1          # 5 wide + 1 gap, no trailing gap
        px = max(2, int(min(w * 0.82 / cols, h * 0.16 / 7)))
        total_w = cols * px
        return px, (w - total_w) / 2, h * 0.26

    def _logo_bottom(self, w: int, h: int) -> float:
        px, _, y0 = self._logo_metrics(w, h)
        return y0 + 7 * px

    def _draw_logo(self, p: QPainter, w: int, h: int, letters: int, glow: bool):
        px, x0, y0 = self._logo_metrics(w, h)
        for li, ch in enumerate(LOGO[:letters]):
            rows = GLYPHS[ch]
            lx = x0 + li * 6 * px
            for ry, row in enumerate(rows):
                for rx, bit in enumerate(row):
                    if bit != "1":
                        continue
                    rect = QRectF(lx + rx * px, y0 + ry * px, px - 1, px - 1)
                    if glow:
                        p.fillRect(rect.adjusted(-1, -1, 1, 1), QColor(0, 90, 50))
                    p.fillRect(rect, NEON)

    def _draw_boot_lines(self, p: QPainter, w: int, h: int, progress: float):
        font = QFont("Courier New")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(max(8, int(h * 0.028)))
        font.setBold(True)
        p.setFont(font)
        shown = int(len(BOOT_LINES) * progress) + 1
        y = self._logo_bottom(w, h) + h * 0.13
        for line in BOOT_LINES[:shown]:
            p.setPen(AMBER if line != "READY" else NEON)
            p.drawText(QPointF(w * 0.18, y), line)
            y += h * 0.055

    def _draw_sweep(self, p: QPainter, w: int, h: int):
        cx, cy = w * 0.82, h * 0.70
        r = min(w, h) * 0.13
        p.setPen(QPen(QColor(0, 110, 60), 1))
        for frac in (0.4, 0.7, 1.0):
            p.drawEllipse(QPointF(cx, cy), r * frac, r * frac)
        ang = math.radians(self.tick * 14 % 360)
        p.setPen(QPen(NEON, 2))
        p.drawLine(QPointF(cx, cy),
                   QPointF(cx + r * math.sin(ang), cy - r * math.cos(ang)))

    def _draw_scanlines(self, p: QPainter, w: int, h: int):
        p.setPen(QPen(QColor(0, 0, 0, 70), 1))
        for y in range(0, h, 3):
            p.drawLine(0, y, w, y)

    def paintEvent(self, _event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), BG)
        t = self.tick

        if t <= self.BARS_END:
            self._draw_bars(p, w, h, t / self.BARS_END)
        else:
            if t <= self.LOGO_END:
                span = self.LOGO_END - self.BARS_END
                letters = min(len(LOGO),
                              int(len(LOGO) * (t - self.BARS_END) / span) + 1)
                self._draw_logo(p, w, h, letters, glow=False)
            else:
                self._draw_logo(p, w, h, len(LOGO), glow=True)
                sub = QFont("Courier New")
                sub.setStyleHint(QFont.Monospace)
                sub.setPointSize(max(7, int(h * 0.024)))
                p.setFont(sub)
                p.setPen(WHITE)
                p.drawText(QRectF(0, self._logo_bottom(w, h) + h * 0.03,
                                  w, h * 0.05),
                           Qt.AlignHCenter, "ADS-B TRAFFIC MONITOR")

            if t > self.LOGO_END:
                span = self.TEST_END - self.LOGO_END
                self._draw_boot_lines(
                    p, w, h, min(1.0, (t - self.LOGO_END) / span))
                self._draw_sweep(p, w, h)

        if t > self.TEST_END:
            alpha = int(255 * (t - self.TEST_END) / (self.FADE_END - self.TEST_END))
            p.fillRect(self.rect(), QColor(6, 10, 8, min(255, alpha)))

        self._draw_scanlines(p, w, h)
        p.end()
