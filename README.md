# 🎙️ Minute - AI-Powered Minutes of Meeting

**Minute** is a local-first, privacy-focused application that turns meeting audio recordings or raw text transcripts into cleanly structured, actionable Minutes of Meeting (MoM).

Powered by **OpenAI Whisper** for speech-to-text audio transcription and **Qwen 2.5** for intelligent summarization and extraction of discussion points, decisions, key takeaways, and owner-assigned action items.

---

## 🌟 Features

- 🎧 **Audio Transcription**: Upload audio files (`.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.webm`, `.mp4`, `.mpeg`, `.mpga`) transcribed locally with Whisper.
- 📄 **Direct Transcript Ingestion**: Upload UTF-8 `.txt` / `.md` transcript files or directly paste text notes.
- 🧠 **Structured Minutes Generation**: Automatically extracts:
  - **Executive Summary**
  - **Attendees, Date & Location**
  - **Discussion Points & Key Takeaways**
  - **Decisions Made**
  - **Action Items** with assigned owners, deadlines, and statuses (`pending`, `in_progress`, `done`)
- 🔍 **Search & Filtering**: Search meeting titles, summaries, and transcripts with real-time filtering by source type.
- 📊 **Meeting Analytics**: Quick metrics for total meetings, decisions, action items, and activity.
- 🔒 **Local & Private**: Runs completely on your machine — no external cloud recording storage.

---

## 🏗️ System Architecture

```text
┌───────────────────────────┐         ┌───────────────────────────┐
│     Next.js Frontend      │ ──────> │      FastAPI Backend      │
│   http://localhost:3000   │ <────── │   http://localhost:8000   │
└───────────────────────────┘         └─────────────┬─────────────┘
                                                    │
                                      ┌─────────────┴─────────────┐
                                      │    Local AI Pipeline      │
                                      │  • Whisper (Audio -> Text)│
                                      │  • Qwen 2.5 (LLM Minutes) │
                                      │  • Local JSON Data Store  │
                                      └───────────────────────────┘
```

---

## 📋 Prerequisites

Ensure you have the following installed on your system:

- **Node.js**: `v20.9` or newer ([Download Node.js](https://nodejs.org/))
- **Python**: `3.10` or newer ([Download Python](https://www.python.org/))
- **FFmpeg**: Required for audio decoding ([Download FFmpeg](https://ffmpeg.org/)) — ensure `ffmpeg` is available on your system `PATH`.
- **Hugging Face Account & Token**: A free read access token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

---

## ⚙️ Quick Setup & Installation

### Step 1: Clone or Navigate to the Workspace
```powershell
cd c:\Users\hp\Downloads\minutes_of_meeting
```

---

### Step 2: Backend Setup (Python & FastAPI)

1. **Create and activate a Python virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. **Install Python backend dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r backend/requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `backend/.env`:
   - **Windows (PowerShell)**:
     ```powershell
     Copy-Item .env.example backend/.env
     ```
   - **Linux / macOS**:
     ```bash
     cp .env.example backend/.env
     ```

   Open `backend/.env` and insert your Hugging Face Access Token:
   ```dotenv
   HF_TOKEN=hf_your_hugging_face_token_here
   FRONTEND_ORIGINS=http://localhost:3000
   MAX_UPLOAD_MB=100
   ```

---

### Step 3: Frontend Setup (Next.js & React)

In a new terminal window:

```powershell
npm --prefix frontend install
```

---

## ▶️ Starting the Application

Run the backend and frontend in two separate terminals:

### Terminal 1 — Start the Backend Server

```powershell
# Make sure virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Start the FastAPI server
python -m uvicorn app.main:app --app-dir backend --port 8000 --reload --reload-dir backend
```
> 📍 **Backend URL**: [http://127.0.0.1:8000](http://127.0.0.1:8000)  
> 📖 **API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Terminal 2 — Start the Frontend Dev Server

```powershell
npm --prefix frontend run dev
```
> 🌐 **Frontend UI**: [http://localhost:3000](http://localhost:3000)

---

## ⚡ Performance & Low-Latency Configuration (CPU vs GPU)

By default, the application runs `openai/whisper-medium.en` and `Qwen/Qwen2.5-3B-Instruct`. If you are running locally on **CPU** without an NVIDIA GPU, processing may take 30–90 seconds per meeting.

### 🚀 For Ultra-Fast CPU Inference (Recommended)
Add the following model configuration overrides to your `backend/.env` file:

```dotenv
WHISPER_MODEL=openai/whisper-base.en
QWEN_MODEL=Qwen/Qwen2.5-0.5B-Instruct
```

| Model Setting | Model Size | Speed (CPU) | Quality |
|---|---|---|---|
| **Fastest (Default CPU)** | `whisper-base.en` + `Qwen2.5-0.5B` | ⚡ Very Fast (~5–10s) | Good |
| **Balanced** | `whisper-small.en` + `Qwen2.5-1.5B` | ⚖️ Moderate (~15–30s) | High |
| **Default / GPU** | `whisper-medium.en` + `Qwen2.5-3B` | 🐢 Slower on CPU / Fast on GPU | Best |

### 🎮 To Enable GPU Acceleration (NVIDIA CUDA)
If you have an NVIDIA GPU, install the CUDA build of PyTorch:
```powershell
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu124
```

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health check |
| `GET` | `/api/models/status` | Real-time status of Whisper & Qwen model readiness |
| `GET` | `/api/meetings` | List all processed meetings (supports `?q=search&source_type=audio`) |
| `GET` | `/api/meetings/{id}` | Retrieve meeting detail and structured minutes |
| `GET` | `/api/analytics` | Summary analytics (total meetings, action items, decisions) |
| `POST` | `/api/meetings/jobs` | Submit async audio/transcript processing job (returns `job_id`) |
| `GET` | `/api/meetings/jobs/{job_id}` | Poll background job progress status |
| `POST` | `/api/meetings/process` | Synchronous processing endpoint |

---

## 🧪 Running Tests & Quality Checks

```powershell
# Run backend test suite (API tests + evals suite)
.\.venv\Scripts\python.exe -m pytest backend/tests

# Lint and build frontend
npm --prefix frontend run lint
npm --prefix frontend run build
```

---

## 📊 AI Pipeline Evaluation & Benchmarks

The repository includes a dedicated benchmark suite under `backend/evals/` that evaluates speech-to-text (Whisper) and minutes extraction (Qwen LLM) against ground truth scenarios:

- **Dataset**: `backend/evals/dataset.json` (sprint planning, outage post-mortem, product strategy)
- **Metrics**: `backend/evals/metrics.py` (ROUGE-1/2/L, Attendee F1, Decision F1, Action Task F1, Owner Attribution Accuracy, WER/CER)
- **Reports**: Generates `eval_report.json` and `eval_report.md` with an executive scorecard

```powershell
# Run full evaluation benchmark (Qwen LLM + Whisper ASR):
.\.venv\Scripts\python.exe backend/evals/run_evals.py

# Run text-only evaluation (skips Whisper audio file transcription):
.\.venv\Scripts\python.exe backend/evals/run_evals.py --skip-audio

# Run quick verification (mock mode, tests pipeline & metrics in < 1s):
.\.venv\Scripts\python.exe backend/evals/run_evals.py --mock
```


---

## 📁 Storage
All meetings and extracted data are stored locally in:
`backend/data/meetings.json`
