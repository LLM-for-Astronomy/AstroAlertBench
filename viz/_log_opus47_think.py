"""One-shot driver to log the Opus 4.7 adaptive-thinking benchmark-full run."""
from __future__ import annotations

from viz.build_run_folder import build_run_folder

HYPOTHESIS = (
    "First full-benchmark evaluation of Claude Opus 4.7 with adaptive thinking "
    "('high' effort). Expect near-100% parse rate and 5-class accuracy competitive "
    "with GPT-5.4 high (the prior closed-source SOTA on this benchmark). Adaptive "
    "thinking should spend thinking tokens proportional to problem difficulty, "
    "unlike GPT-5's fixed-effort knob."
)

COMPARISON = (
    "Benchmarked on the same 1500-row manifest (data/manifest_benchmark_final.csv) "
    "previously used by GPT-5.4 high/none (runs/20260421-2024-gpt-5.4-high-*, "
    "runs/20260421-2032-gpt-5.4-none-*) and the open-source Qwen/Kimi nothink sweep "
    "(runs/20260421-00*). First Anthropic-backend entry in the runs/ registry."
)

OBSERVATIONS_PLACEHOLDER = (
    "Observations: see metrics.json for the full breakdown (will be refreshed "
    "with a metric-driven narrative after the folder is built)."
)


def main() -> None:
    run_dir = build_run_folder(
        jsonl_path="results/benchmark_opus47_think.jsonl",
        manifest_path="data/manifest_benchmark_final.csv",
        model_name="claude-opus-4-7",
        prompts_module="prompts",
        slug_override="opus47-think-benchmark-full",
        hypothesis=HYPOTHESIS,
        comparison=COMPARISON,
        observations=OBSERVATIONS_PLACEHOLDER,
        backend_hint="anthropic",
    )
    print(f"run folder written to: {run_dir}")


if __name__ == "__main__":
    main()
