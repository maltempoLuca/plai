# Roadmap — UI/API

This roadmap covers the web experience and REST API that wrap `core/video_editor.py` to produce synchronized side-by-side videos from multiple uploads, including audio selection (single source or mix) and downloadable outputs. Stack choice: **FastAPI** for the backend and **Angular SPA** for the frontend.

## System Overview

- **API:** RESTful service (FastAPI) exposing a POST endpoint that accepts multiple videos, per-video start offsets, and audio mix selection; delegates to the core sync logic in `core/video_editor.py`.
- **Processing:** Temp storage + validation → background job (Celery/RQ/async task) → call `core/video_editor.py` → store artifact for download.
- **Frontend:** Angular SPA to upload N videos, set start times, choose audio (video 1/video 2/.../mix), trigger sync, and download the output.
- **Auth/quotas:** Optional API key or bearer token; rate limiting to protect the service.

## Roadmap Phases

### Phase A — MVP upload → sync → download
- **Scope:** REST POST `/sync` accepting files + JSON body (start offsets, audio selection, output layout defaults to side-by-side); synchronous job path; temp storage; output download endpoint.
- **Frontend:** Simple form with multi-file input, per-video start time fields, audio selector (dropdown: video N or mix), and progress state; polls for completion.
- **Acceptance:** Upload two short clips, set offsets, pick audio, receive a side-by-side MP4 produced via `core/video_editor.py` within the request/response window.

### Phase B — UX polish and reliability
- **Scope:** Async job queue (Celery/RQ/async tasks) with status endpoint; persisted job IDs; retries for transient ffmpeg failures; size/duration validation; logging + structured errors.
- **Frontend:** Job-status polling with spinners and success/error states; client-side validation for file types/duration; download link once complete.
- **Acceptance:** Jobs survive short outages; errors reported clearly; invalid inputs rejected client-side and server-side.

### Phase C — Scale and integrations
- **Scope:** Object storage for uploads/results; optional webhook callbacks; API keys/rate limiting; configurable layouts (grid vs side-by-side), optional burn-in labels; observability (metrics + tracing).
- **Frontend:** Minimal settings drawer for layout/audio mix options; shareable download links; basic analytics (e.g., recent jobs).
- **Acceptance:** Can handle >5 concurrent jobs without blocking; artifacts stored durably; API-key–protected access suitable for limited beta users.
