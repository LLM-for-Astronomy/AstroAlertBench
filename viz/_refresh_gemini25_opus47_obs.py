"""Replace the '## Observations' placeholder in each newly logged run folder
with a metric-driven narrative.

Targets:
  - runs/20260423-2204-gemini25-pro-high-benchmark-full
  - runs/20260423-2110-gemini25-flash-none-benchmark-full
  - runs/20260423-1200-opus47-nothink-benchmark-full
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


GEMINI25_PRO_OBS = """\
## Observations

**Run is partial: 1050/1500 rows attempted (1002 ok + 48 quota fails) before the
Google daily/per-minute quota tripped.** The unfinished slice is concentrated
in `bogus` (0/300) and `asteroid` (102/300) because the runner walks the
manifest in the order `SN -> AGN -> VS -> asteroid -> bogus`. All numbers
below are computed over the parsed subset only and will shift once
`retry_failed.py --backend google --model gemini-2.5-pro` fills in the
missing rows.

**Headline metrics (parsed n=1002):**
- 5-class accuracy: **47.11%** (300 SN + 300 AGN + 300 VS + 102 asteroid; bogus N/A)
- MSRS: **4.91/5** — *highest of any closed-source or open-source run on this
  benchmark*. Part B narrative quality (key evidence + leading interpretation
  + alternative analysis) is essentially saturated (5.00 / 4.99 / 4.73).
- Calibration gap: **3.71%** — best of any closed-source run, on par with
  Kimi K2.5 (3.25%) and the Opus-think run (3.50%).
- Avg output tokens: **2334** (≈511 visible answer + ~1823 hidden thinking;
  the dynamic `thinking_budget=-1` settled around half of GPT-5.4 high's
  ~2111 reasoning tokens).
- Part C stage breakdown: real-object 89.5%, astrophysical 79.5%, fine-grained
  47.3% (parse-conditional). Stage-1 / stage-2 are ~5 pp ahead of GPT-5.4
  high; stage-3 is the bottleneck.

**The signature failure mode is *VS over-prediction*.** The stage-3 confusion
matrix (parsed subset) shows almost everything that isn't a textbook SN gets
labelled `variable_star`:
- AGN: **6.33%** (19/300). 272/300 AGN -> VS, 1 -> SN, 8 -> N/A.
- asteroid: **0.98%** (1/102). asteroid is missing from the stage-3 confusion
  matrix entirely because the parser routed every asteroid prediction
  through `variable_star` as well.
- VS: **70.67%** is high but inflated by the influx of mis-labelled AGN/asteroid.
- SN: **80.00%** — clean and stable, on par with Opus-think (84.00%).
- bogus: not yet sampled.

This is the *same* pattern as Gemini 2.5 Flash (this report sweep) and is
clearly a Gemini-family bias, not a thinking-budget artefact: the dynamic
thinking budget at 'high' didn't fix it. By contrast, Opus 4.7 think and
GPT-5.4 high spread their errors much more evenly across classes (and Opus
think actually nails asteroid + bogus, the two classes Gemini Pro is missing
or struggling with).

**Implications and follow-ups:**
1. Resume the run with `retry_failed.py --only both --concurrency 4` once
   quota refreshes, to fill in 450 missing + 48 failed rows. The bogus class
   in particular is fully unsampled so the headline number will move.
2. The VS-collapse is not a Flash-only quirk; expect it to persist on the
   completed run. A fairer Gemini-vs-rest comparison may need either
   class-rebalanced metrics or a temperature/effort sweep on the
   AGN-vs-VS axis.
3. Tokens-per-correct (cost-effectiveness) won't be meaningful until the
   missing classes are filled in, but the Part B narrative quality is so
   high (MSRS 4.91/5) that Gemini 2.5 Pro might be the strongest *Part B*
   performer in the benchmark even if Part C remains unbalanced.
"""


GEMINI25_FLASH_OBS = """\
## Observations

**Headline metrics (full 1500/1500 parsed):**
- 5-class accuracy: **36.27%** — the lowest closed-source run on the benchmark
  so far (vs GPT-5.4 none 43.67%, Opus-nothink 59.50% on its parsed slice,
  Gemini 2.5 Pro high 47.11% on its partial slice).
- MSRS: **4.36/5** — Part B narrative quality is competitive with GPT-5.4
  none (4.28) but well below the Pro variant (4.91).
