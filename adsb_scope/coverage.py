"""Antenna coverage tracker: maximum reception range per compass bearing.

This is the measurement half of the project. Every position report
updates the max range seen in that bearing bucket; the polar outline of
those maxima is your antenna's real-world coverage pattern. Build a new
antenna, reset, log for a day, compare.
"""
import json
import time
from pathlib import Path
from threading import Lock

COVERAGE_PATH = Path("coverage.json")


class CoverageTracker:
    def __init__(self, bucket_deg: int = 5):
        self.bucket_deg = bucket_deg
        self.n_buckets = 360 // bucket_deg
        self.max_range_nm = [0.0] * self.n_buckets
        self.started = time.time()
        self.total_positions = 0
        self._lock = Lock()
        self._load()

    def record(self, bearing_deg: float, dist_nm: float):
        idx = int(bearing_deg % 360) // self.bucket_deg
        with self._lock:
            if dist_nm > self.max_range_nm[idx]:
                self.max_range_nm[idx] = dist_nm
            self.total_positions += 1

    def snapshot(self) -> list[float]:
        with self._lock:
            return list(self.max_range_nm)

    def reset(self):
        with self._lock:
            self.max_range_nm = [0.0] * self.n_buckets
            self.total_positions = 0
            self.started = time.time()
        self.save()

    def save(self):
        with self._lock:
            data = {
                "bucket_deg": self.bucket_deg,
                "max_range_nm": self.max_range_nm,
                "started": self.started,
                "total_positions": self.total_positions,
            }
        COVERAGE_PATH.write_text(json.dumps(data, indent=2))

    def _load(self):
        if not COVERAGE_PATH.exists():
            return
        try:
            data = json.loads(COVERAGE_PATH.read_text())
            if data.get("bucket_deg") == self.bucket_deg:
                self.max_range_nm = list(map(float, data["max_range_nm"]))
                self.started = data.get("started", self.started)
                self.total_positions = data.get("total_positions", 0)
        except (json.JSONDecodeError, KeyError, ValueError):
            pass  # corrupt file: start fresh
