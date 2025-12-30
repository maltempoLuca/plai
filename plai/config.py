"""Shared configuration and data models used across the analysis pipeline."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class VideoSpec:
    """Basic video metadata used by ingest and downstream consumers.

    Attributes:
        path: Filesystem path to the source video.
        width: Pixel width as reported by ffprobe (pre-rotation).
        height: Pixel height as reported by ffprobe (pre-rotation).
        rotation: Clockwise rotation in degrees derived from metadata; expected
            to be in {0, 90, 180, 270}.
        fps: Frames per second (float) derived from avg/r_frame_rate.
        duration: Video duration in seconds.
        frame_count: Optional number of frames if ffprobe reports it.
    """

    path: Path
    width: int
    height: int
    rotation: int
    fps: float
    duration: float
    frame_count: Optional[int] = None

    @property
    def effective_size(self) -> tuple[int, int]:
        """Return (width, height) after applying rotation orientation."""
        if self.rotation in {90, 270}:
            return (self.height, self.width)
        return (self.width, self.height)

    def timestamp_for_frame(self, frame_index: int) -> float:
        """Compute the timestamp (seconds) for a zero-based frame index."""
        if frame_index < 0:
            raise ValueError("frame_index must be non-negative")
        return frame_index / self.fps

    def frame_index_at(self, timestamp: float) -> int:
        """Map a timestamp to the nearest frame index."""
        if timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        return round(timestamp * self.fps)


@dataclass(frozen=True)
class PoseConfig:
    """Configuration for MediaPipe Pose (or similar) extraction.

    This keeps the parameters centralized for easier tuning and hashing when
    populating caches. Values here are deliberately conservative for Phase 0
    CPU-only execution.
    """

    model_complexity: int = 1
    enable_segmentation: bool = False
    smooth_landmarks: bool = True
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5

    def cache_key(self) -> str:
        """Return a short string usable in cache file naming."""
        return (
            f"mc{self.model_complexity}"
            f"-seg{int(self.enable_segmentation)}"
            f"-sml{int(self.smooth_landmarks)}"
            f"-det{self.min_detection_confidence:.2f}"
            f"-trk{self.min_tracking_confidence:.2f}"
        )