- Calibration gap: **12.63%** — poor; the model is confidently wrong on a
  lot of AGN/asteroid examples (high-confidence accuracy 36.79% vs
  low-confidence 27.71%, with the bulk routed into the high-confidence bin).
- Avg output tokens: **635** with `thinking_budget=0` strictly enforced
  (n_reasoning_tokens=0 in every row). Cheapest per call of any run logged.
- Part C: real-object 83.5%, astrophysical 63.7%, fine-grained 37.8%
  (parse-conditional). Stage-1 is OK; the model fails to push beyond
  "something real" reliably.

**Failure mode is the same VS-collapse seen on Gemini 2.5 Pro:**
- AGN: **2.00%** (6/300). Stage-3 confusion: 292/300 AGN -> VS.
- asteroid: **0.33%** (1/300).
- bogus: **25.00%** (75/300) — the only class where Flash beats Pro on raw
  recall, and only because it's now treating bogus as a default fallback
  rather than VS.
- VS: **94.33%** (283/300) — inflated by the AGN flood.
- SN: **59.67%** — clean but well behind Pro-high (80.00%) and Opus-think
  (84.00%); SN -> VS slippage costs ~85 examples.

**Pro vs Flash-vs-none on the same family** (Pro PARTIAL, but already
informative for the SN/AGN/VS classes both runs cover): switching from
`thinking_budget=-1` (Pro, dynamic) to `thinking_budget=0` (Flash, off) drops
SN by ~20 pp, AGN by ~4 pp, leaves VS roughly flat. So most of the
intra-family gap is explained by raw model capacity (Pro vs Flash), not by
the missing reasoning step — the SN/AGN axis benefits much more from a
larger backbone than from a thinking budget.

**Closed-source non-reasoning shoot-out** (3-vendor, all `none`/disabled):
- Opus 4.7 nothink: **59.50%** (parsed slice, asteroid + bogus missing
  entirely from parsed subset)
- GPT-5.4 none: **43.67%**
- Gemini 2.5 Flash none: **36.27%**

Anthropic's small-model image grounding is the strongest of the three when
thinking is disabled, but the slice is biased; once Opus nothink is filled
in, the comparison may move. Calibration gap ranking is the same:
Flash (12.63%) > GPT-5.4 none (14.13%) > Opus nothink (9.20%) — the smaller
the model, the less self-aware it is when wrong.

**Implications:**
1. Gemini 2.5 Flash is not a viable swap-in for Pro on this benchmark — the
   VS-bias is amplified, not just preserved. Useful as a baseline data point
   but not as a deployment candidate.
2. The Gemini family appears to need either targeted prompting on AGN vs VS
   (light-curve specifics, host context) or a different prompt format to
   un-collapse the AGN/asteroid -> VS tendency. Worth trying on Pro before
   investing further.
3. Non-reasoning Flash is ~3.5× cheaper in output tokens than Pro-high
   (~635 vs ~2334) and ~1× the input. For pre-screening pipelines, the
   error pattern (90%+ VS recall, near-zero AGN/asteroid) means it could
   serve as a fast "is this VS or not" gate, not as a 5-class classifier.
"""


OPUS47_NOTHINK_OBS = """\
## Observations

**Run is incomplete: only 879/1500 rows have a parsed prediction (621 still
carry runtime errors from the Anthropic 30k-input-tokens-per-minute rate
limit / transient 5xx).** The user has flagged this — the folder will be
re-logged after `retry_failed.py --backend anthropic --model claude-opus-4-7
--reasoning-effort none` mops up the failed rows. Until then all metrics
below are computed over the parsed subset (300 SN + 300 AGN + 279 VS;
asteroid and bogus are entirely absent from the parsed slice — those classes
were the tail of the queue when the rate limit walls hit).

**Headline metrics (parsed n=879):**
- 5-class accuracy: **59.50%** on the SN/AGN/VS-only slice. Comparable to
  Opus-think (60.60%) on the same three classes (think: SN 84%, AGN 7.33%,
  VS 91.00% — combined ~60.8% on a SN+AGN+VS subset). With asteroid/bogus
  still to come, this number will drop unless those classes recover well on
  retry (Opus-think hit 57.33% asteroid, 63.33% bogus, so Opus-nothink may
  also do reasonably).
