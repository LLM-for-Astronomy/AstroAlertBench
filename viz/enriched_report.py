"""Write an enriched EXP-style markdown report containing **every** metric
returned by `evaluate.evaluate_jsonl`, plus run-level metadata.

The layout mirrors the `.cursor/skills/log-experiment/template.md` template but
extends the Results section to include:

- run-level counts
- token statistics (mean/median/min/max/p95)
- truncation stats
- full format + value error breakdown
- Part A per-question accuracy + macro + exact match
- Part B MSRS + per-dim + self-pass rate
- Part B/C calibration block (7 sub-metrics)
- Part C stage1/2/3 raw and conditional accuracy, end-to-end, 5-class
- per-class accuracy, total, correct
- binary PRF at stages 1 and 2
- Stage-3 macro F1 and per-class PRF
- Stage-3 confusion matrix

Intended to be written into `<run_folder>/report.md` by the orchestrator.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _fmt_num(v: Any, pct: bool = False, digits: int = 4) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if pct:
            return f"{v * 100:.2f} %"
        return f"{v:.{digits}f}".rstrip("0").rstrip(".") if "." in f"{v:.{digits}f}" else f"{v}"
    return str(v)


def _section_metadata(meta: dict[str, Any]) -> list[str]:
    lines = ["## Metadata"]
    lines.append(f"- **Run folder:** `{meta.get('run_folder', '?')}`")
    lines.append(f"- **Run timestamp:** {meta.get('run_timestamp', '?')}")
    lines.append(f"- **Slug:** {meta.get('slug', '?')}")
    lines.append(f"- **Status:** {meta.get('status', 'complete')}")
    lines.append(f"- **Commit:** `{meta.get('commit', '?')}`")
    if meta.get("dirty"):
        lines.append(f"- **Working tree dirty:** true")
        if meta.get("dirty_files"):
            lines.append(f"  - modified: {', '.join(meta['dirty_files'])}")
    else:
        lines.append(f"- **Working tree dirty:** false")
    lines.append(f"- **Operator:** {meta.get('operator', 'user')}")
    lines.append("")
    return lines


def _section_config(cfg: dict[str, Any]) -> list[str]:
    lines = ["## Configuration", "", "| Field | Value |", "|---|---|"]
    for k in (
        "model", "backend", "renderer", "reasoning_mode", "reasoning_effort",
        "max_tokens", "temperature", "concurrency", "prompt_module",
    ):
        if k in cfg:
            lines.append(f"| {k} | `{cfg[k]}` |")
    lines.append("")
    return lines


def _section_command(meta: dict[str, Any]) -> list[str]:
    cmd = meta.get("command")
    if not cmd:
        return []
    return ["## Command", "", "```bash", cmd.strip(), "```", ""]


def _section_data(meta: dict[str, Any]) -> list[str]:
    lines = ["## Data"]
    lines.append(f"- **Manifest:** `{meta.get('manifest_path', '?')}`")
    lines.append(f"- **Total records in run:** {meta.get('n_records', '?')}")
    cls_dist = meta.get("class_distribution")
    if cls_dist:
        lines.append(f"- **Class distribution:**")
        lines.append("")
        lines.append("| Class | Count |")
        lines.append("|---|---|")
        for k, v in cls_dist.items():
            lines.append(f"| {k} | {v} |")
    lines.append("")
    return lines


def _section_results(metrics: dict[str, Any]) -> list[str]:  # noqa: C901
    m = metrics
    L: list[str] = ["## Results", ""]

    # --- 1. Run-level counts ---
    L.append("### 1. Run-level counts")
    L.append("")
    L.append("| Metric | Value |")
    L.append("|---|---|")
    L.append(f"| n_examples | {m.get('n_examples', '—')} |")
    L.append(f"| n_errors (runtime) | {m.get('n_errors', '—')} |")
    L.append(f"| json_parseable | {m.get('json_parseable', '—')} |")
    L.append(f"| json_valid_rate | {_fmt_num(m.get('json_valid_rate'), pct=True)} |")
    L.append("")

    # --- 2. Tokens ---
    out_tok = m.get("output_tokens") or {}
    ans_tok = m.get("answer_tokens") or {}
    if out_tok or ans_tok:
        L.append("### 2. Token statistics")
        L.append("")
        L.append("| Statistic | output_tokens (full) | answer_tokens (post-thinking) |")
        L.append("|---|---|---|")
        for stat in ("mean", "median", "min", "max", "p95"):
            v1 = out_tok.get(stat, "—")
            v2 = ans_tok.get(stat, "—")
            L.append(f"| {stat} | {v1} | {v2} |")
        if "n_truncated" in m:
            L.append(f"| n_truncated | {m['n_truncated']} | — |")
            L.append(f"| truncated_rate | {_fmt_num(m.get('truncated_rate'), pct=True)} | — |")
        L.append("")

    # --- 3. Errors ---
    eb = m.get("error_breakdown") or {}
    if eb:
        L.append("### 3. Error breakdown")
        L.append("")
        fmt = eb.get("format") or {}
        if fmt:
            L.append("**Format errors** (mutually exclusive, one code per row):")
            L.append("")
            L.append("| Code | Count |")
            L.append("|---|---|")
            for k, v in sorted(fmt.items(), key=lambda kv: -kv[1]):
                L.append(f"| {k} | {v} |")
            L.append("")
        vtop = eb.get("value_top10") or {}
        if vtop:
            L.append("**Value errors** (top 10, can co-occur):")
            L.append("")
            L.append("| Code | Count |")
            L.append("|---|---|")
            for k, v in sorted(vtop.items(), key=lambda kv: -kv[1]):
                L.append(f"| {k} | {v} |")
            L.append("")
        L.append(f"Rows with ≥ 1 value error: **{eb.get('n_with_value_errors', 0)}**")
        L.append("")

    # --- 4. Part A ---
    pa = m.get("part_a_per_question_accuracy") or {}
    if pa:
        L.append("### 4. Part A — metadata reading")
        L.append("")
        L.append("| Field | Accuracy |")
        L.append("|---|---|")
        for q, v in pa.items():
            L.append(f"| {q} | {_fmt_num(v, pct=True)} |")
        L.append(f"| **macro** | {_fmt_num(m.get('part_a_macro_accuracy'), pct=True)} |")
        L.append(f"| **exact match (all 6)** | {_fmt_num(m.get('part_a_exact_match_rate'), pct=True)} |")
        L.append("")

    # --- 5. Part B ---
    if "part_b_msrs" in m:
        L.append("### 5. Part B — self-rated reasoning")
        L.append("")
        L.append(f"- **MSRS (mean self-rated score):** {_fmt_num(m.get('part_b_msrs'))}")
        pb = m.get("part_b_per_dim_mean_self") or {}
        if pb:
            L.append(f"- **Per-dimension mean self-score:**")
            for k, v in pb.items():
                L.append(f"  - {k}: {_fmt_num(v)}")
        L.append(f"- **Self-pass rate (row-mean ≥ 4):** {_fmt_num(m.get('part_b_self_pass_rate'), pct=True)}")
        L.append("")

    # --- 6. Part B↔C calibration ---
    bc = m.get("part_bc_confidence_accuracy") or {}
    if bc:
        L.append("### 6. Part B ↔ C — confidence-accuracy calibration")
        L.append("")
        L.append("| Metric | Value |")
        L.append("|---|---|")
        L.append(f"| n_linked | {bc.get('n_linked')} |")
        L.append(f"| mean_confidence_correct | {_fmt_num(bc.get('mean_confidence_correct'))} |")
        L.append(f"| mean_confidence_incorrect | {_fmt_num(bc.get('mean_confidence_incorrect'))} |")
        L.append(f"| calibration_gap | {_fmt_num(bc.get('calibration_gap'))} |")
        L.append(f"| pearson_r | {_fmt_num(bc.get('pearson_r'))} |")
        if "accuracy_high_confidence" in bc:
            L.append(f"| accuracy_high_confidence (conf ≥ 4) | {_fmt_num(bc.get('accuracy_high_confidence'), pct=True)} |")
            L.append(f"| n_high_confidence | {bc.get('n_high_confidence')} |")
        if "accuracy_low_confidence" in bc:
            L.append(f"| accuracy_low_confidence (conf < 4) | {_fmt_num(bc.get('accuracy_low_confidence'), pct=True)} |")
            L.append(f"| n_low_confidence | {bc.get('n_low_confidence')} |")
        L.append("")

    # --- 7. Part C stage-wise ---
    if "part_c_n_evaluable" in m:
        L.append("### 7. Part C — stage-wise classification")
        L.append("")
        L.append("| Metric | Value |")
        L.append("|---|---|")
        L.append(f"| n_evaluable | {m.get('part_c_n_evaluable')} |")
        L.append(f"| Stage 1 (real / artifact) | {_fmt_num(m.get('part_c_stage1_accuracy'), pct=True)} |")
        L.append(f"| Stage 2 (astrophysical / solar) | {_fmt_num(m.get('part_c_stage2_accuracy'), pct=True)} |")
        L.append(f"| Stage 3 (subclass) | {_fmt_num(m.get('part_c_stage3_accuracy'), pct=True)} |")
        L.append(f"| Stage 2 conditional on Stage 1 correct | {_fmt_num(m.get('part_c_stage2_conditional_accuracy'), pct=True)} |")
        L.append(f"| Stage 3 conditional on Stages 1+2 correct | {_fmt_num(m.get('part_c_stage3_conditional_accuracy'), pct=True)} |")
        L.append(f"| End-to-end staged accuracy | {_fmt_num(m.get('part_c_end_to_end_staged_accuracy'), pct=True)} |")
        L.append(f"| **Final 5-class accuracy** | **{_fmt_num(m.get('part_c_final_5class_accuracy'), pct=True)}** |")
        L.append("")

    # --- 8. Per-class breakdown ---
    pcacc = m.get("per_class_accuracy") or {}
    pctot = m.get("per_class_total") or {}
    pccor = m.get("per_class_correct") or {}
    if pcacc:
        L.append("### 8. Per-class breakdown")
        L.append("")
        L.append("| Class | Accuracy | Correct | Total |")
        L.append("|---|---|---|---|")
        for c in sorted(pctot.keys()):
            L.append(f"| {c} | {_fmt_num(pcacc.get(c), pct=True)} | {pccor.get(c, 0)} | {pctot.get(c, 0)} |")
        L.append("")

    # --- 9. Binary PRF at stages 1 and 2 ---
    s1prf = m.get("part_c_stage1_prf_real_object")
    s2prf = m.get("part_c_stage2_prf_astrophysical")
    if s1prf or s2prf:
        L.append("### 9. Binary precision/recall/F1 at stages 1 & 2")
        L.append("")
        L.append("| Stage | Precision | Recall | F1 |")
        L.append("|---|---|---|---|")
        if s1prf:
            L.append(f"| Stage 1 (real_object=+) | {_fmt_num(s1prf.get('precision'))} | {_fmt_num(s1prf.get('recall'))} | {_fmt_num(s1prf.get('f1'))} |")
        if s2prf:
            L.append(f"| Stage 2 (astrophysical=+) | {_fmt_num(s2prf.get('precision'))} | {_fmt_num(s2prf.get('recall'))} | {_fmt_num(s2prf.get('f1'))} |")
        L.append("")

    # --- 10. Stage-3 macro F1 and per-class PRF ---
    s3macro = m.get("part_c_stage3_macro_f1")
    s3prf = m.get("part_c_stage3_per_class_prf") or {}
    if s3macro is not None or s3prf:
        L.append("### 10. Stage-3 subclass PRF")
        L.append("")
        if s3macro is not None:
            L.append(f"- **Macro F1:** {_fmt_num(s3macro)}")
            L.append("")
        if s3prf:
            L.append("| Class | Precision | Recall | F1 |")
            L.append("|---|---|---|---|")
            for cls, d in s3prf.items():
                L.append(f"| {cls} | {_fmt_num(d.get('precision'))} | {_fmt_num(d.get('recall'))} | {_fmt_num(d.get('f1'))} |")
            L.append("")

    # --- 11. Stage-3 confusion matrix ---
    cm = m.get("part_c_stage3_confusion_matrix")
    if cm:
        L.append("### 11. Stage-3 confusion matrix")
        L.append("")
        cols = ["supernova", "variable_star", "AGN", "N/A"]
        L.append("| gold \\ pred | " + " | ".join(cols) + " |")
        L.append("|---|" + "---|" * len(cols))
        for r_label in ("supernova", "variable_star", "AGN"):
            row = cm.get(r_label, {})
            L.append(f"| **{r_label}** | " + " | ".join(str(row.get(c, 0)) for c in cols) + " |")
        L.append("")
    return L


def _section_plots(plot_names: list[str]) -> list[str]:
    if not plot_names:
        return []
    L = ["## Plots", ""]
    L.append("The following charts are saved under `./plots/` (see `plots/README.md` for descriptions):")
    L.append("")
    for p in plot_names:
        L.append(f"- `plots/{p}`")
        L.append(f"")
        L.append(f"  ![{p}](./plots/{p})")
        L.append("")
    return L


def _section_viz(viz_counts: dict[str, int]) -> list[str]:
    if not viz_counts:
        return []
    L = ["## Per-datapoint HTML visualizations", ""]
    L.append("Self-contained `logtree` HTML files, one per selected datapoint "
             "(top-10 by ALERCE probability within each class). Open any of them "
             "directly in a browser.")
    L.append("")
    L.append("| Class | HTMLs in `viz/` |")
    L.append("|---|---|")
    for cls, n in viz_counts.items():
        L.append(f"| {cls} | {n} (`viz/{cls}/`) |")
    L.append("")
    return L


def write_enriched_report(
    out_path: Path,
    meta: dict[str, Any],
    config: dict[str, Any],
    metrics: dict[str, Any],
    plot_names: list[str] | None = None,
    viz_counts: dict[str, int] | None = None,
    hypothesis: str | None = None,
    comparison: str | None = None,
    prompt_summary: str | None = None,
    observations: str | None = None,
) -> None:
    """Write `<run_folder>/report.md` with every metric from `metrics`."""
    slug = meta.get("slug", "run")
    ts = meta.get("run_timestamp", "?")
    title = f"# Run report — {meta.get('model_label') or config.get('model', '?')}  ({ts})"
    lines: list[str] = [title, ""]

    lines += _section_metadata(meta)

    if hypothesis:
        lines += ["## Hypothesis", "", hypothesis.strip(), ""]
    if comparison:
        lines += ["## Baseline / Comparison", "", comparison.strip(), ""]

    lines += _section_config(config)

    if prompt_summary:
        lines += ["## Prompt Summary", "", prompt_summary.strip(), ""]

    lines += _section_data(meta)
    lines += _section_command(meta)

    # Output block
    lines += ["## Output", ""]
    lines.append(f"- **Predictions JSONL (in run folder):** `run.jsonl`")
    if meta.get("original_jsonl"):
        lines.append(f"- **Original path:** `{meta['original_jsonl']}`")
    if meta.get("wallclock"):
        lines.append(f"- **Wall-clock runtime:** {meta['wallclock']}")
    lines.append(f"- **Records written:** {meta.get('n_records', '?')}")
    lines.append(f"- **Records with parsed JSON:** {metrics.get('json_parseable', '?')} "
                 f"({_fmt_num(metrics.get('json_valid_rate'), pct=True)})")
    lines.append("")

    lines += _section_results(metrics)
    lines += _section_plots(plot_names or [])
    lines += _section_viz(viz_counts or {})

    if observations:
        lines += ["## Observations", "", observations.strip(), ""]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
