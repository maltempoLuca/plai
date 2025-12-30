"""
Service helpers for syncing videos via the core pipeline.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from api.schemas import SyncRequest, SyncResponse

TEMP_ROOT = Path("tmp/sync-jobs")
CHUNK_SIZE = 1024 * 1024  # 1 MiB


async def plan_sync_job(payload: SyncRequest, files: Sequence[UploadFile]) -> SyncResponse:
    """
    Persist uploads to temp storage and return job metadata.
    """
    job_id = uuid4().hex
    job_dir = TEMP_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    saved = await _persist_uploads(job_dir, files)
    _write_metadata(job_dir, payload, saved)

    return SyncResponse(
        message="Uploaded files stored; processing not yet implemented.",
        status="pending",
        job_id=job_id,
    )


async def _persist_uploads(job_dir: Path, files: Sequence[UploadFile]) -> List[Path]:
    saved_paths: List[Path] = []
    for index, upload in enumerate(files):
        suffix = Path(upload.filename or "").suffix or ".bin"
        dest = job_dir / f"source_{index}{suffix}"
        try:
            await _write_file(upload, dest)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to persist upload: {exc}") from exc
        saved_paths.append(dest)
    return saved_paths


async def _write_file(upload: UploadFile, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as outfile:
        while True:
            chunk = await upload.read(CHUNK_SIZE)
            if not chunk:
                break
            outfile.write(chunk)
        outfile.flush()
        os.fsync(outfile.fileno())
    await upload.seek(0)
    await upload.close()


def _write_metadata(job_dir: Path, payload: SyncRequest, files: Iterable[Path]) -> None:
    metadata_path = job_dir / "job.json"
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload.dict(),
        "files": [str(path.name) for path in files],
        "note": "Temp storage only; TTL cleanup expected in Phase A sweeper.",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))
