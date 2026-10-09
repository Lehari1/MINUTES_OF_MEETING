import json
from pathlib import Path
import pytest

from backend.evals.metrics import (
    calculate_action_item_metrics,
    calculate_rouge,
    calculate_set_metrics,
    calculate_wer_cer,
)
from backend.evals.run_evals import load_dataset, run_evaluation


def test_dataset_json_integrity():
    dataset_path = Path(__file__).resolve().parent.parent / "evals" / "dataset.json"
    assert dataset_path.exists(), "dataset.json must exist"

    scenarios = load_dataset(dataset_path)
    assert len(scenarios) >= 3, "Dataset must contain at least 3 scenarios"

    for item in scenarios:
        assert "id" in item and item["id"]
        assert "title" in item and item["title"]
        assert "transcript" in item and len(item["transcript"]) > 20
        assert "ground_truth" in item

        gt = item["ground_truth"]
        assert "attendees" in gt and isinstance(gt["attendees"], list)
        assert "summary" in gt and len(gt["summary"]) > 10
        assert "decisions" in gt and isinstance(gt["decisions"], list)
        assert "action_items" in gt and isinstance(gt["action_items"], list)
        for act in gt["action_items"]:
            assert "task" in act and act["task"]


def test_metrics_wer_cer():
    res = calculate_wer_cer("the meeting started at noon", "the meeting began at noon")
    assert "wer" in res and res["wer"] > 0
    assert "cer" in res and res["cer"] > 0

    empty = calculate_wer_cer("", "")
    assert empty["wer"] == 1.0


def test_metrics_rouge():
    ref = "The sprint planning covered architecture and deliverables."
    hyp = "The sprint planning covered architecture review and key deliverables."
    res = calculate_rouge(ref, hyp)
    assert res["rouge1"] > 0.6
    assert res["rougeL"] > 0.6


def test_metrics_set_precision_recall_f1():
    ref = ["Sarah", "Michael", "Priya"]
    hyp = ["Sarah", "Michael", "Tom"]
    res = calculate_set_metrics(ref, hyp)
    assert res["precision"] == pytest.approx(0.667, abs=0.01)
    assert res["recall"] == pytest.approx(0.667, abs=0.01)
    assert res["f1"] == pytest.approx(0.667, abs=0.01)


def test_metrics_action_items():
    ref_actions = [
        {"task": "Implement OAuth2 endpoints", "owner": "Michael"},
        {"task": "Review database schema", "owner": "Priya"},
    ]
    hyp_actions = [
        {"task": "Implement OAuth2 backend endpoints", "owner": "Michael"},
        {"task": "Review database schema", "owner": "Priya"},
    ]
    res = calculate_action_item_metrics(ref_actions, hyp_actions)
    assert res["task_f1"] == 1.0
    assert res["owner_accuracy"] == 1.0


def test_eval_runner_mock_mode(tmp_path):
    # Verify run_evaluation executes end-to-end in mock mode without errors
    run_evaluation(skip_audio=True, limit=2, mock=True)

    report_json = Path(__file__).resolve().parent.parent / "evals" / "eval_report.json"
    report_md = Path(__file__).resolve().parent.parent / "evals" / "eval_report.md"

    assert report_json.exists()
    assert report_md.exists()

    with open(report_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["total_test_cases"] == 2
        assert data["successful_runs"] == 2
        assert data["aggregate_metrics"]["summary_rougeL"] == 1.0
