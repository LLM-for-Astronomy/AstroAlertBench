---
title: Leaderboard
---

# Leaderboard

Rankings on the **full benchmark**: **1 500** alerts (300 per class: SN, AGN, VS, asteroid, bogus), one **RGB montage** plus metadata per row, default prompt module **`prompts.py`** (Parts A–C JSON), and scoring with **`evaluate.py`**.

The primary sort key is **absolute 5-class accuracy**: fraction of all 1 500 rows where the model’s JSON parsed and the **final five-way label** matched `target_class`. Each `±` is **one binomial standard error** on that denominator (not a 95 % interval).

| Rank | Model | Reasoning | API | Absolute 5-class | Parse rate | Stage-3 macro F1 | MSRS |
|-----:|---|---|:---:|---:|---:|---:|---:|
| 1 | Claude Opus 4.7 | adaptive (high) | Anthropic | **60.60 ± 1.26 %** | 100.00 % | 0.558 | 3.99 |
| 2 | GPT-5.4 | high | OpenAI | 51.07 ± 1.29 % | 100.00 % | 0.434 | 4.19 |
| 3 | Kimi K2.5 | think | Tinker | 49.34 ± 1.29 % | 99.80 % | 0.500 | 4.49 |
| 4 | Claude Opus 4.7 | disabled | Anthropic | 48.87 ± 1.29 % | 100.00 % | 0.548 | 3.99 |
| 5 | Qwen3.5-397B-A17B | think | Tinker | 44.27 ± 1.28 % | 100.00 % | 0.310 | 4.74 |
| 6 | GPT-5.4 | none | OpenAI | 43.67 ± 1.28 % | 100.00 % | 0.329 | 4.28 |
| 7 | Gemini 2.5 Pro | dynamic thinking | Google | 41.93 ± 1.27 % | 100.00 % | 0.509 | 4.89 |
| 8 | Gemini 2.5 Flash | none | Google | 36.27 ± 1.24 % | 100.00 % | 0.456 | 4.36 |
| 9 | Qwen3.5-397B-A17B | disabled | Tinker | 34.93 ± 1.23 % | 99.87 % | 0.430 | 4.78 |
| 10 | Qwen3.5-35B-A3B | think | Tinker | 26.73 ± 1.14 % | 65.47 % | 0.271 | 4.70 |
| 11 | Qwen3.5-35B-A3B | disabled | Tinker | 25.50 ± 1.13 % | 99.00 % | 0.273 | 4.64 |
| 12 | Qwen3.5-4B | disabled | Tinker | 22.32 ± 1.08 % | 91.13 % | 0.307 | 4.67 |
| 13 | Qwen3.5-4B | think | Tinker | 8.41 ± 0.72 % | 22.27 % | 0.241 | 4.83 |

**MSRS** is the mean self-reasoning score (Part B). **Stage-3 macro F1** is over \{supernova, variable_star, AGN\} conditional on gold astrophysical.

::: warning Heavily truncated runs
**Qwen3.5-35B (think)** and **Qwen3.5-4B (think)** hit the output cap on many rows, so parse rate and absolute accuracy are **not** comparable to the rest without reading the truncation column in the project logs. Treat ranks 10 and 13 as **protocol-stress** cases, not fair capability comparisons at the same effective budget.
:::

## Related tasks

- **Part A** (metadata extraction) and **cascade stages** (real vs bogus → astrophysical → subclass) are reported separately in the evaluation JSON; the table above is only the **headline five-way** endpoint.
- To add a row, rerun the benchmark on **`manifest_benchmark_final.csv`**, then run **`evaluate.py`** with the same manifest and open a pull request with `metrics.json` + brief provenance.

## Version

Numbers are the **13-run refresh** (Apr 21–25, 2026) used internally for the full-benchmark comparison; the ordering matches the **absolute 5-class** column in that sweep. When the paper freeze differs, replace this table with the cited snapshot.
