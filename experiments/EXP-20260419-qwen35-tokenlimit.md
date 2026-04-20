# EXP-20260419-qwen35-tokenlimit

## Metadata
- **Date:** 2026-04-19 (local)
- **Slug:** qwen35-tokenlimit
- **Status:** complete
- **Commit:** `c9a0487` (Merge branch 'main' of .../LLM_FOR_ASTRONOMY_BENCHMARK)
- **Working tree dirty:** true — `evaluate.py` has uncommitted edits from the new parser-error-categorization work
- **Operator:** user

## Hypothesis
Qwen3.5-35B-A3B sometimes spirals in internal reasoning ("Wait, let me re-check…") and exhausts its 20 000-token budget before emitting any JSON. A prompt-level nudge — soft 8 k thinking budget, anti-spiral triggers, output-first commitment — *should* shorten the thinking phase and raise JSON emission rate versus the baseline, hopefully also lifting 5-class accuracy because more rows reach Stage 3.

## Baseline / Comparison
- **Compared to:** `EXP-20260419-qwen35-baseline-newparser` (same model, same manifest, same renderer, same `max_tokens`, same git commit; only difference is the prompt module).
- **What changed since baseline:**
  - `--prompts prompts` → `--prompts prompts_token_limit_instruction`.
  - `prompts_token_limit_instruction` imports `prompts.SYSTEM_PROMPT` and appends `REASONING_BUDGET_GUIDANCE` covering: soft 8 k thinking cap, two-pass evidence rule, anti-spiral trigger list, decision-forcing under uncertainty, output-first commitment, hard JSON-completion requirement.
  - No model, renderer, max_tokens, temperature, concurrency, or manifest changes.

## Configuration
| Field | Value |
|---|---|
| Model | `Qwen/Qwen3.5-35B-A3B` |
| Renderer | `Qwen3_5Renderer` |
| Reasoning mode | enabled (hybrid thinking) |
| max_tokens | 20 000 |
| Temperature | 0.2 |
| Concurrency | 8 |
| Prompt module | `prompts_token_limit_instruction` |

## Prompt Summary

**System prompt header (first ~10 lines):** identical to baseline (re-exported from `prompts.SYSTEM_PROMPT`).

```
You are an experienced astrophysicist. Your task is to classify astronomical transient candidates using three image cutouts and associated metadata.

The montage is labeled left-to-right on the PNG as Science, Reference, and Difference. Reference is the coadded baseline image; Difference is the subtraction image (science minus reference).

Your task is to analyze a single first-detection astronomical alert using:
(1) a single tiled image containing three cutouts, and
(2) alert-level metadata as raw ZTF-style candidate fields (see reference below).

You must classify the alert using only the provided evidence.
```

**Metadata fields exposed to model:** identical to baseline (see baseline report).

**Custom Stage guidance:** `REASONING_BUDGET_GUIDANCE` appended to SYSTEM_PROMPT — a ~40-line block instructing:
1. Soft budget: keep internal thinking under ~8 000 tokens.
2. Two-pass rule: after one full Science/Reference/Difference pass + one metadata pass, stop gathering and commit.
3. Anti-spiral triggers: if you catch yourself writing "Wait, let me re-check…", "Actually…", "Let me re-evaluate…" more than twice, stop thinking and write JSON.
4. Decision forcing: if still uncertain, pick the best hypothesis, lower `confidence`, and move remaining doubt into `alternative_analysis` — do NOT keep reasoning.
5. Output-first commitment: JSON must be complete even if internal reasoning was cut short.
6. Hard requirement: always end with a complete JSON object.

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
  --out results/fewshot_qwen35_tokenlimit.jsonl \
  --prompts prompts_token_limit_instruction \
  --concurrency 8
