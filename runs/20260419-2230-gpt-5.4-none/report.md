# Run report — gpt-5.4  (20260419-2230)

## Metadata
- **Run folder:** `20260419-2230-gpt-5.4-none`
- **Run timestamp:** 20260419-2230
- **Slug:** gpt-5.4-none
- **Status:** complete
- **Commit:** `8550e43`
- **Working tree dirty:** true
  - modified: runs/, viz/
- **Operator:** user

## Hypothesis

A/B counterpart to `EXP-20260419-gpt54-high`. Run GPT-5.4 with `reasoning_effort: none` (CoT disabled) on the same 20-row subset to isolate the effect of the thinking dial. Expectation: lower accuracy (no reasoning), faster, much cheaper. Useful as a non-reasoning baseline for the closed-source comparison.

## Baseline / Comparison

- **Compared to:** `EXP-20260419-gpt54-high` (same model, same prompts, same data; only the `--reasoning-effort` flag changes).

## Configuration

| Field | Value |
|---|---|
| model | `gpt-5.4` |
| backend | `openai` |
| reasoning_effort | `none` |
| max_tokens | `20000` |
| prompt_module | `prompts` |

## Data
- **Manifest:** `data\manifest_fewshot_20.csv`
- **Total records in run:** 20
- **Class distribution:**

| Class | Count |
|---|---|
| AGN | 4 |
| SN | 4 |
| VS | 4 |
| asteroid | 4 |
| bogus | 4 |

## Output

- **Predictions JSONL (in run folder):** `run.jsonl`
- **Original path:** `results\fewshot20_gpt54_none.jsonl`
- **Records written:** 20
- **Records with parsed JSON:** 20 (100.00 %)

## Results

### 1. Run-level counts

| Metric | Value |
|---|---|
| n_examples | 20 |
| n_errors (runtime) | 0 |
| json_parseable | 20 |
| json_valid_rate | 100.00 % |

### 2. Token statistics

| Statistic | output_tokens (full) | answer_tokens (post-thinking) |
|---|---|---|
| mean | 463.0 | 463.0 |
| median | 463 | 463 |
| min | 428 | 428 |
| max | 495 | 495 |
| p95 | 493 | — |
| n_truncated | 0 | — |
| truncated_rate | 0.00 % | — |

### 3. Error breakdown

**Format errors** (mutually exclusive, one code per row):

| Code | Count |
|---|---|
| ok | 20 |

Rows with ≥ 1 value error: **0**

### 4. Part A — metadata reading

| Field | Accuracy |
|---|---|
| filter_band | 100.00 % |
| subtraction_sign | 100.00 % |
| magpsf | 100.00 % |
| sigmapsf | 100.00 % |
| ndethist | 100.00 % |
| ncovhist | 100.00 % |
| **macro** | 100.00 % |
| **exact match (all 6)** | 100.00 % |

### 5. Part B — self-rated reasoning

- **MSRS (mean self-rated score):** 4.25
- **Per-dimension mean self-score:**
  - key_evidence: 4.45
  - leading_interpretation: 4.3
  - alternative_analysis: 4
- **Self-pass rate (row-mean ≥ 4):** 95.00 %

### 6. Part B ↔ C — confidence-accuracy calibration

| Metric | Value |
|---|---|
| n_linked | 20 |
| mean_confidence_correct | 4.2333 |
| mean_confidence_incorrect | 4.2667 |
| calibration_gap | -0.0333 |
| pearson_r | -0.0503 |
| accuracy_high_confidence (conf ≥ 4) | 47.37 % |
| n_high_confidence | 19 |
| accuracy_low_confidence (conf < 4) | 100.00 % |
| n_low_confidence | 1 |

### 7. Part C — stage-wise classification

| Metric | Value |
|---|---|
| n_evaluable | 20 |
| Stage 1 (real / artifact) | 80.00 % |
| Stage 2 (astrophysical / solar) | 75.00 % |
| Stage 3 (subclass) | 55.00 % |
| Stage 2 conditional on Stage 1 correct | 87.50 % |
| Stage 3 conditional on Stages 1+2 correct | 41.67 % |
| End-to-end staged accuracy | 50.00 % |
| **Final 5-class accuracy** | **50.00 %** |

