# FastAPI backend

This directory hosts the FastAPI service that wraps the core sync logic in `core/video_editor.py`.

Suggested layout:
- `api/app.py` (FastAPI entrypoint) – `uvicorn api.app:app --reload`
- `api/routes/` for request handling
- `api/schemas/` for request/response models
- `api/services/` for orchestration that calls into `core.video_editor`

## `/sync` usage (Phase A)

- **Endpoint:** `POST /sync`
- **Body:** `multipart/form-data` with:
  - `metadata`: JSON string matching `SyncRequest` (starts, labels, audio, etc.).
  - `files`: one or more video uploads (`UploadFile` list).
- **Validation:** up to 4 video files, max 512 MiB each; allowed MIME types: `video/mp4`, `video/quicktime`, `video/x-matroska`, `video/webm`. Start offsets must be finite and ≥ 0.
- **Storage:** uploads are streamed to `tmp/sync-jobs/{job_id}` with a per-job `job.json` that records creation time and payload; files are temporary and should be swept by TTL cleanup.
- **Response:** `SyncResponse` with `job_id` and `status="completed"` after calling `core/video_editor.py` to render `output.mp4` inside the job folder.
- **Audio selection:** pass `"none"`, `"mix"`, or a positive integer (1-based) to keep the audio from a specific uploaded clip.
