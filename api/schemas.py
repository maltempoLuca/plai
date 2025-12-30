from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, conint, conlist, validator


class AudioMode(str, Enum):
    NONE = "none"
    MIX = "mix"


AudioSelection = Union[AudioMode, conint(ge=1)]


class SyncRequest(BaseModel):
    """
    Request payload validated via Pydantic (preferred here over a bare dataclass for parsing and OpenAPI docs).
    """
    starts: conlist(float, min_items=1) = Field(..., description="Per-video start offsets (seconds).")
    labels: Optional[List[Optional[str]]] = Field(None, description="Optional labels for each video tile.")
    audio: AudioSelection = Field(
        AudioMode.NONE,
        description="Audio selection: none, mix, or the 1-based index of the clip whose audio should be kept.",
    )
    fps: Optional[float] = Field(None, description="Optional output fps; defaults to derived value.")
    height: Optional[int] = Field(None, description="Optional per-tile height; defaults to core value.")
    overwrite: bool = Field(False, description="Allow overwriting an existing output file.")

    @validator("labels")
    def labels_len_matches(cls, v: Optional[List[Optional[str]]], values: dict) -> Optional[List[Optional[str]]]:
        if v is not None and "starts" in values and len(v) not in (0, len(values["starts"])):
            raise ValueError("labels must be empty or match the number of videos")
        return v

    @validator("audio")
    def audio_valid(cls, v: AudioSelection, values: dict) -> AudioSelection:
        if isinstance(v, str):
            normalized = v.lower()
            if normalized not in (AudioMode.NONE.value, AudioMode.MIX.value):
                raise ValueError("audio must be 'none', 'mix', or a positive integer selecting the video track")
            return AudioMode(normalized)

        if isinstance(v, int):
            if v < 1:
                raise ValueError("audio track index must be >= 1")
            starts = values.get("starts")
            if starts is not None and v > len(starts):
                raise ValueError("audio track index cannot exceed the number of videos")
            return v

        raise ValueError("audio must be 'none', 'mix', or a positive integer selecting the video track")


class SyncResponse(BaseModel):
    message: str
    status: str = Field("pending", description="Current job status.")
    job_id: Optional[str] = Field(None, description="Job identifier when async processing is added.")
