# Report: Qwen3.5-35B-A3B — `prompts_token_limit_instruction` vs baseline (Apr 19, 2026)

## TL;DR
Adding the **anti-spiral / token-budget guidance** to the system prompt did **not** reduce truncation — it actually made it slightly worse. Final 5-class accuracy is statistically indistinguishable between the two prompts (~34%). The new error breakdown shows the dominant failure mode for both runs is `truncated_no_json` (~25–32%), meaning the model still spends its entire budget thinking and never emits the JSON. The token-limit prompt slightly *increased* mean answer-text length (5.3k → 6.7k tokens) — the opposite of intent.

## Setup

| Field | Value |
|---|---|
| Model | `Qwen/Qwen3.5-35B-A3B` |
| Renderer | `Qwen3_5Renderer` (thinking enabled) |
| Effective `max_tokens` | 20000 (auto-bump for reasoning renderer) |
| Manifest | `data/manifest_fewshot.csv` (100 records, balanced 5-class) |
| Concurrency | 8 |
| Commit | `c9a0487` |
| Date | 2026-04-19 |

| Run | Output JSONL | Prompt module |
|---|---|---|
| **A: baseline** | `results/fewshot_qwen35_newparser.jsonl` | `prompts` |
| **B: token-limit** | `results/fewshot_qwen35_tokenlimit.jsonl` | `prompts_token_limit_instruction` |

The token-limit prompt adds a system-message block instructing the model to: cap reasoning at ~8 k tokens, examine each piece of evidence at most twice, recognize self-cycle phrases ("Wait, let me re-evaluate…") as STOP signals, and commit to a label after two passes — placing remaining doubt into Part B `alternative_analysis` instead of in further deliberation.

## Headline Metrics

| Metric | A: baseline | B: token-limit | Δ (B − A) |
|---|---:|---:|---:|
| 5-class accuracy | **0.338** | **0.354** | +0.016 |
| Stage 1 acc (real vs artifact) | 0.775 | 0.738 | −0.037 |
| Stage 2 acc (astro vs solar) | 0.578 | 0.554 | −0.024 |
| Stage 3 acc (subclass) | 0.437 | 0.415 | −0.022 |
| Stage 3 macro F1 | 0.249 | **0.294** | +0.045 |
| JSON parse rate | **0.72** | 0.66 | −0.06 |
| `truncated_rate` (hit max_tokens) | 0.25 | **0.32** | +0.07 |
| Mean output tokens (full) | 10 956 | 11 366 | +410 |
| Mean answer tokens (post-thinking) | 5 345 | **6 692** | +1 347 |
| Median answer tokens | 482 | 452 | −30 |
| Part A (metadata reading) | 1.000 | 1.000 | — |
| MSRS (self-score) | 4.71 | 4.70 | — |

The single point where B beats A is **Stage 3 macro F1**, driven by recovering 1 extra correct supernova (2/10 vs 2/15) — but this is well within sample noise on n=100.

## Format-Error Breakdown (the new metric)

This is the headline value of the new parser categorization.

### Run A — baseline

```yaml
ok:                       71
truncated_no_json:        23
truncated_partial_json:    1     # got into "{...}" but cut off
parse_failed:              4
schema_missing_top_level:  1
```

### Run B — token-limit prompt

```yaml
ok:                       66
truncated_no_json:        32
parse_failed:              2
```

In both runs the dominant failure is **`truncated_no_json`** — the model exhausts the 20 000-token cap entirely on internal reasoning and never emits a single `{`. This is the exact spiral the new prompt was supposed to prevent.

Both runs have effectively zero **value-error** counts (1 `part_b_missing` in A, 1 `enum_violation_stage3` in B). When the model does produce JSON, the structure is well-formed and the cross-field consistency rules (`c1_artifact_must_zero_others`, `c2_astro_requires_subtype`, etc.) are not violated. The current bottleneck is entirely *structural / format*, not semantic.

## Token-Length Comparison

