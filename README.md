# Powerlifting Video Comparison Tool

A Python helper that builds FFmpeg filtergraphs to align portrait powerlifting videos on a shared timeline. It stacks clips side-by-side, freezes the first frame until playback begins, and can optionally add labels and mix audio for clear comparisons.

## Analysis roadmap

We are adding a lifting-aware analysis layer that feeds timestamps and overlay specs into the existing FFmpeg compositor (rendering stays FFmpeg-only). Planning is documented in:

- `docs/ROADMAP.md`: full multi-phase roadmap and architecture overview.
- `docs/PHASE0.md`: detailed plan for the Phase 0 baseline (squat-focused, MediaPipe Pose + heuristics).

Key choices for Phase 0:
- **MediaPipe Pose** as the initial CPU-friendly pose backbone for fast iteration on personal clips.
- **Pose + heuristic rep detection** for transparency and quick tuning, with room for later temporal models.
- **JSON + overlay specifications** to keep analysis separate from FFmpeg rendering while enabling synced annotations.

## Features
- Align multiple MP4 videos by providing per-clip sync timestamps.
- Freeze first frames before playback to avoid blank slates.
- Side-by-side stacking with automatic scaling to a chosen height.
- Optional labels drawn within each tile.
- Flexible audio selection: none, pick a single clip, or mix all available tracks.
- H.264 output with `yuv420p` pixel format and `+faststart` for web playback.

## Requirements
- Python 3.8+.
- FFmpeg and FFprobe available on your PATH (or update `FFMPEG_EXE` / `FFPROBE_EXE` in `video_editor.py`).

## Project layout
- `video_editor.py` — core logic for probing media, building filtergraphs, and running FFmpeg.
- `main.py` — entry point that forwards CLI arguments to the editor logic; includes PyCharm-friendly defaults.

## Usage
From the repository root:

```bash
python main.py --video path/to/left.mp4 --start 4.5 \
    --video path/to/right.mp4 --start 5.5 \
    --output output/comparison.mp4 --audio mix --height 1080 --fps 60 --overwrite
```

Key flags:
- `--video` and `--start` should be provided in pairs for each clip (left-to-right order).
- `--start_mode sync` (default) interprets `--start` as the in-clip sync timestamp; use `--start_mode timeline` to treat `--start` as absolute timeline offsets.
- `--label` (provide one per video) draws text within each tile; use an empty string to skip a specific label.
- `--audio` supports `none`, `mix`, or `videoN` (e.g., `video1`).

### PyCharm defaults
When launched from PyCharm with no CLI arguments, `main.py` uses the `PYCHARM_DEFAULTS` defined in `video_editor.py`. Set `INTERACTIVE_PROMPT = True` there to build arguments interactively inside the IDE.

## Development
- Core CLI parsing lives in `video_editor.py` (see `run_cli`).
- `main.py` is a thin wrapper so alternative entry points can import and reuse the editing functions without duplicating logic.

Feel free to adjust `PYCHARM_DEFAULTS` to match your typical comparison workflow.
