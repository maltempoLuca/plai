# Phase A: UI/API MVP Plan

Goal: deliver a minimal **FastAPI** backend and **Angular SPA** frontend that upload multiple videos, let users set start offsets and pick the audio source/mix, and invoke the core sync logic from `core/video_editor.py` via the API to build a side-by-side render and return a downloadable file.

## Objectives
- Accept N video uploads with validation on size/format.
- Collect per-video start offsets and audio selection (single source by 1-based index or mix).
- Invoke `core/video_editor.py` with requested offsets/audio mode to produce side-by-side output.
- Provide a synchronous response path with a download endpoint for the rendered file.
- Offer basic frontend form with multi-file input, offsets, audio selector, submit, and progress state.

## Deliverables (Phase A)
1. **API endpoint:** POST `/sync` (multipart) that accepts files + JSON metadata (offsets, audio mode), stores temp files, and triggers processing.
2. **Processing path:** Wrapper around `core/video_editor.py` to orchestrate side-by-side render; clear error handling for ffmpeg/video issues.
3. **Output serving:** Endpoint to fetch the generated file; short-lived storage policy.
4. **Frontend MVP (Angular):** Single-page form with: multi-file upload, per-video start offset inputs, audio dropdown, submit button, and basic in-flight status indicator.
5. **Validation + limits:** Server-side checks for file type/size/count; client-side hints and error messages.

## Work plan (stepwise)
1. Define request/response schema (offsets, audio mode enum, target layout) and temp storage structure.
2. Implement synchronous `/sync` endpoint that calls the shared application core (via `core/video_editor.py`) to perform sync; return job/result metadata and download link.
3. Build the Angular form that posts to `/sync` and shows basic progress/polled status.
4. Add validation/errors both server-side and client-side; document size/format limits.
5. Smoke-test with two short clips; adjust defaults (layout, audio mix) based on observed outputs.

## Acceptance criteria (Phase A)
- Two uploaded clips can be offset, rendered side-by-side via `core/video_editor.py`, and downloaded in one flow.
- Unsupported inputs (wrong type/too large) return clear errors; frontend surfaces these states.
- Render completes within expected synchronous timeout for short clips.

## Notes and assumptions
- Synchronous path only (async queue deferred to Phase B).
- Temp storage on local disk; no object storage yet.
- Minimal auth (if any) for initial demo; rate limiting deferred.

## Temp storage handling (Phase A)

Until we introduce an object store (e.g., S3 in Phase C), uploads and outputs live in short-lived local temp storage. The MVP flow should adhere to these rules:

- **Root structure:** create a job-scoped directory per request under `./tmp/sync-jobs/{job_id}` (or a configured `TEMP_ROOT`). Store uploads as `source_{index}.<ext>` and the rendered result as `output.mp4` inside the same folder.
- **Write path:** accept multipart uploads, stream them to disk without loading the whole file into memory, and fsync once each file lands. Reject if the directory would exceed size limits.
- **Ephemeral lifetime:** mark the job directory with a creation timestamp and delete it after a short TTL (e.g., 4–6 hours) or immediately after the client fetches the output. Do not treat this as durable storage—files are **not** kept beyond the TTL.
- **Cleanup:** provide a best-effort background sweeper on startup or per-request to prune expired job folders. In constrained environments, also support an on-demand `python -m api.scripts.cleanup_temp` helper to purge old artifacts.
- **Future swap:** the directory abstraction should be behind a small storage service so we can swap local temp for S3 later without touching the route handler.