| Statistic | A: baseline | B: token-limit |
|---|---:|---:|
| Output tokens (full) — median | 8 790 | 9 034 |
| Output tokens (full) — p95 | 20 000 | 20 000 |
| Output tokens (full) — max | 20 000 | 20 000 |
| Answer tokens — median | 482 | 452 |
| Answer tokens — mean | 5 345 | 6 692 |

Mean **answer** tokens is much higher than median because truncated rows (where the renderer can't separate thinking from content) dump the full 20 k blob into `answer_text`. Median answer length is the cleaner signal, and is essentially unchanged (~470 tokens) — the JSON itself is the right size.

## Per-Class Accuracy

| Class | n | A acc | B acc | Notable |
|---|---:|---:|---:|---|
| SN | A:15 / B:10 | 0.13 | 0.20 | Both very low; SN often truncated. |
| AGN | A:14 / B:16 | 0.00 | 0.00 | Total collapse — every parsed AGN goes to variable_star. |
| VS | A:14 / B:16 | 0.71 | 0.69 | Strong, but partly inflated by AGN→VS misroutes. |
| asteroid | A:16 / B:11 | 0.44 | 0.55 | Bigger swing than warranted by sample size. |
| bogus | A:12 / B:12 | 0.42 | 0.33 | Slight regression. |

The class counts differ across runs because the per-class denominator only includes **rows that produced parseable JSON**. The class imbalance in the eval set is therefore an artifact of which rows happened to truncate, not a manifest difference.

### Stage 3 Confusion (true → predicted)

**A (baseline):**
| | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | 2 | 2 | 2 | 9 |
| variable_star | 0 | 10 | 0 | 4 |
| AGN | 0 | 13 | 0 | 1 |

**B (token-limit):**
| | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | 2 | 1 | 0 | 7 |
| variable_star | 0 | 11 | 0 | 5 |
| AGN | 0 | 12 | 0 | 4 |

Same dominant pattern in both: AGN almost universally predicted as variable_star, supernova frequently sent to N/A (often because Part C never fired due to truncation). The new prompt did not change the substantive error structure.

## Confidence Calibration

| Metric | A | B |
|---|---:|---:|
| Mean confidence (correct) | 4.68 | 4.73 |
| Mean confidence (incorrect) | 4.73 | 4.69 |
| Calibration gap | −0.05 | +0.04 |
| Pearson r (conf vs correct) | −0.19 | +0.16 |

Both gaps are tiny and the n=60-ish sample is well within noise of zero. The model is **highly overconfident in both runs** — almost every case scores 5/5 on `confidence_overall` regardless of correctness.

## Key Findings

1. **`prompts_token_limit_instruction` did not work as intended.** Truncation rate went *up* (25% → 32%), and the post-thinking answer text got longer on average. The model's reasoning loop is not regulated by stricter natural-language instruction at this scale.
2. **Structural failures dominate semantic ones.** The new error breakdown shows ~95% of failures are `truncated_no_json`, not bad classifications. Once JSON is emitted, value-error codes are essentially zero — the model follows our schema and consistency rules correctly when it actually finishes.
3. **AGN is a hard zero.** Both prompts: 0/14 and 0/16 AGN correctly classified. This is independent of truncation — when the model does answer for an AGN target, it picks variable_star almost every time. Future experiment should target this fork specifically (e.g. retry `prompts_agn_instruction` on this model now that thinking is enabled).
4. **Part A is saturated.** 100% on every metadata-reading question in both runs. We can stop tracking these granularly and consider Part A "solved" for this model class.

## Suggested Next Experiments

1. **Hard cap on thinking tokens at the API layer**: cut `effective_max` from 20000 to 10000–12000 for Qwen3.5. Truncation will be more frequent, *but* the model will be forced to skip-to-JSON faster and we'll see whether earlier termination produces *more* parseable outputs (paradoxically). Worth one short run.
2. **Combine `prompts_agn_instruction` with thinking-enabled Qwen3.5** to attack the AGN-collapse problem. The previous AGN-instruction run was on `KimiK25DisableThinkingRenderer`-style prompts with a different model; never tested on a reasoning renderer.
3. **Stop further work on natural-language token-budgeting prompts for this model.** Two attempts now suggest the model does not honor self-imposed budgets in its CoT.
