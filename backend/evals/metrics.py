import re
from typing import Any
import jiwer
from rouge_score import rouge_scorer


def normalize_text(text: str) -> str:
    """Lowercase and strip punctuation for relaxed matching."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def calculate_wer_cer(reference: str, hypothesis: str) -> dict[str, float]:
    """Calculate Word Error Rate (WER) and Character Error Rate (CER)."""
    if not reference.strip() or not hypothesis.strip():
        return {"wer": 1.0, "cer": 1.0}
    wer = jiwer.wer(reference, hypothesis)
    cer = jiwer.cer(reference, hypothesis)
    return {
        "wer": round(float(wer) * 100, 2),
        "cer": round(float(cer) * 100, 2),
    }


def calculate_rouge(reference: str, hypothesis: str) -> dict[str, float]:
    """Calculate ROUGE-1, ROUGE-2, and ROUGE-L F1 scores."""
    if not reference.strip() or not hypothesis.strip():
        return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    scores = scorer.score(reference, hypothesis)
    return {
        "rouge1": round(scores["rouge1"].fmeasure, 3),
        "rouge2": round(scores["rouge2"].fmeasure, 3),
        "rougeL": round(scores["rougeL"].fmeasure, 3),
    }


def calculate_set_metrics(ref_items: list[str], hyp_items: list[str]) -> dict[str, float]:
    """Calculate Precision, Recall, and F1 for textual entities (attendees, decisions)."""
    if not ref_items and not hyp_items:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not ref_items or not hyp_items:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    norm_refs = [normalize_text(r) for r in ref_items]
    norm_hyps = [normalize_text(h) for h in hyp_items]

    # Fuzzy / token-containment matching
    matched_refs = set()
    matched_hyps = set()

    for i, h in enumerate(norm_hyps):
        for j, r in enumerate(norm_refs):
            if r in h or h in r or (len(set(r.split()) & set(h.split())) >= 2):
                matched_hyps.add(i)
                matched_refs.add(j)

    precision = len(matched_hyps) / len(hyp_items) if hyp_items else 0.0
    recall = len(matched_refs) / len(ref_items) if ref_items else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def calculate_action_item_metrics(ref_actions: list[dict[str, Any]], hyp_actions: list[Any]) -> dict[str, float]:
    """Evaluate Action Item task extraction and owner attribution accuracy."""
    if not ref_actions and not hyp_actions:
        return {"task_f1": 1.0, "owner_accuracy": 1.0, "deadline_accuracy": 1.0}
    if not ref_actions or not hyp_actions:
        return {"task_f1": 0.0, "owner_accuracy": 0.0, "deadline_accuracy": 0.0}

    # Extract tasks
    ref_tasks = [a.get("task", "") for a in ref_actions]
    hyp_tasks = [getattr(a, "task", "") if hasattr(a, "task") else a.get("task", "") for a in hyp_actions]
    task_metrics = calculate_set_metrics(ref_tasks, hyp_tasks)

    # Owner attribution accuracy
    ref_owners = {normalize_text(a.get("owner", "")): a for a in ref_actions if a.get("owner")}
    matched_owners = 0
    total_hyp_owners = 0

    for item in hyp_actions:
        hyp_owner = getattr(item, "owner", None) if hasattr(item, "owner") else item.get("owner")
        if hyp_owner:
            total_hyp_owners += 1
            norm_owner = normalize_text(hyp_owner)
            if any(norm_owner in ro or ro in norm_owner for ro in ref_owners):
                matched_owners += 1

    owner_acc = (matched_owners / total_hyp_owners) if total_hyp_owners > 0 else 1.0

    return {
        "task_f1": task_metrics["f1"],
        "task_precision": task_metrics["precision"],
        "task_recall": task_metrics["recall"],
        "owner_accuracy": round(owner_acc, 3),
    }
