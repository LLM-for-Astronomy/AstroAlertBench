"""Re-log only the gemini-2.5-pro full benchmark run (now complete 1500/1500).

Reads RUNS from `_log_gemini25_opus47` and runs build_run_folder only for the
gemini-2.5-pro entry. Used after retry_failed.py finishes the resumed run.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from viz.build_run_folder import build_run_folder
from viz._log_gemini25_opus47 import RUNS


def main() -> None:
    target = next(r for r in RUNS if r["model"] == "gemini-2.5-pro")
    print(f"=== relogging {target['slug']} ===")
    run_dir = build_run_folder(
        jsonl_path=target["jsonl"],
        manifest_path="data/manifest_benchmark_final.csv",
        model_name=target["model"],
        prompts_module="prompts",
        slug_override=target["slug"],
        hypothesis=target["hypothesis"],
        comparison=target["comparison"],
        observations=target["observations"],
        backend_hint=target["backend"],
        extra_config={
            "concurrency": target["concurrency"],
            "reasoning_effort": target["reasoning_effort"],
        },
    )
    print(f"wrote {run_dir}")


if __name__ == "__main__":
    main()
