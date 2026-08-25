"""Fake ADS-B feed for testing without an SDR.

Listens on port 30003 and streams SBS-format messages for a handful of
simulated aircraft flying near your home coordinates. Run this, then
start adsb-scope pointed at localhost, and the scope populates.

Usage:
    python tools/fake_feed.py [--lat 39.9626] [--lon -76.7277] [--n 6]
"""
import argparse
import math
import random
import socket
import time

NM_PER_DEG_LAT = 60.0


class FakePlane:
    def __init__(self, i, home_lat, home_lon):
        self.hex_id = f"a{random.randint(0x10000, 0xFFFFF):05x}"
        self.callsign = random.choice(["UAL", "DAL", "AAL", "SWA", "JBU", "N"]) + str(random.randint(100, 9999))
        bearing = random.uniform(0, 360)
        dist = random.uniform(5, 70)
        self.lat = home_lat + (dist / NM_PER_DEG_LAT) * math.cos(math.radians(bearing))
        self.lon = home_lon + (dist / (NM_PER_DEG_LAT * math.cos(math.radians(home_lat)))) * math.sin(math.radians(bearing))
        self.track = random.uniform(0, 360)
        self.gs = random.randint(140, 480)
        self.alt = random.choice([3500, 8000, 17000, 24000, 33000, 37000])

    def step(self, dt):
        d_nm = self.gs * dt / 3600.0
        self.lat += (d_nm / NM_PER_DEG_LAT) * math.cos(math.radians(self.track))
        self.lon += (d_nm / (NM_PER_DEG_LAT * math.cos(math.radians(self.lat)))) * math.sin(math.radians(self.track))
        self.track = (self.track + random.uniform(-1.5, 1.5)) % 360

    def sbs_lines(self):
        ts = time.strftime("%Y/%m/%d,%H:%M:%S.000")
        yield f"MSG,1,1,1,{self.hex_id},1,{ts},{ts},{self.callsign},,,,,,,,,,,,"
        yield f"MSG,3,1,1,{self.hex_id},1,{ts},{ts},,{self.alt},,,{self.lat:.5f},{self.lon:.5f},,,,,,,"
        yield f"MSG,4,1,1,{self.hex_id},1,{ts},{ts},,,{self.gs},{self.track:.1f},,,,,,,,,"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=39.9626)
    ap.add_argument("--lon", type=float, default=-76.7277)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--port", type=int, default=30003)
    args = ap.parse_args()

    planes = [FakePlane(i, args.lat, args.lon) for i in range(args.n)]
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", args.port))
    server.listen(1)
    print(f"fake feed on 127.0.0.1:{args.port}, {args.n} aircraft near "
          f"{args.lat:.4f},{args.lon:.4f}  (Ctrl+C to stop)")
    while True:
        conn, addr = server.accept()
        print(f"client connected: {addr}")
        try:
            while True:
                for pl in planes:
                    pl.step(1.0)
                    for line in pl.sbs_lines():
                        conn.sendall((line + "\n").encode())
                time.sleep(1.0)
        except (BrokenPipeError, ConnectionResetError):
            print("client disconnected, waiting for next")


if __name__ == "__main__":
    main()