### 8. Per-class breakdown

| Class | Accuracy | Correct | Total |
|---|---|---|---|
| AGN | 0.00 % | 0 | 4 |
| SN | 25.00 % | 1 | 4 |
| VS | 100.00 % | 4 | 4 |
| asteroid | 100.00 % | 4 | 4 |
| bogus | 25.00 % | 1 | 4 |

### 9. Binary precision/recall/F1 at stages 1 & 2

| Stage | Precision | Recall | F1 |
|---|---|---|---|
| Stage 1 (real_object=+) | 0.8333 | 0.9375 | 0.8824 |
| Stage 2 (astrophysical=+) | 0.8333 | 0.8333 | 0.8333 |

### 10. Stage-3 subclass PRF

- **Macro F1:** 0.3556

| Class | Precision | Recall | F1 |
|---|---|---|---|
| supernova | 1 | 0.25 | 0.4 |
| variable_star | 0.5 | 1 | 0.6667 |
| AGN | 0 | 0 | 0 |

### 11. Stage-3 confusion matrix

| gold \ pred | supernova | variable_star | AGN | N/A |
|---|---|---|---|---|
| **supernova** | 1 | 0 | 1 | 2 |
| **variable_star** | 0 | 4 | 0 | 0 |
| **AGN** | 0 | 4 | 0 | 0 |

## Plots

The following charts are saved under `./plots/` (see `plots/README.md` for descriptions):

- `plots/per_class_accuracy.png`

  ![per_class_accuracy.png](./plots/per_class_accuracy.png)

- `plots/five_class_confusion.png`

  ![five_class_confusion.png](./plots/five_class_confusion.png)

- `plots/stage3_confusion.png`

  ![stage3_confusion.png](./plots/stage3_confusion.png)

- `plots/token_distribution.png`

  ![token_distribution.png](./plots/token_distribution.png)

- `plots/error_breakdown.png`

  ![error_breakdown.png](./plots/error_breakdown.png)

- `plots/calibration.png`

  ![calibration.png](./plots/calibration.png)

## Per-datapoint HTML visualizations

Self-contained `logtree` HTML files, one per selected datapoint (top-10 by ALERCE probability within each class). Open any of them directly in a browser.

| Class | HTMLs in `viz/` |
|---|---|
| AGN | 4 (`viz/AGN/`) |
| SN | 4 (`viz/SN/`) |
| VS | 4 (`viz/VS/`) |
| asteroid | 4 (`viz/asteroid/`) |
| bogus | 4 (`viz/bogus/`) |

## Observations

- **Hypothesis matched?** No, in the *opposite* direction. With reasoning disabled, GPT-5.4 *outperforms* the high-reasoning variant on this 20-row slice (50 % vs 40 %). The reasoning model collapses all 4 SNe to AGN; the non-reasoning model gets 1 SN right and N/As 2 others.
- **Surprises:** (1) Token economy is dramatic — non-reasoning is ~4.6× cheaper in output tokens (463 vs 2 130) and roughly $0 vs ~$0.05/record in API cost terms. (2) Stage 2 (astro vs solar) drops 5 pp without reasoning, but Stage 3 (astro subclass) is identical — reasoning is helping narrow stage 2 but actively *hurting* SN classification at stage 3. (3) Asteroid 4/4 vs 3/4: the non-reasoning model gets all asteroids right because it doesn't over-deliberate motion-vs-stellar evidence.
- **Notable failure modes:** Same AGN 0/4 universal failure. SN is the swing class (1/4 vs 0/4).
- **Caveats:** n=20 is small. The 10 pp accuracy gap is exactly 2 records — noise-level on this slice. The directional finding ("reasoning didn't help") is suggestive, not conclusive. Need to rerun on the full 100-row manifest before drawing strong conclusions.
- **Suggested next experiment:** scale both runs to 100 rows and see whether reasoning recovers a meaningful edge.

**See also:** `report/report_gpt54_high_vs_none_Apr19.md`.
