# Phase 0 Progress Log

This log tracks incremental Phase 0 work. Each entry records what changed, why, and what comes next. The focus is documentation-first with code delivered in small steps.

## Current scope (Phase 0)
- Squat-focused baseline using MediaPipe Pose (CPU-friendly).
- Pose + heuristic rep detection; no temporal model yet.
- Outputs: JSON events, overlay spec for FFmpeg; sync by first bottom or movement start.

## Progress entries

### 2024-XX-XX — Scaffolding and organization
- Added project skeleton for the analysis package (`plai/` with submodules for IO, vision, signals, rep detection, overlay, sync, quality, classification, config, CLI).
- Added module placeholders with docstrings describing responsibilities and planned functions.
- Created `pyproject.toml` for package metadata (no heavy dependencies declared yet).
- This keeps code organized for upcoming implementations (ffprobe helpers, pose wrapper, signal generation).

### 2025-12-21 — Video metadata probe + shared configs
- **Why:** We need reliable, rotation-aware metadata before decoding frames so downstream steps (pose extraction, overlays) know the orientation, frame cadence, and expected timestamps.
- **What:** Implemented `VideoSpec` and `PoseConfig` dataclasses to centralize shared parameters; added `io.ingest.probe_video` to wrap `ffprobe` (rotation, fps, width/height, duration, optional frame count) and `iter_expected_timestamps` to map frames to timestamps. Added unit tests that mock `ffprobe` output and verify timestamp math.
- **Example check:** `python -m unittest tests.test_ingest` exercises the mocked ffprobe path and timestamp iterator, confirming a 10s 23.976 fps clip reports 240 frames, 90° rotation, and timestamps `[0.0, 1/30, 2/30]` when `frame_count=3`.
- **Achieved:** We now have metadata structures and helpers ready for rotation-aware normalization and future frame decoding without touching the heavier vision stack yet.
- **Next step:** Implement rotation normalization utilities and a frame iterator contract that respects the probed metadata, then thread `VideoSpec` through the rest of the pipeline.

### 2025-12-21 — Rotation normalization utilities
- **Why:** Downstream analysis (pose, overlays) needs upright coordinates regardless of source orientation while still mapping results back for FFmpeg composition.
- **What:** Added `RotationTransform` in `io.normalization` to convert points between original and normalized orientations, handling 0/90/180/270° rotations and exposing normalized dimensions. Included unit tests that round-trip points and validate dimension swaps plus error handling for unsupported angles.
- **Example check:** `python -m unittest tests.test_normalization` confirms a 1920x1080 clip with 90° rotation swaps to 1080x1920 in normalized space and that point mappings round-trip for 90°/270° cases.
- **Achieved:** We can now reason about upright coordinates independently of video metadata, setting up the upcoming frame iterator to deliver normalized frames and mapping overlays back to raw orientation.
- **Next step:** Implement the frame iterator that decodes frames respecting rotation and uses `RotationTransform`, then propagate `VideoSpec`/transform through pose and overlay modules.

### 2025-12-21 — Frame iterator scaffold
- **Why:** We need a timestamp-aware frame iterator that honors rotation metadata so pose and overlay steps consume upright frames with consistent timing.
- **What:** Added `iter_frames_from_supplier` to pair provided frames with timestamps from `VideoSpec`, optionally applying rotation via `RotationTransform`; `iter_expected_timestamps` remains for synthetic timing checks. Included a helper `_rotate_frame` that rotates nested sequences without extra dependencies. Added an ffmpeg-backed iterator scaffold (`iter_frames_via_ffmpeg`) with lazy numpy import and command builder, plus `iter_normalized_frames` to decode-and-rotate in one step.
- **Example check:** `python -m unittest tests.test_ingest` now covers rotated frames supplied as 2x1 nested lists to verify 90° normalization/timestamp mapping, mocks ffmpeg + numpy to exercise the decode path and error messaging when numpy is absent, and checks `iter_normalized_frames` rotation on mocked ffmpeg output.
- **Achieved:** We can iterate decoded frames (supplied externally or via ffmpeg) with correct timestamps and normalized orientation, ready to plug in OpenCV/ffmpeg decoding in a later step.
- **Next step:** Thread normalization through pose extraction and overlay mapping, add real decode wiring when dependencies are available, and build small end-to-end smoke tests.

### 2025-12-21 — Pose cache format
- **Why:** Pose extraction is expensive; we need a debuggable cache keyed by video hash and pose config to avoid redundant runs and keep provenance clear.
- **What:** Added JSONL cache utilities (`vision.cache`) with `PoseLandmark`/`PoseFrame` dataclasses, SHA-256 video hashing, cache filename/path builders, and save/load helpers. No external dependencies are required.
- **Example check:** `python -m unittest tests.test_pose_cache` writes two frames to a temp cache and reads them back, ensuring equality and verifying the cache filename embeds the pose cache key.
- **Achieved:** We now have a reusable cache format ready for the upcoming pose wrapper, enabling repeatable runs and easy inspection during tuning.
- **Next step:** Implement the pose extraction wrapper to populate the cache using the frame iterator + normalization helpers, then propagate cached outputs into signals/rep detection.
## Next steps
1. Add MediaPipe Pose wrapper and connect it to the JSONL pose cache + frame iterator.
2. Begin signals module stubs (`signals/kinematics.py`, `signals/smoothing.py`, `signals/quality.py`) with interfaces and minimal tests.
3. Wire a minimal CLI shape (`plai/cli.py`) that will later call the analysis pipeline.

## Notes
- Dependencies will be added gradually as implementations land to avoid pinning unused packages prematurely.
- All code remains FFmpeg-composition friendly: analysis produces timestamps/specs; rendering stays in FFmpeg.
