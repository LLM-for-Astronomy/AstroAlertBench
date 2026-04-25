"""Replace the '## Observations' placeholder in the now-complete
gemini-2.5-pro full-benchmark run folder with a metric-driven narrative.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


GEMINI25_PRO_OBS = """\
## Observations

**Now complete: 1500/1500 parsed (0 errors).** The original Apr-23 run was
stopped at 1050/1500 on a Google daily quota; the missing 450 + 48 failed
rows were filled in by `python retry_failed.py --backend google --model
gemini-2.5-pro --reasoning-effort high --concurrency 4 --only both` on
Apr 24. All numbers below are over the full 1500-row manifest.

**Headline metrics (n=1500):**
- 5-class accuracy: **41.93 %** (parse rate 100 %, no truncation). Below the
  preliminary 47.11 % from the SN/AGN/VS-heavy partial slice — the previously
  unsampled asteroid (3/300) and the partially-sampled bogus (155/300)
  classes both pulled the headline down. Sits between Qwen3.5-397B think
  (44.27 %) and Qwen3.5-397B nothink (34.93 %) on the project leaderboard;
  noticeably behind Kimi K2.5 (49.34 %) and GPT-5.4 high (51.07 %).
- Stage-3 macro F1: **0.509** (best of any closed-source run except Kimi at
  0.500 — Gemini Pro slightly edges Kimi here despite trailing on the raw
  5-class number, because what it does *get right* it gets right with high
  precision).
- MSRS: **4.886 / 5** — second-highest of any logged run (only Qwen3.5-4B
  think's 4.83 is in the same neighbourhood, and that's on n=317 of a heavily
  truncated run). Part B narrative quality (key evidence 5.00 / leading
  interpretation 4.998 / alternative analysis 4.66) is essentially saturated.
- Calibration gap: **0.0098** — collapsed from the partial-slice 0.0371.
  Pearson r: **+0.030** (was +0.125 on the partial). Adding asteroid and
  bogus rows — most of which the model labelled with confidence ~5 *and got
  wrong* — completely flattened the confidence distribution between the
  correct and incorrect groups. The model now parks 100 % of predictions
  in the high-conf bin (n_high=1500, n_low=0), so confidence is essentially
  not a usable triage signal at all.
- Avg output tokens: **2 374** (~508 visible answer + ~1 866 hidden
  thinking). Roughly 12 % more visible-answer tokens than GPT-5.4 high
  (~446 visible) and 11 % less reasoning than GPT-5.4 high (2 111). Cost
  profile is a notch heavier than GPT-5.4 for slightly worse 5-class
  accuracy.

**Per-class breakdown (recall, n=300 per class):**
- SN: **80.00 %** (240/300) — the strongest SN recall of any run on the
  benchmark, beating GPT-5.4 high (38.67 %) by +41 pp and matching Opus
  4.7 think (84.00 %) within ~4 pp. SN classification is genuinely strong.
- VS: **70.67 %** (212/300) — middle-of-the-pack; well-behind GPT-5.4 high
  (95.33 %) and Opus think (91.00 %), partly because 88 VS are returning
  N/A as the predicted class (refusal / ambiguous), not because they're
  being misclassified.
- bogus: **51.67 %** (155/300) — better than GPT-5.4 high (38.33 %) and
  open-source Kimi K2.5 (11.04 %), but well behind Opus think (63.33 %).
- AGN: **6.33 %** (19/300) — collapses to VS: 272/300 AGN -> VS in the
  stage-3 confusion matrix. Same VS-collapse pattern as Gemini 2.5 Flash;
  the high reasoning budget did not fix it.
- asteroid: **1.00 %** (3/300) — essentially missing. Compare with Opus
  think (57.33 %), GPT-5.4 high (75.67 %), Kimi K2.5 (75.67 %), GPT-5.4
  none (81.00 %). Asteroid is the weakest class for this model by a wide
  margin and dominates the gap to the top of the leaderboard.

**Stage breakdown (parse-conditional):**
- Stage 1 (real object): **82.27 %** — well behind Opus think (~99 %) and
  GPT-5.4 (~98 %). Gemini Pro is rejecting ~18 % of the real objects.
- Stage 2 (astrophysical): **63.60 %** — middling.
- Stage 3 (fine-grained): **45.53 %** stage-conditional. The cascade leaks
  most heavily at Stage 1 -> Stage 2 (drops 18.67 pp) and Stage 2 -> 3
  (drops 18.07 pp).

**Headline ranking on this benchmark (absolute 5-class over n=1500):**
1. Claude Opus 4.7 think — 60.60 %
2. GPT-5.4 high — 51.07 %
3. Kimi K2.5 think (open-source) — 49.34 %
4. Qwen3.5-397B think — 44.27 %
5. GPT-5.4 none — 43.67 %
6. **Gemini 2.5 Pro high — 41.93 %**  ← *this run*
7. Gemini 2.5 Flash none — 36.27 %
... etc

**Implications and follow-ups:**
1. Gemini 2.5 Pro is *the strongest SN classifier* in the benchmark and one
   of the strongest Part-B narrators (MSRS 4.886), but its 5-class headline
   is dragged down by complete failure on asteroid (1 %) and the same
   AGN -> VS collapse seen on Gemini 2.5 Flash. It is *not* a competitive
   end-to-end classifier on this benchmark in its current configuration.
2. The asteroid collapse is unique to the Gemini family at this scale.
   Worth a focused experiment with class-specific prompt cues (e.g. "if
   the source moves between epochs, label asteroid") to see whether it's
   a prompt-format issue or a fundamental limitation of the model's
   stamp-level grounding.
3. Calibration *worsened* with the resumed rows — the model continues to
   emit confidence ~5 on basically every prediction, including the new
   asteroid + bogus rows it gets wrong. If a downstream pipeline needed
   a triage signal, Gemini 2.5 Pro's confidence dial is essentially
   useless on this benchmark; prefer GPT-5.4 (any mode) or Gemini 2.5
   Flash none for that role.
4. The calibration comparison report
   (`results_comparison/report/20260423_report_calibration_pearson.md`)
   has gemini-2.5-pro flagged with `*` as partial; it should be refreshed
   to reflect the now-complete numbers (gap 0.0098 / r +0.030 / acc 41.93%
   instead of 0.0371 / +0.125 / 31.47%).
"""


PATCH = (
    "runs/20260424-1809-gemini25-pro-high-benchmark-full/report.md",
    GEMINI25_PRO_OBS,
)


def main() -> None:
    rel_report, new_obs_block = PATCH
    report = PROJECT_ROOT / rel_report
    if not report.is_file():
        print(f"!! missing {report}; aborting")
        return
    text = report.read_text(encoding="utf-8")
    marker = "## Observations"
    idx = text.find(marker)
    if idx == -1:
        print(f"!! '## Observations' not found in {report}; aborting")
        return
    new_text = text[:idx] + new_obs_block.rstrip() + "\n"
    report.write_text(new_text, encoding="utf-8")
    print(f"updated Observations: {rel_report}")


if __name__ == "__main__":
    main()
