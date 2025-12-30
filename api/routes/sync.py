from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import SyncRequest, SyncResponse
from api.services.sync import plan_sync_job

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=SyncResponse)
async def create_sync_request(payload: SyncRequest) -> SyncResponse:
    """
    Accept a sync request. File upload wiring will be added in the next step; for now
    this only validates metadata and returns a placeholder status.
    """
    if not payload.starts:
        raise HTTPException(status_code=400, detail="At least one start offset is required.")
    return plan_sync_job(payload)
