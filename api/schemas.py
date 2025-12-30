from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, conlist, validator


class AudioMode(str, Enum):
    NONE = "none"
    MIX = "mix"
    VIDEO1 = "video1"
    VIDEO2 = "video2"
    VIDEO3 = "video3"


class SyncRequest(BaseModel):
    starts: conlist(float, min_items=1) = Field(..., description="Per-video start offsets (seconds).")
    labels: Optional[List[Optional[str]]] = Field(None, description="Optional labels for each video tile.")
    audio: AudioMode = Field(AudioMode.NONE, description="Audio selection: none, mix, or a single video track.")
    fps: Optional[float] = Field(None, description="Optional output fps; defaults to derived value.")
    height: Optional[int] = Field(None, description="Optional per-tile height; defaults to core value.")
    overwrite: bool = Field(False, description="Allow overwriting an existing output file.")

    @validator("labels")
    def labels_len_matches(cls, v: Optional[List[Optional[str]]], values: dict) -> Optional[List[Optional[str]]]:
        if v is not None and "starts" in values and len(v) not in (0, len(values["starts"])):
            raise ValueError("labels must be empty or match the number of videos")
        return v


class SyncResponse(BaseModel):
    message: str
    status: str = Field("pending", description="Current job status.")
    job_id: Optional[str] = Field(None, description="Job identifier when async processing is added.")
