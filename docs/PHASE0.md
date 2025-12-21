# Phase 0: Baseline Implementation Plan

Goal: deliver a squat-focused baseline that works on personal clips, outputs machine-readable events, and integrates with the existing FFmpeg compositor without changing the FFmpeg-driven rendering.

## Objectives
- Ingest + normalize videos (rotation metadata, fps) and iterate frames with timestamps.
- Extract pose with MediaPipe Pose (CPU-friendly), cache results, and expose per-frame keypoints + confidence.
- Generate squat-relevant signals (hip/bar height proxies, velocity) with smoothing and quality masks.
- Detect movement start, bottoms, tops, and reps with heuristic logic, plus confidence scoring.
- Export JSON analysis and overlay specifications (rep counter/phase labels) to feed FFmpeg filtergraphs; provide a sync event timestamp (e.g., first bottom).

## Why these choices
- **MediaPipe Pose**: fast, runs on CPU, robust enough for clean sagittal/45° angles; minimal dependency weight for a first pass.
- **Pose + heuristics**: debuggable, explainable thresholds, quick to tune on personal footage before investing in training data.
- **Savitzky–Golay + EMA smoothing**: handles jitter while preserving peaks/valleys needed for bottom/top detection.
- **JSON + overlay spec**: keeps analysis and rendering separate; FFmpeg continues to own composition.

## Deliverables (Phase 0)
1. **Package scaffolding**: `plai/` package with submodules (`io`, `vision`, `signals`, `repdetect`, `overlay`, `sync`, `quality`, `config`, `cli.py`) and `pyproject.toml`/`requirements.txt`.
2. **Ingest + rotation handling**: `io/ingest.py` (ffprobe wrapper) and `io/normalization.py` for rotation normalization and timestamped frame iteration.
3. **Pose extraction + cache**: `vision/keypoints.py` to run MediaPipe Pose; `vision/cache.py` for on-disk JSONL/NPZ keyed by video hash + model version.
4. **Signals + smoothing**: `signals/kinematics.py` to compute hip/bar heights and velocities; `signals/smoothing.py` for Savitzky–Golay + EMA; `signals/quality.py` for per-frame quality masks (joint confidence thresholds, gap handling).
5. **Squat heuristic detector**: `repdetect/baseline.py` with movement start, bottom, top detection, hysteresis, min-duration constraints, rep assembly, and confidence aggregation; outputs `AnalysisResult`.
6. **Outputs + sync**: `overlay/annotations.py` to build overlay spec (drawtext intervals); `sync/events.py` to pick sync timestamp (first bottom preferred, fallback movement start); JSON export schema.
7. **CLI**: `plai analyze input.mp4 --lift squat --export-json out.json --overlay overlay.json`.
8. **Tests**: basic unit tests on synthetic signals (peaks/valleys) and sanity checks on a small set of personal clips (non-public), asserting JSON shape and presence of expected events.

## Work plan (stepwise)
1. Scaffold project structure and dependencies (pyproject/requirements, `plai/` package).
2. Implement `ffprobe` helpers and rotation-aware frame/timestamp iterator.
3. Wrap MediaPipe Pose with deterministic config + cache format.
4. Build kinematic signals and smoothing utilities; unit-test synthetic signals.
5. Implement squat heuristic detector with thresholds and hysteresis; unit-test synthetic waveforms (descent–bottom–ascent patterns).
6. Implement JSON + overlay spec emitters; wire CLI end-to-end.
7. Dry-run on a couple of real clips; adjust thresholds; capture known gaps as issues for Phase 1.

## Acceptance criteria (Phase 0)
- On personal squat clips: bottoms/tops within ±200 ms of manual marks; no crashes on rotation metadata or variable fps; JSON + overlay spec emitted; sync timestamp available (first bottom preferred, else movement start).
- Quality flags appear when pose coverage is poor; in that case, output remains but marks low confidence.

## Notes and assumptions
- Primary angles: side or ~45°; portrait 30–60 fps; single lifter, spotter may occlude at bottom.
- CPU-only environment is acceptable; GPU support optional but not required for Phase 0.
- FFmpeg composition remains unchanged; only filtergraph specs and sync offsets are added.

