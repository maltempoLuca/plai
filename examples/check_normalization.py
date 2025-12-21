"""Sanity checks for rotation normalization helpers."""

import sys
from pathlib import Path

# Allow running this script directly without installing the package.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from plai.io.normalization import (  # noqa: E402
    map_point_to_normalized,
    map_point_to_original,
    normalized_dimensions,
)


def run_examples() -> None:
    w, h = 4, 2
    rotation = 90
    n_w, n_h = normalized_dimensions(w, h, rotation)
    print(f"orig=({w}x{h}) rotation={rotation} -> normalized=({n_w}x{n_h})")

    sample_points = [(0, 0), (1, 0), (3, 1)]
    for (x, y) in sample_points:
        nx, ny = map_point_to_normalized(x, y, w, h, rotation)
        rx, ry = map_point_to_original(nx, ny, w, h, rotation)
        print(f"orig ({x},{y}) -> norm ({nx},{ny}) -> back ({rx},{ry})")

    # Expect roundtrip equality
    for (x, y) in sample_points:
        nx, ny = map_point_to_normalized(x, y, w, h, rotation)
        rx, ry = map_point_to_original(nx, ny, w, h, rotation)
        assert (round(rx, 6), round(ry, 6)) == (x, y), "Roundtrip mismatch"

    print("Roundtrip checks passed.")


if __name__ == "__main__":
    run_examples()
