"""One-shot: refresh report.md for the Kimi K2.5 full-benchmark run
with filled observations, without redoing eval/HTMLs/plots."""
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

RUN_DIR = PROJECT_ROOT / "runs" / "20260420-1226-kimi-k25-benchmark-full"

OBSERVATIONS = """
- **Hypothesis matched strongly.** The 100-row fewshot result (5-class 49.0 %, parse 100 %, trunc 0 %) reproduces almost exactly at 15x data: 5-class **49.43 %**, parse **99.80 %** (1497/1500), truncated **0 %**. Per-class ordering preserved (VS > asteroid > SN > bogus > AGN).
- **Part A (metadata reading) is 100 % across all 6 questions on 1500 rows.** No surprise given the fewshot result, but useful as a sanity-check that the manifest pipeline is clean at full scale.
- **Dominant failure mode: AGN collapses into VS.** Stage-3 confusion matrix shows 276 / 300 AGN rows predicted as `variable_star`, only 16 as `AGN` (per-class recall 5.33 %, precision 29.1 %). Same pattern as every prior open-source run, now at 300-row statistical significance. The model treats slowly-varying extragalactic sources as intrinsic stellar variability.
- **bogus at 11 % is the second-worst class** — Stage-1 real/artifact accuracy is 81.4 %, but recall on real_object is 98.9 % vs precision 81.7 %, meaning the model almost never says "artifact" when it is one. bogus sources are routed through Stages 2/3 as if they were real.
- **Token budget is comfortable**: mean 3943 output tokens, max 10228, p95 6576 — the 20 000 cap was never approached. Could safely drop max_tokens to ~12 000 for a ~40 % throughput increase on future runs.
- **Calibration is essentially flat** (pearson_r = 0.049, calibration_gap = 0.03): model self-score of 4.5 is almost invariant to whether the row is correct. Self-reported MSRS cannot be used as a confidence filter.
- **Runtime: 8013 s at concurrency 64**, ~5.3 s/row end-to-end. No timeouts or failures on this run.
- **Suggested next experiment:** targeted Stage-3 AGN-vs-VS guidance in `prompts.py` (photometric timescale, blue colour, host-galaxy context), or few-shot AGN exemplars. Isolating Stage 3 conditional on correct Stages 1+2 (53.5 %) is the single biggest accuracy lever.
""".strip()


def main() -> None:
    metrics = json.loads((RUN_DIR / "metrics.json").read_text(encoding="utf-8"))
    rows = _load_jsonl(RUN_DIR / "run.jsonl")
    cfg = _extract_config_from_rows(rows, "moonshotai/Kimi-K2.5", "prompts", "tinker")
    cfg["concurrency"] = 64
    cfg["wallclock"] = "8012.8 s (~2h 14m)"

    git = _git_info()
    meta = {
        "run_folder": RUN_DIR.name,
        "run_timestamp": "20260420-1226",
        "slug": "kimi-k25-benchmark-full",
        "status": "complete",
        "operator": "user",
        "commit": git["commit"],
        "dirty": git["dirty"],
        "dirty_files": git["dirty_files"],
        "manifest_path": "data/manifest_benchmark_final.csv",
        "n_records": len(rows),
        "class_distribution": dict(Counter(r.get("target_class", "?") for r in rows)),
        "model_label": "moonshotai/Kimi-K2.5",
        "original_jsonl": "results/benchmark_kimi_k25.jsonl",
        "wallclock": "8012.8 s (~2h 14m)",
    }

    plot_names = sorted(p.name for p in (RUN_DIR / "plots").glob("*.png"))
    viz_counts = {
        cls: len(list((RUN_DIR / "viz" / cls).glob("*.html")))
        for cls in ("SN", "AGN", "VS", "asteroid", "bogus")
    }

    write_enriched_report(
        out_path=RUN_DIR / "report.md",
        meta=meta,
        config=cfg,
        metrics=metrics,
        plot_names=plot_names,
        viz_counts=viz_counts,
        hypothesis=(
            "First full 1500-row benchmark for Kimi K2.5 (thinking-enabled renderer). "
            "Expect the 100-row fewshot result (49.0 % 5-class, 100 % parse, 0 % trunc) "
            "to roughly hold at 15x data, with per-class patterns preserved."
        ),
        comparison=(
            "Compared to runs/20260419-2230-kimi-k25-think (same model + renderer + "
            "prompts.py + max_tokens=20000, only difference is manifest: fewshot-100 "
            "-> benchmark-final-1500 with top-300-by-ALERCE-probability per class, "
            "no oid overlap)."
        ),
        observations=OBSERVATIONS,
    )
    regenerate_index(PROJECT_ROOT / "runs")
    regenerate_jsonl_index(PROJECT_ROOT / "runs")
    print("report.md + index refreshed")


if __name__ == "__main__":
    main()
