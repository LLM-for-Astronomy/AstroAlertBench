"""One-shot: refresh report.md for the Qwen3.5-4B full-benchmark run
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

RUN_DIR = PROJECT_ROOT / "runs" / "20260420-1920-qwen35-4b-benchmark-full"

OBSERVATIONS = """
- **Qwen3.5-4B is below the capacity threshold for this task.** The fewshot-100 pattern reproduced almost identically at 15x data: parse **22.27 %** (vs fewshot 22 %), truncation **77.47 %** (vs 77 %). 1153 of 1500 rows produced `truncated_no_json` — the model spirals in reasoning and never emits JSON before hitting the 20 000-token cap. Median output tokens is literally **20 000** (the cap), meaning over half of rows maxed out.
- **The 5-class accuracy of 37.78 % is misleadingly high.** It's computed only on the 317 Part-C-evaluable rows (out of 1500). In absolute terms, only **~126 / 1500 rows (8.4 %) were classified correctly end-to-end** — roughly 6x worse than Kimi K2.5 on the same manifest.
- **The model is effectively a 'VS detector' on whatever it manages to emit.** Stage-3 confusion matrix: 36/40 SN -> VS, 94/95 AGN -> VS, 112/115 VS correctly -> VS. The `AGN` label is *never predicted* anywhere in the matrix (precision 0.0, recall 0.0, F1 0.0). The model appears to have collapsed into a single dominant prediction under reasoning budget pressure.
- **Per-class accuracy table is on a small biased sub-sample** (per_class_total sums to 315, not 1500). Only rows that survived truncation + parsing are counted. VS appears to score 98.25 %, but that's 112 correct out of 114 VS rows that parsed, which is itself 114 / 300 = 38 % of the VS class — the other 62 % were lost to truncation.
- **Part A is 100 %** on the 334 parseable rows. Even the tiny 4B model reads the metadata fields correctly when it gets a chance — the failure is entirely on the reasoning side.
- **Runtime is longer than Qwen3.5-397B-A17B** (22 638 s vs 20 239 s, ~15 s/row) despite a much smaller model, because most rows run all the way to the 20 000-token cap. Effectively paying full price for garbage output.
- **Self-calibration is maximally broken**: part_b_self_pass_rate = 1.0, MSRS 4.83 (highest in the sweep), calibration gap 0.007. On rows where only 8.4 % end up correct, the model self-rates 5/5. Confidence signal is worse than noise.
- **Sanity check (vs fewshot-100):** parse 22 % / trunc 77 % / 5-class raw 23.8 % back then -> parse 22 % / trunc 77 % / 5-class raw 37.8 % here. The raw 5-class went *up* only because the denominator (parseable rows) shifted toward the easy class (VS) — absolute correct-rate is essentially the same catastrophe.
- **Suggested next experiment:** If 4B is to be included at all, rerunning with `--prompts prompts_token_limit_instruction` is the only low-cost option (lifted 35B-A3B parse 72 % -> 66 %, so it may help or may not). A stronger anti-spiral prompt, aggressive `max_tokens` cut (e.g. 4000 — forces early output), or simply dropping 4B from the open-source sweep are all reasonable. The 4B is not in the same capability tier as 35B / 397B / Kimi for this task.
""".strip()


def main() -> None:
    metrics = json.loads((RUN_DIR / "metrics.json").read_text(encoding="utf-8"))
    rows = _load_jsonl(RUN_DIR / "run.jsonl")
    cfg = _extract_config_from_rows(rows, "Qwen/Qwen3.5-4B", "prompts", "tinker")
    cfg["concurrency"] = 32
    cfg["wallclock"] = "22638 s (~6h 17m)"

    git = _git_info()
    meta = {
        "run_folder": RUN_DIR.name,
        "run_timestamp": "20260420-1920",
        "slug": "qwen35-4b-benchmark-full",
        "status": "complete",
        "operator": "user",
        "commit": git["commit"],
        "dirty": git["dirty"],
        "dirty_files": git["dirty_files"],
        "manifest_path": "data/manifest_benchmark_final.csv",
        "n_records": len(rows),
        "class_distribution": dict(Counter(r.get("target_class", "?") for r in rows)),
        "model_label": "Qwen/Qwen3.5-4B",
        "original_jsonl": "results/benchmark_qwen35_4b.jsonl",
        "wallclock": "22638 s (~6h 17m)",
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
            "First full 1500-row benchmark for Qwen3.5-4B (hybrid thinking). "
            "The 100-row fewshot was weak (22 % parse, 77 % truncation, 23.8 % 5-class). "
            "Expect similar or worse at 15x data; this is the capacity-threshold test."
        ),
        comparison=(
            "Compared to runs/20260419-2230-qwen35-4b (same model + renderer + "
            "prompts.py + max_tokens=20000). Only manifest changed: fewshot-100 -> "
            "benchmark-final-1500 (top-300 ALERCE-prob per class, no oid overlap)."
        ),
        observations=OBSERVATIONS,
    )
    regenerate_index(PROJECT_ROOT / "runs")
    regenerate_jsonl_index(PROJECT_ROOT / "runs")
    print("report.md + index refreshed")


if __name__ == "__main__":
    main()
