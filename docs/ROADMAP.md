# Powerlifting Video Analysis Roadmap

This roadmap captures the end-to-end plan for a lifting-aware analysis stack that plugs into the existing FFmpeg-based compositor. It is organized for incremental delivery with clear scope and acceptance criteria per phase.

## System Overview

- **Composition constraint:** Final rendering remains FFmpeg-driven (filtergraphs, no Python frame rendering).
- **Pipeline:** ingest → normalization → keypoint/object extraction → 1D signal generation → event/rep detection → confidence + QC → outputs (JSON + overlay spec) → FFmpeg composition.
- **Outputs:** machine-readable JSON (lift type, events, reps, confidences, QC flags), overlay spec for FFmpeg drawtext/filter_complex, sync event timestamps.

## Architecture (modules and responsibilities)

- `io`: ingest, metadata normalization (rotation, fps), frame timestamp iterator.
- `vision`: pose extraction (MediaPipe Pose baseline; optional MMPose), optional bar/plate detector, on-disk cache keyed by video+model hash.
- `signals`: kinematics (hip/bar height, knee angle, bar proxy), smoothing (Savitzky–Golay + EMA), quality masks from joint confidence.
- `repdetect`: heuristic detectors per lift (squat/bench/deadlift); optional temporal model (TCN/RepNet-like) for refinement.
- `classification`: lift classifier (pose-sequence features) for auto lift-type selection.
- `quality`: confidence aggregation, failure modes, QC flags.
- `sync`: selection of sync event (movement start, first bottom, first lockout).
- `overlay`: build overlay spec for FFmpeg (text, enable intervals) without rendering frames.
- `compositor`: build filtergraph fragments that the existing composer can consume (labels, freeze, audio modes).

## Modeling Approaches

1. **Baseline (pose + heuristics)**
   - Models: MediaPipe Pose (CPU-friendly default), optional MMPose (HRNet-lite/ViTPose-s) when GPU available.
   - Signals: hip/shoulder heights, knee angle, bar proxy from wrists or bar detector, velocities.
   - Pros: fast, debuggable, local-friendly. Cons: more sensitive to occlusion/angle.

2. **Advanced (temporal model)**
   - Models: small TCN/1D CNN over pose signals or RepNet-like architecture; optional RGB action backbone for tough angles.
   - Pros: temporal consistency and robustness to noise. Cons: requires labeled data and heavier compute.

**Default recommendation:** start with the baseline; add the temporal refinement model once labeled data is available.

## Rep Segmentation Logic (summary)

- **Common preprocessing:** orientation normalization (rotation metadata), timestamp-based resampling to fixed analysis rate, smoothing (Savitzky–Golay + EMA), quality masks from joint confidence.
- **Squat:** hip/bar height minima for bottom; velocity sign changes with hysteresis; depth threshold via knee angle; phases: descent, bottom, ascent, lockout.
- **Bench:** bar proxy minima for touch; elbow angle + bar velocity; phases: descent, touch/pause, ascent, lockout.
- **Deadlift:** bar/hip velocity for start; lockout via hip height + back angle uprightness; handle single-phase (no lowering) clips.
- **Constraints:** hysteresis on velocity thresholds, min phase durations, multi-signal voting (hip+bar; wrist+elbow), gap-filling for short occlusions; QC flags when coverage is low.

## Robustness Plan

- Handle rotation metadata; operate on timestamps for variable fps; person tracking to pick the primary subject; quality masks for occlusion; optional bar detector to disambiguate bar path; failure modes fall back to movement-start-only sync with low confidence.

## Evaluation Plan

- Ground truth: lightweight labeling of movement start, bottoms, tops; store JSON timestamps and lift label.
- Metrics: boundary error (ms), precision/recall/F1 with tolerance (±150–200 ms), false rep rate, phase IoU, keypoint coverage.
- Test sets stratified by lift, angle, lighting, occlusion (spotter/rack), motion blur, fps (24/30/60).

## Roadmap Phases

### Phase 0 — Baseline for personal clips
- **Scope:** MediaPipe Pose ingest/caching; squat-only heuristic detector; JSON + overlay spec; sync by first bottom or movement start.
- **Acceptance:** detects squats within ±200 ms on own clips; produces JSON and overlay spec consumable by FFmpeg; handles rotation metadata and variable fps without crashes.

### Phase 1 — Generalization and reliability
- **Scope:** add bench and deadlift heuristics; multi-person handling and QC flags; lift classifier; temporal TCN refinement model; optional bar detector integration.
- **Acceptance:** ≥0.9 F1 on mixed validation set; graceful degradation under occlusion/spotter; auto-sync works across angles.

### Phase 2 — Advanced features
- **Scope:** phase labeling for all lifts; multiple auto-sync strategies; richer overlays (rep counter, phase labels); stronger bar/object detection.
- **Acceptance:** phase IoU ≥0.7; sync within ±150 ms across diverse clips; stable JSON + overlay outputs.

