from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    task: str
    owner: str | None = None
    due_date: str | None = None
    status: Literal["pending", "in_progress", "done"] = "pending"


class MeetingMinutes(BaseModel):
    summary: str
    attendees: list[str] = Field(default_factory=list)
    meeting_date: str | None = None
    location: str | None = None
    discussion_points: list[str] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)


class MeetingRecord(BaseModel):
    id: str
    title: str
    source_type: Literal["audio", "transcript"]
    created_at: datetime
    transcript: str
    minutes: MeetingMinutes


class MeetingList(BaseModel):
    meetings: list[MeetingRecord]
    total: int


class MeetingJob(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    stage: Literal["queued", "transcribing", "summarizing", "completed", "failed"]
    message: str
    error: str | None = None
    meeting: MeetingRecord | None = None
