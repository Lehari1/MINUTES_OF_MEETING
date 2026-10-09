## Project

- This workspace contains a Next.js App Router frontend in `frontend/` and a FastAPI backend in `backend/`.
- Keep meeting processing and Hugging Face credentials in the backend. Never expose `HF_TOKEN` via `NEXT_PUBLIC_*`, client components, API responses, or logs.
- `backend/app/ml_service.py` is the owning layer for Whisper transcription and Qwen structured minutes. Preserve the configured notebook models unless requirements change.
- The API contract and Pydantic response models are in `backend/app/main.py` and `backend/app/schemas.py`.
- Frontend API calls use `NEXT_PUBLIC_API_BASE_URL`, defaulting to `http://localhost:8000`.
- Local JSON persistence is for single-user development only; do not describe it as multi-user production storage.

## Validation

- Backend tests: `python -m pytest backend/tests`
- Frontend type/build check: `npm --prefix frontend run build`
- Frontend lint: `npm --prefix frontend run lint`
- Keep `.env`, local meeting data, Python environments, and model caches out of version control.
