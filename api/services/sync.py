"""
Service stubs for syncing videos via the core pipeline.
"""

from __future__ import annotations

from api.schemas import SyncRequest, SyncResponse


def plan_sync_job(payload: SyncRequest) -> SyncResponse:
    """
    Placeholder for future job planning. For Phase A scaffolding, this only validates
    the payload shape and acknowledges receipt.
    """
    return SyncResponse(
        message="Sync request received; processing not yet implemented.",
        status="pending",
        job_id=None,
    )
