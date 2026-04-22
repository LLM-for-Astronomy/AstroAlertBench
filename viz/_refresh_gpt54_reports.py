"""Second pass: refresh report.md for the two GPT-5.4 benchmark-full runs with
observations derived from the now-known metrics. Does NOT re-run eval.

Refreshed Apr 22 2026 after the Apr 21 runs were completed: both runs had
insufficient-quota (429) null rows after the initial pass (55 for high, 240 for
none), which were filled in by two (high) / one (none) concurrent-8 retry
passes via retry_failed.py. Final JSONLs now contain 1500/1500 clean rows.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from viz.build_run_folder import _extract_config_from_rows, _git_info, _load_jsonl
from viz.enriched_report import write_enriched_report
from viz.index import regenerate_index, regenerate_jsonl_index


RUNS = [
    {
        "dir": "runs/20260421-2024-gpt-5.4-high-benchmark-full",
        "model": "gpt-5.4",
        "slug": "gpt-5.4-high-benchmark-full",
        "original_jsonl": "results/benchmark_gpt54_high.jsonl",
        "run_timestamp": "20260421-2024",
        "concurrency": "16 init + 8 retry x2",
        "wallclock": (
            "5145.1 s total across one initial pass and two retry passes "
            "(initial 4741.0 s @ concurrency 16, retry-1 241.9 s @ concurrency 8, "
            "retry-2 162.2 s @ concurrency 8). Retry passes filled in the 55 "
            "rows that returned 429 insufficient_quota from the OpenAI Responses "
            "API during the initial run."
        ),
        "baseline": (
            "runs/20260419-2230-gpt-5.4-high (same model + reasoning_effort=high, "
            "n=20 fewshot subset) and runs/20260420-1226-kimi-k25-benchmark-full "
            "(previous open-source SOTA at 49.43% 5-class)."
        ),
        "hypothesis": (
            "First closed-source run on the full benchmark. On the 20-row "
            "fewshot slice, reasoning_effort=high hit 100% parse / 0% trunc but "
            "only 40% 5-class, with all 4 SNe mislabelled as AGN. Open questions "
            "at 1500 rows: (a) does the 40% -> 50% lift scale with more data or "
            "was the small-n number noise? (b) does SN->AGN collapse persist or "
            "dissolve into a more balanced error pattern? (c) can GPT-5.4-high "
            "beat the open-source ceiling set by Kimi K2.5 (49.43%)?"
        ),
        "comparison": (
            "Compared to runs/20260419-2230-gpt-5.4-high (same model + config, "
            "n=20 -> n=1500 scale-up) and runs/20260420-1226-kimi-k25-benchmark-full "
            "(prior open-source SOTA). Also A/B compared to the sibling "
            "gpt-5.4-none-benchmark-full run (same model + data, only "
            "reasoning_effort changed)."
        ),
        "observations": """
- **NEW PROJECT-WIDE SOTA: 51.07 % 5-class accuracy** — first model to clear 50 % on the full 1500-row benchmark. Beats the previous best (Kimi K2.5-think, 49.43 %) by **+1.64 pt** absolute, and beats its own 20-row fewshot result (40.00 %) by **+11.07 pt**, confirming the fewshot number was too noisy to read as anything definitive. Because parse rate is now 100 %, the "on parsed" and "absolute over 1500" numbers coincide — this is the honest 1500-row figure.
- **Parse rate 100.00 % / truncation 0 % / 0 runtime errors.** After the Apr-22 retry passes the 55 originally-null rows (3.67 %, all 429 insufficient_quota from the OpenAI backend) are now genuine model responses. Every row parsed cleanly, zero format errors, zero value_errors. Model-level JSON discipline is effectively perfect.
- **Per-class profile is very different from the open-source leader.** Compared to Kimi K2.5-think (at 1500 rows):
  - **SN:** 65.00 % (Kimi) -> 38.67 % (GPT-5.4-high, **-26.33 pt**) — Kimi remains the strongest SN detector by a wide margin.
  - **AGN:** 5.33 % -> 7.33 % (+2.00) — both essentially broken; AGN is the universal failure class.
  - **VS:** 90.27 % -> 95.33 % (**+5.06**).
  - **asteroid:** 75.67 % -> 75.67 % (tie).
  - **bogus:** 11.04 % -> 38.33 % (**+27.29**) — GPT-5.4 is the first model to get bogus detection into useful range. This is the single biggest per-class gap over Kimi and the main driver of the new SOTA.
