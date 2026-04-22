"""Second pass: refresh report.md for the 3 reasoning-disabled runs with
observations derived from the now-known metrics. Does NOT re-run eval.
"""
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


RUNS = [
    {
        "dir": "runs/20260421-0002-qwen35-4b-nothink-benchmark-full",
        "model": "Qwen/Qwen3.5-4B",
        "slug": "qwen35-4b-nothink-benchmark-full",
        "original_jsonl": "results/benchmark_qwen35_4b_nothink.jsonl",
        "run_timestamp": "20260421-0002",
        "baseline": "runs/20260420-1920-qwen35-4b-benchmark-full",
        "hypothesis": (
            "Disable reasoning for Qwen3.5-4B on the full 1500-row benchmark. The thinking-enabled "
            "run collapsed at parse 22.27 % / truncated 77.47 % because the 4B model spiraled and "
            "rarely emitted JSON before the 20 000-token cap. Disabling thinking (direct-answer "
            "renderer) should push parse rate way up and truncation near zero; the open question is "
            "whether the stripped-down model is still coherent enough to produce useful labels."
        ),
        "comparison": (
            "Compared to runs/20260420-1920-qwen35-4b-benchmark-full (same model + prompts + data; "
            "only difference: Qwen3_5Renderer there vs Qwen3_5DisableThinkingRenderer here)."
        ),
        "observations": """
- **Hypothesis matched strongly on the mechanism; 5-class accuracy has to be read carefully.** Parse rate jumped **22.27 % -> 91.13 % (+68.86 pt)** and truncation fell **77.47 % -> 0.33 % (-77.14 pt)**. Raw "reported" 5-class accuracy (computed over the parseable subset) actually *fell* from 37.78 % to **24.49 %**, but that is misleading because the parseable subset grew 4x (334 -> 1367 rows). The honest metric is the **absolute 5-class accuracy over all 1500 rows: 8.41 % -> 22.32 % (+13.91 pt)**. Disabling thinking is a clear net win at this model scale — many more rows now have any answer at all, and a higher absolute count of them are correct.
- **Class collapse swapped rather than disappeared.** Thinking-4B collapsed into VS (98.25 % VS accuracy, AGN/asteroid/bogus all < 15 %). Nothink-4B still collapses into VS (86.76 %) but SN accuracy recovers from **5 % -> 27.5 %** (the thinking run couldn't finish enough SN rows to ever get them right). AGN is still **0.0 %** — 4B simply cannot tell AGN from variable stars regardless of renderer. Asteroid accuracy drops (14.81 % -> 4.75 %) and bogus is ~flat (2.56 % -> 3.61 %).
- **Token economy is transformed.** Output tokens: median **20 000 -> 567** (~35x reduction), mean 16 622 -> 583. Per-row compute cost is now ~1/30 of thinking-enabled. Truncation essentially gone (5/1500 rows).
- **Error mix flipped.** In thinking mode the dominant error was `FORMAT_TRUNCATED_NO_JSON` (1153/1500, 77 %). In nothink the dominant error is plain `FORMAT_PARSE_FAILED` (128/1500, 8.5 %) — the 4B model writes JSON but occasionally mangles it. Value errors are small (36/1500), mostly `c2_astro_requires_subtype` (27) — the old "stage-2 said astrophysical but forgot to pick a stage-3" bug.
- **Stage-1 (real vs artifact) only slightly degrades** (87.07 -> 79.30 %) and stage-3 conditional (45.60 -> 38.67 %) is broadly comparable — confirming the 4B model's intrinsic visual reasoning is intact, what was missing before was just the ability to finish a response.
- **Practical takeaway:** For a 4B-scale model, thinking is net-negative at this token budget. Without CoT the model is a usable (if VS-biased) classifier at 30x lower compute cost. With CoT it is effectively broken. Future open-source sweeps at this scale should default to `--thinking disabled` unless explicitly studying CoT behaviour.
""".strip(),
    },
    {
        "dir": "runs/20260421-0019-qwen35-35b-a3b-nothink-benchmark-full",
        "model": "Qwen/Qwen3.5-35B-A3B",
        "slug": "qwen35-35b-a3b-nothink-benchmark-full",
        "original_jsonl": "results/benchmark_qwen35_35b_a3b_nothink.jsonl",
        "run_timestamp": "20260421-0019",
        "baseline": "runs/20260420-2054-qwen35-35b-a3b-benchmark-full",
        "hypothesis": (
            "Disable reasoning for Qwen3.5-35B-A3B on the full 1500-row benchmark. The thinking-enabled "
            "run hit parse 65.47 % / truncated 31.0 %, with most failures being token-budget spirals. "
            "Direct-answer should dramatically cut truncation. Expect parse rate ~100 % and a fair "
            "comparison of this MoE model's intrinsic visual classification skill without CoT scaffolding."
        ),
        "comparison": (
            "Compared to runs/20260420-2054-qwen35-35b-a3b-benchmark-full (same model + prompts + data; "
            "only difference: Qwen3_5Renderer there vs Qwen3_5DisableThinkingRenderer here)."
        ),
        "observations": """
- **Most striking result of the sweep: absolute 5-class accuracy is essentially unchanged (26.73 % -> 25.50 %, delta -1.23 pt).** Thinking lifted per-row accuracy on the parseable subset (40.83 % vs nothink's 25.76 %) but wasted 31 % of rows to truncation; disabling thinking recovered those rows (parse 65.47 % -> **99.00 %**, trunc 31.00 % -> **0.33 %**) but at lower per-row accuracy. Net: the two renderers land on the **same absolute number of correct rows**.
- **But the two modes are doing different things.** Per-class accuracy reveals the trade-off clearly:
  - **VS:** 72.60 % -> **96.61 %** (+24) — without thinking the model defaults to "variable_star" much more aggressively.
  - **asteroid:** 55.61 % -> **8.22 %** (-47) — huge collapse. Thinking was where the model actually picked up asteroid cues (short track, no host).
  - **bogus:** 50.74 % -> **2.68 %** (-48) — similar collapse. Bogus detection apparently requires explicit reasoning about artifact hallmarks.
  - **SN:** 13.86 % -> 17.14 % (+3), **AGN:** 1.62 % -> 0.68 % (-1). Both very weak either way.
- **Interpretation:** thinking is *discriminative* (identifies asteroid / bogus correctly, at the cost of truncating many rows to zero). Nothink is *cheap and uniform* (collapses to VS on almost everything astrophysical-looking, but finishes every row). In absolute terms the two approaches are a wash at 25 %.
- **Token economy:** output_tokens mean **11 822 -> 539** (~22x reduction), median 9 679 -> 528. MoE active params + no CoT = very cheap inference.
- **Error mix:** nothink is almost entirely clean (`parse_failed` 10/1500, `truncated_partial_json` 5/1500). Value errors top out at `c2_astro_requires_subtype` (50) — still the most common schema slip for this family.
- **Stage-1 real vs artifact is slightly *better* without thinking** (77.15 % -> 80.40 %) — the direct-answer renderer doesn't let the model talk itself out of calling things artifacts.
- **Practical takeaway:** Qwen3.5-35B-A3B with thinking is roughly equal in correct-row count but qualitatively different — it's the only setting where the model reliably flags asteroid/bogus. If downstream pipeline values non-astrophysical detection (most do — rejecting artifacts is core to real-time triage), keep thinking on. If the goal is fast bulk labelling of astrophysical sources, nothink is 22x cheaper with comparable SN/VS/AGN numbers.
""".strip(),
    },
    {
        "dir": "runs/20260421-0025-qwen35-397b-a17b-nothink-benchmark-full",
        "model": "Qwen/Qwen3.5-397B-A17B",
        "slug": "qwen35-397b-a17b-nothink-benchmark-full",
        "original_jsonl": "results/benchmark_qwen35_397b_a17b_nothink.jsonl",
        "run_timestamp": "20260421-0025",
        "baseline": "runs/20260420-1554-qwen35-397b-a17b-benchmark-full",
        "hypothesis": (
            "Disable reasoning for Qwen3.5-397B-A17B on the full 1500-row benchmark. The thinking-enabled "
            "run already reached 100 % parse / 0 % truncation at 44.27 % 5-class accuracy, with ~91 % "
            "of tokens spent on reasoning. Direct-answer removes that cost: if 5-class accuracy holds "
            "(or rises), thinking was giving negative value at this scale; if it drops materially, CoT "
            "was providing real lift."
        ),
        "comparison": (
            "Compared to runs/20260420-1554-qwen35-397b-a17b-benchmark-full (same model + prompts + data; "
            "only difference: Qwen3_5Renderer there vs Qwen3_5DisableThinkingRenderer here)."
        ),
        "observations": """
- **Hypothesis resolved: thinking was providing real net lift at this scale**, though not for the reasons expected. Absolute 5-class accuracy dropped **44.27 % -> 34.98 % (-9.29 pt)** without reasoning. Parse rate stayed ~100 % (100.00 -> 99.87 %) and truncation near-zero (0.00 -> 0.07 %), so this is a clean apples-to-apples comparison: the drop is entirely classification quality, not format failure.
- **But the per-class story is surprising — thinking was *hurting* SN.** Without thinking, SN accuracy *jumps* **18.00 % -> 56.67 % (+38.67 pt)**. The SN -> AGN collapse documented in the thinking baseline (141/300 SN predicted as AGN) almost entirely disappears: stage-3 conditional accuracy rises 32.44 % -> **45.61 %** and stage-3 macro F1 rises 0.310 -> **0.429**. The large reasoning chain at 397B was talking the model into calling supernovae AGN; direct-answer mode restores the correct default.
- **Thinking's real value was on non-astrophysical classes.** The loss vs thinking is concentrated in:
  - **asteroid:** 80.67 % -> **17.00 %** (-64) — massive regression. Thinking was where the model identified asteroid trajectory/cadence cues.
  - **bogus:** 43.33 % -> 21.07 % (-22).
  - **AGN:** 6.00 % -> 3.01 % (-3, unchanged-bad).
  - VS: 73.33 % -> 77.00 % (+4, small gain).
  So the 9-point 5-class drop is the net of +38 on SN vs -64 on asteroid vs -22 on bogus, and small effects elsewhere.
- **Token economy:** output_tokens mean **5 171 -> 554** (~9x reduction); the thinking run's answer_tokens were already tiny (455), so the removed cost is overwhelmingly thinking tokens. Runtime dropped from **~20 239 s -> 2 647 s (~7.6x faster)** at the same concurrency 32.
- **MSRS slightly *higher* without thinking** (4.744 -> 4.783) and calibration stays uninformative as in the thinking run. Self-score remains a useless confidence signal.
- **Part A (metadata reading) 100 % in both modes.** The model has no trouble parsing the inputs; the question is purely about how it decides between classes.
- **Practical takeaway:** The right setup at this scale is probably a two-pass hybrid — use nothink for SN-vs-AGN disambiguation and use thinking for the asteroid/bogus detection pass. A simpler alternative is a prompt-level intervention: add explicit "supernovae are NOT AGN unless the host shows a clear active nucleus" language to the thinking-mode prompt, which was the failure mode on runs/20260420-1554-qwen35-397b-a17b-benchmark-full. Running a dedicated SN-vs-AGN stage-3 prompt variant is the cheapest next experiment.
""".strip(),
    },
]


