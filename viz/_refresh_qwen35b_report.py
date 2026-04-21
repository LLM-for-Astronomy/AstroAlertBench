"""One-shot: refresh report.md for the Qwen3.5-35B-A3B full-benchmark run
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

RUN_DIR = PROJECT_ROOT / "runs" / "20260420-2054-qwen35-35b-a3b-benchmark-full"

OBSERVATIONS = """
- **Hypothesis matched directionally but the model degraded slightly at scale.** Parse rate dropped from fewshot 72 % to **65.47 %** (982/1500); truncation rose from 25 % to **31.0 %** (465/1500). Like Qwen3.5-4B, this is a reasoning-budget problem that compounds at full benchmark size — more rows, more chances to spiral into the 20 000-token cap.
- **Reported 5-class 40.83 % is on the 967 Part-C-evaluable subset.** Absolute end-to-end correct = **392 / 1500 = 26.1 %**, computed from `per_class_correct` (3 + 23 + 159 + 104 + 103). Roughly half of Kimi's absolute accuracy (~49 %) on the same manifest. The 4 pt apparent uplift vs fewshot (33.8 % -> 40.8 %) is again a denominator effect — the parseable subset over-weights easy classes (VS, asteroid).
- **Per-class on the parseable subset (raw counts shown):**
  - VS 72.6 % (159/219), asteroid 55.6 % (104/187), bogus **50.7 %** (103/203), SN 13.9 % (23/166), AGN **1.6 %** (3/185).
  - bogus handling is similar to Qwen-397B (43 %) and far better than Kimi (11 %); SN and AGN both collapse.
- **Universal AGN -> VS confusion, again** (148/186 parseable AGN rows -> variable_star, only 3 correct). This is the consistent failure mode across every open-source reasoning model in this sweep.
- **Stage-3 conditional accuracy is 32.1 %** — identical (within noise) to Qwen-397B's 32.4 %, and far below Kimi's 53.5 %. Once the model gets the binary stages right, it still fails to pick the right astrophysical subclass 2/3 of the time.
- **Part A is 100 %** on the 982 parseable rows.
- **Token behaviour is bi-modal**: median output_tokens 9 679, mean 11 822, max 20 000, p95 20 000. Roughly a third of rows complete cleanly under 10 k tokens, a third spiral to ~15 k, and a third hit the cap and truncate. The gap between answer_tokens median (489) and mean (6 520) confirms the same — most successful answers are short (~500 tokens of JSON), but truncated rows pollute the mean because no clean thinking/answer split is emitted.
- **Self-calibration is broken**: MSRS 4.70, self-pass 99.9 %, calibration_gap 0.015, pearson_r 0.062. The model self-rates ~5/5 on rows where end-to-end accuracy is ~26 %.
- **Runtime is 38 543 s (~10h 42m) at concurrency 32**, the slowest in the open-source sweep. Roughly 5x Kimi K2.5 and 2x Qwen-397B for the same 1500 rows. The cause is the long-tail truncation: each truncated row pays the full 20 000-token sampling cost while contributing nothing to results.
- **Suggested next experiment:** the same truncation pattern that hurt Qwen3.5-4B is hurting this model too. Three options worth testing:
  1. `--prompts prompts_token_limit_instruction` (lifted parse 22 % -> 66 % on 4B-fewshot, neutral on 35B-fewshot — worth a 1500-row test).
  2. Cut `max_tokens` to ~12 000 (forces earlier termination; may shift truncated -> partial JSON which `evaluate.extract_json_object` can sometimes recover).
  3. Stage-3 SN/AGN guidance in the system prompt (would help the 967 parseable rows; orthogonal to the truncation fix).
""".strip()


def main() -> None:
    metrics = json.loads((RUN_DIR / "metrics.json").read_text(encoding="utf-8"))
    rows = _load_jsonl(RUN_DIR / "run.jsonl")
    cfg = _extract_config_from_rows(rows, "Qwen/Qwen3.5-35B-A3B", "prompts", "tinker")
    cfg["concurrency"] = 32
    cfg["wallclock"] = "38543 s (~10h 42m)"

    git = _git_info()
    meta = {
        "run_folder": RUN_DIR.name,
        "run_timestamp": "20260420-2054",
        "slug": "qwen35-35b-a3b-benchmark-full",
        "status": "complete",
        "operator": "user",
        "commit": git["commit"],
        "dirty": git["dirty"],
        "dirty_files": git["dirty_files"],
        "manifest_path": "data/manifest_benchmark_final.csv",
        "n_records": len(rows),
        "class_distribution": dict(Counter(r.get("target_class", "?") for r in rows)),
        "model_label": "Qwen/Qwen3.5-35B-A3B",
        "original_jsonl": "results/benchmark_qwen35_35b_a3b.jsonl",
        "wallclock": "38543 s (~10h 42m)",
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
            "First full 1500-row benchmark for Qwen3.5-35B-A3B (hybrid thinking). "
            "The 100-row fewshot baseline reached 33.8 % 5-class / 72 % parse / 25 % "
            "truncation. Expect similar at 15x data; this closes the open-source "
            "4-model sweep (4B / 35B-A3B / 397B-A17B / Kimi-K2.5)."
        ),
        comparison=(
            "Compared to runs/20260419-2047-qwen35-35b-a3b-baseline (same model + "
            "renderer + prompts.py + max_tokens=20000). Only manifest changed: "
            "fewshot-100 -> benchmark-final-1500 (top-300 ALERCE-prob per class, "
            "no oid overlap)."
        ),
        observations=OBSERVATIONS,
    )
    regenerate_index(PROJECT_ROOT / "runs")
    regenerate_jsonl_index(PROJECT_ROOT / "runs")
    print("report.md + index refreshed")


if __name__ == "__main__":
    main()
