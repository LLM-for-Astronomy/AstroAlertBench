# Round 2: Prompt Comparison Report

**Date:** 2026-04-17
**Dataset:** `manifest_fewshot.csv` (100 examples, 20 per class)

## Overview

This report evaluates **4 new experiments** using two prompt versions (`prompts_new.py` and `prompts_old_backup.py`) and compares them against prior results from Round 1 (7 experiments with `prompts.py` and `prompt_agn_instruction.py`).

### Prompt Versions

| Prompt File | Key Characteristics |
|---|---|
| `prompts_old_backup.py` | Decoded field names (e.g. "Filter Band", "PSF Magnitude"), sentinels → N/A, simpler image guide (Science/Reference/Difference labels), no ZTF schema reference |
| `prompts.py` (Round 1) | Raw ZTF field names with field reference, expanded image guide with asteroid/solar-system heuristics, Science/Reference/Difference labels |
| `prompts_new.py` | Raw ZTF field names with full ZTF schema reference, Science/Template/Image labels (original ZTF naming), detailed sentinel handling, explicit Stage 2 solar_system guidance |

### All Experiments

| # | Run | Model | Prompt | 5-Class Acc |
|---|-----|-------|--------|-------------|
| R1-0 | fewshot_kimi_second | Kimi-K2.5 | prompts.py (pre-rev) | 34% |
| R1-1 | fewshot_kimi_prompts | Kimi-K2.5 | prompts.py (rev) | 41% |
| R1-2 | fewshot_kimi_agn | Kimi-K2.5 | prompt_agn_instruction | 35% |
| R1-3 | fewshot_qwen235_prompts | Qwen3-235B | prompts.py (rev) | 35% |
| R1-4 | fewshot_qwen235_agn | Qwen3-235B | prompt_agn_instruction | 31% |
| R1-5 | fewshot_qwen30_prompts | Qwen3-30B | prompts.py (rev) | 33% |
| R1-6 | fewshot_qwen30_agn | Qwen3-30B | prompt_agn_instruction | 31% |
| **R2-1** | **fewshot_kimi_oldbackup** | **Kimi-K2.5** | **prompts_old_backup** | **36%** |
| **R2-2** | **fewshot_kimi_newprompt** | **Kimi-K2.5** | **prompts_new** | **42%** |
| **R2-3** | **fewshot_qwen235_newprompt** | **Qwen3-235B** | **prompts_new** | **44%** |
| **R2-4** | **fewshot_qwen30_newprompt** | **Qwen3-30B** | **prompts_new** | **25%** |

---

## 1. Round 2: Overall Classification Accuracy

![5-Class Accuracy](charts/round2/R01_5class_accuracy.png)

| Run | 5-Class Accuracy | Macro F1 |
|-----|-----------------|----------|
| Kimi old_backup | 36% | 0.411 |
| **Kimi new_prompt** | **42%** | 0.441 |
| **Qwen3-235B new_prompt** | **44%** | **0.476** |
| Qwen3-30B new_prompt | 25% | 0.283 |

**Qwen3-235B achieves the highest 5-class accuracy (44%)** in this round, surpassing Kimi-K2.5 (42%) for the first time. However, Qwen3-30B drops to 25%, the lowest of any run across both rounds.

---

## 2. Stage-wise Accuracy

![Stage-wise Accuracy](charts/round2/R02_stagewise_accuracy.png)

| Run | Stage 1 | Stage 2 | Stage 3 | 5-Class |
|-----|---------|---------|---------|---------|
| Kimi old_backup | 0.77 | 0.65 | 0.41 | 0.36 |
| Kimi new_prompt | 0.79 | 0.66 | **0.54** | 0.42 |
| Qwen235 new_prompt | **0.83** | **0.69** | 0.50 | **0.44** |
| Qwen30 new_prompt | 0.80 | 0.51 | 0.36 | 0.25 |