def _refresh_one(run: dict) -> None:
    run_dir = PROJECT_ROOT / run["dir"]
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    rows = _load_jsonl(run_dir / "run.jsonl")
    cfg = _extract_config_from_rows(rows, run["model"], "prompts", "tinker")
    cfg["concurrency"] = 32

    git = _git_info()
    meta = {
        "run_folder": run_dir.name,
        "run_timestamp": run["run_timestamp"],
        "slug": run["slug"],
        "status": "complete",
        "operator": "user",
        "commit": git["commit"],
        "dirty": git["dirty"],
        "dirty_files": git["dirty_files"],
        "manifest_path": "data/manifest_benchmark_final.csv",
        "n_records": len(rows),
        "class_distribution": dict(Counter(r.get("target_class", "?") for r in rows)),
        "model_label": run["model"],
        "original_jsonl": run["original_jsonl"],
    }

    plot_names = sorted(p.name for p in (run_dir / "plots").glob("*.png"))
    viz_counts = {
        cls: len(list((run_dir / "viz" / cls).glob("*.html")))
        for cls in ("SN", "AGN", "VS", "asteroid", "bogus")
    }

    write_enriched_report(
        out_path=run_dir / "report.md",
        meta=meta,
        config=cfg,
        metrics=metrics,
        plot_names=plot_names,
        viz_counts=viz_counts,
        hypothesis=run["hypothesis"],
        comparison=run["comparison"],
        observations=run["observations"],
    )
    print(f"report refreshed: {run_dir}")


def main() -> None:
    for r in RUNS:
        _refresh_one(r)
    regenerate_index(PROJECT_ROOT / "runs")
    regenerate_jsonl_index(PROJECT_ROOT / "runs")
    print("index + jsonl index regenerated")


if __name__ == "__main__":
    main()
