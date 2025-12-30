"""
FFmpeg helper utilities for building filter graphs and commands.

This module contains only FFmpeg-specific string building and escaping logic.
It is intentionally separated from higher-level video_editor orchestration logic.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Optional, Tuple


def fmt_time(seconds: float) -> str:
    """
    Formats a non-negative float timestamp for FFmpeg arguments.

    Args:
        seconds: Time in seconds (must be >= 0).

    Returns:
        A compact decimal string usable in FFmpeg (e.g. "1.5", "10", "0.033333").
    """
    if seconds < 0:
        raise ValueError("Time values must be non-negative.")
    s = f"{seconds:.6f}"
    s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def format_fps_value(fps: float) -> str:
    """
    Formats an fps value for FFmpeg, rounding near-integers and clamping invalid values.

    Args:
        fps: Frames-per-second value.

    Returns:
        A string fps suitable for FFmpeg's fps filter.
    """
    if fps <= 0 or math.isnan(fps) or math.isinf(fps):
        return "30"
    nearest = round(fps)
    if abs(fps - nearest) < 0.05 and nearest >= 1:
        return str(int(nearest))
    return f"{fps:.3f}".rstrip("0").rstrip(".")


def escape_drawtext_text(text: str) -> str:
    """
    Escapes text for FFmpeg drawtext's `text=` field.

    Args:
        text: Label text.

    Returns:
        Escaped string safe to include inside drawtext text='...'.
    """
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
    """
    Escapes a file path for use inside FFmpeg filter arguments (e.g., fontfile='...').

    Args:
        path_str: Input path string.

    Returns:
        Path normalized to POSIX and escaped for ':' and single quotes.
    """
    p = Path(path_str).expanduser().resolve()
    s = p.as_posix()
    s = s.replace(":", r"\:")
    s = s.replace("'", r"\'")
    return s


def build_drawtext_filter(label: str, height: int, fontfile: Optional[str]) -> str:
    """
    Builds a drawtext filter expression that overlays a centered label near the bottom.

    Args:
        label: Text to render.
        height: Tile height (used to scale text/box sizes).
        fontfile: Optional font file path.

    Returns:
        A drawtext=... filter string (without leading comma).
    """
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
    """
    Parses the audio selection mode.

    Args:
        audio: "none" | "mix" | "videoN" (1-based).
        num_inputs: Number of input videos.

    Returns:
        (mode, single_index)
        - mode in {"none", "mix", "single"}
        - single_index is 0-based index when mode == "single"
    """
    a = (audio or "none").strip().lower()
    if a in ("none", ""):
        return "none", None
    if a == "mix":
        return "mix", None
    if a.startswith("video"):
        suffix = a[len("video"):]
        if not suffix.isdigit():
            raise ValueError("Invalid audio value. Use: none | mix | videoN (e.g., video1, video3).")
        n = int(suffix)
        idx = n - 1
        if idx < 0 or idx >= num_inputs:
            raise ValueError(f"audio={audio} is out of range for {num_inputs} input(s).")
        return "single", idx
    raise ValueError("Invalid audio value. Use: none | mix | videoN (e.g., video1, video3).")


def build_video_chain(
    idx: int,
    height: int,
    start: float,
    total: float,
    label: Optional[str],
    fontfile: Optional[str],
) -> str:
    """
    Builds the per-input video filter chain.

    What it does:
      - resets timestamps
      - scales to the requested tile height
      - normalizes pixel format and SAR
      - optionally overlays drawtext
      - pads with cloned frames before and after so every stream lasts `total`
      - trims to exactly `total`

    Args:
        idx: Input index (0-based).
        height: Output tile height.
        start: Timeline start offset in seconds (pre-roll frozen frames).
        total: Total output duration in seconds.
        label: Optional label text.
        fontfile: Optional font file path.

    Returns:
        A filter chain that outputs a labeled stream [v{idx}].
    """
    out_label = f"v{idx}"
    chain = (
        f"[{idx}:v]"
        f"setpts=PTS-STARTPTS,"
        f"scale=-2:{height},"
        f"format=yuv420p,"
        f"setsar=1"
    )

    if label and label.strip():
        chain += f",{build_drawtext_filter(label.strip(), height, fontfile)}"

    chain += (
        f",tpad=start_duration={fmt_time(start)}:start_mode=clone:"
        f"stop_duration={fmt_time(total)}:stop_mode=clone"
        f",trim=duration={fmt_time(total)},setpts=PTS-STARTPTS"
        f"[{out_label}]"
    )
    return chain


def build_audio_chain(idx: int, delay_ms: int, out_label: str) -> str:
    """
    Builds an audio filter chain for one input.

    What it does:
      - normalizes to stereo/48k/fltp
      - resets timestamps
      - delays audio to match the video timeline offset

    Args:
        idx: Input index (0-based).
        delay_ms: Delay in milliseconds.
        out_label: Output stream label.

    Returns:
        A filter chain that outputs an audio stream [{out_label}].
    """
    return (
        f"[{idx}:a]"
        f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
        f"asetpts=PTS-STARTPTS,"
        f"adelay=delays={delay_ms}:all=1"
        f"[{out_label}]"
    )


def finalize_audio(in_label: str, total: float) -> str:
    """
    Pads/trims an audio stream to exactly `total` seconds and labels it [aout].

    Args:
        in_label: Input audio label (without brackets).
        total: Total duration in seconds.

    Returns:
        A filter chain that outputs [aout].
    """
    return (
        f"[{in_label}]"
        f"apad=whole_dur={fmt_time(total)},"
        f"atrim=start=0:end={fmt_time(total)},"
        f"asetpts=PTS-STARTPTS"
        f"[aout]"
    )


def build_filter_complex(
    *,
    height: int,
    fps_str: str,
    timeline_starts: List[float],
    total: float,
    labels: List[Optional[str]],
    fontfile: Optional[str],
    audio: str,
    has_audio: List[bool],
    warn: Optional[callable] = None,
) -> Tuple[str, bool]:
    """
    Builds the FFmpeg -filter_complex graph to:
      - pad each input video with frozen frames until its timeline start,
      - align all inputs on a shared timeline,
      - hstack videos side-by-side,
      - optionally align/mix audio,
      - output labeled streams [vout] (and [aout] if requested).

    Args:
        height: Output tile height for each video before stacking.
        fps_str: Output fps as string (used by fps filter).
        timeline_starts: Per-input timeline offsets (seconds).
        total: Total output duration (seconds).
        labels: Per-input label strings (same length as inputs).
        fontfile: Optional font path for drawtext.
        audio: "none" | "mix" | "videoN" (1-based).
        has_audio: Flags indicating whether each input has an audio stream.
        warn: Optional function to emit warnings (defaults to print to stderr if provided by caller).

    Returns:
        (filter_complex, include_audio)
        - filter_complex: the filtergraph string for -filter_complex
        - include_audio: True if the graph produces [aout], else False
    """
    n = len(timeline_starts)
    parts: List[str] = []

    # --- video chains (one per input) ---
    for i in range(n):
        parts.append(
            build_video_chain(
                idx=i,
                height=height,
                start=timeline_starts[i],
                total=total,
                label=labels[i],
                fontfile=fontfile,
            )
        )

    # Stack videos horizontally, then enforce output fps.
    stack_inputs = "".join(f"[v{i}]" for i in range(n))
    parts.append(f"{stack_inputs}hstack=inputs={n}:shortest=1[vstack]")
    parts.append(f"[vstack]fps=fps={fps_str}[vout]")

    # --- audio chains ---
    mode, single_idx = parse_audio_mode(audio, n)

    if mode == "none":
        return ";".join(parts), False

    if mode == "single":
        assert single_idx is not None
        if not has_audio[single_idx]:
            if warn:
                warn(f"Warning: requested audio from video{single_idx + 1}, but it has no audio stream. Output will be silent.")
            return ";".join(parts), False

        delay_ms = int(round(timeline_starts[single_idx] * 1000.0))
        parts.append(build_audio_chain(single_idx, delay_ms, "a1"))
        parts.append(finalize_audio("a1", total))
        return ";".join(parts), True

    # mode == "mix"
    audio_labels: List[str] = []
    for i in range(n):
        if not has_audio[i]:
            continue
        delay_ms = int(round(timeline_starts[i] * 1000.0))
        lbl = f"a{i}"
        parts.append(build_audio_chain(i, delay_ms, lbl))
        audio_labels.append(lbl)

    if not audio_labels:
        if warn:
            warn("Warning: audio=mix requested, but none of the inputs have audio. Output will be silent.")
        return ";".join(parts), False

    if len(audio_labels) == 1:
        parts.append(finalize_audio(audio_labels[0], total))
        return ";".join(parts), True

    mix_inputs = "".join(f"[{lbl}]" for lbl in audio_labels)
    parts.append(
        f"{mix_inputs}"
        f"amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=2"
        f"[amixed]"
    )
    parts.append(finalize_audio("amixed", total))
    return ";".join(parts), True


def build_ffmpeg_cmd(
    *,
    ffmpeg_bin: str,
    videos: List[Path],
    output: Path,
    filter_complex: str,
    total_duration: float,
    crf: int,
    preset: str,
    include_audio: bool,
    overwrite: bool,
) -> List[str]:
    """
    Builds the ffmpeg command arguments to execute the render.

    Args:
        ffmpeg_bin: Path to ffmpeg executable.
        videos: Input video paths (same order as used in filtergraph).
        output: Output MP4 path.
        filter_complex: Filtergraph string for -filter_complex.
        total_duration: Output duration cap in seconds.
        crf: libx264 CRF.
        preset: libx264 preset.
        include_audio: Whether to map [aout] or disable audio.
        overwrite: Overwrite output if it already exists.

    Returns:
        Argument list suitable for subprocess.run(...).
    """
    cmd: List[str] = [ffmpeg_bin, "-hide_banner"]
    cmd.append("-y" if overwrite else "-n")

    for v in videos:
        cmd += ["-i", str(v)]

    cmd += ["-filter_complex", filter_complex]
    cmd += ["-map", "[vout]"]

    if include_audio:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-an"]

    cmd += [
        "-t",
        fmt_time(total_duration),
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    return cmd
