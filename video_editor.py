#!/usr/bin/env python3
"""
Video editing pipeline for powerlifting video analysis.

Provides utilities to align multiple portrait MP4 clips on a shared timeline,
freeze starting frames, draw optional labels, and export a side-by-side
comparison via FFmpeg.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

FFMPEG_EXE = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE_EXE = r"C:\ffmpeg\bin\ffprobe.exe"


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


def compute_timeline_starts(starts: List[float], start_mode: str) -> Tuple[List[float], float]:
    if start_mode == "timeline":
        return list(starts), 0.0

    t_sync = max(starts)
    timeline_starts = [t_sync - s for s in starts]
    return timeline_starts, t_sync


def build_filter_complex(
    height: int,
    fps_str: str,
    timeline_starts: List[float],
    total: float,
    labels: List[Optional[str]],
    fontfile: Optional[str],
    audio: str,
    has_audio: List[bool],
) -> Tuple[str, bool]:
    n = len(timeline_starts)
    parts: List[str] = []

    def video_chain(idx: int, start: float, label: Optional[str]) -> str:
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

    for i in range(n):
        parts.append(video_chain(i, timeline_starts[i], labels[i]))

    stack_inputs = "".join(f"[v{i}]" for i in range(n))
    parts.append(f"{stack_inputs}hstack=inputs={n}:shortest=1[vstack]")
    parts.append(f"[vstack]fps=fps={fps_str}[vout]")

    mode, single_idx = parse_audio_mode(audio, n)
    has_audio_out = False

    def audio_chain(idx: int, delay_ms: int, out_label: str) -> str:
        return (
            f"[{idx}:a]"
            f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
            f"asetpts=PTS-STARTPTS,"
            f"adelay=delays={delay_ms}:all=1"
            f"[{out_label}]"
        )

    def finalize_audio(in_label: str) -> str:
        return (
            f"[{in_label}]"
            f"apad=whole_dur={fmt_time(total)},"
            f"atrim=start=0:end={fmt_time(total)},"
            f"asetpts=PTS-STARTPTS"
            f"[aout]"
        )

    if mode == "none":
        return ";".join(parts), False

    if mode == "single":
        assert single_idx is not None
        if not has_audio[single_idx]:
            eprint(
                f"Warning: requested audio from video{single_idx + 1}, but it has no audio stream. Output will be silent."
            )
            return ";".join(parts), False

        delay_ms = int(round(timeline_starts[single_idx] * 1000.0))
        parts.append(audio_chain(single_idx, delay_ms, "a1"))
        parts.append(finalize_audio("a1"))
        return ";".join(parts), True

    audio_labels: List[str] = []
    for i in range(n):
        if not has_audio[i]:
            continue
        delay_ms = int(round(timeline_starts[i] * 1000.0))
        lbl = f"a{i}"
        parts.append(audio_chain(i, delay_ms, lbl))
        audio_labels.append(lbl)

    if not audio_labels:
        eprint("Warning: --audio mix requested, but none of the inputs have audio. Output will be silent.")
        return ";".join(parts), False

    if len(audio_labels) == 1:
        parts.append(finalize_audio(audio_labels[0]))
        return ";".join(parts), True

    mix_inputs = "".join(f"[{lbl}]" for lbl in audio_labels)
    parts.append(
        f"{mix_inputs}"
        f"amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=2"
        f"[amixed]"
    )
    parts.append(finalize_audio("amixed"))
    return ";".join(parts), True


def build_ffmpeg_cmd(
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


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compose N portrait MP4 videos side-by-side on a shared timeline (freeze first frame before start)."
    )

    p.add_argument("--video", action="append", dest="videos", default=[],
                   help="Path to an input MP4. Provide multiple times, in left-to-right order.")
    p.add_argument("--start", action="append", dest="starts", default=[], type=float,
                   help="Start value per video. Meaning depends on --start_mode. Provide same count as --video.")

    p.add_argument("--start_mode", choices=["sync", "timeline"], default="sync",
                   help="sync (default): --start is the in-clip timestamp where clips should be aligned; "
                        "timeline starts become max(starts)-start_i. "
                        "timeline: --start is directly the timeline playback start time.")

    p.add_argument("--label", action="append", dest="labels", default=None,
                   help="Optional label for the corresponding --video. Provide 0 times OR exactly N times. "
                        "Use empty string \"\" to skip a label for a specific video.")
    p.add_argument("--output", required=True, help="Output MP4 path")

    p.add_argument("--height", type=int, default=1080,
                   help="Output height for each side before stacking (default: 1080)")
    p.add_argument("--fps", type=float, default=None,
                   help="Output fps (default: derived from inputs or 30)")
    p.add_argument("--audio", default="none",
                   help="Audio mode: none | mix | videoN (1-based), e.g. video1, video3 (default: none)")
    p.add_argument("--font", default=None,
                   help="Optional font file path for drawtext")
    p.add_argument("--crf", type=int, default=20,
                   help="libx264 CRF (default: 20)")
    p.add_argument("--preset", default="medium",
                   help="libx264 preset (default: medium)")
    p.add_argument("--overwrite", action="store_true",
                   help="Overwrite output file if it exists")
    p.add_argument("--print_ffmpeg_cmd", action="store_true",
                   help="Print the ffmpeg command + filtergraph before running (debugging)")

    return p.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    if args.height <= 0:
        raise ValueError("--height must be a positive integer.")
    if args.fps is not None and args.fps <= 0:
        raise ValueError("--fps must be positive if provided.")
    if args.crf < 0 or args.crf > 51:
        raise ValueError("--crf must be between 0 and 51 for libx264.")
    if args.font is not None and not Path(args.font).expanduser().exists():
        raise FileNotFoundError(f"Font file not found: {args.font}")

    if not args.videos or not args.starts:
        raise ValueError("You must provide --video and --start (repeated), plus --output.")
    if len(args.videos) < 2:
        raise ValueError("Provide at least 2 videos for side-by-side output.")
    if len(args.videos) != len(args.starts):
        raise ValueError(
            f"Count mismatch: got {len(args.videos)} --video but {len(args.starts)} --start.\n"
            f"Provide one --start for every --video, in the same order."
        )

    for s in args.starts:
        if math.isnan(s) or math.isinf(s):
            raise ValueError("All --start values must be finite numbers.")
        if s < 0:
            raise ValueError("All --start values must be >= 0 (they are timestamps in seconds).")

    if args.labels is not None and len(args.labels) != len(args.videos):
        raise ValueError(
            f"Count mismatch: got {len(args.labels)} --label but {len(args.videos)} videos.\n"
            f"Provide 0 labels OR exactly one label per video.\n"
            f"Tip: use --label \"\" to skip a label for a specific video."
        )

    out_path = Path(args.output).expanduser()
    if out_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Output file already exists: {out_path}\n"
            f"Use --overwrite to replace it, or choose a different --output path."
        )
    if out_path.parent and not out_path.parent.exists():
        raise FileNotFoundError(
            f"Output directory does not exist: {out_path.parent}\n"
            f"Create it first, or choose a different --output path."
        )


def run(args: argparse.Namespace) -> int:
    try:
        validate_args(args)

        ffmpeg_bin = FFMPEG_EXE if FFMPEG_EXE else require_tool("ffmpeg")
        ffprobe_bin = FFPROBE_EXE if FFPROBE_EXE else require_tool("ffprobe")

        if not Path(ffmpeg_bin).exists():
            raise RuntimeError(f"FFmpeg not found at: {ffmpeg_bin}")
        if not Path(ffprobe_bin).exists():
            raise RuntimeError(f"FFprobe not found at: {ffprobe_bin}")

        video_paths = [Path(v).expanduser() for v in args.videos]
        out_path = Path(args.output).expanduser()

        infos: List[MediaInfo] = [probe_media(p, ffprobe_bin) for p in video_paths]

        if args.start_mode == "sync":
            for i, (sync_t, info) in enumerate(zip(args.starts, infos), start=1):
                if sync_t > info.duration + 0.25:
                    raise ValueError(
                        f"--start for video{i} is {sync_t:.3f}s but clip duration is {info.duration:.3f}s.\n"
                        f"In sync mode, --start must be inside the clip."
                    )

        timeline_starts, t_sync = compute_timeline_starts(args.starts, args.start_mode)

        total_duration = max(timeline_starts[i] + infos[i].duration for i in range(len(infos)))

        if args.fps is not None:
            fps_out = args.fps
        else:
            candidates = [mi.fps for mi in infos if mi.fps and mi.fps > 0]
            fps_out = max(candidates) if candidates else 30.0
        fps_str = format_fps_value(fps_out)

        if args.labels is None:
            labels = [None] * len(video_paths)
        else:
            labels = [lbl for lbl in args.labels]

        has_audio_flags = [mi.has_audio for mi in infos]

        filter_complex, has_audio_out = build_filter_complex(
            height=args.height,
            fps_str=fps_str,
            timeline_starts=timeline_starts,
            total=total_duration,
            labels=labels,
            fontfile=args.font,
            audio=args.audio,
            has_audio=has_audio_flags,
        )

        cmd = build_ffmpeg_cmd(
            ffmpeg_bin=ffmpeg_bin,
            videos=video_paths,
            output=out_path,
            filter_complex=filter_complex,
            total_duration=total_duration,
            crf=args.crf,
            preset=args.preset,
            include_audio=has_audio_out,
            overwrite=args.overwrite,
        )

        if args.print_ffmpeg_cmd:
            eprint("FFmpeg command:")
            eprint(" ".join(cmd))
            eprint("\nFilter graph:")
            eprint(filter_complex)
            eprint("")

        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            return proc.returncode

        print(f"Done. Wrote: {out_path}")
        if args.start_mode == "sync":
            print(
                f"Sync moment occurs at timeline t={t_sync:.3f}s. Timeline starts: {', '.join(f'{x:.3f}' for x in timeline_starts)}"
            )
        return 0

    except Exception as ex:
        eprint(f"Error: {ex}")
        return 2


PYCHARM_DEFAULTS = [
    "--start_mode", "sync",
    "--video", r"./input/W4 - 142.5.mp4", "--start", "10.45", "--label", "W4",
    "--video", r"./input/W5 - 142.5.mp4", "--start", "11.45", "--label", "W5",
    "--output", r"./output/squat_comparison_2.mp4",
    "--audio", "video2",
    "--fps", "60",
    "--overwrite",
]

INTERACTIVE_PROMPT = False


def _prompt(msg: str, default: Optional[str] = None) -> str:
    if default is None:
        return input(f"{msg}: ").strip()
    v = input(f"{msg} [{default}]: ").strip()
    return v if v else default


def build_args_interactively() -> List[str]:
    n_str = _prompt("How many videos?", "2")
    if not n_str.isdigit() or int(n_str) < 2:
        raise ValueError("Please enter an integer >= 2 for number of videos.")
    n = int(n_str)

    argv: List[str] = []
    start_mode = _prompt("start_mode (sync|timeline)", "sync").strip().lower()
    if start_mode not in ("sync", "timeline"):
        raise ValueError("start_mode must be 'sync' or 'timeline'.")
    argv += ["--start_mode", start_mode]

    for i in range(n):
        v = _prompt(f"video{i+1} path")
        if start_mode == "sync":
            s = _prompt(f"video{i+1} SYNC timestamp inside the clip (seconds)", "0")
        else:
            s = _prompt(f"video{i+1} timeline start time (seconds)", "0")
        lbl = _prompt(f"video{i+1} label (empty = no label)", "")
        argv += ["--video", v, "--start", s, "--label", lbl]

    output = _prompt("output path")
    argv += ["--output", output]

    height = _prompt("height (optional)", "").strip()
    if height:
        argv += ["--height", height]

    fps = _prompt("fps (optional)", "").strip()
    if fps:
        argv += ["--fps", fps]

    audio = _prompt("audio mode: none|mix|videoN (optional)", "").strip()
    if audio:
        argv += ["--audio", audio]

    font = _prompt("font file path (optional)", "").strip()
    if font:
        argv += ["--font", font]

    crf = _prompt("crf (optional)", "").strip()
    if crf:
        argv += ["--crf", crf]

    preset = _prompt("preset (optional)", "").strip()
    if preset:
        argv += ["--preset", preset]

    overwrite = _prompt("overwrite? y/N (optional)", "N").strip().lower()
    if overwrite in ("y", "yes"):
        argv += ["--overwrite"]

    return argv


def run_cli(argv: Optional[List[str]] = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(run_cli())
