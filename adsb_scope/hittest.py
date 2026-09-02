"""Pure geometry helpers for the scope: plotting and click hit-testing.

Kept out of the Qt widget so it can be unit tested without a display.
"""
import math
from typing import Optional


def polar_to_xy(cx: float, cy: float, radius: float, max_range_nm: float,
                bearing: float, dist_nm: float) -> tuple[float, float]:
    """Map (bearing, distance) to screen coords, north up, y growing down."""
    frac = min(dist_nm / max_range_nm, 1.0) if max_range_nm > 0 else 0.0
    rad = math.radians(bearing)
    return (cx + radius * frac * math.sin(rad),
            cy - radius * frac * math.cos(rad))


def hit_test(click_x: float, click_y: float, positions: dict[str, tuple[float, float]],
             tolerance: float = 22.0) -> Optional[str]:
    """Return the hex_id of the nearest plotted aircraft within tolerance px.

    Tolerance is generous by default: this is a capacitive touch panel and
    a fingertip is far bigger than an aircraft glyph.
    """
    best_id, best_d2 = None, tolerance * tolerance
    for hex_id, (x, y) in positions.items():
        d2 = (x - click_x) ** 2 + (y - click_y) ** 2
        if d2 <= best_d2:
            best_id, best_d2 = hex_id, d2
    return best_id
