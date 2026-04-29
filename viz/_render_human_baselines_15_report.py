"""Regenerate results_comparison/report/20260429_report_human_baselines_15_all_runs.md."""
from __future__ import annotations

import math
from pathlib import Path

from viz._make_charts_human_baselines_15 import load_all, ols_slope_stderr

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results_comparison" / "report" / "20260429_report_human_baselines_15_all_runs.md"
CLASSES = ["SN", "AGN", "VS", "asteroid", "bogus"]


def se_prop(p: float, n: int) -> float:
    return math.sqrt(p * (1.0 - p) / n) if n > 0 else 0.0


def pct(p: float, se: float) -> str:
    return f"{p * 100:.2f} ± {se * 100:.2f} %"


def main() -> None:
    runs = load_all()
    runs.sort(key=lambda r: r["p_abs"], reverse=True)

    xs = [r["msrs"] for r in runs]
    ys = [r["p_abs"] * 100 for r in runs]
    m_ols, se_ols = ols_slope_stderr(xs, ys)

    lines: list[str] = []
    lines.append(
        "# Human-baselines comparison — 13 runs on `manifest_human_baselines_15.csv` (Apr 28–29 2026)\n\n"
    )
    lines.append(
        "Cross-run comparison of the **same 13 model configurations** as "
        "[`20260421_report_benchmark_full_all_runs.md`](20260421_report_benchmark_full_all_runs.md), "
        "evaluated on **`data/manifest_human_baselines_15.csv`** — **15** human-curated cutouts "
        "(metadata under `human_samples/human_baselines/`; gold class counts: **AGN 5, VS 3, SN 2, bogus 3, asteroid 3** — see `data/manifest_human_baselines_15.md`). "
        "Prompt module is **`prompts.py`** (same AstroAlertBench-style Parts A–C JSON as the full benchmark); montages default to **`stamps_llm_updated/`** (`prompts.STAMPS_LLM_DIRNAME`). "
        "Metrics come from `evaluate.evaluate_jsonl` and each run’s `runs/<timestamp>-<slug>/metrics.json`.\n\n"
    )
    lines.append(
        "**Small-n warning.** With **n ≈ 15** rows per sweep (Kimi K2.5 has **14** API rows in `run.jsonl`; two Qwen runs have **parse/evaluable n < 15**), "
        "binomial **1σ SE on absolute accuracy is ~10–13 percentage points** near 50 % correctness. "
        "Head-to-head gaps below **~25 pt** are usually **not** significant at |z| > 2; treat this report as a **sanity / qualitative** check on the human slice, not a replacement for the 1500-row benchmark.\n\n"
    )
    lines.append(
        "**Standard error convention:** same as the full-benchmark report: "
        "`SE = √(p·(1−p)/n)` for proportions; **1σ** bars in figures and tables. "
        "OLS slope SE on MSRS vs accuracy (Fig 7) is the usual regression standard error (homoskedastic), **n = 13** points.\n\n"
    )
    lines.append(
        "**Figures.** Nine charts in `charts/human_baselines_15/`, same numbering as the full-benchmark report. Regenerate with `python -m viz._make_charts_human_baselines_15`.\n\n"
    )
    lines.append("| Fig | Section | What it shows |\n|---:|---|---|\n")
    lines.append("| 1 | §1 | Absolute 5-class accuracy ranked (± 1σ SE) |\n")
    lines.append("| 2 | §2 | Per-class accuracy heatmap (13 × 5) |\n")
    lines.append("| 3 | §3 | Stage-wise cascade |\n")
    lines.append("| 4 | §4 | True-AGN predicted distribution, top 4 runs |\n")
    lines.append("| 5 | §6 | Token economy (mean / p95 / max) |\n")
    lines.append("| 6 | §7 | Format error breakdown (stacked counts) |\n")
    lines.append("| 7 | §9 | MSRS vs absolute accuracy + OLS |\n")
    lines.append("| 8 | §10 | Think vs nothink paired bars (5 families) |\n")
    lines.append("| 9 | §12 | Compute–accuracy Pareto (log mean tokens) |\n")
    lines.append("\n---\n\n## Runs covered (13; human baselines)\n\n")
    lines.append("| # | Slug | Run folder | Model | Notes |\n|---|---|---|---|---|\n")
    slug_order = [
        ("1", "opus47-think-human-baselines-15", "20260428-2356-opus47-think-human-baselines-15", "Claude Opus 4.7 think", "n=15"),
        ("2", "gpt-5.4-high-human-baselines-15", "20260428-2358-gpt-5.4-high-human-baselines-15", "gpt-5.4 high", "n=15"),
        ("3", "kimi-k25-human-baselines-15", "20260428-2349-kimi-k25-human-baselines-15", "Kimi K2.5 think", "**n=14** in JSONL"),
        ("4", "opus47-nothink-human-baselines-15", "20260428-2357-opus47-nothink-human-baselines-15", "Claude Opus 4.7 nothink", "n=15"),
        ("5", "qwen35-397b-a17b-human-baselines-15", "20260428-2348-qwen35-397b-a17b-human-baselines-15", "Qwen3.5-397B think", "n=15"),
        ("6", "gpt-5.4-none-human-baselines-15", "20260428-2359-gpt-5.4-none-human-baselines-15", "gpt-5.4 none", "n=15"),
        ("7", "gemini25-pro-high-human-baselines-15", "20260428-2356-gemini25-pro-high-human-baselines-15", "Gemini 2.5 Pro high", "n=15"),
        ("8", "gemini25-flash-none-human-baselines-15", "20260429-0042-gemini25-flash-none-human-baselines-15", "Gemini 2.5 Flash none", "n=15"),
        ("9", "qwen35-397b-a17b-nothink-human-baselines-15", "20260428-2330-qwen35-397b-a17b-nothink-human-baselines-15", "Qwen3.5-397B nothink", "n=15 (n_e=14)"),
        ("10", "qwen35-35b-a3b-human-baselines-15", "20260429-0019-qwen35-35b-a3b-human-baselines-15", "Qwen3.5-35B think", "n=15 (n_e=13)"),
        ("11", "qwen35-35b-a3b-nothink-human-baselines-15", "20260428-2357-qwen35-35b-a3b-nothink-human-baselines-15", "Qwen3.5-35B nothink", "n=15"),
        ("12", "qwen35-4b-nothink-human-baselines-15", "20260428-2356-qwen35-4b-nothink-human-baselines-15", "Qwen3.5-4B nothink", "n=15"),
        ("13", "qwen35-4b-human-baselines-15", "20260429-0026-qwen35-4b-human-baselines-15", "Qwen3.5-4B think", "n=15 (heavy trunc.; n_e=3)"),
    ]
    for row in slug_order:
        lines.append(f"| {row[0]} | `{row[1]}` | `{row[2]}` | {row[3]} | {row[4]} |\n")

    lines.append("\n---\n\n## 1. Headline numbers\n\n")
    lines.append(
        "Absolute 5-class accuracy = **parse_rate × part_c_final_5class_accuracy** over `n_examples` from each `metrics.json`. "
        "Denominator for SE on the absolute column is **`n_examples`** (total manifest rows in that run’s JSONL).\n\n"
    )
    lines.append(
        "| Rank | Run | 5-class (on parsed) | Parse rate | Truncation | **Absolute** | Macro F1 | MSRS |\n"
        "|---:|---|---:|---:|---:|---:|---:|---:|\n"
    )
    rank = 1
    for r in runs:
        m = r["m"]
        nt = r["n_total"]
        ne = r["n_parsed"]
        pr = r["parse_rate"]
        p5 = r["p_parsed"]
        p_abs = r["p_abs"]
        se_on = se_prop(p5, ne)
        se_pr = se_prop(pr, nt)
        se_abs = r["se_abs"]
        trunc = float(m["truncated_rate"])
        f1 = float(m["part_c_stage3_macro_f1"])
        msrs = float(m["part_b_msrs"])
        lines.append(
            f"| {rank} | {r['label']} | {pct(p5, se_on)} (n={ne}) | {pct(pr, se_pr)} | {trunc * 100:.2f} % | "
            f"**{pct(p_abs, se_abs)}** (n={nt}) | {f1:.4f} | {msrs:.2f} |\n"
        )
        rank += 1

    lines.append(
        "\n![Fig 1](charts/human_baselines_15/01_absolute_5class_ranked.png)\n\n"
        f"*Fig 1. Ranked absolute 5-class on the human-baseline slice. **{runs[0]['label']}** leads at "
        f"{runs[0]['p_abs'] * 100:.1f} ± {runs[0]['se_abs'] * 100:.1f} %, but error bars overlap most of the mid-pack — "
        "this is expected at n ≈ 15.*\n\n"
    )
    lines.append(
        "**Takeaway.** Opus 4.7 think remains the best single point on this slice, but **gpt-5.4 high**, "
        "**Qwen3.5-397B think**, and **Gemini 2.5 Pro** tie at **40 %** absolute within ±1σ. "
        "**Qwen3.5-4B think** repeats the full-benchmark failure mode: **86.7 % truncation** and only **three** evaluable Part-C rows.\n\n"
    )

    lines.append("---\n\n## 2. Per-class accuracy\n\n")
    lines.append(
        "Cells: `correct/total ± SE` with binomial SE on that cell’s `total`. "
        "Gold counts follow each run’s `per_class_total` (subset of the 15 rows with a parseable staged prediction for that class). "
        "**Do not** compare to the 300/× full-benchmark denominators.\n\n"
    )
    lines.append("| Run | SN | AGN | VS | asteroid | bogus |\n|---|---:|---:|---:|---:|---:|\n")
    for r in runs:
        cells = []
        for c in CLASSES:
            tot = int(r["per_class_total"].get(c, 0))
            corr = int(r["per_class_correct"].get(c, 0))
            if tot <= 0:
                cells.append("—")
            else:
                p = corr / tot
                se = se_prop(p, tot)
                cells.append(f"{corr}/{tot} ({pct(p, se)})")
        lines.append(f"| {r['label']} | " + " | ".join(cells) + " |\n")

    lines.append(
        "\n![Fig 2](charts/human_baselines_15/02_per_class_heatmap.png)\n\n"
        "*Fig 2. Heatmap (same layout as full-benchmark report). Sparse denominators make individual cells noisy.*\n\n"
    )

    lines.append("---\n\n## 3. Stage-wise accuracy (Part C cascade)\n\n")
    lines.append(
        "| Run | n_p | Stage-1 | Stage-2 | Stage-3 | S3 cond. | End-to-end |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
    )
    for r in runs:
        m = r["m"]
        ne = r["n_parsed"]
        s1, s2, s3 = r["stage1"], r["stage2"], r["stage3"]
        s3c = r["stage3c"]
        e2e = float(m["part_c_end_to_end_staged_accuracy"])
        lines.append(
            f"| {r['label']} | {ne} | {pct(s1, se_prop(s1, ne))} | {pct(s2, se_prop(s2, ne))} | "
            f"{pct(s3, se_prop(s3, ne))} | {pct(s3c, se_prop(s3c, ne))} | {pct(e2e, se_prop(e2e, ne))} |\n"
        )

    lines.append(
        "\n![Fig 3](charts/human_baselines_15/03_stagewise_cascade.png)\n\n"
        "*Fig 3. Cascade bars. Stage definitions match `evaluate.py`.*\n\n"
    )

    lines.append("---\n\n## 4. Stage-3 confusion — top 4 runs (true AGN rows)\n\n")
    lines.append(
        "Mirroring the full report, Fig 4 shows where **true AGN gold** rows land in predicted stage-3 labels for the **top four** runs by absolute accuracy. "
        "Counts come from `part_c_stage3_confusion_matrix['AGN']`.\n\n"
    )
    lines.append("![Fig 4](charts/human_baselines_15/04_agn_collapse_pie.png)\n\n*Fig 4. AGN → predicted (top 4).* \n\n")

    top4 = runs[:4]
    for r in top4:
        cm = r["cm"]
        agn = cm.get("AGN", {})
        lines.append(f"**{r['label']}** — AGN row counts: {dict(agn)}\n\n")

    lines.append("---\n\n## 5. Stage-3 subclass F1 (point estimates)\n\n")
    lines.append("`part_c_stage3_macro_f1` from each `metrics.json` (no binomial SE). Macro-F1 is extremely volatile at n ≈ 15.\n\n")
    lines.append("| Run | Macro F1 |\n|---|---:|\n")
    for r in runs:
        lines.append(f"| {r['label']} | {r['macro_f1']:.4f} |\n")

    lines.append("\n---\n\n## 6. Token economy\n\n")
    lines.append(
        "| Run | Mean | p95 | Max |\n|---|---:|---:|---:|\n"
    )
    for r in runs:
        lines.append(
            f"| {r['label']} | {r['mean_out_tokens']:.0f} | {r['p95_out_tokens']:.0f} | {r['max_out_tokens']:.0f} |\n"
        )
    lines.append(
        "\n![Fig 5](charts/human_baselines_15/05_token_economy.png)\n\n"
        "### 6.1 Wall-clock (run folder)\n\n"
        "| Run | Wall-clock |\n|---|:---|\n"
    )
    for r in sorted(runs, key=lambda x: x["label"]):
        wc = r["m"].get("wall_clock") or {}
        wh = wc.get("wall_clock_human", "—")
        lines.append(f"| {r['label']} | {wh} |\n")

    lines.append("\n---\n\n## 7. Format error breakdown\n\n")
    lines.append("![Fig 6](charts/human_baselines_15/06_error_breakdown_stacked.png)\n\n")
    lines.append(
        "*Fig 6. Stacked `error_breakdown.format` counts. Qwen3.5-4B (think) is almost entirely **truncated_no_json** on this slice.*\n\n"
    )

    lines.append("---\n\n## 8. Part A\n\n")
    lines.append(
        "All completed runs report **100 %** `part_a_macro_accuracy` and **100 %** `part_a_exact_match_rate` on this slice — "
        "same as the full benchmark. Part A is not the discriminator here.\n\n"
    )

    lines.append("---\n\n## 9. Part B / self-scoring\n\n")
    lines.append(
        "MSRS and **self_pass_rate** (pass = row mean of three Part B self-ratings **≥ 4**, see full-benchmark §9). "
        f"OLS on absolute accuracy vs MSRS: slope **{m_ols:.1f} ± {se_ols:.1f}** pp per MSRS unit (n = 13).\n\n"
    )
    lines.append("| Run | MSRS | self_pass_rate |\n|---|---:|---:|\n")
    for r in sorted(runs, key=lambda x: -x["msrs"]):
        m = r["m"]
        ne = r["n_parsed"]
        spr = float(m["part_b_self_pass_rate"])
        lines.append(f"| {r['label']} | {r['msrs']:.4f} | {pct(spr, se_prop(spr, ne))} |\n")
    lines.append(
        "\n![Fig 7](charts/human_baselines_15/07_msrs_vs_accuracy.png)\n\n*Fig 7. MSRS vs accuracy with OLS line.*\n\n"
    )

    lines.append("---\n\n## 10. Think vs nothink (paired)\n\n")
    lines.append("![Fig 8](charts/human_baselines_15/08_think_vs_nothink.png)\n\n")
    lines.append(
        "*Fig 8. Same five families as the full-benchmark report (Qwen 4B / 35B / 397B, GPT-5.4, Opus 4.7). "
        "Δ and z are **not** interpreted at n ≈ 15 — shown for visual parity only.*\n\n"
    )

    lines.append("---\n\n## 11. Closed-source vs open-source (informal)\n\n")
    lines.append(
        "On this slice, **Opus**, **GPT-5.4**, and **Gemini** runs sit mid-pack together with **Qwen3.5-397B think** — "
        "no clean closed-vs-open separation with these error bars. The main **outlier** remains **Qwen3.5-4B think** (truncation).\n\n"
    )

    lines.append("---\n\n## 12. Compute efficiency (Pareto)\n\n")
    lines.append("![Fig 9](charts/human_baselines_15/09_compute_pareto.png)\n\n")
    lines.append(
        "*Fig 9. Mean output tokens (log x) vs absolute accuracy. Frontier is illustrative only at n ≈ 15.*\n\n"
    )

    lines.append("---\n\n## 13. Recommendations\n\n")
    lines.append(
        "1. **Do not** conclude model ordering from this slice alone — use [`20260421_report_benchmark_full_all_runs.md`](20260421_report_benchmark_full_all_runs.md) for ranking. "
        "2. **Use human baselines** to catch gross regressions (e.g. truncation, asteroid collapse on visually curated examples) cheaply. "
        "3. **Complete the Kimi row** to n = 15 if a missing OID is unintended (`run.jsonl` currently has 14 lines). "
        "4. Rebuild figures after any `metrics.json` refresh: `python -m viz._make_charts_human_baselines_15`.\n\n"
    )

    lines.append("---\n\n## 14. Appendix — sources\n\n")
    lines.append(
        "- Manifest: `data/manifest_human_baselines_15.csv` (see also `data/manifest_human_baselines_15.md`).\n"
        "- Per-run JSONL + `metrics.json`: `runs/*-human-baselines-15/`.\n"
        "- Chart generator: `viz/_make_charts_human_baselines_15.py`.\n"
        "- This file: regenerated by `python -m viz._render_human_baselines_15_report`.\n"
    )

    OUT.write_text("".join(lines), encoding="utf-8")
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
