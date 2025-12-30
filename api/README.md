# FastAPI backend

This directory hosts the FastAPI service that wraps the core sync logic in `core/video_editor.py`.

Suggested layout:
- `api/app.py` (FastAPI entrypoint) – `uvicorn api.app:app --reload`
- `api/routes/` for request handling
- `api/schemas/` for request/response models
- `api/services/` for orchestration that calls into `core.video_editor`
