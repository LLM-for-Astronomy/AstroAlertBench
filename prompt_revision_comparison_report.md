# Prompt Revision Comparison Report

**Date:** 2026-04-14
**Dataset:** `manifest_fewshot.csv` (100 examples, 20 per class)
**Change under test:** Revised prompt (raw ZTF field names, updated image labels Science/Reference/Difference, enriched field reference, sentinel handling) vs. previous prompt (decoded field names, Science/Template/Image labels)

## Overview

This report compares the **old prompt** (used in the previous Kimi-K2.5 few-shot run) with the **new revised prompt** across 3 models and 2 prompt variants (6 experiments total). The only change between the old and new runs is the prompt — the dataset, montage images, and evaluation pipeline remain identical.

### Experiments

| # | Model | Prompt | Shorthand |
|---|-------|--------|-----------|
| 0 | Kimi-K2.5 | old prompt | **Kimi (old)** |
| 1 | Kimi-K2.5 | prompts.py (new) | **Kimi (new)** |
| 2 | Kimi-K2.5 | prompt_agn_instruction | **Kimi (agn)** |
| 3 | Qwen3-VL-235B-A22B | prompts.py (new) | **Qwen3-235B** |
| 4 | Qwen3-VL-235B-A22B | prompt_agn_instruction | **Qwen3-235B (agn)** |
| 5 | Qwen3-VL-30B-A3B | prompts.py (new) | **Qwen3-30B** |
| 6 | Qwen3-VL-30B-A3B | prompt_agn_instruction | **Qwen3-30B (agn)** |

---

## 1. Overall Classification Accuracy

![5-Class Accuracy](charts/01_5class_accuracy.png)

| Run | 5-Class Accuracy |
|-----|-----------------|
| Kimi (old) | 34% |
| **Kimi (new)** | **41%** (+7%) |
| Kimi (agn) | 35% |
| Qwen3-235B | 35% |
| Qwen3-235B (agn) | 31% |
| Qwen3-30B | 33% |
| Qwen3-30B (agn) | 31% |

The revised prompt improves Kimi-K2.5 from 34% to **41%**, a +7 percentage point gain — the largest improvement in this comparison.

---

## 2. Stage-wise Accuracy Breakdown

![Stage-wise Accuracy](charts/02_stagewise_accuracy.png)

| Run | Stage 1 | Stage 2 | Stage 3 | End-to-End |
|-----|---------|---------|---------|------------|
| Kimi (old) | 0.77 | 0.65 | 0.39 | 0.34 |
| Kimi (new) | 0.80 | 0.64 | **0.47** | **0.41** |
| Kimi (agn) | 0.79 | 0.62 | 0.40 | 0.35 |
| Qwen3-235B | 0.79 | 0.59 | 0.35 | 0.35 |
| Qwen3-235B (agn) | 0.79 | 0.59 | 0.31 | 0.31 |
| Qwen3-30B | 0.79 | 0.59 | 0.33 | 0.33 |
| Qwen3-30B (agn) | 0.80 | 0.60 | 0.31 | 0.31 |

The main improvement is at **Stage 3** (astrophysical subclassification), where Kimi (new) gains +0.08 over the old prompt. Stage 1 and Stage 2 are stable across all runs.

---

## 3. Per-Class Accuracy

![Per-Class Heatmap](charts/03_perclass_accuracy_heatmap.png)

![Per-Class Grouped](charts/04_perclass_accuracy_grouped.png)

### Key observation 1: SN accuracy substantially improves

![SN Accuracy](charts/07_sn_accuracy.png)

Kimi-K2.5 SN accuracy jumps from **30% → 80%** with the new prompt — a dramatic +50pp improvement. The old prompt had Kimi misclassifying 9/20 SNe as variable stars, while the new prompt largely eliminates this confusion. The other models also show strong SN performance (75-85% with default prompt).

### Key observation 2: AGN remains at 0% across almost all runs

AGN accuracy is **0%** in 6 out of 7 runs. The sole exception is Qwen3-235B (default prompt), which correctly classifies 1/20 AGN (5%). All AGN examples are systematically misclassified as variable stars. The AGN instruction prompt, which adds explicit guidance on using PS1 colors and sgscore1, does not resolve this.

### Key observation 3: Asteroid accuracy collapses with the new prompt

![Asteroid Accuracy](charts/08_asteroid_accuracy.png)

