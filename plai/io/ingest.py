"""Video ingest and metadata helpers."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple

import numpy as np

from plai.config import VideoMetadata

# Binaries (override in env if needed)
FFPROBE_BIN = "ffprobe"
FFMPEG_BIN = "ffmpeg"


class FFprobeError(RuntimeError):
    """Raised when ffprobe fails or returns incomplete metadata."""


class FrameIteratorError(RuntimeError):
    """Raised when frame iteration fails."""


def _run_ffprobe(path: Path) -> Dict[str, Any]:
    """Execute ffprobe and return parsed JSON output."""
    cmd = [
        FFPROBE_BIN,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    try:
        proc = subprocess.run(
            cmd, check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - passthrough
        raise FFprobeError(f"ffprobe failed for {path}") from exc

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - passthrough
        raise FFprobeError(f"ffprobe returned invalid JSON for {path}") from exc


def _fraction_to_float(value: str) -> Optional[float]:
    """Convert ffprobe fractional strings like '30000/1001' to float."""
    if not value:
        return None
    if "/" not in value:
        try:
            return float(value)
        except ValueError:
            return None
    num, denom = value.split("/", maxsplit=1)
    try:
        denom_f = float(denom)
        if denom_f == 0:
            return None
        return float(num) / denom_f
    except ValueError:
        return None


def _get_stream(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the first video stream entry."""
    streams = metadata.get("streams", [])
    for stream in streams:
        if stream.get("codec_type") == "video":
            return stream
    return None


def _get_rotation(stream: Dict[str, Any]) -> int:
    """Extract rotation metadata (degrees)."""
    tags = stream.get("tags") or {}
    rotate_raw = tags.get("rotate") or stream.get("side_data_list", [{}])[0].get("rotation")
    try:
        return int(rotate_raw) % 360
    except (TypeError, ValueError):
        return 0


def video_metadata(path: Path) -> VideoMetadata:
    """Collect core video metadata via ffprobe."""
    info = _run_ffprobe(path)
    stream = _get_stream(info)
    if not stream:
        raise FFprobeError(f"No video stream found in {path}")

    width = int(stream.get("width", 0))
    height = int(stream.get("height", 0))
    fps = _fraction_to_float(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "")
    duration = None

    # Prefer stream duration, fallback to format duration.
    if "duration" in stream:
        try:
            duration = float(stream["duration"])
        except (TypeError, ValueError):
            duration = None
    if duration is None:
        fmt = info.get("format", {})
        try:
            duration = float(fmt.get("duration", 0.0))
        except (TypeError, ValueError):
            duration = 0.0

    rotation = _get_rotation(stream)

    if width <= 0 or height <= 0 or fps is None or math.isclose(fps, 0):
        raise FFprobeError(f"Incomplete metadata for {path}")

    return VideoMetadata(
        width=width,
        height=height,
        fps=fps,
        duration=duration,
        rotation=rotation,
    )


def _apply_rotation(frame: np.ndarray, rotation: int) -> np.ndarray:
    """Rotate frame based on metadata rotation."""
    if rotation == 0:
        return frame
    if rotation == 90:
        return np.rot90(frame, k=3)
    if rotation == 180:
        return np.rot90(frame, k=2)
    if rotation == 270:
        return np.rot90(frame, k=1)
    return frame


def iter_frames_with_timestamps(
    path: Path,
    *,
    apply_rotation: bool = True,
    max_frames: Optional[int] = None,
) -> Generator[Tuple[float, np.ndarray], None, None]:
    """Yield (timestamp_sec, RGB frame ndarray) using ffmpeg pipe.

    Notes:
    - Uses `-noautorotate` so we can control rotation via metadata.
    - Timestamps derived from frame index and stream FPS (sufficient for Phase 0).
    - For variable-FPS sources, this approximates timeline; future phases may parse pts.
    """
    meta = video_metadata(path)
    width, height = meta.width, meta.height
    rotation = meta.rotation if apply_rotation else 0
    frame_size = width * height * 3  # RGB24

    cmd = [
        FFMPEG_BIN,
        "-hide_banner",
        "-loglevel",
        "error",
        "-noautorotate",
        "-i",
        str(path),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-vsync",
        "0",
        "pipe:1",
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:  # pragma: no cover
        raise FrameIteratorError("ffmpeg binary not found") from exc

    frame_idx = 0
    assert proc.stdout is not None
    while True:
        raw = proc.stdout.read(frame_size)
        if len(raw) < frame_size:
            break

        frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        if rotation:
            frame = _apply_rotation(frame, rotation)

        timestamp = frame_idx / meta.fps
        yield (timestamp, frame)

        frame_idx += 1
        if max_frames is not None and frame_idx >= max_frames:
            break

    proc.stdout.close()
    if proc.stderr:
        proc.stderr.close()
    proc.wait()
