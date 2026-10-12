"""GPS position from gpsd, so the deck knows where it is anywhere on earth.

gpsd (the standard Linux GPS daemon) speaks JSON over TCP port 2947.
We send a WATCH command and read TPV (time-position-velocity) reports.
A 2D fix or better updates the home position; no external dependencies.
"""
import json
import socket
import threading
import time
from typing import Callable, Optional

WATCH_CMD = b'?WATCH={"enable":true,"json":true}\n'


M_TO_FT = 3.28084


def parse_gpsd_line(line: str) -> Optional[tuple[float, float]]:
    """Return (lat, lon) from a TPV report with at least a 2D fix, else None."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    if obj.get("class") != "TPV" or obj.get("mode", 0) < 2:
        return None
    lat, lon = obj.get("lat"), obj.get("lon")
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def parse_gpsd_altitude(line: str) -> Optional[tuple[float, Optional[float]]]:
    """Return (site elevation ft MSL, geoid separation ft) from a TPV report.

    Needs a 3D fix (mode 3): a 2D fix carries no altitude at all. gpsd
    reports metres; altMSL is orthometric height, altHAE is height above
    the WGS84 ellipsoid, and geoidSep is the difference. The separation is
    returned because the barometric auto-calibration needs it to compare
    an aircraft's geometric altitude against its pressure altitude.
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    if obj.get("class") != "TPV" or obj.get("mode", 0) < 3:
        return None

    alt_msl = obj.get("altMSL", obj.get("alt"))
    geoid_sep = obj.get("geoidSep")
    if alt_msl is None:
        hae = obj.get("altHAE")
        if hae is None or geoid_sep is None:
            return None
        alt_msl = hae - geoid_sep
    return (float(alt_msl) * M_TO_FT,
            float(geoid_sep) * M_TO_FT if geoid_sep is not None else None)


class GPSClient(threading.Thread):
    """Background thread: read gpsd, push fixes to a callback."""

    daemon = True

    def __init__(self, on_fix: Callable[[float, float], None],
                 host: str = "127.0.0.1", port: int = 2947,
                 on_altitude: Optional[Callable[[float, Optional[float]], None]] = None):
        super().__init__(name="gps-client")
        self.on_fix = on_fix
        self.on_altitude = on_altitude
        self.host = host
        self.port = port
        self.has_fix = False
        self.has_3d = False
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            try:
                with socket.create_connection((self.host, self.port), timeout=5) as sock:
                    sock.settimeout(5)
                    sock.sendall(WATCH_CMD)
                    buf = b""
                    while not self._stop.is_set():
                        try:
                            chunk = sock.recv(4096)
                        except socket.timeout:
                            continue
                        if not chunk:
                            break
                        buf += chunk
                        while b"\n" in buf:
                            raw, buf = buf.split(b"\n", 1)
                            text = raw.decode("ascii", errors="replace")
                            fix = parse_gpsd_line(text)
                            if fix:
                                self.has_fix = True
                                self.on_fix(*fix)
                            if self.on_altitude is not None:
                                alt = parse_gpsd_altitude(text)
                                if alt:
                                    self.has_3d = True
                                    self.on_altitude(*alt)
            except OSError:
                pass
            self.has_fix = False
            self.has_3d = False
            if not self._stop.is_set():
                time.sleep(3)
