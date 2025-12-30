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
- **Storage:** uploads are streamed to `tmp/sync-jobs/{job_id}` with a per-job `job.json` that records creation time and payload; files are temporary and should be swept by TTL cleanup.
- **Response:** `SyncResponse` with `job_id` and `status="pending"` (processing stubbed until Phase A core integration).
