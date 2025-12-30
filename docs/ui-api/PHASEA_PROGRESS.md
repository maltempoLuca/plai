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

## Next steps
- Wire multipart file uploads (videos) into the `/sync` route and persist them to temp storage.
- Call `core/video_editor.py` from the service layer to perform the side-by-side render.
- Add basic error handling and validation messages surfaced through the API response.

## Next steps
- Scaffold API and data contracts; wire `core/video_editor.py` into a synchronous handler.
- Build the MVP frontend and hook it to the endpoint.
- Add validation and error handling; document limits.
