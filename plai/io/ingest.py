"""Video ingest and metadata helpers for baseline analysis.

This module focuses on light-weight ffprobe wrappers and timestamp helpers.
Frame decoding will be implemented in a later Phase 0 step.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional, Tuple

from plai.config import VideoSpec

FFPROBE_CMD = (
    "ffprobe",
    "-v",
    "error",
    "-print_format",
    "json",
    "-show_streams",
    "-show_format",
)


class FFprobeError(RuntimeError):
    """Raised when ffprobe is unavailable or returns invalid data."""


def _parse_rational(value: str) -> float:
    """Convert ffprobe rational strings (e.g., `30000/1001`) to float."""
    if not value or value == "0/0":
        return 0.0
    if "/" in value:
        num, denom = value.split("/", 1)
        denom_value = float(denom)
        if denom_value == 0:
            return 0.0
        return float(num) / denom_value
    return float(value)


def _rotation_from_stream(stream: Dict) -> int:
    tags = stream.get("tags") or {}
    if "rotate" in tags:
        try:
            rotation = int(tags["rotate"])
            return rotation % 360
        except ValueError:
            pass
    for side_data in stream.get("side_data_list", []):
        if side_data.get("rotation") is not None:
            try:
                return int(side_data["rotation"]) % 360
            except (TypeError, ValueError):
                continue
    return 0


def _fps_from_stream(stream: Dict) -> float:
    for key in ("avg_frame_rate", "r_frame_rate"):
        rate = stream.get(key)
        if rate:
            fps = _parse_rational(rate)
            if fps > 0:
                return fps
    return 0.0


def _frame_count_from_stream(stream: Dict) -> Optional[int]:
    nb_frames = stream.get("nb_frames")
    try:
        return int(nb_frames) if nb_frames is not None else None
    except (TypeError, ValueError):
        return None


def _duration_from_format(format_section: Dict) -> float:
    duration = format_section.get("duration")
    try:
        return float(duration) if duration is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _select_video_stream(streams: Iterable[Dict]) -> Dict:
    for stream in streams:
        if stream.get("codec_type") == "video":
            return stream
    raise FFprobeError("ffprobe output did not contain a video stream")


def probe_video(video_path: str | Path) -> VideoSpec:
    """Probe a video with ffprobe to build a :class:`VideoSpec` instance.

    Args:
        video_path: Path to the video file.

    Returns:
        VideoSpec with core metadata used downstream.

    Raises:
        FFprobeError: if ffprobe is not available or returns invalid data.
    """

    path = Path(video_path)
    if not path.exists():
        raise FFprobeError(f"Video does not exist: {video_path}")

    try:
        output = subprocess.check_output(
            [*FFPROBE_CMD, str(path)],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError as exc:
        raise FFprobeError("ffprobe is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise FFprobeError(f"ffprobe failed: {exc.output}") from exc

    try:
        probe_data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise FFprobeError(f"Invalid ffprobe JSON: {exc}") from exc

    streams = probe_data.get("streams") or []
    format_section = probe_data.get("format") or {}
    video_stream = _select_video_stream(streams)

    rotation = _rotation_from_stream(video_stream)
    fps = _fps_from_stream(video_stream)
    frame_count = _frame_count_from_stream(video_stream)
    duration = _duration_from_format(format_section)

    try:
        width = int(video_stream["width"])
        height = int(video_stream["height"])
    except KeyError as exc:
        raise FFprobeError(f"ffprobe missing width/height: {exc}") from exc

    return VideoSpec(
        path=path,
        width=width,
        height=height,
        rotation=rotation,
        fps=fps,
        duration=duration,
        frame_count=frame_count,
    )


def iter_expected_timestamps(
    spec: VideoSpec, *, max_frames: Optional[int] = None
) -> Iterator[Tuple[int, float]]:
    """Yield (frame_index, timestamp) pairs based on fps and duration.

    This is a utility for synthetic tests and pre-flight checks; actual frame
    decoding will rely on the same mapping once implemented.
    """

    if spec.fps <= 0:
        raise ValueError("VideoSpec fps must be positive")

    total_frames = (
        spec.frame_count
        if spec.frame_count is not None
        else int(round(spec.duration * spec.fps))
    )
    if max_frames is not None:
        total_frames = min(total_frames, max_frames)

    for frame_idx in range(total_frames):
        yield frame_idx, spec.timestamp_for_frame(frame_idx)
