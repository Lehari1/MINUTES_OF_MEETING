from time import sleep

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas import MeetingMinutes
from backend.app import main as api

client = TestClient(app)


def test_health_does_not_require_model_credentials():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_loads_each_model_once(monkeypatch):
    loaded = []
    monkeypatch.setattr(api, "load_whisper_model", lambda: loaded.append("whisper"))
    monkeypatch.setattr(api, "load_qwen_model", lambda: loaded.append("qwen"))

    with TestClient(api.app):
        pass

    assert loaded == ["whisper", "qwen"]


def test_model_status_does_not_expose_configuration_or_credentials():
    response = client.get("/api/models/status")
    assert response.status_code == 200
    assert response.json()["status"] in {"queued", "disabled", "loading", "ready", "failed"}
    assert "HF_TOKEN" not in response.text


def test_process_rejects_missing_source():
    response = client.post("/api/meetings/process")
    assert response.status_code == 400
    assert "exactly one" in response.json()["detail"]


def test_process_rejects_unsupported_audio():
    response = client.post(
        "/api/meetings/process",
        files={"audio_file": ("meeting.exe", b"invalid", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_meeting_detail_returns_not_found_for_unknown_id():
    response = client.get("/api/meetings/not-a-real-id")
    assert response.status_code == 404


def test_transcript_job_completes_without_loading_models(monkeypatch):
    monkeypatch.setattr(api, "generate_minutes", lambda transcript: MeetingMinutes(summary="Team aligned on next steps."))
    monkeypatch.setattr(api, "save_meeting", lambda meeting: None)
    monkeypatch.setattr(api, "get_meeting", lambda meeting_id: api.MeetingRecord(
        id=meeting_id,
        title="Planning",
        source_type="transcript",
        created_at=api.datetime.now(api.timezone.utc),
        transcript="We agreed to proceed with the launch plan.",
        minutes=MeetingMinutes(summary="Team aligned on next steps."),
    ))

    response = client.post(
        "/api/meetings/jobs",
        data={"title": "Planning", "transcript_text": "We agreed to proceed with the launch plan."},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    for _ in range(20):
        status = client.get(f"/api/meetings/jobs/{job_id}")
        if status.json()["status"] in {"completed", "failed"}:
            break
        sleep(0.01)

    assert status.status_code == 200
    assert status.json()["status"] == "completed"
    assert status.json()["stage"] == "completed"
    assert status.json()["meeting"]["minutes"]["summary"] == "Team aligned on next steps."
