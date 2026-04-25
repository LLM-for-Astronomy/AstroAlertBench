"""Refresh the Observations section of the relogged Opus 4.7 nothink run.

Run AFTER `_log_opus47_nothink_only.py` so the run.jsonl + metrics.json
already exist. Replaces the placeholder Observations block in report.md
with a metric-driven narrative for the full 1500/1500 run.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RUN_DIR = PROJECT_ROOT / "runs" / "20260424-2324-opus47-nothink-benchmark-full"
REPORT = RUN_DIR / "report.md"

OBS = """Full benchmark numbers (n=1500, 0 errors, 0 truncations) — the run is
now complete after retry_failed.py picked up the 621 rows that the
original sweep had to skip when it hit Anthropic's 30 k input-tokens-
per-minute cap.

Headline numbers:

- **Part C 5-class accuracy: 48.87 %** (1500/1500 evaluable). For
  comparison the same model with adaptive thinking enabled (Opus 4.7
  think, runs/20260423-0942-opus47-think-benchmark-full) scored
  **60.60 %**, so disabling thinking costs Opus ~12 pp of headline
  accuracy.
- **MSRS 3.99** with a 67.07 % self-pass rate. Self-grading per dim is
  key_evidence 4.22 / leading 4.03 / alternative 3.72 — exactly the
  same shape as Opus think but with the alternative-analysis dim
  noticeably weaker (Opus think had ~3.95 there).
- **Calibration gap 0.189** (correct conf 4.09 vs incorrect 3.90),
  **Pearson r 0.252**. Both are dramatically *better* than Opus think's
  gap of 0.035 / r of 0.047. With thinking off, Opus's confidence
  becomes a real triage signal.
- **High-vs-low confidence accuracy bin:** n_high=1006 → 53.48 %,
  n_low=494 → 39.47 %. **Δ = +14.01 pp** on a balanced split, vs
  Opus think's +0.24 pp on a similar 1002/498 split. Same model,
  same prompts, same data — adaptive thinking turns the dial off.
- **Tokens:** mean 652 output, max 818, no reasoning tokens. About
  3.6× cheaper per row than Opus think (which averages ~2.4 k output
  tokens including the adaptive thinking budget).

Per-class breakdown (5-class) tells the same story we saw on the partial
slice plus the asteroid + AGN twist that was previously hidden:

| class | acc | notes |
|---|---:|---|
| VS       | 95.67 % | best class — Opus's first-pass visual reasoning recognises long-baseline variability easily |
| SN       | 79.67 % | strong; 45/300 leak to AGN (similar dropout as Opus think) |
| bogus    | 59.67 % | mid-tier; mostly correctly flagged as artifact-like |
| AGN      | **6.00 %** | catastrophic — 278/300 AGN are predicted as VS (stage3 confusion); the model treats nucleus-located variability as a star, not as AGN |
| asteroid | **3.33 %** | catastrophic — only 10/300 correct, the rest swept into bogus, matching the same pattern Opus think shows |

The AGN→VS confusion (92.7 % of AGN rows) is the single biggest source
of headline-accuracy loss vs Opus think. With thinking on, Opus
recovers most AGN by reasoning about the host-galaxy / nucleus
geometry; without it, the model defaults to "long-history variability
in the same spot = variable star". This is exactly the kind of stage-3
distinction the adaptive thinking budget is being spent on.

Comparison summary (Opus 4.7 think vs nothink, same model, same data):

| metric | think | nothink | Δ |
|---|---:|---:|---|
| 5-class accuracy | 60.60 % | 48.87 % | -11.73 pp |
| MSRS | 4.06 | 3.99 | -0.07 |
| calibration gap | 0.035 | 0.189 | +0.154 |
| Pearson r | 0.047 | 0.252 | +0.205 |
| acc(high) − acc(low), thresh=4 | +0.24 pp | +14.01 pp | +13.77 pp |
| avg output tokens | ~2.4 k | 0.65 k | -73 % |

Headline reading: adaptive thinking buys Opus ~12 pp of 5-class
accuracy at the cost of ~all of its confidence informativeness and
3-4× the cost per row. If you only need to triage / batch alerts the
nothink run is actually the more useful product despite scoring lower
on the 5-class metric. If you need ceiling accuracy on AGN
specifically, you must keep thinking on.
"""


def main() -> None:
    txt = REPORT.read_text(encoding="utf-8")
    pattern = re.compile(r"(## Observations\s*\n)(.*?)(?=\n## |\Z)", re.DOTALL)
    if not pattern.search(txt):
        print("!! could not find Observations section in", REPORT)
        sys.exit(1)
    new_txt = pattern.sub(lambda m: m.group(1) + "\n" + OBS + "\n", txt)
    REPORT.write_text(new_txt, encoding="utf-8")
    print(f"refreshed Observations in {REPORT}")


if __name__ == "__main__":
    main()
