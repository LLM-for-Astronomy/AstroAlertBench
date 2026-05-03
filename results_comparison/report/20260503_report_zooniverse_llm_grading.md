# Zooniverse LLM response grading — cross-check with benchmark self-scores (3 May 2026)

Source export: `temporary_files/llm-for-astronomy-classifications (4).csv`. Workflow labels map to gold OIDs (Zooniverse bundle under `human_samples/llm_example_grading_zooniverse/`):

| Workflow | OID | `target_class` (manifest) |
|---|---|---|
| LLM Response Grading (X) | ZTF26aargnnp | asteroid |
| LLM Response Grading (A) | ZTF19aayhwvd | VS |
| LLM Response Grading (B) | ZTF19abkdsaw | AGN |
| LLM Response Grading (C) | ZTF25aahvsli | bogus |

## Annotators

Three Zooniverse users each grade **all 13 model snapshots** on **ZTF26aargnnp** (workflow X), and each also grades one **other** OID alone: **lukehandley** → (A), **libai_astro** → (B), **RickyN** → (C). That yields 39 + 13 + 13 + 13 = **78** classification rows with a numeric 0–5 score in the annotations.

A **fourth** layer of human feedback on ZTF26aargnnp is the expert-highlighted `.docx` (`temporary_files/LLM Answer Grading ZTF26aargnnp.docx`). That document does not add another 0–5 column here; see the highlight analysis in [`20260430_report_llm_grading_docx_highlights.md`](20260430_report_llm_grading_docx_highlights.md). The same report covers `LLM Answer Grading ZTF19abfqvbg.docx` (OID **ZTF19abfqvbg** is a separate AGN calibration example, not part of this A/B/C/X PNG bundle).

## 1. ZTF26aargnnp — three independent raters

- **Cronbach’s α** (13 models × 3 raters): **0.863**

- **Pairwise Pearson r** between raters: RickyN vs libai_astro **0.62**, RickyN vs lukehandley **0.88**, libai_astro vs lukehandley **0.72**.

![Heatmap](charts/20260503_01_ztf26_rater_heatmap.png)

*Fig 1. Grades (0–5) for each rater (row) and model index (column). Order 1–13 matches `viz/build_llm_example_grading.py` `RUN_SPECS` and the zooniverse README.*

![Mean ± SD](charts/20260503_02_ztf26_mean_sd_by_model.png)

*Fig 2. Mean human score ±1 SD across the three raters, by model index.*

![Pairwise](charts/20260503_03_rater_pairwise_scatter.png)

*Fig 3. Pairwise scatter plots (same 13 points per panel). The dashed line is y = x.*

### Model index ↔ system

| Idx | Model |
|:---:|:---|
| 1 | Gemini 2.5 Pro high |
| 2 | Gemini 2.5 Flash none |
| 3 | GPT-5.4 high |
| 4 | GPT-5.4 none |
| 5 | Opus 4.7 think |
| 6 | Opus 4.7 nothink |
| 7 | Kimi K2.5 think |
| 8 | Qwen3.5-4B think |
| 9 | Qwen3.5-4B nothink |
| 10 | Qwen3.5-35B think |
| 11 | Qwen3.5-35B nothink |
| 12 | Qwen3.5-397B think |
| 13 | Qwen3.5-397B nothink |

## 2. Self-scores vs human grades

For each (OID, model) we join benchmark `run.jsonl` **Part B** numeric self-scores with the **mean human** grade (for ZTF26 that is the mean of three raters; for other OIDs a single rater).

Incomplete Part B self-scores in some `run.jsonl` `parsed` blocks exclude 1 row(s) from the Pearson summaries & scatter fits: `ZTF26aargnnp` · model 13 (Qwen3.5-397B nothink).


- **Pooled Pearson r** (n = 51): mean self (**key + lead + alt**) vs human mean → **r = -0.086**, p = 5.50e-01
- **Pooled Pearson r** (n = 51): mean self (**lead + alt only**) vs human mean → **r = -0.069**, p = 6.31e-01

![Scatter all self](charts/20260503_04_scatter_self_all_vs_human.png)

![Scatter q23](charts/20260503_05_scatter_self_q23_vs_human.png)

*Fig 4–5. One point per (OID, model). Colors distinguish OIDs.*

With only **four** OIDs per model, per-model correlation is very noisy; the bar summary is still useful to spot sign consistency:

![Per-model r](charts/20260503_08_bar_per_model_correlation.png)

*Fig 6. Pearson r between mean self (3 fields) and human mean, using the four OID points per model.*

## 3. Benchmark correctness vs human grades

- **Point-biserial r** (correctness × human mean): **r = 0.833**, p = 1.96e-14

![Violin correctness](charts/20260503_06_violin_human_by_correctness.png)

![By model split](charts/20260503_07_bar_mean_human_correct_vs_wrong_by_model.png)

*Fig 7–8. Human grades tend to be **lower** when Part C is incorrect (violins), with a per-model breakdown.*

## 4. Expert highlight documents

Qualitative markup (red / yellow / green) for reasoning paragraphs is summarized in [`20260430_report_llm_grading_docx_highlights.md`](20260430_report_llm_grading_docx_highlights.md). It complements the numeric Zooniverse scores on ZTF26aargnnp.

## 5. Extra metrics worth tracking later

- **Reliability growth**: add more raters or duplicate subjects to stabilize ICC/α.
- **Ordinal treatment**: treat 0–5 as ordered and use Kendall’s τ or proportional-odds models (here Pearson is a quick linear summary).
- **Per-field human scores**: if the UI later separates key vs lead vs alt, test which field drives disagreement.
- **Alert difficulty**: bogus vs asteroid vs AGN may anchor graders differently; separate calibration curves per `target_class`.

---

Regenerate: `python -m viz.build_20260503_zooniverse_grading_report`
