# Few-Shot Evaluation Report: 3 Models x 2 Prompts (6 Experiments)

**Date:** 2026-04-14
**Dataset:** `manifest_fewshot.csv` (100 examples, 20 per class: SN, AGN, VS, asteroid, bogus)
**Prompt variants:** `prompts.py` (default ZTF-field prompt) and `prompt_agn_instruction.py` (default + AGN vs VS guidance)
**Montage labels:** Science / Reference / Difference (updated)

## Experiment Matrix

| # | Model | Prompt | Result file |
|---|-------|--------|-------------|
| 1 | Kimi-K2.5 | prompts | `fewshot_kimi_prompts.jsonl` |
| 2 | Kimi-K2.5 | prompt_agn_instruction | `fewshot_kimi_agn.jsonl` |
| 3 | Qwen3-VL-235B-A22B | prompts | `fewshot_qwen235_prompts.jsonl` |
| 4 | Qwen3-VL-235B-A22B | prompt_agn_instruction | `fewshot_qwen235_agn.jsonl` |
| 5 | Qwen3-VL-30B-A3B | prompts | `fewshot_qwen30_prompts.jsonl` |
| 6 | Qwen3-VL-30B-A3B | prompt_agn_instruction | `fewshot_qwen30_agn.jsonl` |

All 6 runs: n_examples=100, n_errors=0, json_parseable=100, json_valid_rate=1.0.

---

## Part A: Metadata Grounding

All 6 experiments achieved **100% accuracy** on all Part A fields (filter_band, subtraction_sign, magpsf, sigmapsf, ndethist, ncovhist). Part A macro accuracy = 1.0, exact match rate = 1.0 across the board. All three models perfectly extract and decode the raw ZTF candidate fields.

---

## Part B: Self-Assessed Reasoning

| Model | Prompt | MSRS | Key Evidence | Leading Interp. | Alt. Analysis | Self Pass Rate |
|-------|--------|------|-------------|-----------------|---------------|----------------|
| Kimi-K2.5 | prompts | 4.49 | 4.89 | 4.65 | 3.93 | 0.91 |
| Kimi-K2.5 | agn_instruction | 4.40 | 4.79 | 4.49 | 3.93 | 0.91 |
| Qwen3-235B | prompts | 4.80 | 5.00 | 5.00 | 4.39 | 1.00 |
| Qwen3-235B | agn_instruction | 4.87 | 5.00 | 5.00 | 4.62 | 1.00 |
| Qwen3-30B | prompts | 4.66 | 4.99 | 4.98 | 4.01 | 1.00 |
| Qwen3-30B | agn_instruction | 4.66 | 5.00 | 4.98 | 4.00 | 1.00 |

Both Qwen models give themselves near-perfect self-scores (5.0 on key_evidence and leading_interpretation) with 100% self-pass rate. Kimi-K2.5 is marginally more self-critical (MSRS ~4.45, pass rate 0.91). Self-scores are self-reported and not externally validated.

---

## Part C: Classification Results

### Stage-Level Accuracy

| Model | Prompt | Stage 1 | Stage 2 | Stage 3 | End-to-End | 5-Class Acc. |
|-------|--------|---------|---------|---------|------------|-------------|
| Kimi-K2.5 | prompts | 0.80 | 0.64 | 0.47 | 0.41 | **0.41** |
| Kimi-K2.5 | agn_instruction | 0.79 | 0.62 | 0.40 | 0.35 | 0.35 |
| Qwen3-235B | prompts | 0.79 | 0.59 | 0.35 | 0.35 | 0.35 |
| Qwen3-235B | agn_instruction | 0.79 | 0.59 | 0.31 | 0.31 | 0.31 |
| Qwen3-30B | prompts | 0.79 | 0.59 | 0.33 | 0.33 | 0.33 |
| Qwen3-30B | agn_instruction | 0.80 | 0.60 | 0.31 | 0.31 | 0.31 |

**Best overall: Kimi-K2.5 + prompts (41% 5-class accuracy).**

