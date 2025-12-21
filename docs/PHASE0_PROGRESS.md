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

## Next steps
1. Implement `io/ingest.py` with ffprobe helpers (rotation, fps, duration) and a timestamped frame iterator contract.
2. Define data models in `config.py` (e.g., VideoSpec, PoseConfig) and shared types.
3. Add MediaPipe Pose wrapper and caching scaffolding (`vision/keypoints.py`, `vision/cache.py`), documenting cache format.
4. Begin signals module stubs (`signals/kinematics.py`, `signals/smoothing.py`, `signals/quality.py`) with interfaces and minimal tests.
5. Wire a minimal CLI shape (`plai/cli.py`) that will later call the analysis pipeline.

## Notes
- Dependencies will be added gradually as implementations land to avoid pinning unused packages prematurely.
- All code remains FFmpeg-composition friendly: analysis produces timestamps/specs; rendering stays in FFmpeg.
