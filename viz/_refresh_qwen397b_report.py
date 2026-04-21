"""One-shot: refresh report.md for the Qwen3.5-397B-A17B full-benchmark run
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

RUN_DIR = PROJECT_ROOT / "runs" / "20260420-1554-qwen35-397b-a17b-benchmark-full"

OBSERVATIONS = """
- **Hypothesis partially matched.** Parse rate went *up* to **100.00 %** (1500/1500, not a single format error) vs the fewshot 99.0 %, and truncation remained **0 %** (max output 16 882 tokens, well under the 20 000 cap). However, 5-class accuracy *dropped* from fewshot 48.5 % to **44.27 %** — a 4-pt regression at 15x data. Not what we expected.
- **New failure mode distinct from Kimi: SN -> AGN confusion.** Stage-3 confusion matrix shows 141 / 300 SN rows predicted as `AGN` (47 %), only 54 correctly as `supernova`. Per-class SN accuracy collapses to **18.0 %**, vs Kimi's 65.0 %. This is a different miscalibration than Kimi's AGN→VS: Qwen-397B treats many supernovae as AGN, then *still* treats most AGN as VS (265/300 AGN → VS). Two stacked confusions compound the damage.
- **AGN→VS is universal, again** (265 / 300 AGN -> variable_star, same pattern as every prior open-source run). Per-class AGN accuracy 6.0 %, F1 0.078.
- **bogus handling is much better than Kimi** (43.3 % vs Kimi's 11.0 %). Stage-1 real/artifact accuracy 80.9 %, similar to Kimi's 81.4 %, but the precision/recall trade-off is different: Qwen-397B's stage-1 real_object recall is 90.2 % (Kimi: 98.9 %) — it's willing to call things artifact more often, which helps bogus without hurting real sources catastrophically.
- **Part A (metadata reading) is 100 %** on all 6 fields, same as Kimi.
- **Stage-3 conditional accuracy is the killer: 32.4 %** vs Kimi's 53.5 %. When Stages 1+2 are correct, Qwen-397B picks the wrong subclass 2/3 of the time. The end-to-end staged accuracy (44.3 %) is basically capped by this one bottleneck.
- **Thinking-heavy outputs**: mean output_tokens 5171, but mean answer_tokens only 456 — roughly **91 %** of tokens go to thinking. answer_tokens tightly bounded (341-758), so the JSON envelope is consistent; variability is entirely in reasoning length.
- **Calibration is completely flat** (pearson_r 0.005, calibration_gap 0.001, high-conf accuracy 44.3 % vs low-conf 0.0 % on only n=2). Self-rated MSRS 4.74 is highest in the sweep, and 99.86 % of rows self-pass at >= 4 — self-confidence is useless as a filter.
- **Runtime: 20 239 s (~5h 37m) at concurrency 32**, ~13.5 s/row. Roughly 2.5x slower than Kimi K2.5 at the same concurrency, as expected for a much larger model. No timeouts.
- **Suggested next experiment:** The SN -> AGN collapse is new and specific to this model. Targeted Stage-3 SN-vs-AGN guidance in `prompts.py` (rise-time, colour evolution, host-galaxy alignment) or few-shot SN exemplars would be more useful than generic AGN-VS tuning here. Alternatively, comparing per-class accuracy against Qwen3.5-35B-A3B when that finishes will show whether this is a scaling artifact or a 397B-specific quirk.
""".strip()


def main() -> None:
    metrics = json.loads((RUN_DIR / "metrics.json").read_text(encoding="utf-8"))
    rows = _load_jsonl(RUN_DIR / "run.jsonl")
    cfg = _extract_config_from_rows(rows, "Qwen/Qwen3.5-397B-A17B", "prompts", "tinker")
    cfg["concurrency"] = 32
    cfg["wallclock"] = "20239 s (~5h 37m)"

    git = _git_info()
    meta = {
        "run_folder": RUN_DIR.name,
        "run_timestamp": "20260420-1554",
        "slug": "qwen35-397b-a17b-benchmark-full",
        "status": "complete",
        "operator": "user",
        "commit": git["commit"],
        "dirty": git["dirty"],
        "dirty_files": git["dirty_files"],
        "manifest_path": "data/manifest_benchmark_final.csv",
        "n_records": len(rows),
        "class_distribution": dict(Counter(r.get("target_class", "?") for r in rows)),
        "model_label": "Qwen/Qwen3.5-397B-A17B",
        "original_jsonl": "results/benchmark_qwen35_397b_a17b.jsonl",
        "wallclock": "20239 s (~5h 37m)",
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
            "First full 1500-row benchmark for Qwen3.5-397B-A17B (hybrid thinking enabled). "
            "The 100-row fewshot run reached 48.5 % 5-class / 99 % parse; expect similar "
            "numbers at 15x data. This is the largest open-source model in the sweep."
        ),
        comparison=(
            "Compared to runs/20260419-2230-qwen35-397b-a17b (same model + renderer + "
            "prompts.py + max_tokens=20000, only difference: fewshot-100 -> "
            "benchmark-final-1500 with top-300-by-ALERCE-probability per class, "
            "no oid overlap with fewshot)."
        ),
        observations=OBSERVATIONS,
    )
    regenerate_index(PROJECT_ROOT / "runs")
    regenerate_jsonl_index(PROJECT_ROOT / "runs")
    print("report.md + index refreshed")


if __name__ == "__main__":
    main()