Stage 1 accuracy is consistent across all runs (~0.79-0.80). The main differentiator is Stage 3 (astrophysical subclassification), where Kimi-K2.5 + prompts leads at 0.47.

### Per-Class Accuracy

| Model | Prompt | SN | AGN | VS | Asteroid | Bogus |
|-------|--------|-----|-----|-----|----------|-------|
| Kimi-K2.5 | prompts | 0.80 | **0.00** | **0.95** | 0.05 | 0.25 |
| Kimi-K2.5 | agn_instruction | 0.65 | **0.00** | **1.00** | 0.00 | 0.10 |
| Qwen3-235B | prompts | 0.75 | **0.05** | 0.80 | 0.00 | 0.15 |
| Qwen3-235B | agn_instruction | 0.45 | **0.00** | **1.00** | 0.00 | 0.10 |
| Qwen3-30B | prompts | **0.85** | **0.00** | 0.75 | 0.00 | 0.05 |
| Qwen3-30B | agn_instruction | 0.55 | **0.00** | **1.00** | 0.00 | 0.00 |

### Stage 3 Macro F1

| Model | Prompt | Macro F1 | SN F1 | VS F1 | AGN F1 |
|-------|--------|----------|-------|-------|--------|
| Kimi-K2.5 | prompts | **0.511** | 0.889 | 0.644 | 0.000 |
| Kimi-K2.5 | agn_instruction | 0.485 | 0.788 | 0.667 | 0.000 |
| Qwen3-235B | prompts | 0.476 | 0.750 | 0.582 | 0.095 |
| Qwen3-235B | agn_instruction | 0.437 | 0.621 | 0.690 | 0.000 |
| Qwen3-30B | prompts | 0.455 | 0.829 | 0.536 | 0.000 |
| Qwen3-30B | agn_instruction | 0.439 | 0.710 | 0.606 | 0.000 |

---

## Stage 3 Confusion Matrices

### Kimi-K2.5 + prompts (best overall)

| True \ Pred | SN | VS | AGN | N/A |
|-------------|----|----|-----|-----|
| **SN** | **16** | 0 | 3 | 1 |
| **VS** | 0 | **19** | 0 | 1 |
| **AGN** | 0 | 20 | **0** | 0 |

### Kimi-K2.5 + agn_instruction

| True \ Pred | SN | VS | AGN | N/A |
|-------------|----|----|-----|-----|
| **SN** | **13** | 0 | 7 | 0 |
| **VS** | 0 | **20** | 0 | 0 |
| **AGN** | 0 | 20 | **0** | 0 |

### Qwen3-235B + prompts (only run with AGN > 0%)

| True \ Pred | SN | VS | AGN | N/A |
|-------------|----|----|-----|-----|
| **SN** | **15** | 3 | 0 | 2 |
| **VS** | 4 | **16** | 0 | 0 |
| **AGN** | 1 | 16 | **1** | 2 |

### Qwen3-235B + agn_instruction

| True \ Pred | SN | VS | AGN | N/A |
|-------------|----|----|-----|-----|
| **SN** | **9** | 0 | 10 | 1 |
| **VS** | 0 | **20** | 0 | 0 |
| **AGN** | 0 | 18 | **0** | 2 |

### Qwen3-30B + prompts

| True \ Pred | SN | VS | AGN | N/A |
|-------------|----|----|-----|-----|
| **SN** | **17** | 2 | 1 | 0 |
| **VS** | 3 | **15** | 0 | 2 |
| **AGN** | 1 | 19 | **0** | 0 |

### Qwen3-30B + agn_instruction

| True \ Pred | SN | VS | AGN | N/A |
|-------------|----|----|-----|-----|
| **SN** | **11** | 6 | 3 | 0 |
| **VS** | 0 | **20** | 0 | 0 |
| **AGN** | 0 | 20 | **0** | 0 |

---

## Key Findings

### 1. AGN remains completely unrecognized

Across all 6 experiments, AGN accuracy is 0% in 5 out of 6 runs. The sole exception is Qwen3-235B + prompts, which correctly classified 1 out of 20 AGN (5%). In every other case, all 20 AGN examples are misclassified as variable_star. This is the dominant failure mode and the single largest drag on overall accuracy.

