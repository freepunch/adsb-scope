"""Threaded TCP client for the SBS-1 'BaseStation' stream (port 30003).

Every decoder in the dump1090 family emits this: one CSV line per
decoded message. The fields we care about:

  index  meaning
  0      "MSG"
  1      transmission type (1=ident, 3=position, 4=velocity)
  4      ICAO hex address
  10     callsign        (MSG,1)
  11     altitude ft     (MSG,3)
  12     ground speed kt (MSG,4)
  13     track deg       (MSG,4)
  14     latitude        (MSG,3)
  15     longitude       (MSG,3)

Anything malformed is skipped; radio data is messy by nature.
"""
import socket
import threading
import time

from .aircraft import AircraftStore


def _to_float(s: str):
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _to_int(s: str):
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def parse_sbs_line(line: str) -> tuple[str, dict] | None:
    """Return (hex_id, fields) for a useful line, else None."""
    parts = line.strip().split(",")
    if len(parts) < 11 or parts[0] != "MSG":
        return None
    hex_id = parts[4].strip().lower()
    if not hex_id:
        return None
    msg_type = parts[1]
    fields: dict = {}
    if msg_type == "1":
        cs = parts[10].strip()
        if cs:
            fields["callsign"] = cs
    elif msg_type == "3" and len(parts) >= 16:
        fields["altitude_ft"] = _to_int(parts[11])
        fields["lat"] = _to_float(parts[14])
        fields["lon"] = _to_float(parts[15])
    elif msg_type == "4" and len(parts) >= 14:
        fields["ground_speed_kt"] = _to_int(parts[12])
        fields["track_deg"] = _to_float(parts[13])
    if not fields:
        return None
    return hex_id, fields


class SBSClient(threading.Thread):
    """Background thread: connect, read lines, feed the store, reconnect."""

    daemon = True

    def __init__(self, host: str, port: int, store: AircraftStore):
        super().__init__(name="sbs-client")
        self.host = host
        self.port = port
        self.store = store
        self.connected = False
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            try:
                with socket.create_connection((self.host, self.port), timeout=5) as sock:
                    sock.settimeout(5)
                    self.connected = True
                    buf = b""
                    while not self._stop.is_set():
                        try:
                            chunk = sock.recv(4096)
                        except socket.timeout:
                            continue
                        if not chunk:
                            break  # server closed; reconnect
                        buf += chunk
                        while b"\n" in buf:
                            raw, buf = buf.split(b"\n", 1)
                            parsed = parse_sbs_line(raw.decode("ascii", errors="replace"))
                            if parsed:
                                self.store.update(parsed[0], **parsed[1])
            except OSError:
                pass
            self.connected = False
            if not self._stop.is_set():
                time.sleep(2)  # back off before reconnecting
