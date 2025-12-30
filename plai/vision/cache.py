"""On-disk cache utilities for pose/detection outputs.

This module provides a lightweight JSONL cache keyed by (video hash, pose
config cache key) to avoid re-running pose extraction when inputs are
unchanged. The cache format is intentionally simple to ease inspection and
debugging during Phase 0.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator, List

from plai.config import PoseConfig


@dataclass(frozen=True)
class PoseLandmark:
    """Single pose landmark with visibility score."""

    x: float
    y: float
    z: float
    visibility: float


@dataclass(frozen=True)
class PoseFrame:
    """Pose data for a single frame."""

    frame_index: int
    timestamp: float
    landmarks: List[PoseLandmark]
    score: float | None = None


def video_sha256(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Compute a deterministic hash for the video to key caches."""

    sha = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def cache_filename(video_hash: str, pose_config: PoseConfig) -> str:
    """Build a cache filename using video hash and pose config cache key."""
    return f"{video_hash}_{pose_config.cache_key()}.jsonl"


def cache_path(cache_dir: Path, video_path: Path, pose_config: PoseConfig) -> Path:
    """Return the path for the cache file without creating it."""
    return cache_dir / cache_filename(video_sha256(video_path), pose_config)


def _frame_to_json(frame: PoseFrame) -> str:
    payload = {
        "frame_index": frame.frame_index,
        "timestamp": frame.timestamp,
        "score": frame.score,
        "landmarks": [asdict(lm) for lm in frame.landmarks],
    }
    return json.dumps(payload)


def _frame_from_obj(obj: dict) -> PoseFrame:
    landmarks = [PoseLandmark(**lm) for lm in obj["landmarks"]]
    return PoseFrame(
        frame_index=obj["frame_index"],
        timestamp=obj["timestamp"],
        landmarks=landmarks,
        score=obj.get("score"),
    )


def save_pose_frames(
    cache_file: Path, frames: Iterable[PoseFrame], *, overwrite: bool = True
) -> Path:
    """Write pose frames to a JSONL cache file.

    Args:
        cache_file: Destination path for the JSONL file.
        frames: Iterable of PoseFrame instances.
        overwrite: Whether to overwrite an existing file.
    """

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    if cache_file.exists() and not overwrite:
        raise FileExistsError(f"Cache already exists: {cache_file}")

    with cache_file.open("w", encoding="utf-8") as fh:
        for frame in frames:
            fh.write(_frame_to_json(frame))
            fh.write("\n")
    return cache_file


def load_pose_frames(cache_file: Path) -> Iterator[PoseFrame]:
    """Read pose frames from a JSONL cache file."""
    with cache_file.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            yield _frame_from_obj(json.loads(line))