```

## Output
- **Results file:** `results/fewshot_qwen35_tokenlimit.jsonl`
- **Wall-clock runtime:** ~unknown (not recorded)
- **Records written:** 100
- **Records with parsed JSON:** 66 (66 %)

## Code Diff vs Baseline

Both runs were launched from the same commit `c9a0487`. The only delta between `EXP-20260419-qwen35-baseline-newparser` and this run is the `--prompts` flag and the content of `prompts_token_limit_instruction.py` (which imports, does not modify, `prompts.py`).

```
no changes
```

## Library Versions
- tinker: `0.13.1`
- tinker-cookbook: `0.1.0`

---

## Results

| Metric | Value | Δ vs baseline |
|---|---|---|
| 5-class accuracy | **35.4 %** | +1.6 pp |
| JSON parse rate | 66.0 % | −6.0 pp |
| Stage 1 (real vs artifact) | 73.8 % | −3.7 pp |
| Stage 2 (astro vs solar) | 55.4 % | −2.4 pp |
| Stage 3 (subclass) accuracy | 41.5 % | −2.2 pp |
| Stage 3 macro F1 | **0.294** | +0.045 |
| Part A (metadata reading) | 100 % | 0 |
| MSRS (reasoning self-score) | 4.70 | −0.01 |
| Mean output tokens (full) | 11 366 | +410 |
| Median output tokens (full) | 9 034 | +244 |
| Max output tokens (full) | 20 000 | 0 |
| Mean answer tokens (post-thinking) | 6 692 | +1 347 |
| Median answer tokens | 452 | −30 |
| Truncated runs (hit max_tokens) | 32 (32 %) | +7 pp |

The single point where the token-limit prompt beats baseline is Stage 3 macro F1, driven by recovering 1 extra correct supernova. Well within sample noise on n=100.

**Format error breakdown (new parser):**
```
ok:                       66
truncated_no_json:        32
parse_failed:              2
```
**Value error breakdown:** `enum_violation_stage3: 1` (out of 100). Baseline had 1 `part_b_missing`. No Part C consistency violations (`c1_*`, `c2_*`) in either run.

**Per-class accuracy** (denominator = rows with parseable JSON):
| Class | Acc | n |
|---|---|---|
| SN | 20.0 % | 10 |
| AGN | 0.0 % | 16 |
| VS | 68.8 % | 16 |
| asteroid | 54.5 % | 11 |
| bogus | 33.3 % | 12 |

**Stage 3 confusion (true → predicted):**
|  | supernova | variable_star | AGN | N/A |
|---|---|---|---|---|
| supernova | 2 | 1 | 0 | 7 |
| variable_star | 0 | 11 | 0 | 5 |
| AGN | 0 | 12 | 0 | 4 |

## Observations
- **Hypothesis matched?** No. The token-limit guidance made the model *more* verbose, not less: mean output tokens rose by ~410, mean answer tokens rose by ~1 350, truncation rate rose by 7 pp, and JSON parse rate dropped 6 pp. 5-class accuracy ticked up 1.6 pp but this is noise-level on n=100.
- **Surprises:** (1) Simply adding prompt text increased thinking length — likely the model "reads" the anti-spiral instructions as one more topic to deliberate about. (2) AGN collapse persists (0 / 16 correct) exactly as in baseline, which rules out any AGN-specific interaction with the added guidance. (3) Value-error codes remain near-zero — when the model emits JSON, the schema and cross-stage consistency rules hold. The ceiling is structural (truncation), not semantic.
- **Notable failure modes:** `truncated_no_json` is 32 / 34 format errors (94 %). Natural-language self-budgeting is not a lever the model respects inside its CoT for this renderer / size. The model is also highly overconfident — near-5/5 on `confidence_overall` regardless of correctness (Pearson r conf×correct ≈ +0.16 here, −0.19 in baseline — both indistinguishable from zero at n≈60).
- **Suggested next experiment:** Stop pursuing natural-language thinking-budget prompts for Qwen3.5-35B-A3B. Either (a) hard-cap `effective_max` at 10–12 k at the API layer to force earlier exits, or (b) switch to `prompts_agn_instruction` on the reasoning renderer to see whether targeted subclass guidance can break the AGN→VS collapse independently of the truncation issue.

**See also:** baseline `EXP-20260419-qwen35-baseline-newparser.md` and the combined report `report/report_qwen35_tokenlimit_vs_baseline_Apr19.md`.
