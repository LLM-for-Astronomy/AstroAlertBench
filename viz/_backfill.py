"""One-shot backfill script: convert the existing 6 flat runs into `runs/` folders.

Run once:
    python -m viz._backfill
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from viz.build_run_folder import build_run_folder  # noqa: E402


def _section(md: str, header: str) -> str | None:
    """Extract the body under a '## Header' from a markdown file (until the next ## header)."""
    pat = rf"(?ms)^##\s+{re.escape(header)}\s*\n(.+?)(?=\n##\s|\Z)"
    m = re.search(pat, md)
    return m.group(1).strip() if m else None


# slug → (jsonl, manifest, model, exp_md_filename, prompts_module, backend, slug_override, timestamp_override)
BACKFILLS: list[dict] = [
    {
        "jsonl": "results/fewshot_qwen35_newparser.jsonl",
        "manifest": "data/manifest_fewshot.csv",
        "model": "Qwen/Qwen3.5-35B-A3B",
        "exp_md": "experiments/EXP-20260419-qwen35-baseline-newparser.md",
        "prompts_module": "prompts",
        "backend": "tinker",
        "slug": "qwen35-35b-a3b-baseline",
    },
    {
        "jsonl": "results/fewshot_qwen35_tokenlimit.jsonl",
        "manifest": "data/manifest_fewshot.csv",
        "model": "Qwen/Qwen3.5-35B-A3B",
        "exp_md": "experiments/EXP-20260419-qwen35-tokenlimit.md",
        "prompts_module": "prompts_token_limit_instruction",
        "backend": "tinker",
        "slug": "qwen35-35b-a3b-tokenlimit",
    },
    {
        "jsonl": "results/fewshot_qwen35_397b_newparser.jsonl",
        "manifest": "data/manifest_fewshot.csv",
        "model": "Qwen/Qwen3.5-397B-A17B",
        "exp_md": "experiments/EXP-20260419-qwen35-397b.md",
        "prompts_module": "prompts",
        "backend": "tinker",
        "slug": "qwen35-397b-a17b",
    },
    {
        "jsonl": "results/fewshot_qwen35_4b_newparser.jsonl",
        "manifest": "data/manifest_fewshot.csv",
        "model": "Qwen/Qwen3.5-4B",
        "exp_md": "experiments/EXP-20260419-qwen35-4b.md",
        "prompts_module": "prompts",
        "backend": "tinker",
        "slug": "qwen35-4b",
    },
    {
        "jsonl": "results/fewshot20_gpt54_high.jsonl",
        "manifest": "data/manifest_fewshot_20.csv",
        "model": "gpt-5.4",
        "exp_md": "experiments/EXP-20260419-gpt54-high.md",
        "prompts_module": "prompts",
        "backend": "openai",
        "slug": "gpt-5.4-high",
    },
    {
        "jsonl": "results/fewshot20_gpt54_none.jsonl",
        "manifest": "data/manifest_fewshot_20.csv",
        "model": "gpt-5.4",
        "exp_md": "experiments/EXP-20260419-gpt54-none.md",
        "prompts_module": "prompts",
        "backend": "openai",
        "slug": "gpt-5.4-none",
    },
]


def main() -> None:
    for spec in BACKFILLS:
        exp_md_path = PROJECT_ROOT / spec["exp_md"]
        hypothesis = comparison = observations = None
        if exp_md_path.exists():
            md = exp_md_path.read_text(encoding="utf-8")
            hypothesis = _section(md, "Hypothesis")
            comparison = _section(md, "Baseline / Comparison")
            observations = _section(md, "Observations")

        jsonl_path = PROJECT_ROOT / spec["jsonl"]
        if not jsonl_path.exists():
            print(f"[skip] {spec['slug']}: jsonl missing → {jsonl_path}")
            continue

        print(f"[build] {spec['slug']} <- {spec['jsonl']}")
        extra_cfg = {}
        if spec["backend"] == "openai":
            extra_cfg["reasoning_effort"] = "high" if "high" in spec["slug"] else "none"
        run_dir = build_run_folder(
            jsonl_path=spec["jsonl"],
            manifest_path=spec["manifest"],
            model_name=spec["model"],
            prompts_module=spec["prompts_module"],
            slug_override=spec["slug"],
            hypothesis=hypothesis,
            comparison=comparison,
            observations=observations,
            backend_hint=spec["backend"],
            extra_config=extra_cfg,
        )
        print(f"   -> {run_dir}")


if __name__ == "__main__":
    main()
