---
name: log-experiment
description: Build a complete per-run folder under `runs/<timestamp>-<slug>/` for a VLM benchmark run in this ZTF project — runs evaluate.py if needed, copies the JSONL into the run folder, generates one logtree HTML per datapoint (top-10 per class by ALERCE probability), generates matplotlib plots, writes an enriched markdown report with every metric from evaluate.py, and updates runs/index.md. Use when the user starts, finishes, or wants to document a benchmark run (e.g. "log this experiment", "write up the run", "log the run we just did"). Use proactively right after `run_tinker_benchmark.py` finishes.
---

# Log Experiment

Produces a self-contained `runs/<timestamp>-<slug>/` folder for every VLM benchmark run, containing:

```
runs/20260420-1855-<slug>/
  run.jsonl            # copy of predictions (annotated with error_category + value_errors by evaluate.py)
  metrics.json         # full metrics dict from evaluate.py
  report.md            # enriched markdown report, every metric listed
  viz/                 # per-datapoint HTML (top-10 per class by ALERCE probability)
    SN/     <oid>.html x up-to-10
    AGN/    <oid>.html x up-to-10
    VS/     <oid>.html x up-to-10
    asteroid/ ...
    bogus/    ...
  plots/               # matplotlib charts + README.md describing each
    per_class_accuracy.png
    five_class_confusion.png
    stage3_confusion.png
    token_distribution.png
    error_breakdown.png
    calibration.png
    README.md
```

Also updates `runs/index.md` (human-readable table) and `runs/index.jsonl` (programmatic) with the new run's key metrics.

## When to Use

- Right after `run_tinker_benchmark.py` finishes and the user says "log this experiment" / "write up the run" / similar.
- Right after `evaluate.py` completes.
- Before/after any `prompts.py` / `api_tinker.py` / `api_openai.py` change worth A/B-comparing.

## Workflow

```
- [ ] 1. Identify the run's JSONL + manifest + model
- [ ] 2. Gather per-run context (hypothesis, baseline, observations)
- [ ] 3. Call viz.build_run_folder.build_run_folder(...)
- [ ] 4. Verify output structure + index update
- [ ] 5. Report back with paths + top-line metrics
```

### Step 1 — Identify inputs

From the launch command or recent terminal output, pull:

- `--out <path.jsonl>` → `jsonl_path`
- `--manifest <path.csv>` → `manifest_path`
- `--model <HF id or openai id>` → `model_name`
- `--prompts <module>` → `prompts_module` (default `"prompts"`)
- `--backend` if specified, otherwise infer from model id (anything with `gpt` → openai, else tinker)

### Step 2 — Gather per-run context (optional but strongly encouraged)

Before building the folder, ask the user (or infer):

- **Hypothesis** (1-3 sentences): what is this run testing / expected to show
- **Baseline comparison** (1-3 sentences): which prior run is this compared against, what changed
- **Observations** (fill AFTER seeing metrics): did the hypothesis match, any surprises, suggested next experiment

Also peek at `git rev-parse --short HEAD` and `git status --porcelain` to know which commit + whether the tree is dirty. `build_run_folder` captures these automatically.

### Step 3 — Build the run folder

Invoke the orchestrator. Two options:

**(a) From Python (preferred when you already have all args):**

```python
from viz.build_run_folder import build_run_folder

run_dir = build_run_folder(
    jsonl_path="results/fewshot_kimi_think_newparser.jsonl",
    manifest_path="data/manifest_fewshot.csv",
    model_name="moonshotai/Kimi-K2.5",
    prompts_module="prompts",
    slug_override="kimi-k25-think",          # optional; default = slugified model name
    run_timestamp=None,                       # optional; default = jsonl mtime as YYYYMMDD-HHMM
    hypothesis="Switch Kimi K2.5 to thinking-enabled renderer; expect parse rate stays ~100%, accuracy lifts.",
    comparison="Compared to prior Kimi DisableThinking run. Only renderer changed.",
    observations="Best open-source result so far: 49% 5-class, 100% parse. AGN still 0/20 — universal failure mode.",
    backend_hint="tinker",
)
```

**(b) From CLI:**

```bash
python -m viz.build_run_folder \
  --jsonl results/fewshot_kimi_think_newparser.jsonl \
  --manifest data/manifest_fewshot.csv \
  --model moonshotai/Kimi-K2.5 \
  --slug kimi-k25-think \
  --hypothesis "..." \
  --comparison "..." \
  --observations "..."
```

