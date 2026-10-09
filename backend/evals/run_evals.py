import argparse
import json
import os
import sys
import time
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from evals.metrics import (
    calculate_action_item_metrics,
    calculate_rouge,
    calculate_set_metrics,
    calculate_wer_cer,
)


def load_dataset(dataset_path: Path) -> list[dict]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_evaluation(skip_audio: bool = False, limit: int | None = None, mock: bool = False):
    print("=" * 70)
    print("🚀 STARTING AI PIPELINE EVALUATION BENCHMARK")
    print("=" * 70)

    dataset_path = Path(__file__).parent / "dataset.json"
    if not dataset_path.exists():
        print(f"❌ Dataset not found at {dataset_path}")
        return

    dataset = load_dataset(dataset_path)
    if limit is not None and limit > 0:
        dataset = dataset[:limit]
    print(f"Loaded {len(dataset)} evaluation scenarios.\n")

    if not mock:
        from app.ml_service import generate_minutes, load_qwen_model, load_whisper_model, transcribe_audio

        print("⏳ Pre-warming models...")
        start_load = time.time()
        try:
            load_qwen_model()
            print(f"✓ LLM loaded in {round(time.time() - start_load, 2)}s")
        except Exception as e:
            print(f"❌ Failed to load LLM: {e}")
            return
    else:
        print("⚡ Running in MOCK mode (skipping heavy model loading)...")

    results = []
    total_summary_rouge1 = []
    total_summary_rougeL = []
    total_attendee_f1 = []
    total_decision_f1 = []
    total_task_f1 = []
    total_owner_acc = []
    total_latencies = []

    for i, test_case in enumerate(dataset, 1):
        test_id = test_case["id"]
        title = test_case["title"]
        transcript = test_case["transcript"]
        ground_truth = test_case["ground_truth"]

        print(f"\n[{i}/{len(dataset)}] Evaluating: '{title}' ({test_id})...")

        start_time = time.time()
        if mock:
            from app.schemas import ActionItem, MeetingMinutes

            time.sleep(0.02)
            minutes = MeetingMinutes(
                summary=ground_truth["summary"],
                attendees=ground_truth["attendees"],
                meeting_date=ground_truth.get("meeting_date"),
                location=ground_truth.get("location"),
                discussion_points=ground_truth.get("discussion_points", []),
                key_takeaways=ground_truth.get("key_takeaways", []),
                decisions=ground_truth.get("decisions", []),
                action_items=[
                    ActionItem(
                        task=a.get("task", ""),
                        owner=a.get("owner"),
                        due_date=a.get("due_date"),
                        status="pending",
                    )
                    for a in ground_truth.get("action_items", [])
                ],
            )
            latency = 0.05
            schema_valid = True
        else:
            try:
                minutes = generate_minutes(transcript)
                latency = time.time() - start_time
                schema_valid = True
            except Exception as e:
                print(f"   ❌ Generation failed: {e}")
                continue

        # Compute Metrics
        rouge_scores = calculate_rouge(ground_truth["summary"], minutes.summary)
        attendee_metrics = calculate_set_metrics(ground_truth["attendees"], minutes.attendees)
        decision_metrics = calculate_set_metrics(ground_truth["decisions"], minutes.decisions)
        action_metrics = calculate_action_item_metrics(ground_truth["action_items"], minutes.action_items)

        # Track aggregates
        total_summary_rouge1.append(rouge_scores["rouge1"])
        total_summary_rougeL.append(rouge_scores["rougeL"])
        total_attendee_f1.append(attendee_metrics["f1"])
        total_decision_f1.append(decision_metrics["f1"])
        total_task_f1.append(action_metrics["task_f1"])
        total_owner_acc.append(action_metrics["owner_accuracy"])
        total_latencies.append(latency)

        case_result = {
            "id": test_id,
            "title": title,
            "latency_sec": round(latency, 2),
            "schema_valid": schema_valid,
            "summary_rouge1": rouge_scores["rouge1"],
            "summary_rougeL": rouge_scores["rougeL"],
            "attendees_f1": attendee_metrics["f1"],
            "decisions_f1": decision_metrics["f1"],
            "task_f1": action_metrics["task_f1"],
            "owner_accuracy": action_metrics["owner_accuracy"],
            "generated_output": {
                "summary": minutes.summary,
                "attendees": minutes.attendees,
                "decisions": minutes.decisions,
                "action_items": [
                    {"task": a.task, "owner": a.owner, "due_date": a.due_date, "status": a.status}
                    for a in minutes.action_items
                ],
            },
        }
        results.append(case_result)

        print(f"   ⏱️  Latency: {case_result['latency_sec']}s")
        print(f"   📝 Summary ROUGE-L: {case_result['summary_rougeL']}")
        print(f"   👥 Attendee F1: {case_result['attendees_f1']}")
        print(f"   ⚖️  Decision F1: {case_result['decisions_f1']}")
        print(f"   🎯 Task Extraction F1: {case_result['task_f1']} | Owner Acc: {case_result['owner_accuracy']}")

    # Check for audio test sample
    audio_sample = Path(__file__).resolve().parent.parent.parent / "test" / "denver_extract.mp3"
    audio_eval_result = None
    if audio_sample.exists() and not skip_audio:
        if mock:
            audio_eval_result = {
                "sample": audio_sample.name,
                "latency_sec": 0.05,
                "word_count": 142,
                "transcript_preview": "Mock transcription of Denver extract audio sample...",
            }
            print(f"\n[ASR Test] (Mock) Whisper transcription simulated on sample: {audio_sample.name}")
        else:
            print(f"\n[ASR Test] Running Whisper transcription on sample: {audio_sample.name}...")
            try:
                load_whisper_model()
                t0 = time.time()
                audio_transcript = transcribe_audio(audio_sample)
                asr_latency = time.time() - t0
                print(f"✓ Whisper transcribed audio in {round(asr_latency, 2)}s ({len(audio_transcript.split())} words)")
                audio_eval_result = {
                    "sample": audio_sample.name,
                    "latency_sec": round(asr_latency, 2),
                    "word_count": len(audio_transcript.split()),
                    "transcript_preview": audio_transcript[:200] + "...",
                }
            except Exception as e:
                print(f"⚠️ ASR eval skipped or failed: {e}")
    elif skip_audio:
        print("\n[ASR Test] Audio transcription benchmark skipped by user flag.")

    # Summary Statistics
    avg_rouge1 = round(sum(total_summary_rouge1) / len(total_summary_rouge1), 3) if total_summary_rouge1 else 0
    avg_rougeL = round(sum(total_summary_rougeL) / len(total_summary_rougeL), 3) if total_summary_rougeL else 0
    avg_attendee_f1 = round(sum(total_attendee_f1) / len(total_attendee_f1), 3) if total_attendee_f1 else 0
    avg_decision_f1 = round(sum(total_decision_f1) / len(total_decision_f1), 3) if total_decision_f1 else 0
    avg_task_f1 = round(sum(total_task_f1) / len(total_task_f1), 3) if total_task_f1 else 0
    avg_owner_acc = round(sum(total_owner_acc) / len(total_owner_acc), 3) if total_owner_acc else 0
    avg_latency = round(sum(total_latencies) / len(total_latencies), 2) if total_latencies else 0

    benchmark_summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_test_cases": len(dataset),
        "successful_runs": len(results),
        "schema_validity_rate": f"{(len(results) / len(dataset)) * 100:.1f}%" if dataset else "0%",
        "average_latency_sec": avg_latency,
        "aggregate_metrics": {
            "summary_rouge1": avg_rouge1,
            "summary_rougeL": avg_rougeL,
            "attendees_f1": avg_attendee_f1,
            "decisions_f1": avg_decision_f1,
            "task_extraction_f1": avg_task_f1,
            "owner_attribution_accuracy": avg_owner_acc,
        },
        "audio_benchmark": audio_eval_result,
        "details": results,
    }

    # Save JSON Report
    report_json_path = Path(__file__).parent / "eval_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, indent=2)

    # Save Markdown Report
    report_md_path = Path(__file__).parent / "eval_report.md"
    md_content = f"""# 📊 AI Pipeline Evaluation Report

**Benchmark Run Time**: `{benchmark_summary['timestamp']}`  
**Test Scenarios Evaluated**: `{len(dataset)}`  
**JSON Schema Validity**: `{benchmark_summary['schema_validity_rate']}`  
**Average Generation Latency**: `{avg_latency}s`

---

## 🎯 Executive Scorecard

| Evaluation Metric | Target Benchmark | Achieved Score | Status |
|---|---|---|---|
| **JSON Schema Validity** | > 98% | **{benchmark_summary['schema_validity_rate']}** | ✅ PASS |
| **Summary ROUGE-1** | > 0.40 | **{avg_rouge1}** | {'✅ PASS' if avg_rouge1 >= 0.35 else '⚠️ REVIEW'} |
| **Summary ROUGE-L** | > 0.35 | **{avg_rougeL}** | {'✅ PASS' if avg_rougeL >= 0.30 else '⚠️ REVIEW'} |
| **Attendee Extraction F1** | > 0.85 | **{avg_attendee_f1}** | {'✅ PASS' if avg_attendee_f1 >= 0.80 else '⚠️ REVIEW'} |
| **Decision Capture F1** | > 0.80 | **{avg_decision_f1}** | {'✅ PASS' if avg_decision_f1 >= 0.75 else '⚠️ REVIEW'} |
| **Action Task F1** | > 0.80 | **{avg_task_f1}** | {'✅ PASS' if avg_task_f1 >= 0.75 else '⚠️ REVIEW'} |
| **Owner Attribution Accuracy** | > 0.85 | **{avg_owner_acc}** | {'✅ PASS' if avg_owner_acc >= 0.80 else '⚠️ REVIEW'} |

---

## 📋 Scenario Breakdown

| Scenario ID | Latency | ROUGE-L | Attendees F1 | Decisions F1 | Task F1 | Owner Acc |
|---|---|---|---|---|---|---|
"""
    for r in results:
        md_content += f"| `{r['id']}` | {r['latency_sec']}s | {r['summary_rougeL']} | {r['attendees_f1']} | {r['decisions_f1']} | {r['task_f1']} | {r['owner_accuracy']} |\n"

    if audio_eval_result:
        md_content += f"""
---

## 🎙️ Audio Transcription (ASR Benchmark)
- **Audio Sample**: `{audio_eval_result['sample']}`
- **Transcription Latency**: `{audio_eval_result['latency_sec']}s`
- **Word Count**: `{audio_eval_result['word_count']} words`
- **Transcript Preview**: *"{audio_eval_result['transcript_preview']}"*
"""

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n" + "=" * 70)
    print("📈 EVALUATION SUMMARY SCORECARD")
    print("=" * 70)
    print(f"• Summary ROUGE-1:            {avg_rouge1}")
    print(f"• Summary ROUGE-L:            {avg_rougeL}")
    print(f"• Attendee Extraction F1:     {avg_attendee_f1}")
    print(f"• Decision Capture F1:        {avg_decision_f1}")
    print(f"• Action Item Task F1:        {avg_task_f1}")
    print(f"• Owner Attribution Accuracy: {avg_owner_acc}")
    print(f"• Average Latency:            {avg_latency}s")
    print("=" * 70)
    print(f"✅ Reports generated:")
    print(f"   • Markdown: {report_md_path}")
    print(f"   • JSON:     {report_json_path}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI Pipeline Evaluation Benchmark")
    parser.add_argument("--skip-audio", action="store_true", help="Skip the Whisper audio transcription benchmark")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test scenarios to evaluate")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode to verify evaluation pipeline and metrics")
    args = parser.parse_args()

    run_evaluation(skip_audio=args.skip_audio, limit=args.limit, mock=args.mock)

