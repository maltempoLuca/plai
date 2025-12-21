"""Rotation and normalization helpers.

Responsibilities:
- Normalize rotation for analysis while preserving ability to map coordinates back.
- Provide helpers for coordinate transforms between original and normalized spaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from plai.config import VideoMetadata

SUPPORTED_ROTATIONS = {0, 90, 180, 270}


@dataclass(slots=True)
class NormalizedView:
    """Describes the normalized (rotation-free) view of a video."""

    width: int
    height: int
    rotation_applied: int  # degrees clockwise that were applied


def normalized_dimensions(width: int, height: int, rotation: int) -> Tuple[int, int]:
    """Return dimensions after applying rotation."""
    if rotation not in SUPPORTED_ROTATIONS:
        rotation = rotation % 360
    if rotation in (90, 270):
        return height, width
    return width, height


def normalize_metadata(meta: VideoMetadata) -> NormalizedView:
    """Produce normalized dimensions and record applied rotation."""
    n_width, n_height = normalized_dimensions(meta.width, meta.height, meta.rotation)
    return NormalizedView(width=n_width, height=n_height, rotation_applied=meta.rotation)


def map_point_to_normalized(
    x: float, y: float, orig_width: int, orig_height: int, rotation: int
) -> Tuple[float, float]:
    """Map a point (x, y) from original orientation to normalized orientation."""
    if rotation not in SUPPORTED_ROTATIONS:
        rotation = rotation % 360
    if rotation == 0:
        return x, y
    if rotation == 90:
        # 90 deg clockwise
        return y, (orig_width - 1) - x
    if rotation == 180:
        return (orig_width - 1) - x, (orig_height - 1) - y
    if rotation == 270:
        # 90 deg counter-clockwise
        return (orig_height - 1) - y, x
    return x, y


def map_point_to_original(
    x: float, y: float, orig_width: int, orig_height: int, rotation: int
) -> Tuple[float, float]:
    """Map a point from normalized orientation back to original orientation."""
    if rotation not in SUPPORTED_ROTATIONS:
        rotation = rotation % 360
    if rotation == 0:
        return x, y
    if rotation == 90:
        return (orig_width - 1) - y, x
    if rotation == 180:
        return (orig_width - 1) - x, (orig_height - 1) - y
    if rotation == 270:
        return y, (orig_height - 1) - x
    return x, y