Kimi (old) classified 30% of asteroids correctly; the new prompt drops this to 5% (Kimi new) or 0% (all other runs). The revised prompt's more detailed field reference and reasoning instructions appear to make models over-classify solar-system objects as astrophysical sources. This suggests the expanded metadata descriptions may inadvertently discourage the `solar_system` classification path.

---

## 4. Kimi-K2.5: Old Prompt vs New Prompt (Direct Comparison)

![Kimi Old vs New](charts/13_kimi_old_vs_new.png)

![Kimi Per-Class Old vs New](charts/14_kimi_perclass_old_vs_new.png)

| Metric | Old | New | Delta |
|--------|-----|-----|-------|
| 5-Class Accuracy | 0.34 | **0.41** | +0.07 |
| Stage 1 | 0.77 | 0.80 | +0.03 |
| Stage 2 | 0.65 | 0.64 | -0.01 |
| Stage 3 | 0.39 | **0.47** | +0.08 |
| Macro F1 | 0.343 | **0.511** | +0.168 |
| SN accuracy | 0.30 | **0.80** | +0.50 |
| AGN accuracy | 0.00 | 0.00 | 0.00 |
| VS accuracy | 0.95 | 0.95 | 0.00 |
| Asteroid accuracy | 0.30 | 0.05 | -0.25 |
| Bogus accuracy | 0.15 | 0.25 | +0.10 |

The new prompt's net effect on Kimi is strongly positive for astrophysical subclassification (SN, macro F1) but negative for asteroid recognition. The tradeoff is overall beneficial: SN gains (+50pp) far outweigh asteroid losses (-25pp).

---

## 5. Stage 3 F1 Scores

![Macro F1](charts/05_stage3_macro_f1.png)

![Per-Class F1](charts/06_stage3_perclass_f1.png)

| Run | SN F1 | VS F1 | AGN F1 | Macro F1 |
|-----|-------|-------|--------|----------|
| Kimi (old) | 0.462 | 0.567 | 0.000 | 0.343 |
| **Kimi (new)** | **0.889** | 0.644 | 0.000 | **0.511** |
| Kimi (agn) | 0.788 | **0.667** | 0.000 | 0.485 |
| Qwen3-235B | 0.750 | 0.582 | **0.095** | 0.476 |
| Qwen3-235B (agn) | 0.621 | 0.690 | 0.000 | 0.437 |
| Qwen3-30B | 0.829 | 0.536 | 0.000 | 0.455 |
| Qwen3-30B (agn) | 0.710 | 0.606 | 0.000 | 0.439 |

SN F1 is the main driver of the macro F1 improvement. Kimi (new) achieves 0.889 SN F1, nearly double the old prompt's 0.462.

---

## 6. Confusion Matrix: Old vs New Prompt (Kimi-K2.5)

![Confusion Matrices](charts/09_kimi_confusion_oldvsnew.png)

The most striking change: with the old prompt, 9/20 SNe were misclassified as VS; with the new prompt, **0/20 SNe go to VS** (instead, 3 go to AGN and 1 to N/A). The revised field reference appears to help Kimi differentiate SN from VS, though AGN remains a blind spot.

---

## 7. Impact of the AGN Instruction Prompt

![AGN Prompt Impact](charts/12_agn_prompt_impact.png)

Adding the AGN vs VS guidance consistently **hurts overall performance**:

| Model | Default → AGN prompt | 5-Class Delta | SN Delta | VS Delta |
|-------|---------------------|---------------|----------|----------|
| Kimi-K2.5 | 0.41 → 0.35 | -0.06 | -0.15 | +0.05 |
| Qwen3-235B | 0.35 → 0.31 | -0.04 | -0.30 | +0.20 |
| Qwen3-30B | 0.33 → 0.31 | -0.02 | -0.30 | +0.25 |

The AGN instruction prompt creates a consistent pattern: VS accuracy increases (often to 100%) while SN accuracy drops substantially. The extra guidance appears to make models more conservative about assigning SN, pushing borderline cases toward VS or AGN, without actually enabling correct AGN classification.

---

## 8. Confidence Calibration (Part B-C Linkage)

![Confidence vs Accuracy](charts/10_confidence_vs_accuracy.png)

![Pearson Correlation](charts/11_pearson_correlation.png)

