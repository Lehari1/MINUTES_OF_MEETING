import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024
MEETINGS_FILE = Path(os.getenv("MEETINGS_FILE", str(BACKEND_DIR / "data" / "meetings.json")))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "openai/whisper-medium.en")
QWEN_MODEL = os.getenv("QWEN_MODEL", "Qwen/Qwen2.5-3B-Instruct")
