---
name: log-experiment
description: Generate a structured experiment-log markdown report for VLM benchmark runs in this ZTF project, capturing prompts, model config, hyperparameters, git commit, data inputs, runtime, and evaluation metrics. Use when the user starts, plans, finishes, or wants to document a benchmark run (e.g. "log this experiment", "write up the run", "create an experiment readme", "record this run"). Also use proactively right after launching `run_tinker_benchmark.py` or completing an `evaluate.py` invocation.
---

# Log Experiment

Produces a self-contained markdown report under `experiments/` for every VLM benchmark run, so future runs can be compared by config and results without re-reading scattered logs.

## When to Use

- Right after the user launches `run_tinker_benchmark.py` (capture *config*).
- Right after `evaluate.py` completes (append *metrics* + observations).
- When the user explicitly asks to log, document, or write up an experiment.
- Before/after any prompt or `api_tinker.py` change that's worth A/B comparing.

## Workflow

Copy this checklist and track progress:

```
- [ ] 1. Determine experiment label & output path
- [ ] 2. Gather config (model, prompts, command, git state)
- [ ] 3. Gather data slice info (manifest path, n samples, classes)
- [ ] 4. Capture diff vs prior run (if applicable)
- [ ] 5. Fill template, write to experiments/EXP-<date>-<slug>.md
- [ ] 6. After eval: append metrics + observations
```

### Step 1 — Label & path

- Slug: short kebab-case (e.g. `qwen35-think-newprompt`, `kimi-fewshot-v2`).
- Path: `experiments/EXP-YYYYMMDD-<slug>.md` (use today's date in local TZ).
- If a file with the same slug already exists today, append `-2`, `-3`, etc.

### Step 2 — Config gathering (REQUIRED, do these tool calls)

Run these in parallel where possible:

- `git rev-parse --short HEAD` → commit hash
- `git status --porcelain` → flag dirty working tree
- `git log -1 --format="%s%n%an %ad" --date=short` → last commit subject/author/date
- Read `prompts.py` (or whichever module was passed via `--prompts`) — capture: `SYSTEM_PROMPT` first ~10 lines, list of metadata keys returned by `manifest_row_to_metadata`, any Stage 1/2/3 guidance.
- Read the relevant section of `api_tinker.py` to capture the **renderer** chosen for this model and the effective `max_tokens` (reasoning models auto-bump to 16384).
- From the launch command (or terminal output): record `--model`, `--manifest`, `--out`, `--prompts`, `--concurrency`, `--limit`, any other flags.

### Step 3 — Data slice

Read the manifest CSV referenced by `--manifest`:
- Total rows.
- Class distribution (count per `target_class`).
- Whether it's `manifest_fewshot.csv` (held-out 100), `manifest_enriched.csv` (full), or other.

### Step 4 — Diff vs prior run

If a prior `experiments/EXP-*.md` file exists for the same model OR same prompt module:
- Pick the most recent matching one as the "baseline".
- Note what changed: prompt module, renderer, max_tokens, concurrency, model, manifest size, code diffs in `prompts.py` / `api_tinker.py` / `evaluate.py` since baseline's commit (use `git diff <baseline_commit>..HEAD -- prompts.py api_tinker.py evaluate.py --stat`).
- Record explicitly: "Compared to EXP-XXXX, this run changes: …".

### Step 5 — Write the report

Use [template.md](template.md) verbatim, filling every section. Leave `TBD` for fields that require post-run info (parse rate, accuracy). NEVER invent numbers.

### Step 6 — Post-eval update

After `evaluate.py` runs, append the **Results** section with:
- 5-class accuracy, per-class accuracy, per-class F1
- Stage 1/2/3 staged accuracy
- JSON parse rate (`json_valid_rate`)
- Effective n (parsed / total)
- Confusion matrix (use the `part_c_stage3_confusion_matrix` block, formatted as a small markdown table)
- Notable misclassification patterns (top 1-2 sentences)

Then add an **Observations** section answering:
- Did the result match the hypothesis?
- Any surprises (e.g. parse rate dropped, one class collapsed)?
- Suggested next experiment (one sentence).

## Required Sections (template summary)

The report must contain:

1. **Metadata** — date, slug, status, commit, dirty? operator
2. **Hypothesis** — what are we testing, expected outcome
3. **Baseline / Comparison** — which prior EXP to compare against, what changed
4. **Configuration** — model, renderer, max_tokens, temperature, concurrency, prompt module
5. **Prompt summary** — system prompt fingerprint (first 10 lines) + listed metadata fields + any custom Stage instructions
6. **Data** — manifest path, n samples, class distribution
7. **Command** — exact CLI invocation
8. **Output** — path to results JSONL, runtime, n successful
9. **Code diff vs baseline** — `git diff --stat` of relevant files
10. **Library versions** — `pip show tinker-cookbook tinker | grep -i version` (one line each)
11. **Results** — metrics, confusion matrix (filled post-eval)
12. **Observations** — did it match hypothesis, surprises, next steps

See [template.md](template.md) for the exact format.

## Iterative Improvement

This skill is meant to evolve. After 2-3 reports, ask:
- Are any sections never filled? → Remove them from the template.
- Are any new fields needed (e.g. cost tracking, GPU type)? → Add to the template.
- Is the slug convention working? → Adjust naming rule.

## Anti-patterns

- Do not invent metrics — if eval hasn't run, leave `TBD` and update later.
- Do not paste the entire `prompts.py` — only the system-prompt header + key field list.
- Do not skip the git commit hash; it is the single most important field for reproducibility.
- Do not store reports anywhere except `experiments/`.
- If the working tree is dirty, set `Dirty: true` and list modified files — this is a *warning*, not a blocker.
