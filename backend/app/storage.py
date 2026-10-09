import json
import threading
from pathlib import Path

from .config import MEETINGS_FILE
from .schemas import MeetingRecord

_lock = threading.RLock()


def list_meetings(query: str = "", source_type: str = "") -> list[MeetingRecord]:
    with _lock:
        if not MEETINGS_FILE.exists():
            return []
        try:
            raw_records = json.loads(MEETINGS_FILE.read_text(encoding="utf-8"))
            records = [MeetingRecord.model_validate(item) for item in raw_records]
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return []

    normalized_query = query.casefold().strip()
    return [
        record
        for record in records
        if (not source_type or record.source_type == source_type)
        and (
            not normalized_query
            or normalized_query in record.title.casefold()
            or normalized_query in record.transcript.casefold()
            or normalized_query in record.minutes.summary.casefold()
        )
    ]


def get_meeting(meeting_id: str) -> MeetingRecord | None:
    return next((item for item in list_meetings() if item.id == meeting_id), None)


def save_meeting(meeting: MeetingRecord) -> None:
    with _lock:
        MEETINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        records = list_meetings()
        records.insert(0, meeting)
        temporary_path = MEETINGS_FILE.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps([record.model_dump(mode="json") for record in records], indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(MEETINGS_FILE)
