# 📊 AI Pipeline Evaluation Report

**Benchmark Run Time**: `2026-10-09 11:07:23 UTC`  
**Test Scenarios Evaluated**: `3`  
**JSON Schema Validity**: `100.0%`  
**Average Generation Latency**: `375.65s`

---

## 🎯 Executive Scorecard

| Evaluation Metric | Target Benchmark | Achieved Score | Status |
|---|---|---|---|
| **JSON Schema Validity** | > 98% | **100.0%** | ✅ PASS |
| **Summary ROUGE-1** | > 0.40 | **0.41** | ✅ PASS |
| **Summary ROUGE-L** | > 0.35 | **0.335** | ✅ PASS |
| **Attendee Extraction F1** | > 0.85 | **1.0** | ✅ PASS |
| **Decision Capture F1** | > 0.80 | **0.746** | ⚠️ REVIEW |
| **Action Task F1** | > 0.80 | **0.833** | ✅ PASS |
| **Owner Attribution Accuracy** | > 0.85 | **0.867** | ✅ PASS |

---

## 📋 Scenario Breakdown

| Scenario ID | Latency | ROUGE-L | Attendees F1 | Decisions F1 | Task F1 | Owner Acc |
|---|---|---|---|---|---|---|
| `eval-01-sprint-planning` | 424.28s | 0.4 | 1.0 | 0.571 | 0.5 | 0.6 |
| `eval-02-incident-postmortem` | 343.24s | 0.366 | 1.0 | 0.667 | 1.0 | 1.0 |
| `eval-03-product-strategy` | 359.43s | 0.239 | 1.0 | 1.0 | 1.0 | 1.0 |

---

## 🎙️ Audio Transcription (ASR Benchmark)
- **Audio Sample**: `denver_extract.mp3`
- **Transcription Latency**: `1428.25s`
- **Word Count**: `2182 words`
- **Transcript Preview**: *"kind of the confluence of this whole idea of the confluence week, the merging of two rivers and as we've kind of seen recently in politics and in the world, there's a lot of situations where water is ..."*
