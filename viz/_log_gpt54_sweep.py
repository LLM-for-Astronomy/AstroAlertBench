"""One-shot driver: log the 2 GPT-5.4 benchmark-full runs (first closed-source
models run on the full 1500-row benchmark).

Creates runs/<ts>-<slug>/ for each of:
  - gpt-5.4, reasoning_effort=high  (results/benchmark_gpt54_high.jsonl)
  - gpt-5.4, reasoning_effort=none  (results/benchmark_gpt54_none.jsonl)

Observations are a placeholder here — refined in a second pass once metrics
are known (see _refresh_gpt54_reports.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from viz.build_run_folder import build_run_folder


# Concurrency labels reflect the actual sampling pattern: the initial run was at
# concurrency 16, then two retry passes via retry_failed.py at concurrency 8
# filled in the 55 (high) and 240 (none) samples that had 429 quota/timeout
# errors. Using a string so the value flows through to config as-is.
HIGH_CONCURRENCY = "16 init + 8 retry x2"
NONE_CONCURRENCY = "16 init + 8 retry x1"

RUNS = [
    {
        "jsonl": "results/benchmark_gpt54_high.jsonl",
        "model": "gpt-5.4",
        "slug": "gpt-5.4-high-benchmark-full",
        "concurrency": HIGH_CONCURRENCY,
        "baseline": (
            "runs/20260419-2230-gpt-5.4-high (same model + reasoning_effort, "
            "n=20 fewshot subset). Scale-up from 20 rows -> 1500 rows with the "
            "top-300-by-ALERCE-probability per class manifest, no oid overlap. "
            "Also compared to the best open-source run so far "
            "(runs/20260420-1226-kimi-k25-benchmark-full, 49.43% 5-class) as a "
            "closed-vs-open ceiling check."
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
    },
    {
        "jsonl": "results/benchmark_gpt54_none.jsonl",
        "model": "gpt-5.4",
        "slug": "gpt-5.4-none-benchmark-full",
        "concurrency": NONE_CONCURRENCY,
        "baseline": (
            "runs/20260419-2230-gpt-5.4-none (same model + reasoning_effort, "
            "n=20 fewshot subset). Also A/B-compared against the new "
            "gpt-5.4-high-benchmark-full run — same model and data, only the "
            "reasoning dial changed, mirroring the Qwen3.5 think/nothink A/B we "
            "did on the open-source side."
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
    },
]


def main() -> None:
    for r in RUNS:
        print(f"\n=== building {r['slug']} ===")
        run_dir = build_run_folder(
            jsonl_path=r["jsonl"],
            manifest_path="data/manifest_benchmark_final.csv",
            model_name=r["model"],
            prompts_module="prompts",
            slug_override=r["slug"],
            hypothesis=r["hypothesis"],
            comparison=f"Compared to {r['baseline']}.",
            observations="(placeholder - refined in _refresh_gpt54_reports.py once metrics are known)",
            backend_hint="openai",
            extra_config={"concurrency": r["concurrency"]},
        )
        print(f"wrote {run_dir}")


if __name__ == "__main__":
    main()
