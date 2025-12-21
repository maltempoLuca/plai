"""Shared configuration and data models for the analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

Lift = Literal["squat", "bench", "deadlift", "unknown"]


@dataclass(slots=True)
class VideoSpec:
    """Description of an input video."""

    path: Path
    lift: Lift = "unknown"
    label: Optional[str] = None  # optional overlay label


@dataclass(slots=True)
class PoseConfig:
    """Configuration for pose extraction."""

    backend: Literal["mediapipe", "mmpose"] = "mediapipe"
    model_name: str = "mediapipe_pose_full"
    min_confidence: float = 0.5
    max_people: int = 1
    # Future extensions: device selection, mmpose config checkpoint, image size.


@dataclass(slots=True)
class VideoMetadata:
    """Basic video metadata sourced from ffprobe."""

    width: int
    height: int
    fps: float
    duration: float
    rotation: int


@dataclass(slots=True)
class AnalysisResult:
    """Placeholder for analysis outputs (will be expanded in later steps)."""

    lift: Lift
    movement_start: Optional[float] = None
    # Future: events, reps, overlay specs, QC flags.
