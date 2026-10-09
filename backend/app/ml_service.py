import json
import re
import threading
from pathlib import Path
from typing import Any

from .config import HF_TOKEN, QWEN_MODEL, WHISPER_MODEL
from .schemas import MeetingMinutes

_asr = None
_tokenizer = None
_llm = None
_asr_lock = threading.Lock()
_llm_lock = threading.Lock()
_load_lock = threading.Lock()

# PyAV 14+ removed 'metadata_errors' keyword argument which faster_whisper 1.2 still passes
try:
    import av

    _orig_av_open = av.open

    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)

    av.open = _safe_av_open
except ImportError:
    pass

_SYSTEM_PROMPT = """You create accurate, concise meeting minutes from a transcript. Return only valid JSON, without markdown fences, using exactly these keys: summary (string), attendees (array of strings), meeting_date (string or null), location (string or null), discussion_points (array of strings), key_takeaways (array of strings), decisions (array of strings), action_items (array of objects with task, owner, due_date, status). Use null or an empty array when the transcript does not provide information. Never invent attendees, dates, owners, decisions, or deadlines. Action item status must be pending, in_progress, or done."""


def _require_token() -> str:
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN is missing. Add it to backend/.env and restart the API.")
    return HF_TOKEN


def _load_asr():
    global _asr
    if _asr is None:
        with _load_lock:
            if _asr is None:
                token = _require_token()
                try:
                    import torch
                    from faster_whisper import WhisperModel

                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    compute_type = "float16" if device == "cuda" else "int8"
                    model_size = WHISPER_MODEL.replace("openai/whisper-", "")
                    _asr = WhisperModel(model_size, device=device, compute_type=compute_type, use_auth_token=token)
                except Exception:
                    from transformers import pipeline
                    import torch

                    _asr = pipeline(
                        "automatic-speech-recognition",
                        model=WHISPER_MODEL,
                        token=token,
                        device=0 if torch.cuda.is_available() else -1,
                        torch_dtype="auto",
                        chunk_length_s=30,
                        stride_length_s=(5, 2),
                    )
    return _asr


def transcribe_audio(audio_path: Path) -> str:
    recognizer = _asr
    if recognizer is None:
        raise RuntimeError("Whisper is not loaded. Models are initialized during API startup.")
    with _asr_lock:
        if hasattr(recognizer, "transcribe"):
            segments, _ = recognizer.transcribe(str(audio_path), beam_size=5)
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
        else:
            result = recognizer(str(audio_path), batch_size=16, return_timestamps=False)
            transcript = result.get("text", "").strip()
    if not transcript:
        raise ValueError("No speech could be transcribed from this audio file.")
    return transcript


def _load_qwen():
    global _tokenizer, _llm
    if _llm is None or _tokenizer is None:
        with _load_lock:
            if _llm is None or _tokenizer is None:
                from transformers import AutoModelForCausalLM, AutoTokenizer
                import torch

                token = _require_token()
                device = 0 if torch.cuda.is_available() else "cpu"
                _tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL, token=token)
                _llm = AutoModelForCausalLM.from_pretrained(
                    QWEN_MODEL,
                    token=token,
                    device_map={"": device},
                    torch_dtype="auto",
                )
                _llm.eval()
    return _tokenizer, _llm


def load_whisper_model() -> None:
    _load_asr()


def load_qwen_model() -> None:
    _load_qwen()


def _decode_json(raw: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("The language model did not return structured meeting minutes.")
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("The language model returned invalid meeting-minutes JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError("The language model returned an unexpected minutes format.")
    return value


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _normalize_minutes(value: dict[str, Any]) -> MeetingMinutes:
    action_items = value.get("action_items", value.get("actions", [])) or []
    if isinstance(action_items, str):
        action_items = [{"task": action_items}]
    normalized_actions = []
    for item in action_items if isinstance(action_items, list) else []:
        if isinstance(item, str):
            normalized_actions.append({"task": item})
        elif isinstance(item, dict):
            normalized_actions.append(
                {
                    "task": item.get("task") or item.get("action") or item.get("description") or "",
                    "owner": item.get("owner") or item.get("assigned_to"),
                    "due_date": item.get("due_date") or item.get("deadline"),
                    "status": item.get("status") or "pending",
                }
            )

    return MeetingMinutes(
        summary=str(value.get("summary") or value.get("executive_summary") or "Summary unavailable."),
        attendees=_as_text_list(value.get("attendees")),
        meeting_date=value.get("meeting_date") or value.get("date"),
        location=value.get("location"),
        discussion_points=_as_text_list(value.get("discussion_points") or value.get("discussion")),
        key_takeaways=_as_text_list(value.get("key_takeaways") or value.get("takeaways")),
        decisions=_as_text_list(value.get("decisions")),
        action_items=normalized_actions,
    )


def generate_minutes(transcript: str) -> MeetingMinutes:
    tokenizer, model = _tokenizer, _llm
    if tokenizer is None or model is None:
        raise RuntimeError("Qwen is not loaded. Models are initialized during API startup.")
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Create meeting minutes from this transcript:\n\n{transcript}"},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with _llm_lock:
        output = model.generate(
            **inputs,
            max_new_tokens=1200,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated_tokens = output[0][inputs["input_ids"].shape[-1] :]
    raw = tokenizer.decode(generated_tokens, skip_special_tokens=True)
    return _normalize_minutes(_decode_json(raw))
