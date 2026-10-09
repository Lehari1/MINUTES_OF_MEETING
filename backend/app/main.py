import logging
import tempfile
import threading
import uuid
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from .config import FRONTEND_ORIGINS, MAX_UPLOAD_BYTES
from .ml_service import generate_minutes, load_qwen_model, load_whisper_model, transcribe_audio
from .schemas import MeetingJob, MeetingList, MeetingMinutes, MeetingRecord
from .storage import get_meeting, list_meetings, save_meeting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_job_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="meeting-processor")
_job_lock = threading.RLock()
_jobs: dict[str, dict[str, Any]] = {}
_model_status_lock = threading.RLock()
_model_status = {
    "status": "queued",
    "stage": "queued",
    "message": "Models will load during API startup.",
}


def _preload_models() -> None:
    try:
        with _model_status_lock:
            _model_status.update(status="loading", stage="loading_whisper", message="Loading Whisper before meeting processing.")
        load_whisper_model()
        with _model_status_lock:
            _model_status.update(stage="loading_qwen", message="Whisper is ready. Loading Qwen before meeting processing.")
        load_qwen_model()
        with _model_status_lock:
            _model_status.update(status="ready", stage="ready", message="Whisper and Qwen are loaded and ready.")
        logger.info("Whisper and Qwen are warmed and ready for meeting jobs")
    except Exception:
        with _model_status_lock:
            _model_status.update(
                status="failed",
                stage="failed",
                message="Model warm-up failed. Check HF_TOKEN, available memory, and API logs.",
            )
        logger.exception("Model warm-up failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await run_in_threadpool(_preload_models)
    yield


app = FastAPI(title="Minutes of Meeting API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4", ".mpeg", ".mpga"}
TEXT_EXTENSIONS = {".txt", ".md"}


def _update_job(job_id: str, **updates: Any) -> None:
    with _job_lock:
        _jobs[job_id].update(updates)


def _run_meeting_job(
    job_id: str,
    source_type: str,
    transcript: str,
    title: str,
    audio_payload: bytes | None = None,
    audio_extension: str = "",
) -> None:
    temporary_path: Path | None = None
    try:
        if audio_payload is not None:
            _update_job(job_id, status="running", stage="transcribing", message="Transcribing audio with Whisper…")
            with tempfile.NamedTemporaryFile(delete=False, suffix=audio_extension) as temporary:
                temporary.write(audio_payload)
                temporary_path = Path(temporary.name)
            transcript = transcribe_audio(temporary_path)

        if not transcript.strip():
            raise ValueError("Transcript text cannot be empty.")

        _update_job(job_id, status="running", stage="summarizing", message="Generating the meeting summary with Qwen…")
        minutes = generate_minutes(transcript)
        created_at = datetime.now(timezone.utc)
        record = MeetingRecord(
            id=str(uuid.uuid4()),
            title=title or minutes.meeting_date or f"Meeting · {created_at:%b %d, %Y}",
            source_type=source_type,
            created_at=created_at,
            transcript=transcript,
            minutes=minutes,
        )
        save_meeting(record)
        _update_job(job_id, status="completed", stage="completed", message="Your meeting minutes are ready.", meeting_id=record.id)
    except RuntimeError as exc:
        logger.warning("Meeting model setup failed: %s", exc)
        _update_job(job_id, status="failed", stage="failed", message=str(exc), error=str(exc))
    except ValueError as exc:
        _update_job(job_id, status="failed", stage="failed", message=str(exc), error=str(exc))
    except Exception:
        logger.exception("Background meeting processing failed")
        message = "Meeting processing failed. Check the API logs and model configuration."
        _update_job(job_id, status="failed", stage="failed", message=message, error=message)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/models/status")
def model_status() -> dict[str, str]:
    with _model_status_lock:
        return _model_status.copy()


@app.get("/api/meetings", response_model=MeetingList)
def meetings(
    q: str = Query(default="", max_length=200),
    source_type: str = Query(default="", pattern="^(audio|transcript)?$"),
) -> MeetingList:
    results = list_meetings(query=q, source_type=source_type)
    return MeetingList(meetings=results, total=len(results))


@app.get("/api/meetings/{meeting_id}", response_model=MeetingRecord)
def meeting_detail(meeting_id: str) -> MeetingRecord:
    record = get_meeting(meeting_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return record


@app.get("/api/analytics")
def analytics() -> dict[str, int]:
    records = list_meetings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent = [item for item in records if item.created_at >= cutoff]
    return {
        "total_meetings": len(records),
        "audio_meetings": sum(item.source_type == "audio" for item in records),
        "transcript_meetings": sum(item.source_type == "transcript" for item in records),
        "action_items": sum(len(item.minutes.action_items) for item in records),
        "decisions": sum(len(item.minutes.decisions) for item in records),
        "recent_meetings": len(recent),
    }


@app.post("/api/meetings/process", response_model=MeetingRecord)
async def process_meeting(
    audio_file: UploadFile | None = File(default=None),
    transcript_file: UploadFile | None = File(default=None),
    transcript_text: str | None = Form(default=None),
    title: str | None = Form(default=None),
) -> MeetingRecord:
    provided_sources = sum(
        source is not None and (bool(source.strip()) if isinstance(source, str) else True)
        for source in (audio_file, transcript_file, transcript_text)
    )
    if provided_sources != 1:
        raise HTTPException(status_code=400, detail="Provide exactly one audio file, transcript file, or transcript text.")

    source_type = "transcript"
    transcript = ""
    temporary_path: Path | None = None
    try:
        if audio_file is not None or transcript_file is not None:
            upload = audio_file or transcript_file
            filename = upload.filename or ""
            extension = Path(filename).suffix.lower()
            supported = AUDIO_EXTENSIONS if audio_file is not None else TEXT_EXTENSIONS
            if extension not in supported:
                formats = ", ".join(sorted(item.lstrip(".") for item in supported))
                raise HTTPException(status_code=415, detail=f"Unsupported file type. Supported formats: {formats}.")

            payload = await upload.read(MAX_UPLOAD_BYTES + 1)
            if len(payload) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="File exceeds the configured upload limit.")
            if not payload:
                raise HTTPException(status_code=400, detail="The uploaded file is empty.")

            if audio_file is not None:
                source_type = "audio"
                with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temporary:
                    temporary.write(payload)
                    temporary_path = Path(temporary.name)
                transcript = await run_in_threadpool(transcribe_audio, temporary_path)
            else:
                try:
                    transcript = payload.decode("utf-8-sig").strip()
                except UnicodeDecodeError as exc:
                    raise HTTPException(status_code=400, detail="Transcript files must be UTF-8 encoded text.") from exc
        else:
            transcript = (transcript_text or "").strip()

        if not transcript:
            raise HTTPException(status_code=400, detail="Transcript text cannot be empty.")
        minutes = await run_in_threadpool(generate_minutes, transcript)
        created_at = datetime.now(timezone.utc)
        record = MeetingRecord(
            id=str(uuid.uuid4()),
            title=(title or "").strip() or minutes.meeting_date or f"Meeting · {created_at:%b %d, %Y}",
            source_type=source_type,
            created_at=created_at,
            transcript=transcript,
            minutes=minutes,
        )
        save_meeting(record)
        return record
    except HTTPException:
        raise
    except RuntimeError as exc:
        logger.warning("Meeting model setup failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Meeting processing failed")
        raise HTTPException(status_code=500, detail="Meeting processing failed. Check the API logs and model configuration.") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        for upload in (audio_file, transcript_file):
            if upload is not None:
                await upload.close()


@app.post("/api/meetings/jobs", response_model=MeetingJob, status_code=202)
async def create_meeting_job(
    audio_file: UploadFile | None = File(default=None),
    transcript_file: UploadFile | None = File(default=None),
    transcript_text: str | None = Form(default=None),
    title: str | None = Form(default=None),
) -> MeetingJob:
    provided_sources = sum(
        source is not None and (bool(source.strip()) if isinstance(source, str) else True)
        for source in (audio_file, transcript_file, transcript_text)
    )
    if provided_sources != 1:
        raise HTTPException(status_code=400, detail="Provide exactly one audio file, transcript file, or transcript text.")

    source_type = "transcript"
    transcript = ""
    audio_payload: bytes | None = None
    audio_extension = ""
    try:
        if audio_file is not None or transcript_file is not None:
            upload = audio_file or transcript_file
            extension = Path(upload.filename or "").suffix.lower()
            supported = AUDIO_EXTENSIONS if audio_file is not None else TEXT_EXTENSIONS
            if extension not in supported:
                formats = ", ".join(sorted(item.lstrip(".") for item in supported))
                raise HTTPException(status_code=415, detail=f"Unsupported file type. Supported formats: {formats}.")

            payload = await upload.read(MAX_UPLOAD_BYTES + 1)
            if len(payload) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="File exceeds the configured upload limit.")
            if not payload:
                raise HTTPException(status_code=400, detail="The uploaded file is empty.")

            if audio_file is not None:
                source_type = "audio"
                audio_payload = payload
                audio_extension = extension
            else:
                try:
                    transcript = payload.decode("utf-8-sig").strip()
                except UnicodeDecodeError as exc:
                    raise HTTPException(status_code=400, detail="Transcript files must be UTF-8 encoded text.") from exc
        else:
            transcript = (transcript_text or "").strip()

        if source_type == "transcript" and not transcript:
            raise HTTPException(status_code=400, detail="Transcript text cannot be empty.")

        job_id = str(uuid.uuid4())
        job = {
            "job_id": job_id,
            "status": "queued",
            "stage": "queued",
            "message": "Upload received. Waiting for the meeting processor…",
            "error": None,
            "meeting_id": None,
        }
        with _job_lock:
            _jobs[job_id] = job
        _job_executor.submit(
            _run_meeting_job,
            job_id,
            source_type,
            transcript,
            (title or "").strip(),
            audio_payload,
            audio_extension,
        )
        return MeetingJob(**job)
    finally:
        for upload in (audio_file, transcript_file):
            if upload is not None:
                await upload.close()


@app.get("/api/meetings/jobs/{job_id}", response_model=MeetingJob)
def meeting_job_status(job_id: str) -> MeetingJob:
    with _job_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Meeting processing job not found.")
        job_data = job.copy()

    meeting = get_meeting(job_data["meeting_id"]) if job_data["meeting_id"] else None
    return MeetingJob(**{**job_data, "meeting": meeting})
