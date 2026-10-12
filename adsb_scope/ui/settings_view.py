"""In-field settings, changeable from the screen alone.

Design principle: anything that needs adjusting away from a keyboard
must be reachable here. Today that means the altimeter setting (changes
every session), site elevation (changes when you move sites), and the
alert and sound toggles.

All controls are sized for a fingertip on the 7 inch panel.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QFrame)

from ..alerts import save_settings

NEON = "#00ff88"
AMBER = "#ffbe3c"

STEP_BTN = f"""
QPushButton {{
    background-color:#0d1a12; color:{NEON};
    border:1px solid #1d5c3a; border-radius:5px;
    font-size:26px; font-weight:bold;
}}
QPushButton:pressed {{ background-color:#1d5c3a; color:#ffffff; }}
QPushButton:disabled {{ color:#38503f; border-color:#13301f; }}
"""

ACTION_BTN = f"""
QPushButton {{
    background-color:#0d1a12; color:{NEON};
    border:1px solid #1d5c3a; border-radius:5px;
    font-size:15px; font-weight:bold; letter-spacing:1px; padding:0 20px;
}}
QPushButton:pressed {{ background-color:#1d5c3a; color:#ffffff; }}
QPushButton:checked {{ background-color:#1d5c3a; color:#ffffff; }}
"""

KEY_CSS = f"color:{NEON}; font-size:12px; letter-spacing:1px;"
VAL_CSS = "color:#ffffff; font-size:30px; font-weight:bold;"
HINT_CSS = "color:#7f8c7f; font-size:11px;"


class StepperRow(QWidget):
    """A labelled value with big minus/plus buttons either side."""

    changed = Signal(float)

    def __init__(self, title: str, hint: str, value: float, step: float,
                 fmt: str = "{:.2f}", lo: float = None, hi: float = None,
                 parent=None):
        super().__init__(parent)
        self.value = value
        self.step = step
        self.fmt = fmt
        self.lo, self.hi = lo, hi
        self.locked = False     # set while an auto source owns this value

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 8)
        root.setSpacing(2)

        key = QLabel(title.upper())
        key.setStyleSheet(KEY_CSS)
        root.addWidget(key)

        row = QHBoxLayout()
        self.minus = QPushButton("\u2212")
        self.plus = QPushButton("+")
        for b in (self.minus, self.plus):
            b.setFixedSize(58, 54)
            b.setStyleSheet(STEP_BTN)
            b.setFocusPolicy(Qt.NoFocus)
        self.minus.clicked.connect(lambda: self._bump(-1))
        self.plus.clicked.connect(lambda: self._bump(+1))

        self.readout = QLabel()
        self.readout.setStyleSheet(VAL_CSS)
        self.readout.setAlignment(Qt.AlignCenter)
        self.readout.setMinimumWidth(170)

        # keep the three controls together so they are reachable with one
        # thumb, rather than spread to opposite edges of a 1024px screen
        row.addWidget(self.minus)
        row.addWidget(self.readout)
        row.addWidget(self.plus)
        row.addStretch(1)
        root.addLayout(row)

        if hint:
            h = QLabel(hint)
            h.setStyleSheet(HINT_CSS)
            h.setWordWrap(True)
            root.addWidget(h)

        self._refresh()

    def _bump(self, direction: int):
        v = self.value + direction * self.step
        if self.lo is not None:
            v = max(self.lo, v)
        if self.hi is not None:
            v = min(self.hi, v)
        self.value = round(v, 4)
        self._refresh()
        self.changed.emit(self.value)

    def set_value(self, v: float):
        self.value = v
        self._refresh()

    def set_locked(self, locked: bool):
        """Grey out the buttons while an automatic source owns this value."""
        self.locked = locked
        self._refresh()

    def _refresh(self):
        self.readout.setText(self.fmt.format(self.value))
        if self.locked:
            self.minus.setEnabled(False)
            self.plus.setEnabled(False)
            return
        self.minus.setEnabled(self.lo is None or self.value > self.lo)
        self.plus.setEnabled(self.hi is None or self.value < self.hi)


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color:#14301f;")
    return line


class SettingsView(QWidget):
    """Edits the live AlertSettings object; Save writes alerts.json."""

    def __init__(self, monitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        s = monitor.settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)

        title = QLabel("SETTINGS")
        title.setStyleSheet(f"color:{NEON}; font-size:15px; font-weight:bold;"
                            " letter-spacing:2px;")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 10, 0)

        self.auto_alt_btn = QPushButton()
        self.auto_elev_btn = QPushButton()
        for b in (self.auto_alt_btn, self.auto_elev_btn):
            b.setMinimumHeight(44)
            b.setCheckable(True)
            b.setStyleSheet(ACTION_BTN)
            b.setFocusPolicy(Qt.NoFocus)
        self.auto_alt_btn.clicked.connect(self._toggle_auto_altimeter)
        self.auto_elev_btn.clicked.connect(self._toggle_auto_elevation)
        auto_row = QHBoxLayout()
        auto_row.addWidget(self.auto_alt_btn)
        auto_row.addWidget(self.auto_elev_btn)
        lay.addLayout(auto_row)

        self.auto_status = QLabel("Auto-calibration starting...")
        self.auto_status.setStyleSheet(HINT_CSS)
        self.auto_status.setWordWrap(True)
        lay.addWidget(self.auto_status)
        lay.addWidget(_divider())

        self.altimeter = StepperRow(
            "Altimeter setting", "Derived from traffic reporting both baro and "
            "geometric altitude. Switch to MANUAL to enter a METAR value.",
            s.altimeter_inhg, 0.01, "{:.2f}", 27.50, 31.50)
        self.altimeter.changed.connect(self._on_altimeter)
        lay.addWidget(self.altimeter)
        lay.addWidget(_divider())

        self.elevation = StepperRow(
            "Site elevation", "Feet MSL at the site, from a 3D GPS fix. MANUAL steps 50 ft.",
            s.site_elev_ft if s.site_elev_ft is not None else 0.0,
            50.0, "{:.0f} ft", -300.0, 15000.0)
        self.elevation.changed.connect(self._on_elevation)
        lay.addWidget(self.elevation)
        lay.addWidget(_divider())

        toggles = QHBoxLayout()
        self.alerts_btn = QPushButton()
        self.sound_btn = QPushButton()
        for b in (self.alerts_btn, self.sound_btn):
            b.setMinimumHeight(52)
            b.setCheckable(True)
            b.setStyleSheet(ACTION_BTN)
            b.setFocusPolicy(Qt.NoFocus)
            toggles.addWidget(b)
        self.alerts_btn.clicked.connect(self._toggle_alerts)
        self.sound_btn.clicked.connect(self._toggle_sound)
        lay.addLayout(toggles)
        lay.addWidget(_divider())

        rings = QLabel("ALERT RINGS")
        rings.setStyleSheet(f"color:{NEON}; font-size:13px; font-weight:bold;"
                            " letter-spacing:2px;")
        lay.addWidget(rings)

        self.ring_rows = {}
        for key, title, step, fmt, lo, hi in (
                ("advisory_nm", "Advisory radius", 0.5, "{:.1f} nm", 0.5, 20.0),
                ("advisory_agl_ft", "Advisory ceiling", 250.0, "{:.0f} ft AGL", 250.0, 10000.0),
                ("warning_nm", "Warning radius", 0.25, "{:.2f} nm", 0.25, 10.0),
                ("warning_agl_ft", "Warning ceiling", 100.0, "{:.0f} ft AGL", 100.0, 5000.0),
                ("alert_nm", "Alert radius", 0.1, "{:.2f} nm", 0.1, 5.0),
                ("alert_agl_ft", "Alert ceiling", 100.0, "{:.0f} ft AGL", 100.0, 3000.0)):
            row = StepperRow(title, "", getattr(s, key), step, fmt, lo, hi)
            row.changed.connect(lambda v, k=key: self._set_ring(k, v))
            lay.addWidget(row)
            self.ring_rows[key] = row
        lay.addWidget(_divider())

        save_row = QHBoxLayout()
        self.save_btn = QPushButton("SAVE TO DISK")
        self.save_btn.setMinimumHeight(52)
        self.save_btn.setStyleSheet(ACTION_BTN)
        self.save_btn.setFocusPolicy(Qt.NoFocus)
        self.save_btn.clicked.connect(self._save)
        save_row.addWidget(self.save_btn)
        save_row.addStretch()
        lay.addLayout(save_row)

        self.status = QLabel("Changes apply immediately. Save to keep them "
                             "across a restart.")
        self.status.setStyleSheet(HINT_CSS)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        lay.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll)
        self._refresh_auto_status()
        self._refresh_toggles()

    # ---------- handlers: edit the live settings object ----------

    def _on_altimeter(self, v: float):
        self.monitor.settings.altimeter_inhg = v
        self._dirty()

    def _on_elevation(self, v: float):
        self.monitor.settings.site_elev_ft = v
        self._dirty()

    def _toggle_alerts(self):
        self.monitor.settings.enabled = not self.monitor.settings.enabled
        self._refresh_toggles()
        self._dirty()

    def _toggle_sound(self):
        self.monitor.settings.sound = not self.monitor.settings.sound
        self._refresh_toggles()
        self._dirty()

    def _set_ring(self, key: str, value: float):
        setattr(self.monitor.settings, key, value)
        self._dirty()

    def _toggle_auto_altimeter(self):
        s = self.monitor.settings
        s.auto_altimeter = not s.auto_altimeter
        self._refresh_toggles()
        self._dirty()

    def _toggle_auto_elevation(self):
        s = self.monitor.settings
        s.auto_site_elev = not s.auto_site_elev
        self._refresh_toggles()
        self._dirty()

    def note_auto_altimeter(self, inhg: float, samples: int):
        """Called when the calibrator derives a setting from traffic."""
        if self.monitor.settings.auto_altimeter:
            self.altimeter.set_value(inhg)
        self._auto_alt_text = (f"altimeter {inhg:.2f} from {samples} aircraft")
        self._refresh_auto_status()

    def note_auto_elevation(self, elev_ft: float):
        if self.monitor.settings.auto_site_elev:
            self.elevation.set_value(round(elev_ft))
        self._auto_elev_text = f"elevation {elev_ft:.0f} ft from GPS"
        self._refresh_auto_status()

    def _refresh_auto_status(self):
        parts = [t for t in (getattr(self, "_auto_alt_text", None),
                             getattr(self, "_auto_elev_text", None)) if t]
        self.auto_status.setText(
            "   |   ".join(parts) if parts
            else "Auto-calibration waiting: needs a 3D GPS fix and traffic "
                 "reporting both barometric and geometric altitude.")

    def _refresh_toggles(self):
        s = self.monitor.settings
        self.alerts_btn.setText("ALERTS: ON" if s.enabled else "ALERTS: OFF")
        self.alerts_btn.setChecked(s.enabled)
        self.sound_btn.setText("SOUND: ON" if s.sound else "SOUND: MUTED")
        self.sound_btn.setChecked(s.sound)
        self.auto_alt_btn.setText(
            "ALTIMETER: AUTO" if s.auto_altimeter else "ALTIMETER: MANUAL")
        self.auto_alt_btn.setChecked(s.auto_altimeter)
        self.auto_elev_btn.setText(
            "ELEVATION: AUTO" if s.auto_site_elev else "ELEVATION: MANUAL")
        self.auto_elev_btn.setChecked(s.auto_site_elev)
        # manual steppers are pointless while auto is overwriting them
        self.altimeter.set_locked(s.auto_altimeter)
        self.elevation.set_locked(s.auto_site_elev)

    def _dirty(self):
        self.status.setText("Unsaved. Changes are live now but will revert "
                            "on restart unless you save.")
        self.status.setStyleSheet(f"color:{AMBER}; font-size:11px;")

    def _save(self):
        if save_settings(self.monitor.settings):
            self.status.setText("Saved to alerts.json.")
            self.status.setStyleSheet(HINT_CSS)
        else:
            # Most likely the overlay filesystem, or a root-owned file.
            self.status.setText(
                "COULD NOT SAVE. The filesystem is read-only (overlay FS "
                "enabled) or alerts.json is owned by another user. Settings "
                "stay active for this session only.")
            self.status.setStyleSheet("color:#ff6a6a; font-size:11px;")
