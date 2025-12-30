from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Form, HTTPException, UploadFile, File

from api.schemas import SyncRequest, SyncResponse
from api.services.storage import persist_uploads
from api.services.sync import plan_sync_job

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=SyncResponse)
async def create_sync_request(
    metadata: str = Form(..., description="SyncRequest as JSON string."),
    files: List[UploadFile] = File(..., description="Video files to sync."),
) -> SyncResponse:
    """
    Accept a sync request with multipart uploads. Metadata is provided as a JSON string in the
    `metadata` form field, and videos are provided via repeated `files` fields.
    """
    try:
        payload = SyncRequest.model_validate_json(metadata)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid metadata JSON: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not payload.starts:
        raise HTTPException(status_code=400, detail="At least one start offset is required.")
    if len(files) != len(payload.starts):
        raise HTTPException(
            status_code=400,
            detail="Number of uploaded files must match number of start offsets.",
        )

    job_dir, saved_paths = await persist_uploads(files)
    try:
        return plan_sync_job(payload, saved_paths, job_dir)
    except Exception as exc:
        # Best-effort cleanup if we reject the request after persisting files.
        from api.services.storage import cleanup_job_dir

        cleanup_job_dir(job_dir)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
