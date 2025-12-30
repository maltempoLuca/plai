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

### 2025-01-07 — Multipart uploads with temp storage
- `/sync` now accepts multipart uploads: `metadata` form field carries the `SyncRequest` JSON and repeated `files` fields carry videos. Requests are validated for count and non-negative offsets.
- Added `api/services/storage.py` to persist uploads under `/tmp/plai-sync` (override with `$SYNC_TMP_DIR`), returning a per-request directory and file paths; placeholder cleanup helper added for future TTL enforcement.
- Service layer now checks video/count alignment and returns a job id derived from the temp directory name.

## Next steps
- Invoke `core/video_editor.py` from the service layer to render the side-by-side output into the job directory.
- Add basic error handling/validation messages surfaced through the API response, plus simple cleanup of old temp folders.
- Expose a download endpoint for the rendered output once the core call is wired.

## Next steps
- Scaffold API and data contracts; wire `core/video_editor.py` into a synchronous handler.
- Build the MVP frontend and hook it to the endpoint.
- Add validation and error handling; document limits.
