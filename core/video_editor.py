#!/usr/bin/env python3
"""
Video editing pipeline for powerlifting video analysis.

Aligns multiple portrait MP4 clips on a shared timeline, freezes starting frames,
draws optional labels, and exports a side-by-side comparison via FFmpeg.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
from enum import Enum
from core.ffmpeg_lib import (
    build_filter_complex,
    build_ffmpeg_cmd,
    format_fps_value,
)

FFMPEG_EXE = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE_EXE = r"C:\ffmpeg\bin\ffprobe.exe"

class StartMode(str, Enum):
    """Defines how `starts[]` values are interpreted."""
    SYNC = "sync"
    TIMELINE = "timeline"


@dataclass(frozen=True)
class SideBySideComparisonRequest:
    """
    Defines a side-by-side comparison render job.

    Attributes:
        videos: Input MP4 paths in left-to-right order.
        starts: Per-video start values. Meaning depends on `start_mode`:
            - "sync": each value is an in-clip timestamp (seconds) that should align across videos.
            - "timeline": each value is the absolute timeline start time (seconds) for the clip.
        start_mode: "sync" (default) or "timeline".
        labels: Optional per-video labels. Provide None for no labels, or a list of length N (use ""/None to skip).
        output: Output MP4 path.

        height: Output height (per tile) before stacking.
        fps: Output fps. If None, derived from inputs (or defaults to 30).
        audio: "none" | "mix" | "videoN" (1-based).
        font: Optional font file path for drawtext.
        crf: libx264 CRF.
        preset: libx264 preset.
        overwrite: Overwrite output file if exists.
        print_ffmpeg_cmd: Print ffmpeg command + filtergraph before running.
    """
    videos: List[str] = field(default_factory=list)
    starts: List[float] = field(default_factory=list)

    start_mode: StartMode = StartMode.SYNC
    labels: Optional[List[Optional[str]]] = None
    output: str = ""

    height: int = 1080
    fps: Optional[float] = None
    audio: str = "none"
    font: Optional[str] = None
    crf: int = 20
    preset: str = "medium"
    overwrite: bool = False
    print_ffmpeg_cmd: bool = False


@dataclass(frozen=True)
class MediaInfo:
    duration: float
    fps: Optional[float]
    has_audio: bool


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def require_tool(tool_name: str) -> str:
    tool_path = shutil.which(tool_name)
    if not tool_path:
        raise RuntimeError(
            f"Required tool '{tool_name}' not found on PATH.\n"
            f"Install FFmpeg (must include '{tool_name}') and ensure it's available on your PATH."
        )
    return tool_path


def parse_fraction(frac: str) -> Optional[float]:
    if not frac or frac in ("0/0", "N/A"):
        return None
    try:
        if "/" in frac:
            num_s, den_s = frac.split("/", 1)
            num = float(num_s)
            den = float(den_s)
            if den == 0:
                return None
            return num / den
        return float(frac)
    except Exception:
        return None


def fmt_time(seconds: float) -> str:
    if seconds < 0:
        raise ValueError("Time values must be non-negative.")
    s = f"{seconds:.6f}"
    s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def format_fps_value(fps: float) -> str:
    if fps <= 0 or math.isnan(fps) or math.isinf(fps):
        return "30"
    nearest = round(fps)
    if abs(fps - nearest) < 0.05 and nearest >= 1:
        return str(int(nearest))
    return f"{fps:.3f}".rstrip("0").rstrip(".")


def escape_drawtext_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\", r"\\")
    text = text.replace("'", r"\'")
    text = text.replace(":", r"\:")
    text = text.replace(",", r"\,")
    text = text.replace("%", r"\%")
    text = text.replace("[", r"\[")
    text = text.replace("]", r"\]")
    text = text.replace("\n", r"\n")
    return text


def escape_ffmpeg_filter_path(path_str: str) -> str:
    p = Path(path_str).expanduser().resolve()
    s = p.as_posix()
    s = s.replace(":", r"\:")
    s = s.replace("'", r"\'")
    return s


def probe_media(path: Path, ffprobe_bin: str) -> MediaInfo:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed for: {path}\n"
            f"Command: {' '.join(cmd)}\n"
            f"ffprobe stderr:\n{proc.stderr}"
        )

    data = json.loads(proc.stdout)
    streams = data.get("streams", []) or []
    if not streams:
        raise RuntimeError(f"No streams found in file: {path}")

    video_stream = None
    has_audio = False
    fps = None

    for s in streams:
        if s.get("codec_type") == "video" and video_stream is None:
            video_stream = s
            fps = parse_fraction(s.get("avg_frame_rate") or s.get("r_frame_rate") or "")
        if s.get("codec_type") == "audio":
            has_audio = True

    if video_stream is None:
        raise RuntimeError(f"No video stream found in file: {path}")

    duration: Optional[float] = None
    fmt = data.get("format") or {}
    dur_str = fmt.get("duration")
    if dur_str and dur_str != "N/A":
        try:
            duration = float(dur_str)
        except ValueError:
            duration = None

    if not duration or duration <= 0:
        best = 0.0
        for s in streams:
            ds = s.get("duration")
            if ds and ds != "N/A":
                try:
                    best = max(best, float(ds))
                except ValueError:
                    pass
        duration = best if best > 0 else None

    if duration is None or duration <= 0:
        raise RuntimeError(
            f"Could not determine a valid duration for: {path}\n"
            f"Try remuxing it (e.g., ffmpeg -i in.mp4 -c copy out.mp4) and re-run."
        )

    return MediaInfo(duration=duration, fps=fps, has_audio=has_audio)


def build_drawtext_filter(label: str, height: int, fontfile: Optional[str]) -> str:
    label_escaped = escape_drawtext_text(label)

    fontsize = max(14, int(round(height * 0.05)))
    bottom_margin = max(8, int(round(height * 0.03)))
    boxborder = max(4, int(round(height * 0.015)))

    opts: List[str] = []
    if fontfile:
        font_escaped = escape_ffmpeg_filter_path(fontfile)
        opts.append(f"fontfile='{font_escaped}'")

    opts += [
        f"text='{label_escaped}'",
        f"fontsize={fontsize}",
        "fontcolor=white",
        "box=1",
        "boxcolor=black@0.5",
        f"boxborderw={boxborder}",
        "x=(w-text_w)/2",
        f"y=h-text_h-{bottom_margin}",
    ]
    return "drawtext=" + ":".join(opts)


def parse_audio_mode(audio: str, num_inputs: int) -> Tuple[str, Optional[int]]:
    a = (audio or "none").strip().lower()
    if a in ("none", ""):
        return "none", None
    if a == "mix":
        return "mix", None
    if a.startswith("video"):
        suffix = a[len("video"):]
        if not suffix.isdigit():
            raise ValueError("Invalid --audio value. Use: none | mix | videoN (e.g., video1, video3).")
        n = int(suffix)
        idx = n - 1
        if idx < 0 or idx >= num_inputs:
            raise ValueError(f"--audio {audio} is out of range for {num_inputs} input(s).")
        return "single", idx
    raise ValueError("Invalid --audio value. Use: none | mix | videoN (e.g., video1, video3).")


def compute_timeline_starts(starts: List[float], start_mode: StartMode) -> Tuple[List[float], float]:
    match start_mode:
        case StartMode.TIMELINE:
            return list(starts), 0.0

        case StartMode.SYNC:
            t_sync = max(starts)
            timeline_starts = [t_sync - s for s in starts]
            return timeline_starts, t_sync

        case _:
            raise ValueError(f"Unsupported start_mode: {start_mode!r}")


def validate_request(req: SideBySideComparisonRequest) -> None:
    """
    Validates a comparison request.

    Args:
        req: Job specification to validate.

    Returns:
        None. Raises an exception if the request is invalid.
    """
    if req.height <= 0:
        raise ValueError("--height must be a positive integer.")
    if req.fps is not None and req.fps <= 0:
        raise ValueError("--fps must be positive if provided.")
    if req.crf < 0 or req.crf > 51:
        raise ValueError("--crf must be between 0 and 51 for libx264.")
    if req.font is not None and not Path(req.font).expanduser().exists():
        raise FileNotFoundError(f"Font file not found: {req.font}")

    if not req.videos or not req.starts:
        raise ValueError("You must provide --video and --start (repeated), plus --output.")
    if len(req.videos) < 2:
        raise ValueError("Provide at least 2 videos for side-by-side output.")
    if len(req.videos) != len(req.starts):
        raise ValueError(
            f"Count mismatch: got {len(req.videos)} --video but {len(req.starts)} --start.\n"
            f"Provide one --start for every --video, in the same order."
        )

    for s in req.starts:
        if math.isnan(s) or math.isinf(s):
            raise ValueError("All --start values must be finite numbers.")
        if s < 0:
            raise ValueError("All --start values must be >= 0 (they are timestamps in seconds).")

    if req.labels is not None and len(req.labels) != len(req.videos):
        raise ValueError(
            f"Count mismatch: got {len(req.labels)} --label but {len(req.videos)} videos.\n"
            f"Provide 0 labels OR exactly one label per video.\n"
            f"Tip: use --label \"\" to skip a label for a specific video."
        )

    out_path = Path(req.output).expanduser()
    if out_path.exists() and not req.overwrite:
        raise FileExistsError(
            f"Output file already exists: {out_path}\n"
            f"Use --overwrite to replace it, or choose a different --output path."
        )
    if out_path.parent and not out_path.parent.exists():
        raise FileNotFoundError(
            f"Output directory does not exist: {out_path.parent}\n"
            f"Create it first, or choose a different --output path."
        )


def export_side_by_side_comparison(req: SideBySideComparisonRequest) -> int:
    """
    Exports a side-by-side comparison video (MP4) using FFmpeg.

    Alignment behavior:
      - start_mode="sync": each `starts[i]` is a sync timestamp inside clip i. All sync moments align together.
      - start_mode="timeline": each `starts[i]` is the absolute timeline start time for clip i.

    Rendering behavior:
      - Frames before a clip's timeline start are frozen (first frame cloned) until the clip begins.
      - Optional per-clip labels can be drawn using drawtext.
      - Output is stacked horizontally (hstack) and converted to a fixed output fps.

    Args:
        req: Render job definition (inputs, alignment, output path, encoding options).

    Returns:
        Exit code: 0 on success; non-zero on failure.
        (On failure, the error is printed to stderr and 2 is returned.)
    """
    try:
        validate_request(req)

        ffmpeg_bin = FFMPEG_EXE if FFMPEG_EXE else require_tool("ffmpeg")
        ffprobe_bin = FFPROBE_EXE if FFPROBE_EXE else require_tool("ffprobe")

        if not Path(ffmpeg_bin).exists():
            raise RuntimeError(f"FFmpeg not found at: {ffmpeg_bin}")
        if not Path(ffprobe_bin).exists():
            raise RuntimeError(f"FFprobe not found at: {ffprobe_bin}")

        video_paths = [Path(v).expanduser() for v in req.videos]
        out_path = Path(req.output).expanduser()

        infos: List[MediaInfo] = [probe_media(p, ffprobe_bin) for p in video_paths]

        if req.start_mode == "sync":
            for i, (sync_t, info) in enumerate(zip(req.starts, infos), start=1):
                if sync_t > info.duration + 0.25:
                    raise ValueError(
                        f"--start for video{i} is {sync_t:.3f}s but clip duration is {info.duration:.3f}s.\n"
                        f"In sync mode, --start must be inside the clip."
                    )

        timeline_starts, t_sync = compute_timeline_starts(req.starts, req.start_mode)
        total_duration = max(timeline_starts[i] + infos[i].duration for i in range(len(infos)))

        if req.fps is not None:
            fps_out = req.fps
        else:
            candidates = [mi.fps for mi in infos if mi.fps and mi.fps > 0]
            fps_out = max(candidates) if candidates else 30.0
        fps_str = format_fps_value(fps_out)

        if req.labels is None:
            labels = [None] * len(video_paths)
        else:
            labels = [lbl for lbl in req.labels]

        has_audio_flags = [mi.has_audio for mi in infos]

        filter_complex, has_audio_out = build_filter_complex(
            height=req.height,
            fps_str=fps_str,
            timeline_starts=timeline_starts,
            total=total_duration,
            labels=labels,
            fontfile=req.font,
            audio=req.audio,
            has_audio=has_audio_flags,
            warn=eprint,
        )

        cmd = build_ffmpeg_cmd(
            ffmpeg_bin=ffmpeg_bin,
            videos=video_paths,
            output=out_path,
            filter_complex=filter_complex,
            total_duration=total_duration,
            crf=req.crf,
            preset=req.preset,
            include_audio=has_audio_out,
            overwrite=req.overwrite,
        )

        if req.print_ffmpeg_cmd:
            eprint("FFmpeg command:")
            eprint(" ".join(cmd))
            eprint("\nFilter graph:")
            eprint(filter_complex)
            eprint("")

        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            return proc.returncode

        print(f"Done. Wrote: {out_path}")
        if req.start_mode == "sync":
            print(
                f"Sync moment occurs at timeline t={t_sync:.3f}s. Timeline starts: {', '.join(f'{x:.3f}' for x in timeline_starts)}"
            )
        return 0

    except Exception as ex:
        eprint(f"Error: {ex}")
        return 2
