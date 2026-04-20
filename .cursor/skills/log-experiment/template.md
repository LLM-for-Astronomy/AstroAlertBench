# Report template reference

> **NOTE:** You no longer fill this template by hand. `viz.enriched_report.write_enriched_report`
> generates the full `runs/<ts>-<slug>/report.md` for you. This file is kept as a
> structural reference so you know what sections to expect in the output and can
> answer questions about the format.

The orchestrator produces the following sections, in order:

---

# Run report — {model}  ({YYYYMMDD-HHMM})

## Metadata
- Run folder, timestamp, slug, status
- Commit + working-tree-dirty flag (with modified files)
- Operator

## Hypothesis
_Passed via `hypothesis=...` kwarg; free-form._

## Baseline / Comparison
_Passed via `comparison=...` kwarg; free-form._

## Configuration
Table with: model, backend, renderer, reasoning_mode, reasoning_effort,
max_tokens, temperature, concurrency, prompt_module.

## Prompt Summary
_Optional; passed via `prompt_summary=...`. Normally unused because the prompts
module + commit hash already pin the prompt content deterministically._

## Data
- Manifest path
- Total records in run
- Class distribution table

## Command
_Optional; include the CLI if the launch command was non-standard._

## Output
- Path to `run.jsonl`
- Original JSONL path (archive reference)
- Wall-clock runtime (if known)
- Records written + records with parsed JSON

## Results  (11 sub-sections, ALL metrics from `evaluate.evaluate_jsonl`)

1. **Run-level counts** — n_examples, n_errors, json_parseable, json_valid_rate
2. **Token statistics** — output_tokens + answer_tokens mean/median/min/max/p95, n_truncated, truncated_rate
3. **Error breakdown** — format codes (mutually exclusive), top-10 value errors, n_with_value_errors
4. **Part A — metadata reading** — per-field accuracy, macro, exact-match
5. **Part B — self-rated reasoning** — MSRS, per-dim mean, self-pass rate
6. **Part B ↔ C — confidence-accuracy calibration** — n_linked, mean conf correct/incorrect, gap, pearson r, high/low-conf accuracy
7. **Part C — stage-wise classification** — stage-1/2/3 raw + conditional, end-to-end, final 5-class
8. **Per-class breakdown** — accuracy/correct/total for SN/AGN/VS/asteroid/bogus
9. **Binary precision/recall/F1 at stages 1 & 2** — real_object=+, astrophysical=+
10. **Stage-3 subclass PRF** — macro F1 + per-class
11. **Stage-3 confusion matrix** — gold × predicted

## Plots
Inline previews of every PNG under `plots/` that was generated (may skip some if data is missing; e.g. `calibration.png` requires ≥ 5 linked Part-B records).

## Per-datapoint HTML visualizations
Table of class × HTML count, pointing at `viz/<class>/<oid>.html`.

## Observations
_Passed via `observations=...` kwarg; free-form. Add after seeing metrics._

---

## Field-by-field source map (for developers)

| Section | Produced by |
|---|---|
| Metadata | `viz.build_run_folder._git_info()` + folder name |
| Configuration | `viz.build_run_folder._extract_config_from_rows()` (reads first JSONL row + `api_tinker.get_renderer`) |
| Data | `pandas.read_csv(manifest)` + `Counter(target_class)` |
| Results | `evaluate.evaluate_jsonl(predictions, manifest, write_back_errors=True)` |
| Plots | `viz.plots.build_all_plots(metrics, rows, out_dir)` |
| HTMLs | `viz.html_report.render_datapoint_html(...)` for top-10 by prob per class |
