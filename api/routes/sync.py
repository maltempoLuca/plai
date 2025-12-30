from __future__ import annotations

import json
from json import JSONDecodeError
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from api.schemas import SyncRequest, SyncResponse
from api.services.sync import plan_sync_job

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=SyncResponse)
async def create_sync_request(
    metadata: str = Form(..., description="JSON payload matching SyncRequest."),
    files: List[UploadFile] = File(..., description="Video files to sync."),
) -> SyncResponse:
    """
    Accept a sync request with multipart uploads and JSON metadata.
    """
    try:
        payload_dict = json.loads(metadata)
    except JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid metadata JSON: {exc.msg}") from exc

    try:
        payload = SyncRequest(**payload_dict)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc

    if not files:
        raise HTTPException(status_code=400, detail="At least one video file is required.")
    if len(payload.starts) != len(files):
        raise HTTPException(
            status_code=400,
            detail=f"Mismatch between metadata starts ({len(payload.starts)}) and uploaded files ({len(files)}).",
        )

    return await plan_sync_job(payload, files)
