"""
Service stubs for syncing videos via the core pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from api.schemas import SyncRequest, SyncResponse
from api.services.storage import cleanup_job_dir

def plan_sync_job(payload: SyncRequest, video_paths: List[Path], job_dir: Path) -> SyncResponse:
    """
    Placeholder for future job planning. For Phase A scaffolding, this validates
    the payload shape, asserts counts match, and acknowledges receipt.
    """
    if len(video_paths) != len(payload.starts):
        cleanup_job_dir(job_dir)
        raise ValueError("Number of videos must match number of start offsets.")

    return SyncResponse(
        message=(
            f"Sync request received with {len(video_paths)} videos. "
            "Processing is not yet implemented; files are stored in temporary storage."
        ),
        status="pending",
        job_id=str(job_dir.name),
    )
