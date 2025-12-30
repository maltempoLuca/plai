"""
Service helpers for syncing videos via the core pipeline.
"""

from __future__ import annotations

import json
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from api.schemas import AudioMode, SyncRequest, SyncResponse
from core.video_editor import (
    SideBySideComparisonRequest,
    StartMode,
    export_side_by_side_comparison,
)

TEMP_ROOT = Path("tmp/sync-jobs")
CHUNK_SIZE = 1024 * 1024  # 1 MiB


async def plan_sync_job(payload: SyncRequest, files: Sequence[UploadFile]) -> SyncResponse:
    """
    Persist uploads to temp storage, invoke the core renderer, and return job metadata.
    """
    job_id = uuid4().hex
    job_dir = TEMP_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    saved = await _persist_uploads(job_dir, files)
    _write_metadata(job_dir, payload, saved)

    exit_code = await _render_side_by_side(payload, saved, job_dir)
    if exit_code != 0:
        raise HTTPException(status_code=500, detail=f"Render failed with exit code {exit_code}")

    return SyncResponse(
        message="Render completed",
        status="completed",
        job_id=job_id,
    )


async def _persist_uploads(job_dir: Path, files: Sequence[UploadFile]) -> List[Path]:
    """
    Stream uploaded files to the per-job temp directory.
    """
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
    """
    Write an UploadFile to disk using chunked reads to avoid buffering the whole file.
    """
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
    """
    Persist minimal job metadata for cleanup and traceability.
    """
    metadata_path = job_dir / "job.json"
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload.dict(),
        "files": [str(path.name) for path in files],
        "note": "Temp storage only; TTL cleanup expected in Phase A sweeper.",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))


async def _render_side_by_side(payload: SyncRequest, files: List[Path], job_dir: Path) -> int:
    """
    Invoke the core video editor to produce a side-by-side output for this job.
    """
    audio = payload.audio
    if isinstance(audio, AudioMode):
        audio_value = audio.value
    else:
        audio_value = f"video{audio}"

    request = SideBySideComparisonRequest(
        videos=[str(path) for path in files],
        starts=list(payload.starts),
        labels=payload.labels,
        output=str(job_dir / "output.mp4"),
        start_mode=StartMode.SYNC,
        fps=payload.fps,
        height=payload.height or 1080,
        audio=audio_value,
        overwrite=payload.overwrite,
    )

    try:
        return await asyncio.to_thread(export_side_by_side_comparison, request)
    except Exception as exc:  # noqa: BLE001 - surface underlying render error
        raise HTTPException(status_code=500, detail=f"Render failed: {exc}") from exc