### 2. The AGN instruction prompt does not help — it hurts

Contrary to expectations, adding the AGN vs VS guidance (`prompt_agn_instruction`) consistently **decreased** performance compared to the default prompt:

| Model | prompts (5-class) | agn_instruction (5-class) | Delta |
|-------|-------------------|---------------------------|-------|
| Kimi-K2.5 | 0.41 | 0.35 | -0.06 |
| Qwen3-235B | 0.35 | 0.31 | -0.04 |
| Qwen3-30B | 0.33 | 0.31 | -0.02 |

The AGN instruction prompt tends to make models over-classify SN as AGN (Kimi SN accuracy drops 0.80 → 0.65; Qwen3-235B drops 0.75 → 0.45) while still failing to classify actual AGN correctly. It also pushes VS accuracy to 1.0 in most cases, but at the cost of absorbing all AGN into VS predictions.

### 3. Kimi-K2.5 is the best-performing model

Kimi-K2.5 + prompts achieves the highest 5-class accuracy (41%), highest Stage 3 accuracy (47%), and highest macro F1 (0.511). It particularly excels at SN classification (80% accuracy, 0.889 F1). Kimi's advantage is primarily in its Stage 3 discrimination — it classifies SN more reliably than the Qwen models.

### 4. Qwen3-235B shows a hint of AGN recognition

Qwen3-235B + prompts is the only configuration that correctly identified any AGN (1/20). While this is too few to be meaningful, it suggests that the larger Qwen model may have slightly more capacity for the AGN/VS distinction. However, this came at the cost of more SN↔VS confusion compared to Kimi.

### 5. Asteroid and bogus remain poorly classified

All models struggle with asteroid (0-5% accuracy) and bogus (0-25% accuracy). These classes are overwhelmingly misclassified as real astrophysical objects at Stage 1. The consistent Stage 1 accuracy of ~0.80 reflects this: models correctly identify ~94-97% of real objects but only ~55-65% of artifacts/bogus, and almost no asteroids are classified as solar_system at Stage 2.

### 6. Model size does not clearly correlate with performance

Qwen3-235B (235B parameters, 22B active) and Qwen3-30B (30B parameters, 3B active) perform similarly on the classification task (35% vs 33% with prompts; 31% vs 31% with agn_instruction). The 8x difference in active parameters does not translate into meaningful accuracy gains for this benchmark.

---

## Summary Table

| Rank | Model | Prompt | 5-Class Acc. | Stage 3 F1 | SN | AGN | VS |
|------|-------|--------|-------------|------------|-----|-----|-----|
| 1 | Kimi-K2.5 | prompts | **0.41** | **0.511** | 0.80 | 0.00 | 0.95 |
| 2 | Kimi-K2.5 | agn_instruction | 0.35 | 0.485 | 0.65 | 0.00 | 1.00 |
| 3 | Qwen3-235B | prompts | 0.35 | 0.476 | 0.75 | 0.05 | 0.80 |
| 4 | Qwen3-30B | prompts | 0.33 | 0.455 | 0.85 | 0.00 | 0.75 |
| 5 | Qwen3-235B | agn_instruction | 0.31 | 0.437 | 0.45 | 0.00 | 1.00 |
| 6 | Qwen3-30B | agn_instruction | 0.31 | 0.439 | 0.55 | 0.00 | 1.00 |

---

## Conclusion

The AGN classification problem remains the central bottleneck. No model-prompt combination achieves more than 5% AGN accuracy on this benchmark. The added AGN instruction prompt, which provides explicit guidance on using PS1 colors and sgscore1 to distinguish AGN from VS, paradoxically worsens performance — likely because it introduces additional reasoning overhead that destabilizes SN classification without actually enabling AGN recognition. The underlying issue appears to be that AGN and VS are genuinely difficult to distinguish from single-epoch stamp images and metadata alone, and current VLMs lack the domain-specific visual features needed to make this distinction.
