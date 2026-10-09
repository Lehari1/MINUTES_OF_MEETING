# 🎙️ Minute — AI-Powered Minutes of Meeting

**Minute** is a local-first, privacy-focused application that converts meeting audio recordings or raw transcripts into clean, structured, and actionable **Minutes of Meeting (MoM)**.

It uses **OpenAI Whisper** for speech-to-text transcription and **Qwen 2.5** for intelligent summarization and extraction of discussions, decisions, key takeaways, and action items.

---

## ✨ Features

### 🎧 Audio Transcription
Upload meeting recordings in common formats:

- `.mp3`
- `.wav`
- `.m4a`
- `.flac`
- `.ogg`
- `.webm`
- `.mp4`
- `.mpeg`
- `.mpga`

Audio is transcribed locally using **Whisper**.

### 📄 Transcript Ingestion

You can also provide meeting content directly through:

- `.txt` files
- `.md` files
- Pasted transcript text

### 🧠 Structured Minutes Generation

Minute automatically extracts and organizes:

- **Executive Summary**
- **Attendees**
- **Date & Location**
- **Discussion Points**
- **Key Takeaways**
- **Decisions Made**
- **Action Items**
  - Owner
  - Deadline
  - Status

Supported action-item statuses:

```text
pending
in_progress
done
```

### 🔍 Search & Filtering

Search across:

- Meeting titles
- Summaries
- Transcripts

Filter meetings by source type such as:

- Audio
- Transcript
- Pasted text

### 📊 Meeting Analytics

View quick statistics for:

- Total meetings
- Total decisions
- Total action items
- Meeting activity

### 🔒 Local & Privacy-Focused

Minute is designed to run locally on your machine.

Meeting recordings and generated meeting data are not uploaded to an external cloud storage service.

---

## 🏗️ Architecture

```text
┌───────────────────────────┐
│      Next.js Frontend     │
│                           │
│   http://localhost:3000   │
└─────────────┬─────────────┘
              │
              │ HTTP / REST API
              ▼
┌───────────────────────────┐
│      FastAPI Backend      │
│                           │
│   http://localhost:8000   │
└─────────────┬─────────────┘
              │
              ▼
┌────────────────────────────────────┐
│          Local AI Pipeline          │
│                                    │
│  Whisper                           │
│  Audio ────────────────► Text     │
│                                    │
│  Qwen 2.5                          │
│  Transcript ────────────► MoM     │
│                                    │
│  Local JSON Data Store              │
└────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, React |
| Backend | FastAPI, Python |
| Speech-to-Text | OpenAI Whisper |
| LLM | Qwen 2.5 |
| API | REST |
| Storage | Local JSON |
| Package Management | npm, pip |
| AI Models | Hugging Face |

---

## 📋 Prerequisites

Make sure the following are installed:

### Node.js

**Node.js 20.9 or newer**

Download: https://nodejs.org/

### Python

**Python 3.10 or newer**

Download: https://www.python.org/

### FFmpeg

FFmpeg is required for audio decoding.

Download: https://ffmpeg.org/

Make sure `ffmpeg` is available in your system `PATH`.

Verify:

```powershell
ffmpeg -version
```

### Hugging Face Account

A Hugging Face account and a **Read Access Token** are required to download the models.

Create a token from:

https://huggingface.co/settings/tokens

---

## ⚙️ Installation

### 1. Clone the Repository

```powershell
git clone <your-repository-url>
cd minutes_of_meeting
```

If the project is already downloaded:

```powershell
cd C:\Users\hp\Downloads\minutes_of_meeting
```

### 2. Backend Setup

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 3. Configure Environment Variables

```powershell
Copy-Item .env.example backend/.env
```

Open:

```text
backend/.env
```

and configure:

```dotenv
HF_TOKEN=hf_your_hugging_face_token_here
FRONTEND_ORIGINS=http://localhost:3000
MAX_UPLOAD_MB=100
```

### 4. Frontend Setup

```powershell
npm --prefix frontend install
```

---

## ▶️ Running the Application

Minute requires **two development servers**.

### Terminal 1 — Backend

```powershell
.\.venv\Scripts\Activate.ps1

python -m uvicorn app.main:app --app-dir backend --port 8000 --reload --reload-dir backend
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

### Terminal 2 — Frontend

```powershell
npm --prefix frontend run dev
```

Open:

```text
http://localhost:3000
```

---

## ⚡ Performance Configuration

By default:

```text
Whisper: openai/whisper-medium.en
Qwen:    Qwen/Qwen2.5-3B-Instruct
```

### 🚀 Recommended CPU Configuration

For systems without an NVIDIA GPU:

```dotenv
WHISPER_MODEL=openai/whisper-base.en
QWEN_MODEL=Qwen/Qwen2.5-0.5B-Instruct
```

| Configuration | Whisper | Qwen | CPU Performance | Quality |
|---|---|---|---|---|
| Fastest | `whisper-base.en` | `Qwen2.5-0.5B` | ⚡ Very Fast | Good |
| Balanced | `whisper-small.en` | `Qwen2.5-1.5B` | ⚖️ Moderate | High |
| Default / GPU | `whisper-medium.en` | `Qwen2.5-3B` | 🐢 Slow on CPU | Best |

Actual processing time depends on audio duration, CPU, RAM, model loading time, and transcript length.

---

## 🎮 NVIDIA GPU Acceleration

If you have an NVIDIA GPU:

```powershell
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu124
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health check |
| `GET` | `/api/models/status` | Whisper and Qwen model status |
| `GET` | `/api/meetings` | List processed meetings |
| `GET` | `/api/meetings/{id}` | Retrieve meeting details |
| `GET` | `/api/analytics` | Meeting analytics |
| `POST` | `/api/meetings/jobs` | Submit asynchronous processing job |
| `GET` | `/api/meetings/jobs/{job_id}` | Check processing status |
| `POST` | `/api/meetings/process` | Process audio/transcript synchronously |

---

## 🧪 Testing & Quality Checks

### Backend Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
```

### Frontend Linting

```powershell
npm --prefix frontend run lint
```

### Production Build

```powershell
npm --prefix frontend run build
```

---

## 📁 Data Storage

Processed meeting information is stored locally in:

```text
backend/data/meetings.json
```

The data includes structured minutes, decisions, action items, and other extracted meeting information.

---

## 🔐 Privacy

Minute follows a **local-first architecture**:

```text
Meeting Audio
      ↓
Local Whisper
      ↓
Transcript
      ↓
Local Qwen 2.5
      ↓
Structured MoM
      ↓
Local Storage
```

No external cloud recording storage is required.

> Model downloads require an internet connection during initial setup. Once the models are available locally, inference can be performed locally.

---

## 📌 Project Structure

```text
minutes_of_meeting/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── ...
│   │
│   ├── data/
│   │   └── meetings.json
│   │
│   ├── tests/
│   │   └── ...
│   │
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── .env.example
└── README.md
```

---

## 🚀 Future Improvements

- Speaker diarization
- Automatic speaker identification
- Calendar integration
- PDF/DOCX export
- Automatic action-item notifications
- Persistent database support
- Meeting comparison
- Action-item reminders
- Additional local LLM support
- GPU/CPU auto-detection
- Streaming transcription
- Real-time meeting transcription

---

## ⭐ About

**Minute** is designed to make meeting documentation faster and more actionable while keeping meeting data under the user's control.

**Record → Transcribe → Summarize → Extract Decisions → Assign Actions**