| Run | MSRS | Calibration Gap | Pearson r |
|-----|------|-----------------|-----------|
| Kimi (old) | 4.37 | +0.21 | +0.25 |
| Kimi (new) | 4.49 | -0.03 | -0.05 |
| Kimi (agn) | 4.40 | +0.17 | +0.24 |
| Qwen3-235B | 4.80 | +0.09 | +0.27 |
| Qwen3-235B (agn) | 4.87 | +0.07 | +0.21 |
| Qwen3-30B | 4.66 | -0.01 | -0.03 |
| Qwen3-30B (agn) | 4.66 | -0.01 | -0.06 |

Key observations:
- **Kimi (old) had the best calibration** (Pearson r = 0.25, positive calibration gap) — it was more confident when correct.
- **Kimi (new) lost calibration** (Pearson r = -0.05, negative calibration gap) — self-scores no longer predict correctness.
- **Qwen models have universally high self-scores** (MSRS 4.66-4.87), giving themselves 5/5 on nearly every dimension, which renders the self-assessment uninformative. All 100 examples fall in the "high confidence" bucket regardless of correctness.
- The revised prompt appears to have decoupled self-confidence from actual performance for Kimi, while the Qwen models were never well-calibrated to begin with.

---

## 9. Summary of Key Findings

1. **The revised prompt substantially improves SN classification.** Kimi-K2.5 SN accuracy jumps from 30% to 80%, and all models achieve 45-85% SN accuracy with the new prompt. The raw ZTF field presentation and enriched field reference appear to help models correctly identify supernova signatures.

2. **AGN remains unrecognized.** 0% AGN accuracy persists across 6/7 runs. The AGN instruction prompt does not help. All AGN examples are systematically classified as variable stars, suggesting that single-epoch stamp images with metadata are insufficient for this distinction, or that current VLMs lack the relevant domain knowledge.

3. **Asteroid accuracy collapses from 30% to ~0%.** The more detailed prompt may have inadvertently discouraged the solar_system classification pathway. The old prompt's simpler field descriptions may have preserved some heuristic cues (e.g., ndethist=1) that the new prompt's "soft context, not rules" framing weakened.

4. **The AGN instruction prompt consistently hurts.** It shifts the SN-VS boundary toward VS (boosting VS to 100% while dropping SN by 15-30pp) without fixing the core AGN problem. The additional reasoning guidance adds noise rather than signal.

5. **Kimi-K2.5 remains the best model.** It achieves the highest 5-class accuracy (41%) and macro F1 (0.511) with the default new prompt. Qwen3-235B and Qwen3-30B perform similarly to each other (31-35%) despite an 8x difference in active parameters.

6. **Self-confidence scores are poorly calibrated.** The new prompt disrupted Kimi's previously modest calibration, and Qwen models give near-perfect self-scores regardless of correctness. Self-assessed reasoning quality is not a reliable predictor of classification accuracy.

---

## Charts Index

| # | File | Description |
|---|------|-------------|
| 1 | `charts/01_5class_accuracy.png` | Final 5-class accuracy bar chart |
| 2 | `charts/02_stagewise_accuracy.png` | Stage 1/2/3 + 5-class grouped bars |
| 3 | `charts/03_perclass_accuracy_heatmap.png` | Per-class accuracy heatmap |
| 4 | `charts/04_perclass_accuracy_grouped.png` | Per-class accuracy grouped bars |
| 5 | `charts/05_stage3_macro_f1.png` | Stage 3 macro F1 bar chart |
| 6 | `charts/06_stage3_perclass_f1.png` | Stage 3 per-class F1 grouped bars |
| 7 | `charts/07_sn_accuracy.png` | SN accuracy comparison |
| 8 | `charts/08_asteroid_accuracy.png` | Asteroid accuracy comparison |
| 9 | `charts/09_kimi_confusion_oldvsnew.png` | Kimi confusion matrix side-by-side |
| 10 | `charts/10_confidence_vs_accuracy.png` | MSRS vs actual accuracy dual-axis |
| 11 | `charts/11_pearson_correlation.png` | Confidence-accuracy Pearson r |
| 12 | `charts/12_agn_prompt_impact.png` | AGN prompt delta impact |
| 13 | `charts/13_kimi_old_vs_new.png` | Kimi old vs new prompt metrics |
| 14 | `charts/14_kimi_perclass_old_vs_new.png` | Kimi old vs new per-class accuracy |
