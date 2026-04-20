# EXP-20260419-qwen35-baseline-newparser

## Metadata
- **Date:** 2026-04-19 (local)
- **Slug:** qwen35-baseline-newparser
- **Status:** complete
- **Commit:** `c9a0487` (Merge branch 'main' of .../LLM_FOR_ASTRONOMY_BENCHMARK)
- **Working tree dirty:** true — `evaluate.py` has uncommitted edits from the new parser-error-categorization work (value/format error taxonomy)
- **Operator:** user

## Hypothesis
Establish a fresh Qwen3.5-35B-A3B baseline on the 100-datapoint few-shot set using the default `prompts` module, with the new error-categorization parser and per-row `n_output_tokens` / `truncated` tracking. Purpose: provide a control for the A/B comparison against `prompts_token_limit_instruction` and verify the new parser classifies format errors correctly for reasoning-model outputs. Expected outcome: ~30–35 % 5-class accuracy, ~70 % JSON parse rate, with `truncated_no_json` being the dominant format-error code.

## Baseline / Comparison
- **Compared to:** No prior `experiments/EXP-*.md` exists — this is the first logged run. The informal predecessor is `results/fewshot_qwen35_think.jsonl` (3-record sanity run earlier the same day).
- **What changed since the informal predecessor:**
  - JSONL now carries `error_category`, `value_errors`, `n_output_tokens`, `n_answer_tokens`, `truncated`, `max_tokens`.
  - `api_tinker.sample_vlm` now returns `raw_text` (full model output incl. thinking) **and** `answer_text` (post-thinking only), with a helper (`_extract_text_content`) that reads the cookbook renderer's structured parts list.
  - `effective_max` bumped 16 384 → 20 000 for reasoning renderers.
  - `prompts_new.py` renamed to `prompts.py` (the prior `prompts.py` was deleted).

## Configuration
| Field | Value |
|---|---|
| Model | `Qwen/Qwen3.5-35B-A3B` |
| Renderer | `Qwen3_5Renderer` (from `tinker_cookbook.renderers.qwen3_5`) |
| Reasoning mode | enabled (hybrid thinking) |
| max_tokens | 20 000 (auto-bump for reasoning renderer; caller default 2 048) |
| Temperature | 0.2 |
| Concurrency | 8 |
| Prompt module | `prompts` |

## Prompt Summary

**System prompt header (first ~10 lines):**

```
You are an experienced astrophysicist. Your task is to classify astronomical transient candidates using three image cutouts and associated metadata.

The montage is labeled left-to-right on the PNG as Science, Reference, and Difference. Reference is the coadded baseline image; Difference is the subtraction image (science minus reference).

Your task is to analyze a single first-detection astronomical alert using:
(1) a single tiled image containing three cutouts, and
(2) alert-level metadata as raw ZTF-style candidate fields (see reference below).

You must classify the alert using only the provided evidence.
```

**Metadata fields exposed to model** (from `manifest_row_to_metadata`):
`fid, isdiffpos_raw, magpsf, sigmapsf, sgscore1, distpsnr1, classtar, fwhm, ndethist, ncovhist, firstmjd, chinr, sharpnr, sgmag1, srmag1, simag1, szmag1, ssnrms1, distnr, magnr, sigmagnr, rb, drb, drbversion, jd, ra, dec, deltajd`

**Custom Stage guidance:** default (no AGN-vs-VS block, no token-budget block).

## Data
- **Manifest:** `data/manifest_fewshot.csv`
- **Total samples used:** 100 (limit=none)
- **Class distribution:**
  | Class | Count |
  |---|---|
  | SN | 20 |
  | AGN | 20 |
  | VS | 20 |
  | asteroid | 20 |
  | bogus | 20 |

## Command

```bash
python run_tinker_benchmark.py \
  --manifest data/manifest_fewshot.csv \
  --model Qwen/Qwen3.5-35B-A3B \
  --out results/fewshot_qwen35_newparser.jsonl \
  --prompts prompts \
  --concurrency 8
```

## Output
- **Results file:** `results/fewshot_qwen35_newparser.jsonl`
- **Wall-clock runtime:** ~unknown (not recorded)
- **Records written:** 100
- **Records with parsed JSON:** 72 (72 %)

## Code Diff vs Baseline
No prior EXP to diff against. See the "What changed" list in the *Baseline / Comparison* section above for the changes relative to the informal predecessor run.

## Library Versions
- tinker: `0.13.1`
- tinker-cookbook: `0.1.0`

---

## Results

| Metric | Value |
|---|---|
| 5-class accuracy | **33.8 %** |
| JSON parse rate | 72.0 % |
| Stage 1 (real vs artifact) | 77.5 % |
| Stage 2 (astro vs solar) | 57.8 % |
| Stage 3 (astro subclass) macro F1 | 0.249 |
| Part A (metadata reading) | 100 % |
| MSRS (reasoning self-score) | 4.71 |
| Mean output tokens (full) | 10 956 |
| Median output tokens (full) | 8 790 |
| Max output tokens (full) | 20 000 |
| Mean answer tokens (post-thinking) | 5 345 (inflated by truncated rows) |
| Median answer tokens | 482 |
| Truncated runs (hit max_tokens) | 25 (25 %) |

**Format error breakdown (new parser):**
```
ok:                       71
truncated_no_json:        23
truncated_partial_json:    1
parse_failed:              4
schema_missing_top_level:  1
```
**Value error breakdown:** `part_b_missing: 1` (out of 100). No Part C consistency violations (no `c1_*`, no `c2_*`, no enum violations).

**Per-class accuracy:**
| Class | Acc | n (parsed denominator) |
|---|---|---|
| SN | 13.3 % | 15 |
| AGN | 0.0 % | 14 |
| VS | 71.4 % | 14 |
| asteroid | 43.8 % | 16 |
| bogus | 41.7 % | 12 |

**Stage 3 confusion (true → predicted):**
|  | supernova | variable_star | AGN | N/A |
|---|---|---|---|---|
| supernova | 2 | 2 | 2 | 9 |
| variable_star | 0 | 10 | 0 | 4 |
| AGN | 0 | 13 | 0 | 1 |

Notable patterns: AGN almost universally re-predicted as variable_star (0/13 correct); most SN failures land in `N/A` (i.e. the run truncated before emitting Part C stage3).

## Observations
- **Hypothesis matched?** Yes. 34 % 5-class accuracy and 72 % parse rate fell inside the predicted band, and `truncated_no_json` is indeed the dominant format-error code (23 / 29 failures).
- **Surprises:** Complete AGN collapse (0 / 14) is sharper than in prior Kimi / Qwen3-VL runs at similar parse rates. Value-error codes are essentially zero — when the model emits JSON, the schema and cross-stage consistency rules hold. The bottleneck is entirely structural / format, not semantic.
- **Notable failure modes:** The reasoning loop exhausts the 20 k-token cap on ~25 % of rows. When this happens the model never produces a `{`. The post-thinking `answer_text` length is only ~480 tokens median, so "more budget for the answer" is not the problem — it's "more budget for the thinking".
- **Suggested next experiment:** `prompts_agn_instruction` on this same config (Qwen3.5 with `Qwen3_5Renderer`, thinking enabled) — isolate whether the AGN-vs-VS guidance that helped Kimi also helps the reasoning variant. Alternatively, hard-cap `effective_max` at 10–12 k to force earlier termination and see whether it raises JSON emission paradoxically.

**See also:** companion A/B run `EXP-20260419-qwen35-tokenlimit.md` and the comparison report `report/report_qwen35_tokenlimit_vs_baseline_Apr19.md`.
