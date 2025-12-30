# Phase A Progress Log — UI/API

This log tracks incremental Phase A work for the sync UI/API. Each entry notes what changed, why, and next steps.

## Current scope (Phase A)
- Synchronous `/sync` endpoint wrapping `core/video_editor.py`.
- Minimal frontend form for multi-upload, offsets, audio selector, progress state.
- Temp storage; no queue/object storage yet.

## Progress entries

### 2025-01-06 — FastAPI scaffold
- Added initial FastAPI app (`api/app.py`) with a `/sync` route, request/response schemas, and placeholder service layer. The endpoint currently validates metadata and returns a stub response; file uploads and core integration will follow.
- Documented the backend directory structure and how to run `uvicorn api.app:app --reload`.

### 2025-01-07 — Temp storage plan
- Documented Phase A temp storage behavior in `PHASEA.md`, emphasizing per-job folders under `tmp/sync-jobs`, streaming uploads to disk, TTL-based cleanup, and a swappable storage abstraction for future S3 migration.

### 2025-01-08 — Next-step alignment
- Merged the duplicated “Next steps” sections into a single ordered list to clarify the execution order.
- Identified the immediate action: wire multipart uploads into `/sync` and persist to temp storage, documenting progress as it starts and completes.

### 2025-01-09 — Multipart uploads to temp storage
- Wired `/sync` to accept multipart form data (`metadata` JSON + `files[]` uploads), validating the metadata and requiring at least one video.
- Persisted uploads to per-job temp directories under `tmp/sync-jobs/{job_id}`, writing `job.json` with creation time and payload for TTL cleanup. Response now includes the job ID while processing remains pending.

### 2025-01-10 — Core render integration
- After persisting uploads, the service now calls `core/video_editor.py` to render a side-by-side `output.mp4` within the job folder.
- Audio selection supports `none`, `mix`, or a 1-based clip index; the rendered job completes synchronously and returns `status="completed"`.

### 2025-01-11 — Validation limits
- Added server-side validation for file count (≤ 4), per-file size (≤ 512 MiB), and MIME types (`video/mp4`, `video/quicktime`, `video/x-matroska`, `video/webm`).
- Start offsets must be finite and ≥ 0; failures now return HTTP 400 with clear messages.

## Next steps
1. Build the MVP frontend, hook it to the endpoint, and surface progress/errors.
