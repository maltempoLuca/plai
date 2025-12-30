# FastAPI backend

This directory will host the FastAPI service that wraps the core sync logic in `core/video_editor.py`.

Suggested layout:
- `api/app.py` (FastAPI entrypoint)
- `api/routes/` for request handling
- `api/schemas/` for request/response models
- `api/services/` for orchestration that calls into `core.video_editor`
