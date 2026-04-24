"""One-shot driver to log three new closed-source benchmark-full runs:

  1. Gemini 2.5 Pro, dynamic thinking (reasoning_effort=high)
     -> results/benchmark_gemini25_pro_high.jsonl  [PARTIAL — see notes]
  2. Gemini 2.5 Flash, thinking disabled (reasoning_effort=none)
     -> results/benchmark_gemini25_flash_none.jsonl
  3. Claude Opus 4.7, thinking disabled (reasoning_effort=none)
     -> results/benchmark_opus47_nothink.jsonl     [some rows still failing]

Notes:
  - Gemini 2.5 Pro hit a daily/per-minute quota and was stopped mid-run; the
    JSONL contains ~1002 successful + ~48 failed rows, with ~450 manifest OIDs
    never attempted. Logged anyway so we have a placeholder folder, but the
    metrics are computed only over the ~1002 ok rows. Will be re-logged after
    `python retry_failed.py ... --backend google --model gemini-2.5-pro`
    finishes the missing/failed rows.
  - Opus 4.7 nothink has a small number of fails (rate-limit / transient); the
    folder will be re-logged once retry_failed.py mops them up.
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
        "jsonl": "results/benchmark_gemini25_pro_high.jsonl",
        "model": "gemini-2.5-pro",
        "slug": "gemini25-pro-high-benchmark-full",
        "backend": "google",
        "concurrency": "8 init (stopped on quota; partial 1050/1500)",
        "hypothesis": (
            "First Google-backend entry on the full 1500-row benchmark. "
            "Gemini 2.5 Pro with dynamic thinking_budget=-1 ('high' effort) is "
            "Google's flagship reasoning model in the 2.5 family; expected to "
            "land between GPT-5.4 high (closed-source ceiling so far) and Kimi "
            "K2.5 (open-source ceiling). Of particular interest: how Gemini's "
            "ALERCE-trained image priors (the model has likely seen ZTF "
            "stamps in training data via Web crawl) translate to first-alert "
            "classification accuracy, especially for the SN vs AGN axis where "
            "GPT-5.4 collapsed."
        ),
        "comparison": (
            "Compared to GPT-5.4 high "
            "(runs/20260421-2024-gpt-5.4-high-benchmark-full), Claude Opus 4.7 "
            "adaptive thinking (runs/20260423-0942-opus47-think-benchmark-full), "
            "and the open-source Kimi K2.5 / Qwen3.5 sweeps "
            "(runs/20260420-1226-kimi-k25-benchmark-full and the Apr-21 "
            "thinking/no-thinking grid)."
        ),
        "observations": (
            "(placeholder — partial run, full metrics require resuming with "
            "retry_failed.py once the per-day quota refreshes; a follow-up "
            "log pass will refresh this section with a metric-driven "
            "narrative.)"
        ),
        "reasoning_effort": "high",
    },
    {
        "jsonl": "results/benchmark_gemini25_flash_none.jsonl",
        "model": "gemini-2.5-flash",
        "slug": "gemini25-flash-none-benchmark-full",
        "backend": "google",
        "concurrency": "8",
        "hypothesis": (
            "Cheap-and-fast non-reasoning Google baseline: Gemini 2.5 Flash "
            "with thinking_budget=0 (reasoning_effort='none'), the only way "
            "to fully disable thinking on the 2.5 family. Tests two things: "
            "(a) how a non-reasoning Flash variant compares to non-reasoning "
            "GPT-5.4 ('none') and Claude Opus 4.7 ('none'), i.e. is "
            "Google's small-model image grounding strong enough without CoT? "
            "and (b) whether the fall-off from Pro-high -> Flash-none is "
            "dominated by the missing reasoning step or by the smaller model "
            "capacity itself."
        ),
        "comparison": (
            "Same 1500-row benchmark as the other closed-source runs. Direct "
            "A/B vs gemini-2.5-pro high (this same script); also compared "
            "to gpt-5.4 none "
            "(runs/20260421-2032-gpt-5.4-none-benchmark-full) and Claude Opus "
            "4.7 nothink (this script) to triangulate non-reasoning behaviour "
            "across all three closed-source vendors."
        ),
        "observations": (
            "(placeholder — refreshed in a second pass once metrics are known.)"
        ),
        "reasoning_effort": "none",
    },
    {
        "jsonl": "results/benchmark_opus47_nothink.jsonl",
        "model": "claude-opus-4-7",
        "slug": "opus47-nothink-benchmark-full",
        "backend": "anthropic",
        "concurrency": "2 (rate-limit-bound; SDK retry on 429/5xx)",
        "hypothesis": (
            "Direct A/B counterpart to the already-logged Opus 4.7 adaptive-"
            "thinking run (runs/20260423-0942-opus47-think-benchmark-full). "
            "Same model, same 1500 rows, only thinking is disabled "
            "(thinking.type='disabled'). Tests whether Opus 4.7's strong "
            "first-pass visual judgement is enough on its own, or whether "
            "the adaptive thinking budget is doing meaningful work."
        ),
        "comparison": (
            "A/B vs runs/20260423-0942-opus47-think-benchmark-full "
            "(same model + manifest, only thinking flag changed). Also "
            "compared to gpt-5.4 none "
            "(runs/20260421-2032-gpt-5.4-none-benchmark-full) as a "
            "non-reasoning closed-source ceiling check, and gemini-2.5-flash "
            "none (this script) for a third non-reasoning vendor data point."
        ),
        "observations": (
            "(placeholder — a small number of rows still failed with rate-"
            "limit / transient errors; this folder will be re-logged after "
            "retry_failed.py mops them up so the metrics reflect a clean "
            "1500/1500 run.)"
        ),
        "reasoning_effort": "none",
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
            comparison=r["comparison"],
            observations=r["observations"],
            backend_hint=r["backend"],
            extra_config={
                "concurrency": r["concurrency"],
                "reasoning_effort": r["reasoning_effort"],
            },
        )
        print(f"wrote {run_dir}")


if __name__ == "__main__":
    main()
