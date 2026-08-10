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


class GPSClient(threading.Thread):
    """Background thread: read gpsd, push fixes to a callback."""

    daemon = True

    def __init__(self, on_fix: Callable[[float, float], None],
                 host: str = "127.0.0.1", port: int = 2947):
        super().__init__(name="gps-client")
        self.on_fix = on_fix
        self.host = host
        self.port = port
        self.has_fix = False
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
                            fix = parse_gpsd_line(raw.decode("ascii", errors="replace"))
                            if fix:
                                self.has_fix = True
                                self.on_fix(*fix)
            except OSError:
                pass
            self.has_fix = False
            if not self._stop.is_set():
                time.sleep(3)
