"""One-shot driver: log the 3 reasoning-disabled Qwen3.5 benchmark runs.

Creates runs/<ts>-<slug>/ for each of:
  - Qwen3.5-4B      (results/benchmark_qwen35_4b_nothink.jsonl)
  - Qwen3.5-35B-A3B (results/benchmark_qwen35_35b_a3b_nothink.jsonl)
  - Qwen3.5-397B-A17B (results/benchmark_qwen35_397b_a17b_nothink.jsonl)

Observations are left placeholder here — refined in a second pass once metrics
are known (see _refresh_nothink_reports.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from viz.build_run_folder import build_run_folder


RUNS = [
    {
        "jsonl": "results/benchmark_qwen35_4b_nothink.jsonl",
        "model": "Qwen/Qwen3.5-4B",
        "slug": "qwen35-4b-nothink-benchmark-full",
        "baseline": "runs/20260420-1920-qwen35-4b-benchmark-full (same model + prompts + data; only difference: thinking enabled there, disabled here via Qwen3_5DisableThinkingRenderer)",
        "hypothesis": (
            "Disable reasoning for Qwen3.5-4B on the full 1500-row benchmark. The thinking-enabled "
            "run collapsed at parse 22.27 % / truncated 77.47 % because the 4B model spiraled and "
            "rarely emitted JSON before the 20 000-token cap. Disabling thinking (direct-answer "
            "renderer) should push parse rate way up and truncation near zero; the open question is "
            "whether the stripped-down model is still coherent enough to produce useful labels."
        ),
    },
    {
        "jsonl": "results/benchmark_qwen35_35b_a3b_nothink.jsonl",
        "model": "Qwen/Qwen3.5-35B-A3B",
        "slug": "qwen35-35b-a3b-nothink-benchmark-full",
        "baseline": "runs/20260420-2054-qwen35-35b-a3b-benchmark-full (same model + prompts + data; only difference: thinking enabled there, disabled here via Qwen3_5DisableThinkingRenderer)",
        "hypothesis": (
            "Disable reasoning for Qwen3.5-35B-A3B on the full 1500-row benchmark. The thinking-enabled "
            "run hit parse 65.47 % / truncated 31.0 %, with most failures being token-budget spirals. "
            "Direct-answer should dramatically cut truncation. Expect parse rate ~100 % and a fair "
            "comparison of this MoE model's intrinsic visual classification skill without CoT scaffolding."
        ),
    },
    {
        "jsonl": "results/benchmark_qwen35_397b_a17b_nothink.jsonl",
        "model": "Qwen/Qwen3.5-397B-A17B",
        "slug": "qwen35-397b-a17b-nothink-benchmark-full",
        "baseline": "runs/20260420-1554-qwen35-397b-a17b-benchmark-full (same model + prompts + data; only difference: thinking enabled there, disabled here via Qwen3_5DisableThinkingRenderer)",
        "hypothesis": (
            "Disable reasoning for Qwen3.5-397B-A17B on the full 1500-row benchmark. The thinking-enabled "
            "run already reached 100 % parse / 0 % truncation at 44.27 % 5-class accuracy, with ~91 % "
            "of tokens spent on reasoning. Direct-answer removes that cost: if 5-class accuracy holds "
            "(or rises), thinking was giving negative value at this scale; if it drops materially, CoT "
            "was providing real lift."
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
            observations="(placeholder — refined in _refresh_nothink_reports.py once metrics are known)",
            backend_hint="tinker",
            extra_config={"concurrency": 32},
        )
        print(f"wrote {run_dir}")


if __name__ == "__main__":
    main()