- MSRS: **4.16/5** — meaningful step down from Opus-think (3.99/5 actually,
  almost identical) and from GPT-5.4 none (4.28). Narrative quality is OK
  but the reasoning trace is gone.
- Calibration gap: **9.20%** — worse than Opus-think (3.50%) but better than
  GPT-5.4 none (14.13%).
- Avg output tokens: **648** (vs Opus-think's 805; the ~150 tokens saved
  per call is the cost of the disabled adaptive thinking).
- Part C stage breakdown: stage-1 97.16% and stage-2 97.16% are exceptionally
  high (Opus is *very* sure something real and astrophysical happened);
  stage-3 (fine-grained) collapses to 59.5%.

**Failure mode (parsed slice):**
- AGN: **6.00%** (18/300). 278/300 AGN -> VS in stage-3 confusion. Same
  AGN -> VS leak as the Gemini family; Opus is not immune.
- VS: **95.34%** (266/279) — strongest VS recall of any run logged.
- SN: **79.67%** (239/300), with 45 -> AGN and 8 -> VS. The SN -> AGN slip
  is unique to Opus among the closed-source runs (Gemini Pro: 44 -> AGN
  too; GPT-5.4 high: lots of SN -> AGN; GPT-5.4 none: SN collapse to 14.33%).
  This is a clean SN-vs-AGN texture confusion that adaptive thinking
  partially fixed in the think variant (84% SN there).

**Think vs no-think on Opus 4.7** (paired, same model + 1500-row manifest):
| metric | think (high) | nothink (parsed slice) | delta |
|---|---:|---:|---:|
| 5-class accuracy | 60.60% | 59.50% | −1.10 pp |
| SN per-class | 84.00% | 79.67% | −4.33 pp |
| VS per-class | 91.00% | 95.34% | +4.34 pp |
| AGN per-class | 7.33% | 6.00% | −1.33 pp |
| MSRS | 3.99 | 4.16 | +0.17 |
| Calibration gap | 3.50% | 9.20% | +5.70 pp |
| Avg out tokens | 805 | 648 | −157 |

The think vs nothink delta on the SN/AGN/VS subset is small (~1 pp), but the
calibration gap nearly triples without thinking. So adaptive thinking on
Opus 4.7 isn't buying much raw accuracy — its main value is reining in
overconfidence on borderline calls. This will need to be re-checked once the
asteroid/bogus rows are filled in: in the think variant those two classes
are where Opus most outperformed everyone else (57% / 63%), so the
think-vs-nothink gap may widen substantially.

**Implications and follow-ups:**
1. Run `retry_failed.py --backend anthropic --model claude-opus-4-7
   --reasoning-effort none --concurrency 2 --only both` to fill in the 621
   missing rows. Expect asteroid/bogus to swing the headline 5-class number
   meaningfully.
2. The 30k-ITPM rate limit at concurrency=2 is brittle for Opus prompts
   (~4500 input tokens/call); even sequential is borderline. The retry
   pass should keep the SDK-level retry on (max_retries=8) and run at
   concurrency 1 if 429s persist.
3. Once the run is complete, re-log with this script to refresh the
   metrics in this folder (placeholder Observations will be replaced with
   a clean 1500/1500 narrative, including a real asteroid/bogus signal).
"""


PATCHES = [
    ("runs/20260423-2204-gemini25-pro-high-benchmark-full/report.md",
     GEMINI25_PRO_OBS),
    ("runs/20260423-2110-gemini25-flash-none-benchmark-full/report.md",
     GEMINI25_FLASH_OBS),
    ("runs/20260423-1200-opus47-nothink-benchmark-full/report.md",
     OPUS47_NOTHINK_OBS),
]


def main() -> None:
    for rel_report, new_obs_block in PATCHES:
        report = PROJECT_ROOT / rel_report
        if not report.is_file():
            print(f"!! missing {report}; skipping")
            continue
        text = report.read_text(encoding="utf-8")
        marker = "## Observations"
        idx = text.find(marker)
        if idx == -1:
            print(f"!! '## Observations' not found in {report}; skipping")
            continue
        new_text = text[:idx] + new_obs_block.rstrip() + "\n"
        report.write_text(new_text, encoding="utf-8")
        print(f"updated Observations: {rel_report}")


if __name__ == "__main__":
    main()