Kimi new_prompt achieves the highest Stage 3 accuracy (0.54) of any run across all rounds, up from 0.47 with prompts.py. Qwen3-235B leads in Stages 1 and 2. Qwen3-30B collapses at Stage 2 (0.51), indicating it struggles with the real_object → solar_system/astrophysical distinction.

---

## 3. Per-Class Accuracy

![Per-Class Heatmap](charts/round2/R03_perclass_heatmap.png)

![Per-Class Grouped — 3 Models](charts/round2/R04_perclass_3models_newprompt.png)

| Run | SN | AGN | VS | Asteroid | Bogus |
|-----|-----|-----|-----|---------|-------|
| Kimi old_backup | 45% | 0% | 95% | 20% | 20% |
| Kimi new_prompt | 50% | 0% | 95% | **50%** | 15% |
| Qwen235 new_prompt | **60%** | **5%** | 90% | 40% | **25%** |
| Qwen30 new_prompt | 20% | 0% | 80% | 25% | 0% |

### Key finding 1: Asteroid accuracy recovers dramatically

The most significant change from Round 1: **asteroid accuracy recovers from near-zero to 25–50%**. In Round 1, prompts.py produced 0–5% asteroid accuracy across all models. With prompts_new, Kimi reaches 50% and Qwen3-235B reaches 40%. The `prompts_new.py` prompt includes explicit Stage 2 solar_system guidance and uses the original ZTF image labels (Science/Template/Image), which appear to help models recognize moving objects.

### Key finding 2: SN accuracy trades off with asteroid accuracy

Kimi's SN accuracy drops from 80% (prompts.py) to 50% (prompts_new). The prompt revision that recovered asteroids has partially shifted the SN-asteroid boundary: some SNe are now misclassified as AGN or get N/A at Stage 3.

### Key finding 3: AGN remains at 0% (except Qwen3-235B at 5%)

The persistent AGN blindness continues. Qwen3-235B is the only model to correctly classify any AGN (1/20 = 5%), consistent with its Round 1 performance.

---

## 4. Kimi-K2.5 Across All 4 Prompt Versions

![Kimi Pipeline Cascade](charts/round2/R05_kimi_4prompts_cascade.png)

![Kimi Per-Class Across Prompts](charts/round2/R06_kimi_4prompts_perclass.png)

| Prompt | 5-Class | Stage 3 | SN | AGN | VS | Asteroid | Bogus | Macro F1 |
|--------|---------|---------|-----|-----|-----|---------|-------|----------|
| old_prompt (pre-rev) | 34% | 0.39 | 30% | 0% | 95% | 30% | 15% | 0.343 |
| prompts.py (rev) | 41% | 0.47 | **80%** | 0% | 95% | 5% | 25% | **0.511** |
| old_backup | 36% | 0.41 | 45% | 0% | 95% | 20% | 20% | 0.411 |
| new_prompt | **42%** | **0.54** | 50% | 0% | 95% | **50%** | 15% | 0.441 |

The 4 Kimi runs reveal a clear tradeoff:
- **prompts.py** maximizes SN accuracy (80%) but sacrifices asteroids (5%)
- **prompts_new** balances SN (50%) and asteroid (50%) more evenly, achieving the best Stage 3 accuracy (0.54)
- **old_backup** sits in between — moderate SN (45%), moderate asteroid (20%)
- VS accuracy is rock-solid at 95% regardless of prompt

---

## 5. Stage 3 F1 Scores

![Macro F1](charts/round2/R07_macro_f1.png)

| Run | SN F1 | VS F1 | AGN F1 | Macro F1 |
|-----|-------|-------|--------|----------|
| Kimi old_backup | 0.621 | 0.613 | 0.000 | 0.411 |
| Kimi new_prompt | 0.667 | 0.655 | 0.000 | 0.441 |
| Qwen235 new_prompt | **0.727** | 0.621 | **0.080** | **0.476** |
| Qwen30 new_prompt | 0.308 | 0.542 | 0.000 | 0.283 |

