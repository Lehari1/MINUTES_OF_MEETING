# FastAPI backend

The API is implemented in `app/`. From the workspace root, start it with:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend
```

Put `HF_TOKEN` in `backend/.env` (copy the workspace `.env.example`); it is loaded by `app/config.py` and is not exposed by any API endpoint. Whisper and Qwen load once during API startup, using CUDA when available and CPU otherwise. Startup may take several minutes and require several gigabytes of memory. Local meeting records are written to `backend/data/meetings.json`.

The dashboard uses `POST /api/meetings/jobs` and polls `GET /api/meetings/jobs/{job_id}` for transcription/summarization stage updates. One in-process worker runs one job at a time; loaded model instances are reused between jobs. This queue is suitable for a single-user local app, not a multi-worker or multi-user deployment.

For faster CPU inference at some quality cost, set `WHISPER_MODEL=openai/whisper-small.en` and `QWEN_MODEL=Qwen/Qwen2.5-0.5B-Instruct` in `backend/.env`. The notebook model IDs remain the defaults. For GPU acceleration, install a PyTorch build compatible with the machine's CUDA setup.

Install backend dependencies from the workspace root with `python -m pip install -r backend/requirements.txt`. Choose a PyTorch build suited to the host before running model inference. Run API tests with `python -m pytest backend/tests`.