- **SN -> AGN confusion persists but is not total.** Stage-3 confusion shows **141 / 300** SN rows going to AGN (47 %), vs 116 correct, 22 N/A, and 21 -> VS. The fewshot-20 run was 4/4 SN -> AGN = 100 %; at n=1500 the failure mode softens to ~47 %, enough to explain both the Apr-19 doom signal and the real SOTA result here. Stage-3 macro F1 is **0.4345** (vs Kimi's 0.500) — the SN recall ceiling is what GPT-5.4 is paying for its bogus gain.
- **Reasoning dominates the output budget.** output_tokens mean **2 557** of which answer_tokens mean 445 — **~82.6 % of generated tokens are hidden CoT**. Max output 8 156 tokens (well under the 20 000 cap). Compared to Kimi K2.5-think's mean 3 943 total / 435 visible (~89 % CoT), GPT-5.4 is slightly more compact per row but spends its budget the same way: almost entirely on reasoning.
- **Stage-1 and stage-2 are both solid.** Stage-1 (real vs artifact) **83.93 %**, stage-2 (astrophysical vs solar_system) **80.00 %**. End-to-end staged accuracy = final 5-class = 51.07 % by construction. Stage-3 conditional accuracy **47.11 %** is the actual ceiling once the model has decided "astrophysical".
- **Calibration (Part B <-> Part C) is weak but present.** MSRS 4.185, self_pass_rate 92.13 %, calibration_gap +0.130, pearson_r 0.203, high-conf (>=4) accuracy 51.88 % vs low-conf 41.53 %. Unlike every Qwen run, GPT-5.4's high-conf rows really are *slightly* more accurate than low-conf rows — calibration is miscalibrated upward but not monotonically wrong.
- **Practical takeaway:** GPT-5.4 high is the current SOTA for *balanced* performance — it trades ~26 pt of SN accuracy for +27 pt of bogus accuracy, which is a good deal for most downstream pipelines (bogus rejection is the first gate in alert triage). For a supernova-heavy workflow, however, Kimi K2.5-think still wins. Next cheapest experiment: a hybrid that routes SN-candidate-looking rows to Kimi and everything else to GPT-5.4 would likely top 55 % without any model change.
""".strip(),
    },
    {
        "dir": "runs/20260421-2032-gpt-5.4-none-benchmark-full",
        "model": "gpt-5.4",
        "slug": "gpt-5.4-none-benchmark-full",
        "original_jsonl": "results/benchmark_gpt54_none.jsonl",
        "run_timestamp": "20260421-2032",
        "concurrency": "16 init + 8 retry x1",
        "wallclock": (
            "929.5 s total across one initial pass and one retry pass "
            "(initial 682.1 s @ concurrency 16, retry 247.4 s @ concurrency 8). "
            "Retry pass filled in the 240 rows that returned 429 "
            "insufficient_quota from the OpenAI Responses API during the "
            "initial run."
        ),
        "baseline": (
            "runs/20260419-2230-gpt-5.4-none (same model + reasoning_effort=none, "
            "n=20 fewshot subset) and the sibling gpt-5.4-high-benchmark-full "
            "run (same model + data, only reasoning_effort changed)."
        ),
        "hypothesis": (
            "Direct-answer closed-source baseline at full benchmark scale. On "
            "the 20-row fewshot, reasoning_effort=none actually *beat* "
            "reasoning_effort=high (50% vs 40% 5-class) at ~5x less output "
            "tokens, which was suspicious. This run tests whether that finding "
            "holds at 1500 rows or whether the sample was too small. If high "
            "decisively wins here, the fewshot result was just small-n; if none "
            "stays close or ahead, GPT-5.4's non-reasoning mode is genuinely "
            "competitive for this visual-classification task."
        ),
        "comparison": (
            "A/B compared to the sibling gpt-5.4-high-benchmark-full run "
            "(same model + data, only reasoning_effort changed). Also compared "
            "to runs/20260419-2230-gpt-5.4-none (same model + config, n=20 -> n=1500 "
            "scale-up) to check whether the fewshot 'none beats high' result held."
        ),
        "observations": """
- **Hypothesis resolved: the fewshot 'none beats high' result was small-n noise.** At n=1500 the ranking flips decisively — **high wins by +7.40 pt (51.07 % vs 43.67 %)**. At n=20 a 4-row flip was worth 20 pt of accuracy, so the 10-pt gap in the wrong direction was well inside the noise floor. The full benchmark gives the honest number: reasoning_effort=high is materially better at this task.
- **Parse rate 100.00 % / 0 runtime errors** after the Apr-22 retry pass (the initial pass had 240 null rows, all 429 insufficient_quota from the OpenAI backend — an infra issue, not a model pathology). Every row parses cleanly (0 JSON errors, 0 format errors, 0 value_errors).
- **Per-class profile vs the high variant (same model, only reasoning changed):**
  - **SN:** 38.67 % -> 14.33 % (**-24.34 pt**) — biggest per-class drop. Without CoT, SN rows get routed to AGN (137/300) or stage-3 N/A (92/300). N/A is a failure mode that is much larger on none (92) than high (22/300) because the refusal rate jumps when the model can't reason through the call.
  - **AGN:** 7.33 % -> 7.00 % (tie within noise, both broken).
  - **VS:** 95.33 % -> 92.33 % (-3.00) — nearly identical; VS detection barely needs reasoning.
  - **asteroid:** 75.67 % -> **81.00 % (+5.33)** — **new per-class SOTA for asteroid across all benchmark-full runs**. Direct-answer mode is actually *better* at the asteroid cue, mirroring what we saw on Qwen3.5-35B (though inverted vs Qwen3.5-397B nothink where asteroid collapsed).
  - **bogus:** 38.33 % -> 23.67 % (-14.66) — the bogus advantage the high variant enjoyed over open-source models is half eroded without reasoning; bogus detection depends on explicit artifact reasoning.
- **Stage-3 macro F1 0.3294** (vs high's 0.4345) driven almost entirely by SN recall collapse: SN precision stays 1.00 but recall falls 0.387 -> 0.143.
- **Token economy is a night-and-day gap.** output_tokens = answer_tokens, mean **446** (**~5.74x fewer total tokens per row than high**, p95 482 vs 4 887). Zero reasoning tokens by construction. If compute cost is the binding constraint, this is where the trade-off lives: -7.40 pt of 5-class accuracy in exchange for ~6x cheaper inference and ~6x lower latency per row.
- **Stage-1 / -2 drop vs high.** Stage-1 77.47 % (vs high 83.93 %), stage-2 71.53 % (vs 80.00 %). The drop is concentrated in stage-3 (conditional 37.89 % vs 47.11 %), consistent with the class-collapse pattern: deciding "real astrophysical" is easy; picking the right sub-class is where reasoning pays off.
- **MSRS 4.284 (slightly higher than high's 4.185) and self_pass_rate 97.60 % (vs 92.13 %).** The non-reasoning variant is *more confident* in its own answers despite being less accurate — a calibration regression that matches the usual pattern (models without CoT are worse-calibrated). Calibration_gap is +0.141 with pearson_r 0.219 — confidence is still weakly signal-bearing but the absolute offset is larger than high.
- **Practical takeaway:** reasoning_effort=none is the right pick only if (a) the workload is asteroid-heavy, (b) inference cost is the binding constraint, or (c) latency requires single-call decode. For general 5-class classification on this dataset, reasoning_effort=high is a clear win at ~6x the cost. For comparison with the Qwen3.5 think/nothink sweep: GPT-5.4 behaves most like Qwen3.5-397B (thinking helps decisively) but with a milder asteroid regression and a larger bogus regression.
""".strip(),
    },
]


def _refresh_one(run: dict) -> None:
    run_dir = PROJECT_ROOT / run["dir"]
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    rows = _load_jsonl(run_dir / "run.jsonl")
    cfg = _extract_config_from_rows(rows, run["model"], "prompts", "openai")
    cfg["concurrency"] = run["concurrency"]

    git = _git_info()
    meta = {
        "run_folder": run_dir.name,
        "run_timestamp": run["run_timestamp"],
        "slug": run["slug"],
        "status": "complete",
        "operator": "user",
        "commit": git["commit"],
        "dirty": git["dirty"],
        "dirty_files": git["dirty_files"],
        "manifest_path": "data/manifest_benchmark_final.csv",
        "n_records": len(rows),
        "class_distribution": dict(Counter(r.get("target_class", "?") for r in rows)),
        "model_label": run["model"],
        "original_jsonl": run["original_jsonl"],
        "wallclock": run["wallclock"],
    }

    plot_names = sorted(p.name for p in (run_dir / "plots").glob("*.png"))
    viz_counts = {
        cls: len(list((run_dir / "viz" / cls).glob("*.html")))
        for cls in ("SN", "AGN", "VS", "asteroid", "bogus")
    }

    write_enriched_report(
        out_path=run_dir / "report.md",
        meta=meta,
        config=cfg,
        metrics=metrics,
        plot_names=plot_names,
        viz_counts=viz_counts,
        hypothesis=run["hypothesis"],
        comparison=run["comparison"],
        observations=run["observations"],
    )
    print(f"report refreshed: {run_dir}")


def main() -> None:
    for r in RUNS:
        _refresh_one(r)
    regenerate_index(PROJECT_ROOT / "runs")
    regenerate_jsonl_index(PROJECT_ROOT / "runs")
    print("index + jsonl index regenerated")


if __name__ == "__main__":
    main()