Qwen3-235B leads in macro F1 (0.476), driven by the highest SN F1 (0.727) and the only non-zero AGN F1 (0.080).

---

## 6. Cross-Round Comparison: All Prompt Versions

![5-Class Accuracy — All Runs](charts/round2/R10_5class_all_runs.png)

![SN Accuracy — All Runs](charts/round2/R09_sn_all_runs.png)

![Asteroid Accuracy — All Runs](charts/round2/R08_asteroid_all_runs.png)

### Impact of prompts_new vs prompts.py (delta)

![Prompt Delta](charts/round2/R14_newprompt_delta.png)

| Model | prompts.py → prompts_new | 5-Class | SN | Asteroid | VS |
|-------|--------------------------|---------|-----|---------|-----|
| Kimi-K2.5 | 41% → 42% | +1pp | -30pp | **+45pp** | 0pp |
| Qwen3-235B | 35% → 44% | **+9pp** | -15pp | **+40pp** | +10pp |
| Qwen3-30B | 33% → 25% | -8pp | -65pp | +25pp | +5pp |

The pattern is consistent for Kimi and Qwen3-235B: prompts_new **dramatically recovers asteroid accuracy** (+40–45pp) at the cost of SN accuracy (-15 to -30pp), with a net positive effect on overall accuracy. Qwen3-30B is the exception — it loses too much SN (-65pp) for the asteroid gains to compensate.

---

## 7. Misclassification Analysis

![AGN Misclassification](charts/round2/R12_agn_pie.png)

AGN examples continue to be overwhelmingly classified as VS (19–20 out of 20) across all runs. Qwen3-30B additionally misclassifies 8/20 AGN as asteroids with prompts_new.

![Asteroid Misclassification](charts/round2/R13_asteroid_pie.png)

Asteroid misclassification patterns have improved with prompts_new: Kimi now correctly identifies 10/20 (vs 1/20 with prompts.py), though SN remains the most common misclassification for asteroids across Qwen models.

---

## 8. Model Comparison (prompts_new only)

![Radar — 3 Models](charts/round2/R11_radar_3models_newprompt.png)

| Metric | Kimi-K2.5 | Qwen3-235B | Qwen3-30B |
|--------|-----------|------------|-----------|
| 5-Class Accuracy | 42% | **44%** | 25% |
| Macro F1 | 0.441 | **0.476** | 0.283 |
| MSRS | 4.44 | 4.76 | 4.66 |
| Pearson r | 0.067 | -0.078 | 0.058 |
| Part A Accuracy | 100% | 100% | 100% |

Qwen3-235B is the best model on prompts_new, achieving the highest accuracy and F1. Kimi-K2.5 is a close second. Qwen3-30B underperforms significantly — its smaller active parameter count (3B vs 22B for Qwen3-235B) appears insufficient for this task with the more complex prompt.

---

## 9. Confidence Calibration

| Run | MSRS | Calibration Gap | Pearson r |
|-----|------|-----------------|-----------|
| Kimi old_backup | 4.36 | +0.175 | **+0.201** |
| Kimi new_prompt | 4.44 | +0.049 | +0.067 |
| Qwen235 new_prompt | 4.76 | -0.025 | -0.078 |
| Qwen30 new_prompt | 4.66 | +0.004 | +0.058 |

Kimi old_backup has the best calibration (Pearson r = 0.201) — its simpler prompt produces self-scores that correlate with actual correctness. The more complex prompts (new_prompt, prompts.py) tend to decouple confidence from accuracy.

---

## 10. Summary of Key Findings

1. **prompts_new recovers asteroid accuracy.** The most dramatic improvement: asteroid accuracy jumps from 0–5% (prompts.py) to 25–50% (prompts_new). The explicit Stage 2 solar_system guidance and original ZTF image labels (Science/Template/Image) appear critical for this.

2. **SN accuracy trades off with asteroid recovery.** prompts_new reduces SN accuracy by 15–65pp compared to prompts.py. The prompt modifications that help models recognize moving objects also make them more conservative about assigning SN.

