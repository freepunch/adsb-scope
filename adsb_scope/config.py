"""App configuration: loads config.json beside the working directory,
creating it with defaults on first run so it's easy to find and edit."""
import json
from dataclasses import dataclass, asdict
from pathlib import Path

CONFIG_PATH = Path("config.json")


@dataclass
class Config:
    host: str = "127.0.0.1"      # machine running dump1090/readsb
    port: int = 30003            # SBS BaseStation text stream
    home_lat: float = 39.9626    # YOUR antenna location
    home_lon: float = -76.7277
    max_range_nm: float = 100.0  # scope radius
    stale_seconds: float = 30.0  # drop aircraft not heard for this long
    coverage_bucket_deg: int = 5 # polar coverage resolution
    gps_enabled: bool = False    # read position from gpsd (cyberdeck mode)
    fullscreen: bool = False     # start as a fullscreen kiosk


def load() -> Config:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text())
        return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
    cfg = Config()
    CONFIG_PATH.write_text(json.dumps(asdict(cfg), indent=2))
    return cfg
