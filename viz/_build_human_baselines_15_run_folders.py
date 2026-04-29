"""Build `runs/<ts>-<slug>/` for all human-baselines-15 JSONLs via `build_run_folder`.

Usage:
    python -m viz._build_human_baselines_15_run_folders
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from viz.build_run_folder import build_run_folder  # noqa: E402

RESULTS = PROJECT_ROOT / "results"
MANIFEST = PROJECT_ROOT / "data" / "manifest_human_baselines_15.csv"

# Same model grid / ordering as `results_comparison/report/20260421_report_benchmark_full_all_runs.md`.
# Slugs mirror full-benchmark folders but end with `-human-baselines-15` instead of `-benchmark-full`.
RUNS: list[dict] = [
    {
        "jsonl_stem": "human_baselines_15_opus47_think",
        "slug": "opus47-think-human-baselines-15",
        "model": "claude-opus-4-7",
        "backend_hint": "anthropic",
    },
    {
        "jsonl_stem": "human_baselines_15_gpt54_high",
        "slug": "gpt-5.4-high-human-baselines-15",
        "model": "gpt-5.4",
        "backend_hint": "openai",
    },
    {
        "jsonl_stem": "human_baselines_15_kimi_k25",
        "slug": "kimi-k25-human-baselines-15",
        "model": "moonshotai/Kimi-K2.5",
        "backend_hint": "tinker",
    },
    {
        "jsonl_stem": "human_baselines_15_opus47_nothink",
        "slug": "opus47-nothink-human-baselines-15",
        "model": "claude-opus-4-7",
        "backend_hint": "anthropic",
    },
    {
        "jsonl_stem": "human_baselines_15_qwen35_397b_think",
        "slug": "qwen35-397b-a17b-human-baselines-15",
        "model": "Qwen/Qwen3.5-397B-A17B",
        "backend_hint": "tinker",
    },
    {
        "jsonl_stem": "human_baselines_15_gpt54_none",
        "slug": "gpt-5.4-none-human-baselines-15",
        "model": "gpt-5.4",
        "backend_hint": "openai",
    },
    {
        "jsonl_stem": "human_baselines_15_gemini25_pro_high",
        "slug": "gemini25-pro-high-human-baselines-15",
        "model": "gemini-2.5-pro",
        "backend_hint": "google",
    },
    {
        "jsonl_stem": "human_baselines_15_gemini25_flash_none",
        "slug": "gemini25-flash-none-human-baselines-15",
        "model": "gemini-2.5-flash",
        "backend_hint": "google",
    },
    {
        "jsonl_stem": "human_baselines_15_qwen35_397b_nothink",
        "slug": "qwen35-397b-a17b-nothink-human-baselines-15",
        "model": "Qwen/Qwen3.5-397B-A17B",
        "backend_hint": "tinker",
    },
    {
        "jsonl_stem": "human_baselines_15_qwen35_35b_think",
        "slug": "qwen35-35b-a3b-human-baselines-15",
        "model": "Qwen/Qwen3.5-35B-A3B",
        "backend_hint": "tinker",
    },
    {
        "jsonl_stem": "human_baselines_15_qwen35_35b_nothink",
        "slug": "qwen35-35b-a3b-nothink-human-baselines-15",
        "model": "Qwen/Qwen3.5-35B-A3B",
        "backend_hint": "tinker",
    },
    {
        "jsonl_stem": "human_baselines_15_qwen35_4b_nothink",
        "slug": "qwen35-4b-nothink-human-baselines-15",
        "model": "Qwen/Qwen3.5-4B",
        "backend_hint": "tinker",
    },
    {
        "jsonl_stem": "human_baselines_15_qwen35_4b_think",
        "slug": "qwen35-4b-human-baselines-15",
        "model": "Qwen/Qwen3.5-4B",
        "backend_hint": "tinker",
    },
]


def main() -> None:
    shared_hyp = (
        "VLM sweep on **`data/manifest_human_baselines_15.csv`** (15 human-baseline cutouts; "
        "same `prompts` + montage pipeline as the 1500-row benchmark)."
    )
    shared_comp = (
        "Parallel to the matching **`*-benchmark-full`** run under `runs/` "
        "(same model family / reasoning mode; different manifest only)."
    )
    shared_obs = (
        "Small **n=15** — headline accuracies are noisy; use for qualitative comparison to humans "
        "and for per-OID HTML review under `viz/`."
    )

    for spec in RUNS:
        jp = RESULTS / f"{spec['jsonl_stem']}.jsonl"
        if not jp.exists():
            raise SystemExit(f"missing predictions: {jp}")
        run_dir = build_run_folder(
            jsonl_path=jp,
            manifest_path=MANIFEST,
            model_name=spec["model"],
            prompts_module="prompts",
            runs_root=PROJECT_ROOT / "runs",
            run_timestamp=None,
            slug_override=spec["slug"],
            hypothesis=shared_hyp,
            comparison=shared_comp,
            observations=shared_obs,
            backend_hint=spec["backend_hint"],
            keep_original_jsonl=True,
        )
        print(run_dir)


if __name__ == "__main__":
    main()