3. **Qwen3-235B is now the best model.** With prompts_new, Qwen3-235B achieves 44% accuracy and 0.476 macro F1 — the highest across both rounds. It is also the only model to classify any AGN correctly (5%).

4. **Qwen3-30B struggles with prompts_new.** At 25% accuracy, it performs at random-baseline level. The complex raw-field prompt with extensive ZTF schema reference appears to exceed its capacity.

5. **AGN remains the hardest class.** 0% AGN accuracy across 10 of 11 total runs. This is a fundamental limitation of single-epoch stamp classification for AGN vs VS distinction.

6. **VS accuracy is the most stable.** 75–100% across all runs and all prompts, suggesting VS has the most distinctive visual+metadata signature.

7. **Simpler prompts produce better-calibrated confidence.** Kimi old_backup (decoded field names, no schema reference) yields the highest confidence-accuracy correlation (r = 0.201), while complex prompts decouple self-assessment from actual performance.

8. **No single prompt dominates.** prompts.py maximizes SN, prompts_new maximizes asteroid + overall balance, and old_backup provides moderate performance with the best calibration. The optimal prompt depends on which classes matter most for the application.

---

## 5-Class Confusion Matrices

### Kimi-K2.5 + old_backup (36%)
```
True\Pred     SN   AGN    VS  asteroid  bogus
SN             9     6     3         0      2
AGN            0     0    20         0      0
VS             0     0    19         0      1
asteroid       7     0     5         4      4
bogus          7     1     7         1      4
```

### Kimi-K2.5 + new_prompt (42%)
```
True\Pred     SN   AGN    VS  asteroid  bogus
SN            10     5     0         5      0
AGN            0     0    19         1      0
VS             0     0    19         1      0
asteroid       4     0     2        10      4
bogus          5     2     2         8      3
```

### Qwen3-235B + new_prompt (44%)
```
True\Pred     SN   AGN    VS  asteroid  bogus
SN            12     4     1         3      0
AGN            0     1    19         0      0
VS             1     0    18         1      0
asteroid       7     0     3         8      2
bogus          3     2     6         4      5
```

### Qwen3-30B + new_prompt (25%)
```
True\Pred     SN   AGN    VS  asteroid  bogus
SN             4     0    11         5      0
AGN            0     0    12         8      0
VS             2     1    16         1      0
asteroid       8     0     7         5      0
bogus          4     0     5        11      0
```

---

## Charts Index

| # | File | Description |
|---|------|-------------|
| R01 | `charts/round2/R01_5class_accuracy.png` | 5-class accuracy (4 new runs) |
| R02 | `charts/round2/R02_stagewise_accuracy.png` | Stage-wise accuracy (4 new runs) |
| R03 | `charts/round2/R03_perclass_heatmap.png` | Per-class accuracy heatmap |
| R04 | `charts/round2/R04_perclass_3models_newprompt.png` | Per-class accuracy grouped bar (3 models) |
| R05 | `charts/round2/R05_kimi_4prompts_cascade.png` | Kimi pipeline cascade across 4 prompts |
| R06 | `charts/round2/R06_kimi_4prompts_perclass.png` | Kimi per-class across 4 prompts |
| R07 | `charts/round2/R07_macro_f1.png` | Stage 3 Macro F1 |
| R08 | `charts/round2/R08_asteroid_all_runs.png` | Asteroid accuracy all runs |
| R09 | `charts/round2/R09_sn_all_runs.png` | SN accuracy all runs |
| R10 | `charts/round2/R10_5class_all_runs.png` | 5-class accuracy all runs |
| R11 | `charts/round2/R11_radar_3models_newprompt.png` | Radar chart 3 models |
| R12 | `charts/round2/R12_agn_pie.png` | AGN misclassification pie |
| R13 | `charts/round2/R13_asteroid_pie.png` | Asteroid misclassification pie |
| R14 | `charts/round2/R14_newprompt_delta.png` | prompts_new vs prompts.py delta |
