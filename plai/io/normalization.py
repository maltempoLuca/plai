"""Rotation and normalization helpers.

The ingest step surfaces rotation metadata via :class:`plai.config.VideoSpec`.
This module provides lightweight coordinate transforms to work in a consistent
upright space for analysis while retaining the ability to map results back to
the original orientation for FFmpeg composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from plai.config import VideoSpec

SUPPORTED_ROTATIONS = {0, 90, 180, 270}


def _assert_supported_rotation(rotation: int) -> None:
    if rotation not in SUPPORTED_ROTATIONS:
        raise ValueError(f"Unsupported rotation: {rotation}. Expected one of {SUPPORTED_ROTATIONS}.")


@dataclass(frozen=True)
class RotationTransform:
    """Bidirectional mapping between original and normalized coordinates.

    Normalized space corresponds to applying the inverse of the rotation
    reported in metadata (i.e., upright for analysis). Coordinates are pixel
    indices (x, y) in integer space.
    """

    width: int
    height: int
    rotation: int

    @classmethod
    def from_video_spec(cls, spec: VideoSpec) -> "RotationTransform":
        return cls(width=spec.width, height=spec.height, rotation=spec.rotation)

    @property
    def normalized_size(self) -> Tuple[int, int]:
        """Return (width, height) after normalizing rotation."""
        _assert_supported_rotation(self.rotation)
        if self.rotation in {90, 270}:
            return (self.height, self.width)
        return (self.width, self.height)

    def to_normalized(self, point: Tuple[int, int]) -> Tuple[int, int]:
        """Map a point from original orientation to upright normalized space."""
        _assert_supported_rotation(self.rotation)
        x, y = point
        if self.rotation == 0:
            return (x, y)
        if self.rotation == 90:
            return (y, self.width - 1 - x)
        if self.rotation == 180:
            return (self.width - 1 - x, self.height - 1 - y)
        # rotation == 270
        return (self.height - 1 - y, x)

    def to_original(self, point: Tuple[int, int]) -> Tuple[int, int]:
        """Map a point from normalized space back to the original orientation."""
        _assert_supported_rotation(self.rotation)
        x, y = point
        if self.rotation == 0:
            return (x, y)
        if self.rotation == 90:
            return (self.width - 1 - y, x)
        if self.rotation == 180:
            return (self.width - 1 - x, self.height - 1 - y)
        # rotation == 270
        return (y, self.height - 1 - x)

    def map_points_to_normalized(self, points: Iterable[Tuple[int, int]]) -> Tuple[Tuple[int, int], ...]:
        """Vectorized convenience wrapper to normalize a list/tuple of points."""
        return tuple(self.to_normalized(p) for p in points)

    def map_points_to_original(self, points: Iterable[Tuple[int, int]]) -> Tuple[Tuple[int, int], ...]:
        """Vectorized convenience wrapper to restore a list/tuple of points."""
        return tuple(self.to_original(p) for p in points)
