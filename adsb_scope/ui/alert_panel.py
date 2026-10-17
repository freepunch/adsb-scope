"""Alert banner + audio. Owns the AlertMonitor and its 1 Hz timer, so it can
be dropped into any layout. Other views read panel.monitor.threats."""
import math
import struct
import tempfile
import wave
from pathlib import Path

import subprocess
import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel, QApplication

from ..alerts import AlertMonitor, Level


from ..audio import player_cmd as _player_cmd

STYLE = {
    Level.NONE:     ("#0b1a0b", "#58c058"),
    Level.ADVISORY: ("#2a2a00", "#f0e040"),
    Level.WARNING:  ("#3a1d00", "#ffa030"),
    Level.ALERT:    ("#4a0000", "#ff5050"),
    Level.LOST:     ("#202030", "#b0b0ff"),
}


def _make_tone(path: Path, freq: float, ms: int):
    rate = 22050
    n = int(rate * ms / 1000)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        frames = b"".join(
            struct.pack("<h", int(12000 * math.sin(2 * math.pi * freq * i / rate)
                                  * min(1, i / 300, (n - i) / 300)))
            for i in range(n))
        w.writeframes(frames)


class AlertPanel(QLabel):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.monitor = AlertMonitor(store)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setMinimumHeight(36)
        self._prev = Level.NONE
        self._since_repeat = 0.0
        self._sounds = {}
        self._cmd = _player_cmd()
        tmp = Path(tempfile.gettempdir())
        for lvl, (f, ms) in {Level.WARNING: (880, 250),
                             Level.ALERT: (1320, 400),
                             Level.LOST: (440, 300)}.items():
            path = tmp / f"adsb_alert_{lvl.name}.wav"
            if not path.exists():
                _make_tone(path, f, ms)
            self._sounds[lvl] = path
        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(1000)
        self._tick()

    def _play(self, lvl):
        if not self.monitor.settings.sound:
            return
        path = self._sounds.get(lvl)
        try:
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            elif self._cmd:
                subprocess.Popen(self._cmd + [str(path)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                QApplication.beep()
        except Exception:
            QApplication.beep()

    def _tick(self):
        s = self.monitor.settings
        threats = self.monitor.update()
        top = self.monitor.max_level()

        if top > self._prev and top >= Level.WARNING:
            self._play(top)
            self._since_repeat = 0
        elif top == Level.ALERT:
            self._since_repeat += 1
            if self._since_repeat >= s.alert_repeat_s:
                self._play(Level.ALERT)
                self._since_repeat = 0
        self._prev = top

        bg, fg = STYLE[top]
        self.setStyleSheet(f"background:{bg}; color:{fg}; font: bold 13px monospace;"
                           f"padding:6px; border-bottom:2px solid {fg};")
        if not s.enabled:
            self.setText("ALERTS OFF")
        elif not threats:
            warn = "" if s.site_elev_ft is not None else "   (set site_elev_ft in alerts.json)"
            self.setText(f"CLEAR  r{s.advisory_nm:g}nm / {s.advisory_agl_ft:.0f}ft AGL"
                         f"  alt {s.altimeter_inhg:.2f}{warn}")
        else:
            head = f"{top.name}: " + threats[0].summary()
            more = f"   (+{len(threats) - 1} more)" if len(threats) > 1 else ""
            self.setText(head + more)
