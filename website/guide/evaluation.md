# Metrics & runner

Headline **model-vs-model rankings** on the 1 500-row benchmark are on the [Leaderboard](/guide/leaderboard) page.

## Producing predictions

`run_tinker_benchmark.py` reads the manifest, attaches images, calls the selected **backend** (`tinker`, `openai`, `google`, `anthropic`, …), and writes **JSONL** with one record per row (model output + usage metadata when available).

Key flags include model id, concurrency, reasoning / thinking mode, output path, and prompt module selection. See repository docstrings for the **current** CLI.

## Scoring

`evaluate.py --predictions <file.jsonl> --manifest <matching.csv>` emits an **aggregate metrics JSON** and optional per-row diagnostics.

### Metric families

| Group | Examples |
|-------|----------|
| Coverage | row counts, JSON parse success, truncation rates |
| Part A | per-field accuracy, macro average, six-field exact match |
| Part B | MSRS, per-dimension means, self-pass rate |
| Calibration | MSRS vs correctness splits, correlation |
| Part C | stage accuracies (incl. conditional), end-to-end cascade, **final 5-class accuracy**, per-class P/R/F1, confusion matrix |

Exact key names match the public evaluator (e.g. `part_c_final_5class_accuracy`, `part_b_msrs`). The website does not duplicate every key; the repository table / LaTeX appendix lists the full schema.

## Fair comparison checklist

1. Same **manifest** and **montage root**.
2. Same **prompt module** (unless intentionally comparing prompts).
3. Same **post-processing** (none beyond parser repair, if any).
4. Report **concurrency / hardware** only for timing; primary scores are **accuracy-dominant**.
