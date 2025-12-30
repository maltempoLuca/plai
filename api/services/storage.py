"""
Temporary storage helpers for uploaded videos.

Current strategy:
- Store uploads under a per-request directory inside /tmp (or $SYNC_TMP_DIR).
- Files are short-lived; a future task will enforce TTL or external storage (e.g., S3).
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Iterable, List, Tuple

from fastapi import UploadFile

DEFAULT_TMP_BASE = Path(os.getenv("SYNC_TMP_DIR", "/tmp/plai-sync"))


def ensure_tmp_base(base: Path = DEFAULT_TMP_BASE) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    return base


async def persist_uploads(
    files: Iterable[UploadFile],
    base: Path = DEFAULT_TMP_BASE,
) -> Tuple[Path, List[Path]]:
    """
    Persist uploaded files to a unique temp directory.

    Returns:
        job_dir: directory containing the persisted files.
        paths: list of file paths in the order received.
    """
    ensure_tmp_base(base)
    job_dir = base / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=False)

    saved: List[Path] = []
    for idx, upload in enumerate(files, start=1):
        suffix = Path(upload.filename or "").suffix or ".bin"
        dest = job_dir / f"video{idx}{suffix}"
        with dest.open("wb") as fh:
            while True:
                chunk = await upload.read(1_048_576)
                if not chunk:
                    break
                fh.write(chunk)
        saved.append(dest)
    return job_dir, saved


def cleanup_job_dir(job_dir: Path) -> None:
    """Remove a job directory. Safe to call during future TTL enforcement."""
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