The orchestrator does, in order:

1. Loads the JSONL + manifest.
2. Computes run timestamp (JSONL mtime by default) and slug (from model name by default).
3. Creates `runs/<timestamp>-<slug>/` and copies the JSONL to `run.jsonl`.
4. Runs `evaluate.evaluate_jsonl(...)` on the in-folder copy — this writes `error_category` + `value_errors` back into each JSONL row *and* saves the full metrics dict to `metrics.json`.
5. Picks top-10-by-ALERCE-probability per class from the manifest, filtered to oids actually present in the run.
6. Generates one `logtree` HTML per selected oid into `viz/<class>/<oid>.html`.
7. Generates up to 6 matplotlib plots into `plots/` + a `plots/README.md`.
8. Writes `report.md` containing every metric from `evaluate.py` (11 sub-sections, see `viz/enriched_report.py`).
9. Regenerates `runs/index.md` and `runs/index.jsonl`.

### Step 4 — Verify output

Check:

- `runs/<ts>-<slug>/report.md` exists and contains a non-empty Results section.
- `runs/<ts>-<slug>/viz/` has 5 subfolders (SN / AGN / VS / asteroid / bogus) with HTMLs.
- `runs/<ts>-<slug>/plots/` has PNGs plus `README.md`.
- The new run appears in `runs/index.md`.

### Step 5 — Report back to user

Tell the user:

- The new run folder path.
- Top-line metrics: 5-class accuracy, parse rate, truncated rate, MSRS.
- Where the interactive HTMLs live (`viz/<class>/<oid>.html`).
- Which plots were generated (or skipped because of missing data — e.g. `calibration.png` is skipped if fewer than 5 linked Part-B records exist).

## What gets captured

The enriched `report.md` contains **every** metric returned by `evaluate.evaluate_jsonl`, organized into 11 sub-sections:

1. Run-level counts (`n_examples`, `n_errors`, `json_parseable`, `json_valid_rate`)
2. Token statistics (`output_tokens` + `answer_tokens`: mean / median / min / max / p95; `n_truncated`, `truncated_rate`)
3. Error breakdown (all format codes + top-10 value errors + n rows with value errors)
4. Part A (per-question + macro + exact-match)
5. Part B (MSRS + per-dim mean + self-pass rate)
6. Part B↔C calibration (n_linked, mean-confidence-correct / -incorrect, calibration_gap, pearson_r, high/low-confidence accuracy)
7. Part C stage-wise (n_evaluable, stage-1 / -2 / -3 raw + conditional, end-to-end, **final 5-class**)
8. Per-class breakdown (accuracy / correct / total for all 5 classes)
9. Binary PRF at stages 1 & 2 (real_object=+, astrophysical=+)
10. Stage-3 subclass PRF (macro F1 + per-class)
11. Stage-3 confusion matrix

Metadata, Configuration (model/renderer/max_tokens/reasoning_mode/concurrency/prompt_module), Data (manifest path, class distribution), Hypothesis, Comparison, Observations, Plots (inline preview), and Per-datapoint HTML links round out the report.

## Anti-patterns

- Do **not** invent metrics. If eval hasn't run, `build_run_folder` will run it automatically; don't pre-fill numbers.
- Do **not** write to `experiments/` or `report/` anymore — those directories are kept as archive only. All new runs go under `runs/`.
- Do **not** skip capturing the git commit; `build_run_folder` does this for you, don't override.
- If the working tree is dirty, the report records it — this is a *warning*, not a blocker. Recommend the user commit first for a fully reproducible run.
- Never hand-edit `runs/index.md` or `runs/index.jsonl` — they are regenerated from every run's `metrics.json` on each invocation.

## Iterative improvement

This skill is designed to evolve. After a handful of real runs, consider:

- Adding cross-run comparison tables to `runs/index.md` (e.g. difference vs best run).
- Adding a `plots/trend.png` showing metric trajectory over time.
- Adding cost tracking fields (OpenAI `$` per run) once available.
- Trimming unused report sections if a metric never varies meaningfully.

## Backfilling historical runs

The 7 runs prior to this skill's existence were backfilled with `python -m viz._backfill`. That script is preserved in `viz/` as a reference for what to do when migrating future legacy jsonl+EXP-md pairs into the `runs/` layout.
