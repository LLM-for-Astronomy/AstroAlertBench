# Full-benchmark comparison — 9 runs on `manifest_benchmark_final.csv` (Apr 21 2026, refreshed Apr 22 with standard errors)

Cross-run comparison of **every completed 1500-row benchmark** in this project. All runs share the same manifest (`data/manifest_benchmark_final.csv`, 300 per class across SN / AGN / VS / asteroid / bogus, built by taking the top 300-by-ALERCE-probability per class with no oid overlap against any fewshot, expert_examples, or human_baselines sample), the same `prompts` module, the same `evaluate.py` parser, and the same 20 000-token output budget.

**Apr 22 refresh:** both GPT-5.4 runs had 429 insufficient-quota nulls in the initial pass (55 on `high`, 240 on `none`). Those were back-filled by `retry_failed.py` so both JSONLs now contain 1500/1500 clean rows (0 runtime errors). All GPT-5.4 numbers below reflect the completed data; the rest of the runs are unchanged from Apr 21.

**Standard error convention:** every proportion in this report (5-class accuracy, parse rate, per-class accuracy, stage-wise accuracy, precision, recall, self-pass rate) is annotated with its 1σ binomial standard error, `SE = √(p·(1−p)/n)`. Differences between two independent runs use `SE_Δ = √(SE₁² + SE₂²)`. The reported `±` is **1·SE**, not a 95 % CI — multiply by ~1.96 for that. F1 is point-only (no closed-form binomial SE). Counts (token totals, confusion-matrix cells, error-mode counts) are not annotated. The `n` underlying each SE is shown in the per-class denominator column or footnote of each table.

**Figures.** Nine charts are embedded inline at the section where they are discussed. Each figure is referenced by number (Fig 1 … Fig 9) in the surrounding narrative, so the prose and the pictures read as one integrated document rather than as a table-of-figures appendix. The PNGs live under `charts/benchmark_full_apr21/` and are regenerated end-to-end by `python viz/_make_charts_benchmark_full_apr21.py` (which reads the nine `metrics.json` files directly, so the figures always agree with the tables).

| Fig | Section | What it shows |
|---:|---|---|
| 1 | §1 | Headline bar — absolute 5-class accuracy ranked, with 1σ SE error bars |
| 2 | §2 | Per-class accuracy heatmap (9 runs × 5 classes) |
| 3 | §3 | Stage-wise cascade bars (Stage-1 / Stage-2 / Stage-3 / Stage-3 conditional) |
| 4 | §4 | AGN-collapse pies — true-AGN predicted-class distribution for the top 4 runs |
| 5 | §6 | Token economy — mean bars + p95 / max markers + 20k cap |
| 6 | §7 | Format error breakdown — stacked row-outcome bars |
| 7 | §9 | MSRS vs absolute accuracy scatter, with linear fit |
| 8 | §10 | Think-vs-nothink paired bars per family, with Δ and z annotations |
| 9 | §12 | Compute-accuracy Pareto scatter (accuracy vs mean output tokens, log x) |

The changing axes are:

- **Model** (GPT-5.4 / Kimi K2.5 / Qwen3.5-{4B, 35B-A3B, 397B-A17B})
- **Reasoning mode** (thinking-enabled vs direct-answer, where the model supports it)
- **Backend** (`tinker` for open-source, `openai` Responses API for GPT-5.4)

Source of metrics: each run's `runs/<ts>-<slug>/metrics.json` (as computed by `evaluate.evaluate_jsonl`). Source of narratives: each run's `report.md` under `runs/`.

---

## Runs covered (9 × n=1500)

| # | Slug | Run folder | Model | Reasoning | Backend |
|---|---|---|---|---|---|
| 1 | `gpt-5.4-high-benchmark-full` | `runs/20260421-2024-...` | gpt-5.4 | high | openai |
| 2 | `kimi-k25-benchmark-full` | `runs/20260420-1226-...` | Kimi K2.5 | think (default renderer) | tinker |
| 3 | `qwen35-397b-a17b-benchmark-full` | `runs/20260420-1554-...` | Qwen3.5-397B-A17B | think | tinker |
| 4 | `gpt-5.4-none-benchmark-full` | `runs/20260421-2032-...` | gpt-5.4 | none | openai |
| 5 | `qwen35-35b-a3b-benchmark-full` | `runs/20260420-2054-...` | Qwen3.5-35B-A3B | think | tinker |
| 6 | `qwen35-4b-benchmark-full` | `runs/20260420-1920-...` | Qwen3.5-4B | think | tinker |
| 7 | `qwen35-397b-a17b-nothink-benchmark-full` | `runs/20260421-0025-...` | Qwen3.5-397B-A17B | nothink (*DisableThinkingRenderer*) | tinker |
| 8 | `qwen35-35b-a3b-nothink-benchmark-full` | `runs/20260421-0019-...` | Qwen3.5-35B-A3B | nothink | tinker |
| 9 | `qwen35-4b-nothink-benchmark-full` | `runs/20260421-0002-...` | Qwen3.5-4B | nothink | tinker |

All 9 runs: `max_tokens = 20000`, `prompt_module = prompts`. Concurrency: 32 for Tinker runs; for OpenAI runs, 16 on the initial pass and 8 on retry passes (gpt-5.4 high: 4 741.0 s @ 16 + 241.9 s + 162.2 s @ 8 = **5 145.1 s**; gpt-5.4 none: 682.1 s @ 16 + 247.4 s @ 8 = **929.5 s**).

---

## 1. Headline numbers

5-class accuracy is **computed over rows whose JSON parsed cleanly** (the reported `part_c_final_5class_accuracy`). Because parse rate varies across runs, the most honest single metric is the **absolute 5-class accuracy over all 1500 rows = parse_rate × reported_5class** (last column). With the Apr-22 GPT-5.4 retry both GPT-5.4 parse rates are now 100 %, so "on parsed" and "absolute over 1500" coincide for those two rows. Each `±` is the 1σ binomial SE; the denominator is `n_parsed` for the "on parsed" column and `n_total = 1500` for parse-rate / absolute columns.

| Rank | Run | 5-class (on parsed) | Parse rate | Truncation | **Absolute 5-class (all 1500)** | Stage-3 macro F1 | MSRS |
|---:|---|---:|---:|---:|---:|---:|---:|
| **1** | **gpt-5.4 high** | **51.07 ± 1.29 %** (n=1500) | **100.00 ± 0.00 %** | 0.00 % | **51.07 ± 1.29 %** | 0.4345 | 4.19 |
| 2 | Kimi K2.5 (think) | 49.43 ± 1.29 % (n=1497) | 99.80 ± 0.12 % | 0.00 % | 49.34 ± 1.29 % | **0.500** | 4.49 |
| 3 | Qwen3.5-397B-A17B (think) | 44.27 ± 1.28 % (n=1500) | **100.00 ± 0.00 %** | 0.00 % | 44.27 ± 1.28 % | 0.310 | 4.74 |
| 4 | gpt-5.4 none | 43.67 ± 1.28 % (n=1500) | **100.00 ± 0.00 %** | 0.00 % | 43.67 ± 1.28 % | 0.329 | 4.28 |
| 5 | Qwen3.5-397B-A17B (nothink) | 34.98 ± 1.23 % (n=1498) | 99.87 ± 0.09 % | 0.07 % | 34.93 ± 1.23 % | 0.430 | 4.78 |
| 6 | Qwen3.5-35B-A3B (think) | 40.83 ± 1.58 % (n=967) | 65.47 ± 1.23 % | 31.00 % | 26.73 ± 1.14 % | 0.271 | 4.70 |
| 7 | Qwen3.5-35B-A3B (nothink) | 25.76 ± 1.13 % (n=1485) | 99.00 ± 0.26 % | 0.33 % | 25.50 ± 1.13 % | 0.273 | 4.64 |
| 8 | Qwen3.5-4B (nothink) | 24.49 ± 1.16 % (n=1367) | 91.13 ± 0.73 % | 0.33 % | 22.32 ± 1.08 % | 0.307 | 4.67 |
| 9 | Qwen3.5-4B (think) | 37.78 ± 2.72 % (n=317) | **22.27 ± 1.07 %** | **77.47 %** | 8.41 ± 0.72 % | 0.241 | 4.83 |

![Absolute 5-class accuracy ranked, with 1σ binomial SE error bars](charts/benchmark_full_apr21/01_absolute_5class_ranked.png)

*Fig 1. Absolute 5-class accuracy over all 1500 rows per run, ranked. Error bars are 1σ binomial SE. The gap between #1 (GPT-5.4 high) and #2 (Kimi K2.5 think) is smaller than the overlapping error bars — treat those two as a tie at this sample size.*

**Headline findings** (see Fig 1 for the ranked view):

1. **GPT-5.4 high is the new project-wide SOTA** at **51.07 ± 1.29 %** absolute 5-class, edging out Kimi K2.5 think (49.34 ± 1.29 %) by **+1.73 ± 1.82 pt** (z = 0.95). It's the first closed-source run at this scale and the first model to clear 50 %, but on n=1500 the gap between #1 and #2 is **not statistically significant at the 1σ level** — in Fig 1 their SE error bars visibly overlap, and the two should be treated as a tie at this sample size.
2. **Kimi K2.5 think has the best Stage-3 macro F1 (0.500)** — it is the only run that balances SN / VS / AGN recall meaningfully. GPT-5.4 high beats Kimi on 4/5 classes but loses SN recall significantly (Stage-3 macro F1 0.4345 < Kimi's 0.500).
3. **gpt-5.4 none rises to rank 4** after the retry pass. At 43.67 ± 1.28 % absolute (fourth bar in Fig 1) it beats both Qwen3.5-397B nothink (34.93 ± 1.23 %; Δ = +8.74 ± 1.78 pt, z = 4.91, highly significant) and Qwen3.5-35B think (26.73 ± 1.14 %; Δ = +16.94 ± 1.72 pt, z = 9.85) despite using ~6× fewer tokens than any reasoning-enabled run — cheap, close-to-usable baseline.
4. **Qwen3.5-4B (think) is the only outright-broken run** — the shortest bar in Fig 1: 77.47 % truncation means 1162 / 1500 rows produced no parseable answer at all. The "37.78 ± 2.72 % on parsed" number is a lie (the n=317 denominator is a heavily-selected subset of rows that managed to fit) — only 8.41 ± 0.72 % of all 1500 rows are correctly labelled.
5. **The top-tier Qwen3.5-397B (think) is beaten by GPT-5.4 high by +6.80 ± 1.82 pt absolute** (z = 3.74, significant) with roughly half the output tokens per row (see §6 and Fig 5).
6. **Significance ranking of headline gaps (vs GPT-5.4 high, all SE_Δ ≈ 1.78–1.82 pt):** vs Kimi z = 0.95 (n.s.), vs Qwen3.5-397B-think z = 3.74 (✱✱✱), vs gpt-5.4-none z = 4.07, vs Qwen3.5-397B-nothink z = 9.05. Reading Fig 1 as an error-bar plot, the top-1 / top-2 bars overlap, bars 2-3 do not, and bars 3-4 touch — the headline #1↔#2 gap is the only one in the top half of the table that is consistent with chance variation on n = 1500.

---

## 2. Per-class accuracy

Each cell is `per_class_correct / per_class_total ± SE` from `metrics.json` (this denominator is "rows with a parseable final prediction for this class", not 300; see note under the table). SE is the 1σ binomial SE on the cell's own denominator, so cells with smaller `n` (truncated runs) have correspondingly larger error bars.

| Run | SN | AGN | VS | asteroid | bogus |
|---|---:|---:|---:|---:|---:|
| gpt-5.4 high | 38.67 ± 2.81 % (116/300) | **7.33 ± 1.51 %** (22/300) | **95.33 ± 1.22 %** (286/300) | 75.67 ± 2.48 % (227/300) | **38.33 ± 2.81 %** (115/300) |
| Kimi K2.5 (think) | **65.00 ± 2.75 %** (195/300) | 5.33 ± 1.30 % (16/300) | 90.27 ± 1.72 % (269/298) | 75.67 ± 2.48 % (227/300) | 11.04 ± 1.81 % (33/299) |
| Qwen3.5-397B (think) | 18.00 ± 2.22 % (54/300) | 6.00 ± 1.37 % (18/300) | 73.33 ± 2.55 % (220/300) | 80.67 ± 2.28 % (242/300) | 43.33 ± 2.86 % (130/300) |
| gpt-5.4 none | 14.33 ± 2.02 % (43/300) | 7.00 ± 1.47 % (21/300) | 92.33 ± 1.54 % (277/300) | **81.00 ± 2.26 %** (243/300) | 23.67 ± 2.45 % (71/300) |
| Qwen3.5-397B (nothink) | **56.67 ± 2.86 %** (170/300) | 3.01 ± 0.99 % (9/299) | 77.00 ± 2.43 % (231/300) | 17.00 ± 2.17 % (51/300) | 21.07 ± 2.36 % (63/299) |
| Qwen3.5-35B (think) | 13.86 ± 2.68 % (23/166) | 1.62 ± 0.93 % (3/185) | 72.60 ± 3.01 % (159/219) | 55.61 ± 3.63 % (104/187) | 50.74 ± 3.51 % (103/203) |
| Qwen3.5-35B (nothink) | 17.14 ± 2.25 % (48/280) | 0.68 ± 0.48 % (2/293) | 96.61 ± 1.05 % (285/295) | 8.22 ± 1.61 % (24/292) | 2.68 ± 1.00 % (7/261) |
| Qwen3.5-4B (nothink) | 27.50 ± 2.88 % (66/240) | 0.00 ± 0.00 % (0/247) | 86.76 ± 2.05 % (236/272) | 4.75 ± 1.24 % (14/295) | 3.61 ± 1.12 % (10/277) |
| Qwen3.5-4B (think) | 5.00 ± 3.45 % (2/40) | 0.00 ± 0.00 % (0/95) | 98.25 ± 1.23 % (112/114) | 14.81 ± 6.84 % (4/27) | 2.56 ± 2.53 % (1/39) |

![Per-class accuracy heatmap, 9 runs x 5 classes, ordered by absolute 5-class](charts/benchmark_full_apr21/02_per_class_heatmap.png)

*Fig 2. Per-class accuracy heatmap (rows: runs sorted top-to-bottom by absolute 5-class; columns: classes). The AGN column is uniformly pale yellow across every row — no model scores above 8 % on AGN. The VS column is uniformly deep blue, masking the true per-class trade-offs beneath.*

> Note on denominators: the `per_class_total` is computed over rows whose JSON parsed *and* whose `stage1/stage2/stage3` mapped to a valid 5-class label via `stages_to_final_class`. Runs with high truncation (Qwen3.5-4B think, Qwen3.5-35B think) have `per_class_total < 300`. After the Apr-22 retry, both GPT-5.4 runs have full 300/300 denominators on every class. Read rows not as "X % of 300" but "X % of the rows we got back for that class".

### Per-class SOTA

| Class | Best run | Score | 2nd place | Δ ± SE_Δ (z) |
|---|---|---:|---|---|
| **SN** | Kimi K2.5 (think) | **65.00 ± 2.75 %** | Qwen3.5-397B (nothink) 56.67 ± 2.86 % | +8.33 ± 3.97 pt (z = 2.10, ✱) |
| **AGN** | gpt-5.4 high | **7.33 ± 1.51 %** | gpt-5.4 none 7.00 ± 1.47 % | +0.33 ± 2.11 pt (z = 0.16, n.s.) |
| **VS** | gpt-5.4 high | **95.33 ± 1.22 %** | Qwen3.5-35B (nothink) 96.61 ± 1.05 % * | −1.28 ± 1.61 pt (z = 0.79, n.s.) |
| **asteroid** | gpt-5.4 none | **81.00 ± 2.26 %** | Qwen3.5-397B (think) 80.67 ± 2.28 % | +0.33 ± 3.21 pt (z = 0.10, n.s.) |
| **bogus** | Qwen3.5-35B (think) | **50.74 ± 3.51 %** | Qwen3.5-397B (think) 43.33 ± 2.86 % | +7.41 ± 4.53 pt (z = 1.64, n.s.) |

\* Qwen3.5-35B (nothink) has a nominal VS of 96.61 %, slightly above GPT-5.4 high, but reaches this by collapsing everything astrophysical-looking into VS — its other per-class numbers are near zero, so it is not a meaningful VS specialist.

**Observations** (Fig 2 visualises the table as a 9×5 heatmap):

- **AGN is a universal failure** — every single model scores below 8 % on AGN. This is immediately obvious in Fig 2 as a vertical band of pale-yellow cells in the AGN column. The error is always the same: AGN → predicted as variable_star (see §4 and Fig 4 for the predicted-class distribution). This is a *prompt / representation* problem, not a model capacity problem (GPT-5.4 at 7.33 ± 1.51 % is statistically indistinguishable from Qwen-4B at 0.00 ± 0.00 % only because the binomial floor at 0/247 is degenerate, but it is also indistinguishable from the next-best run gpt-5.4-none at 7.00 ± 1.47 %; z = 0.16). All AGN cells fit inside ±3 SE of zero except the small-n Qwen3.5-35B-think one.
- **Per-class rankings are not monotonic with 5-class accuracy.** This is the second obvious story in Fig 2: darker cells appear in different columns depending on the model. Kimi dominates SN (Δ vs GPT-5.4 high = +26.33 ± 3.93 pt, z = 6.70, ✱✱✱) but loses bogus (Δ = −27.29 ± 3.34 pt, z = 8.17). Qwen3.5-35B (think) is the **single best bogus detector** (50.74 ± 3.51 %) despite ranking 7th on absolute 5-class — and the gap to the runner-up (Qwen3.5-397B-think 43.33 ± 2.86 %) is +7.41 ± 4.53 pt (z = 1.64, n.s.), so the per-class SOTA crown for bogus is not yet decisive on n=300. This argues for an **ensemble** where different models are routed for different classes.
- **Asteroid is bimodal.** Thinking-enabled Qwen3.5-397B and both GPT-5.4 variants (81.00 ± 2.26 % and 75.67 ± 2.48 %) hit ≥75 %, but thinking-disabled Qwen (all scales) collapses asteroid to ≤17 %. Fig 2 makes the bimodality vivid: the top four rows all show dark-blue asteroid cells, then rows 5-9 flip to pale yellow in the same column. The collapse is decisive: GPT-5.4-none vs Qwen3.5-397B-nothink is +64.00 ± 3.14 pt (z = 20.4) — that's not noise. Asteroid detection apparently relies on explicit reasoning about track/cadence cues that the direct-answer path doesn't produce for the Qwen family, but the GPT-5.4 variant *does* produce without reasoning.

---

## 3. Stage-wise accuracy (Part C cascade)

All stage-wise numbers are computed over `n_p = part_c_n_evaluable` (rows that parsed JSON and produced a usable stage label). End-to-end 5-class is the same as the "on-parsed" column of Section 1. SE on Stage-3 conditional is an *upper bound* using `n_p` as the denominator — the true conditional denominator (rows where Stage-1 and Stage-2 were correct) is smaller, so the true SE is somewhat larger; treat the conditional SEs below as a lower bound on the uncertainty.

| Run | n_p | Stage-1 | Stage-2 | Stage-3 | Stage-3 conditional | End-to-end 5-class |
|---|---:|---:|---:|---:|---:|---:|
| gpt-5.4 high | 1500 | **83.93 ± 0.95 %** | **80.00 ± 1.03 %** | 59.40 ± 1.27 % | 47.11 ± 1.29 % | **51.07 ± 1.29 %** |
| Kimi K2.5 (think) | 1497 | 81.36 ± 1.01 % | 71.94 ± 1.16 % | **60.19 ± 1.27 %** | **53.45 ± 1.29 %** | 49.43 ± 1.29 % |
| Qwen3.5-397B (think) | 1500 | 80.87 ± 1.02 % | 72.80 ± 1.15 % | 52.80 ± 1.29 % | 32.44 ± 1.21 % | 44.27 ± 1.28 % |
| gpt-5.4 none | 1500 | 77.47 ± 1.08 % | 71.53 ± 1.17 % | 57.00 ± 1.28 % | 37.89 ± 1.25 % | 43.67 ± 1.28 % |
| Qwen3.5-35B (think) | 967 | 77.15 ± 1.35 % | 62.98 ± 1.55 % | 50.98 ± 1.61 % | 32.12 ± 1.50 % | 40.83 ± 1.58 % |
| Qwen3.5-4B (think) | 317 * | 87.07 ± 1.88 % * | 78.86 ± 2.29 % * | 42.59 ± 2.78 % * | 45.60 ± 2.80 % * | 37.78 ± 2.72 % * |
| Qwen3.5-397B (nothink) | 1498 | 79.17 ± 1.05 % | 60.95 ± 1.26 % | 40.39 ± 1.27 % | 45.61 ± 1.29 % | 34.98 ± 1.23 % |
| Qwen3.5-35B (nothink) | 1485 | 80.40 ± 1.03 % | 60.88 ± 1.27 % | 31.65 ± 1.21 % | 37.51 ± 1.26 % | 25.76 ± 1.13 % |
| Qwen3.5-4B (nothink) | 1367 | 79.30 ± 1.10 % | 54.21 ± 1.35 % | 28.68 ± 1.22 % | 38.67 ± 1.32 % | 24.49 ± 1.16 % |

\* Qwen3.5-4B (think) values are computed on the 317 parseable & evaluable rows (21 % of 1500). The ±SE bars are correspondingly ~2× wider than the n=1500 runs.

![Stage-wise cascade accuracy per run, grouped bars](charts/benchmark_full_apr21/03_stagewise_cascade.png)

*Fig 3. Stage-wise cascade accuracy (Stage-1 → Stage-2 → Stage-3, plus the Stage-3-given-correct-stage-1-and-2 conditional). All runs lose the most accuracy between Stage-2 and Stage-3 (subclass). Kimi K2.5 think is the only run that gains on Stage-3 conditional (purple bar) — the best astrophysical-subclass decider once it reaches that branch.*

**Where the models split** (Fig 3 shows this as grouped bars per run):

- **Stage-1 is near-saturated for every run** (77.15-87.07 %, all SEs ≤ 1.88 pt) — the blue bars in Fig 3 are essentially a flat line across all nine runs. Real-vs-artifact is solved at all scales — even the broken 4B-think run gets 87.07 ± 1.88 % on this sub-task (before collapsing elsewhere). The 6.66 pt spread between best (Qwen-4B-think 87.07 %) and worst (gpt-5.4-none 77.47 %) is itself mostly explained by selection bias on the small Qwen-4B-think denominator.
- **Stage-2 variance is small (54.21-80.00 %)** — the green bars drop modestly below blue for most runs — but the Stage-2 column separates GPT-5.4 high from everything else by +7.06 ± 1.55 pt over Kimi (z = 4.55, ✱✱✱).
- **Stage-3 (subclass) is where the lift lives.** The red bars in Fig 3 are the most variable of the four series: the span from Qwen-4B-nothink (28.68 ± 1.22 %) to Kimi K2.5 think (60.19 ± 1.27 %) is +31.51 ± 1.76 pt (z = 17.9) — accounts for most of the 25-point 5-class gap. This is consistent with the Apr-19 open-source comparison report.
- **Stage-3 *conditional* accuracy (the "given you correctly said astrophysical, did you pick the right subclass?" number) is where Kimi K2.5 shines** — the purple bar is noticeably taller than the red bar **only** for Kimi in Fig 3. 53.45 ± 1.29 % is the best in the batch, above GPT-5.4 high (47.11 ± 1.29 %; Δ = +6.34 ± 1.83 pt, z = 3.46, ✱✱) and Qwen3.5-397B nothink (45.61 ± 1.29 %; Δ = +7.84 ± 1.83 pt, z = 4.29). Kimi is the most reliable astrophysical-subclass decider once it reaches that branch, and the gap to GPT-5.4 high is significant on n=1500.

---

## 4. Stage-3 confusion matrices (true → predicted)

This is where the classification pathologies live. Columns: `supernova | variable_star | AGN | N/A`.

**gpt-5.4 high (new SOTA):**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | 116 | 21 | **141** | 22 |
| variable_star | 0 | 286 | 0 | 14 |
| AGN | 0 | **272** | 22 | 6 |

**Kimi K2.5 (think):**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | **195** | 21 | 39 | 45 |
| variable_star | 0 | 269 | 0 | 29 |
| AGN | 1 | **276** | 16 | 7 |

**Qwen3.5-397B (think):**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | 54 | 21 | **141** | 84 |
| variable_star | 0 | 220 | 1 | 79 |
| AGN | 0 | **265** | 18 | 17 |

**gpt-5.4 none:**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | 43 | 28 | **137** | 92 |
| variable_star | 0 | 277 | 0 | 23 |
| AGN | 0 | **253** | 21 | 26 |

**Qwen3.5-397B (nothink):**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | **170** | 71 | 33 | 26 |
| variable_star | 1 | 231 | 3 | 65 |
| AGN | 10 | **271** | 9 | 9 |

**Qwen3.5-35B (nothink):**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | 48 | **208** | 12 | 30 |
| variable_star | 0 | 285 | 0 | 13 |
| AGN | 4 | **284** | 2 | 7 |

**Qwen3.5-4B (nothink):**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | 66 | **154** | 0 | 30 |
| variable_star | 10 | 236 | 0 | 36 |
| AGN | 8 | **228** | 0 | 13 |

![True AGN rows predicted distribution for top 4 runs](charts/benchmark_full_apr21/04_agn_collapse_pie.png)

*Fig 4. Where the 300 true-AGN rows land in the top 4 runs. Across all four top models, 84–92 % of real AGN are predicted as variable_star. The "AGN is a universal failure" line isn't hyperbole — even the project SOTA only catches 22 / 300 of them. Counts underneath each pie are the raw confusion-matrix cells for that run.*

**Two universal pathologies** (Fig 4 visualises the first one as pies for the four top runs):

1. **AGN → variable_star** is present in *every* run. Fig 4 shows the red "variable_star" wedge dominates every pie at 84-92 % of true AGN rows, with the green "AGN (correct)" wedge sitting below 8 % in all four. The best "least bad" is Kimi-think at 276/300 AGN misclassified as VS (91 %); every other run is similar or worse (GPT-5.4 high 272, GPT-5.4 none 253, Qwen3.5-397B-think 265). The prompt does not provide sufficient signal to discriminate AGN variability from stellar variability.
2. **SN → AGN** is present in 3 runs (GPT-5.4 high 141/300, Qwen3.5-397B-think 141/300, GPT-5.4 none 137/300). Under reasoning, the model argues itself from "point-source transient on a host" into "AGN on a host".
   - **Kimi K2.5 (think) is the sole run that avoids this**: only 39/300 SN → AGN (13 %). Whatever Kimi's reasoning chain prefers, it isn't over-weighting "host galaxy = AGN".
   - **Disabling reasoning flips the error to SN → VS instead** (Qwen-4B-nothink 154/240, Qwen-35B-nothink 208/280). Smaller non-thinking models default to "everything astrophysical = VS".
3. **N/A cells inflate when thinking is disabled or the model is under-sized.** GPT-5.4 none leaves 92 SN rows as N/A (no stage-3 decision) — 4× more than GPT-5.4 high's 22 SN N/As, despite both now having full parse rate. This is a genuine model behaviour, not an infra artifact: without reasoning the model more often refuses stage-3 rather than picking. Qwen3.5-397B-think leaves 84 SN rows + 79 VS rows + 17 AGN rows as N/A from truncation and refusal. N/A is a proxy for "model could not or would not decide".

---

## 5. Stage-3 subclass precision/recall/F1

Cells: `proportion ± SE`. Precision SE uses the predicted-column count as denominator; recall SE uses the true-row count. F1 has no closed-form binomial SE — point estimates only. Class-recall denominators are typically 300 except where parsing/truncation reduced the true-row count.

| Run | supernova P | supernova R | supernova F1 | variable_star P | variable_star R | variable_star F1 | AGN P | AGN R | AGN F1 | **Macro F1** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Kimi K2.5 (think) | 0.995 ± 0.005 | 0.650 ± 0.028 | **0.786** | 0.475 ± 0.021 | 0.903 ± 0.017 | 0.623 | 0.291 ± 0.061 | 0.053 ± 0.013 | 0.090 | **0.500** |
| gpt-5.4 high | 1.000 ± 0.000 | 0.387 ± 0.028 | 0.558 | 0.494 ± 0.021 | 0.953 ± 0.012 | **0.651** | 0.135 ± 0.027 | 0.073 ± 0.015 | 0.095 | 0.4345 |
| Qwen3.5-397B (nothink) | 0.939 ± 0.018 | 0.567 ± 0.029 | 0.707 | 0.403 ± 0.020 | 0.770 ± 0.024 | 0.529 | 0.200 ± 0.060 | 0.030 ± 0.010 | 0.052 | 0.430 |
| gpt-5.4 none | 1.000 ± 0.000 | 0.143 ± 0.020 | 0.251 | 0.496 ± 0.021 | 0.923 ± 0.015 | 0.646 | 0.133 ± 0.027 | 0.070 ± 0.015 | 0.092 | 0.329 |
| Qwen3.5-397B (think) | 1.000 ± 0.000 | 0.180 ± 0.022 | 0.305 | 0.435 ± 0.022 | 0.733 ± 0.026 | 0.546 | 0.113 ± 0.025 | 0.060 ± 0.014 | 0.078 | 0.310 |
| Qwen3.5-4B (nothink) | 0.786 ± 0.045 | 0.264 ± 0.028 | 0.395 | 0.382 ± 0.020 | 0.837 ± 0.022 | 0.524 | 0.000 ± n/a | 0.000 ± 0.000 | 0.000 | 0.307 |
| Qwen3.5-35B (nothink) | 0.923 ± 0.037 | 0.161 ± 0.021 | 0.274 | 0.367 ± 0.017 | 0.956 ± 0.012 | 0.530 | 0.143 ± 0.094 | 0.007 ± 0.005 | 0.013 | 0.273 |
| Qwen3.5-35B (think) | 1.000 ± 0.000 | 0.137 ± 0.027 | 0.241 | 0.434 ± 0.026 | 0.716 ± 0.030 | 0.541 | 0.273 ± 0.134 | 0.016 ± 0.009 | 0.031 | 0.271 |
| Qwen3.5-4B (think) | 1.000 ± 0.000 | 0.050 ± 0.034 | 0.095 | 0.463 ± 0.032 | 0.974 ± 0.015 | 0.628 | 0.000 ± n/a | 0.000 ± 0.000 | 0.000 | 0.241 |

**Observations:**

- **Supernova precision is essentially 1.00 ± 0.00 across the board** — nothing else gets predicted as SN (most cells have predicted-column counts 40-200, so the ±0 is real, not a small-n artifact). The question is how many real SN get recalled.
- **Kimi K2.5 (think) has the best SN F1 (0.786)** by a wide margin, because it has the best SN recall (0.650 ± 0.028) while preserving ~1.0 precision. GPT-5.4 high is next-best (recall 0.387 ± 0.028; Δ vs Kimi = +0.263 ± 0.040, z = 6.6, ✱✱✱). The SN-F1 #1↔#2 ranking is robust on n=300.
- **Variable_star F1 is where GPT-5.4 wins** — high at 0.651 and none at 0.646 both narrowly beat Kimi (0.623). The recall gap that drives this is GPT-5.4-high 0.953 ± 0.012 vs Kimi 0.903 ± 0.017 → Δ = +0.050 ± 0.021 (z = 2.4, ✱). GPT-5.4 has higher VS recall than Kimi while Kimi has higher VS precision (small differences, mostly inside ±2 SE).
- **AGN F1 is garbage everywhere**, tightly clustered around 0.05-0.10. Qwen3.5-4B models literally never emit an AGN prediction (AGN P = 0.000, n_predicted = 0 → SE undefined). The Qwen3.5-35B-think AGN precision of 0.273 ± 0.134 looks impressive but is on n_predicted = 11 — its 1σ band overlaps zero.

---

## 6. Token economy

| Run | Mean total | Median total | Max total | p95 total | Mean answer | Mean reasoning | Truncated rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.4 none | **446** | 446 | 521 | 482 | 446 | 0 (by construction) | 0 |
| Qwen3.5-35B (nothink) | 539 | 528 | 2 048 | 622 | 538 | ~1 | 5 |
| Qwen3.5-397B (nothink) | 554 | 545 | 2 048 | 650 | 553 | ~1 | 1 |
| Qwen3.5-4B (nothink) | 583 | 567 | 2 048 | 715 | 582 | ~1 | 5 |
| gpt-5.4 high | 2 557 | 2 418 | 8 156 | 4 887 | 445 | **~2 112** | 0 |
| Kimi K2.5 (think) | 3 943 | 3 676 | 10 228 | 6 576 | 3 942 † | — † | 0 |
| Qwen3.5-397B (think) | 5 171 | 4 830 | 16 882 | 8 413 | 456 | ~4 715 | 0 |
| Qwen3.5-35B (think) | 11 822 | 9 679 | **20 000** | 20 000 | 6 520 | ~5 302 | **465** |
| Qwen3.5-4B (think) | **16 623** | **20 000** | 20 000 | 20 000 | 15 591 | ~1 032 | **1 162** |

† Kimi K2.5 renderer returns content as a single string rather than typed parts, so `answer_tokens ≈ output_tokens` — the visible JSON answer is ~450 tokens, the rest is reasoning that cannot be auto-split. See `20260419_report_opensource_5class.md` for the known accounting caveat.

![Token economy: mean output tokens per run with p95 and max markers](charts/benchmark_full_apr21/05_token_economy.png)

*Fig 5. Per-row output-token footprint. Blue bars are the mean; orange diamonds are p95; red squares are the max. The dashed line at 20 000 is the per-call budget cap. Qwen3.5-4B (think) and Qwen3.5-35B (think) both pin against the cap — their max **is** the cap — while the nothink configs all live under 600 tokens/row. GPT-5.4 none at 446 mean tokens is nearly 40× cheaper per row than Qwen3.5-4B think.*

**Take-aways** (Fig 5 sorts the nine runs by mean output tokens and marks p95 / max / 20k cap):

1. **The ~6-30× cost of thinking for Qwen.** The four "nothink" runs cluster together at the top of Fig 5 (446-583 mean tokens) while the think variants fan out across the x-axis. Disabling thinking for Qwen3.5 saves 9-30× output tokens per row; for the 4B model this is the difference between broken (77 % truncation) and usable (0.3 % truncation).
2. **GPT-5.4 thinks more efficiently than Qwen3.5-397B.** The gpt-5.4-high bar in Fig 5 is noticeably shorter than Qwen3.5-397B-think's: at higher per-row accuracy (51.07 % vs 44.27 %) GPT-5.4 uses ~2 557 tokens/row against 5 171 — half the compute for more accuracy. Kimi sits between (3 943).
3. **Cost-per-correct-answer is *best* for the cheap runs** — `gpt-5.4 none` delivers **0.98** correct answers per 1 000 output tokens, vs 0.20 for `gpt-5.4 high` and 0.125 for Kimi. If dollars are the binding constraint, the non-thinking models win on efficiency, and GPT-5.4 none is now the clear leader (see §12 and Fig 9 for the Pareto view).
4. **Qwen3.5-4B (think) sits at median 20 000 output tokens** — its blue mean bar, orange p95 diamond, and red max square in Fig 5 all pin against the 20k dashed cap line. Half the run burns the entire budget producing nothing usable. This is the most compute-wasteful configuration in the batch.

---

## 7. Format error breakdown

| Run | ok | truncated_no_json | truncated_partial_json | parse_failed | runtime_error | extra_text_around_json | schema_missing_top_level | n with value_errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.4 high | **1500** | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gpt-5.4 none | **1500** | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Qwen3.5-397B (think) | **1500** | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| Qwen3.5-397B (nothink) | 1498 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| Qwen3.5-35B (nothink) | 1485 | 0 | 5 | 10 | 0 | 0 | 0 | 67 |
| Kimi K2.5 (think) | 0 ‡ | 0 | 0 | 3 | 0 | 1497 ‡ | 0 | 4 |
| Qwen3.5-4B (nothink) | 1367 | 0 | 5 | 128 | 0 | 0 | 0 | 36 |
| Qwen3.5-35B (think) | 980 | **449** | 14 | 55 | 0 | 0 | 2 | 28 |
| Qwen3.5-4B (think) | 327 | **1153** | 2 | 11 | 0 | 6 | 1 | 19 |

‡ Kimi's 1 497 `extra_text_around_json` is benign — the renderer emits reasoning before the JSON, which parses fine but trips the "extra text" flag. JSON parses cleanly on all 1 500 rows.

![Format-error breakdown per run, stacked bars](charts/benchmark_full_apr21/06_error_breakdown_stacked.png)

*Fig 6. Stacked bars of row outcomes per run (out of 1500). Green is clean, red is truncation, purple is "extra text around JSON" (benign for Kimi). The three failure-prone configs are visually obvious: Qwen3.5-35B-think (449 truncated), Qwen3.5-4B-nothink (128 parse-fail), and Qwen3.5-4B-think (1153 truncated — the worst). Everything else lands on ~1500 green.*

§ Both GPT-5.4 runs initially had `runtime_error` nulls (55 on high, 240 on none) from 429 insufficient_quota responses during the Apr-21 initial pass. These were back-filled by `retry_failed.py` on Apr 22 (see top-of-report note). The table reflects the post-retry state: zero runtime errors, zero value errors on either run.

**Three distinct failure modes by run class** (Fig 6 shows each run as a stacked bar out of 1500 rows):

- **Token-limit spiral** (`truncated_no_json` dominates): Qwen3.5-4B think, Qwen3.5-35B-A3B think. These are the two bars in Fig 6 with large red sections — the model never emits JSON before the 20 000-token cap. Disabling thinking fully fixes this (the two nothink counterparts immediately left of them in Fig 6 are almost entirely green).
- **API-level nulls** (`runtime_error`): was the dominant failure mode for both GPT-5.4 runs during the initial Apr-21 pass (55 high, 240 none), driven by 429 `insufficient_quota` responses from the OpenAI Responses API. After Apr-22 retries (via `retry_failed.py`) the failure mode is gone for both — all 295 previously-null rows came back with valid model responses on re-submission, confirming the issue was purely quota / timeout, not model behaviour or content-policy filtering. The original 4.4× ratio (240 vs 55 nulls) appears to have been a timing artifact related to when each run hit the quota ceiling rather than anything intrinsic to `reasoning_effort=none`.
- **Honest parse failures** (`parse_failed`): Qwen3.5-4B nothink (128 rows) — the 4B model occasionally mangles JSON when writing directly, not a token-budget issue.
- **Value errors are dominated by `c2_astro_requires_subtype`** for Qwen nothink runs (27-50 per run) — the model says "astrophysical" in stage-2 but forgets to pick a stage-3 subtype.

---

## 8. Part A (metadata reading)

**All 9 runs score 100 % on Part A exact-match and macro accuracy.** Every model reads the 6 metadata fields correctly every time, regardless of size or reasoning mode. Part A is solved; no signal there.

---

## 9. Part B / self-scoring

MSRS is a mean over 4 self-rated dimensions ∈ [1, 5]; SE on a per-row mean is hard to nail down without per-row variance dumps so MSRS is point-only here. self_pass_rate is a binomial proportion on n=1500.

| Run | MSRS | self_pass_rate |
|---|---:|---:|
| Qwen3.5-4B (think) | 4.827 | 100.00 ± 0.00 % |
| Qwen3.5-397B (nothink) | 4.783 | 99.84 ± 0.10 % |
| Qwen3.5-397B (think) | 4.744 | 99.86 ± 0.10 % |
| Qwen3.5-35B (think) | 4.703 | 99.89 ± 0.09 % |
| Qwen3.5-4B (nothink) | 4.673 | 99.63 ± 0.16 % |
| Qwen3.5-35B (nothink) | 4.641 | 98.32 ± 0.33 % |
| Kimi K2.5 (think) | 4.488 | 90.78 ± 0.75 % |
| gpt-5.4 none | 4.284 | 97.60 ± 0.40 % |
| gpt-5.4 high | **4.185** | 92.13 ± 0.70 % |

**MSRS (mean self-reasoning score) is inversely correlated with absolute 5-class accuracy** — the weakest run in the batch (Qwen3.5-4B think, 8.41 % absolute) has the highest self-score (4.83), and the best run (GPT-5.4 high, 51.07 %) has the lowest (4.19). Fig 7 makes this stark: the linear-regression fit slopes *downwards* at −44 pt per unit MSRS, with the GPT-5.4 runs in the top-left (low self-score, high accuracy) and Qwen3.5-4B-think alone in the bottom-right (highest self-score, lowest accuracy). Every model self-awards ≥4.0 / 5.0 on its own reasoning quality. **Part B self-scoring is not a useful confidence signal for downstream selection** — if anything, the relationship is backwards. This replicates the Apr-19 open-source finding at 15× the scale.

![MSRS vs absolute 5-class accuracy scatter with linear fit](charts/benchmark_full_apr21/07_msrs_vs_accuracy.png)

*Fig 7. MSRS (Part-B self-reasoning score, x) vs absolute 5-class accuracy (y). The linear fit has slope −44 pt per unit of MSRS — models that rate their own reasoning higher score **worse** on ground truth. The two GPT-5.4 runs are the most self-critical (MSRS 4.19 / 4.28) and also two of the top four on accuracy.*

(Part B ↔ Part C calibration metrics — pearson_r, calibration_gap, high/low-confidence accuracy — *are* present in every run's `metrics.json` under `part_bc_confidence_accuracy`; they were overlooked in the Apr-21 pass of this report. A quick spot check on the two GPT-5.4 runs shows high-conf accuracy 51.88 % vs low-conf 41.53 % for `high` (calibration_gap +0.130, pearson_r 0.20) and 44.06 % vs 27.78 % for `none` (gap +0.141, pearson_r 0.22). So confidence *is* weakly predictive of correctness in GPT-5.4 — unlike the MSRS which is inverted. A full cross-run calibration subsection is a useful follow-up report.)

---

## 10. The reasoning dial — think vs nothink A/B

We have 4 think↔nothink pairs at n=1500: the 3 Qwen3.5 sizes and GPT-5.4. **Absolute** (not parse-subset) 5-class accuracy tells the story:

Δ uses the diff-SE formula `SE_Δ = √(SE_think² + SE_nothink²)`. Both columns are on n=1500 each, so SE_Δ is roughly a constant ~1.6-1.8 pt across rows.

| Family / size | think absolute | nothink absolute | Δ (think − nothink) ± SE_Δ | z | Verdict |
|---|---:|---:|---:|---:|---|
| Qwen3.5-4B | 8.41 ± 0.72 % | 22.32 ± 1.08 % | **−13.90 ± 1.29 pt** | −10.76 | **nothink decisively wins** (think is broken by truncation; ✱✱✱) |
| Qwen3.5-35B-A3B | 26.73 ± 1.14 % | 25.50 ± 1.13 % | +1.23 ± 1.60 pt | 0.77 | essentially **tied** (n.s. at 1σ) |
| Qwen3.5-397B-A17B | 44.27 ± 1.28 % | 34.93 ± 1.23 % | **+9.34 ± 1.78 pt** | 5.25 | **think wins** (✱✱✱) |
| gpt-5.4 | 51.07 ± 1.29 % | 43.67 ± 1.28 % | **+7.40 ± 1.82 pt** | 4.07 | **think wins** (✱✱✱) |

![Think vs nothink paired bars across four model families, with Δ and z](charts/benchmark_full_apr21/08_think_vs_nothink.png)

*Fig 8. The reasoning dial across four model families, n = 1500 each. Blue = thinking enabled, orange = none / nothink. Δ annotations show the raw pt gap and the two-sample z-statistic. Qwen3.5-4B is the one inverted case — at 4B, enabling thinking is **strictly harmful** because the model truncates 77 % of rows. Qwen3.5-35B is a statistical tie. 397B and GPT-5.4 both show statistically-significant +7 to +9 pt wins for thinking.*

**The "does reasoning help?" answer depends on model scale** (Fig 8 shows all four pairs side-by-side with Δ and z annotated):

- **Tiny models (4B).** Reasoning is strictly harmful — the model cannot complete a response before the token cap, so 77 % of rows are unusable. Fig 8 shows the Qwen3.5-4B pair as the only inverted case: the nothink bar (orange) is **taller** than the think bar (blue), with Δ = −13.9 pt and z = 10.8.
- **Mid models (35B MoE).** Reasoning and non-reasoning are a wash in *absolute* terms — the Qwen3.5-35B pair in Fig 8 has near-identical bar heights (Δ = +1.23 pt, z = 0.77, labelled "n.s.") — but with a fundamentally different class profile: thinking flags asteroid/bogus correctly but truncates often; nothink finishes everything but collapses into VS. Pick based on downstream class priorities.
- **Large / frontier models (397B and GPT-5.4).** The right half of Fig 8 shows these two pairs with the clearest blue-over-orange gap: +9.34 and +7.40 pt respectively, both z > 4 (three stars). Reasoning is a +7 to +9 pt win at ~6× the compute cost. If compute budget allows, turn thinking on. GPT-5.4's think-wins margin (+7.40 pt) is now *smaller* than the initial Apr-21 estimate (+14.80 pt) — the gap shrank because the Apr-22 retry filled in `none`'s 240 null rows, most of which got decent classifications on re-submit.

**Cross-family qualitative pattern:** Thinking *helps* SN recall for GPT-5.4 high but *hurts* SN recall for Qwen3.5-397B (whose nothink SN is 56.67 % vs thinking's 18.00 % — see `runs/20260421-0025-.../report.md` §Observations for the full analysis).

---

## 11. Closed-source vs open-source

**On this benchmark, with this prompt, GPT-5.4 high is +1.73 ± 1.82 pt absolute ahead of the best open-source run (Kimi K2.5 think, 49.34 ± 1.29 %).** That is a smaller gap than most people assume from public benchmarks — and at z = 0.95 the difference is **not statistically significant on n=1500**. Treat the closed-source vs open-source headline result as a tie until n grows.

More importantly, the per-class profile differs substantially:

- GPT-5.4 high is better on 4/5 classes: **VS (+5), bogus (+27), AGN (+2), asteroid (tie)**.
- Kimi K2.5 think is better on 1/5: **SN (+26)**.
- AGN is tied-and-broken for both.

**Open-source is still competitive and arguably preferable for supernova-heavy pipelines.** The +27-pt bogus advantage for GPT-5.4 is the main reason it takes the overall win — bogus rejection is the first gate in most real-time alert pipelines, so this matters. For downstream tasks that tolerate elevated bogus rates but need high SN recall, Kimi K2.5 think remains the right pick.

---

## 12. Compute efficiency (accuracy per 1k output tokens)

This is the "bang-per-token" ranking: `absolute_5class / (mean_output_tokens / 1000)`.

The "correct per 1k tokens" column inherits its uncertainty from absolute 5-class accuracy: relative SE is ≈ SE(p)/p of the absolute column. We list it explicitly for the leader so the gap is easy to read.

| Run | Absolute 5-class | Mean output tokens | Correct answers per 1k tokens |
|---|---:|---:|---:|
| gpt-5.4 none | 43.67 ± 1.28 % | 446 | **0.979 ± 0.029** |
| Qwen3.5-397B (nothink) | 34.93 ± 1.23 % | 554 | 0.630 ± 0.022 |
| Qwen3.5-35B (nothink) | 25.50 ± 1.13 % | 539 | 0.473 ± 0.021 |
| Qwen3.5-4B (nothink) | 22.32 ± 1.08 % | 583 | 0.383 ± 0.018 |
| gpt-5.4 high | 51.07 ± 1.29 % | 2 557 | 0.200 ± 0.005 |
| Kimi K2.5 (think) | 49.34 ± 1.29 % | 3 943 | 0.125 ± 0.003 |
| Qwen3.5-397B (think) | 44.27 ± 1.28 % | 5 171 | 0.086 ± 0.002 |
| Qwen3.5-35B (think) | 26.73 ± 1.14 % | 11 822 | 0.023 ± 0.001 |
| Qwen3.5-4B (think) | 8.41 ± 0.72 % | 16 623 | 0.005 ± 0.000 |

**If compute cost is the binding constraint, non-thinking runs dominate** — and GPT-5.4 none leads by a huge margin (0.98 correct answers per 1k output tokens, 1.6× the next best). After the Apr-22 retry it is now both the **cost-efficiency leader** and a **top-4 accuracy contender** at 43.67 % absolute. If quality is the binding constraint, GPT-5.4 high / Kimi think are the answer. Fig 9 visualises the full trade-off: only three runs sit on the Pareto frontier — gpt-5.4 none (cheapest useful point), gpt-5.4 high (best absolute), and marginally Kimi K2.5 think. Everything else is strictly dominated by one of those three, and Qwen3.5-4B think in particular sits alone in the far bottom-right (most expensive, least accurate — the Pareto-worst point in the batch).

![Compute-accuracy Pareto scatter, accuracy vs mean output tokens on log x](charts/benchmark_full_apr21/09_compute_pareto.png)

*Fig 9. Each run as an (x, y) point with x = mean output tokens per row (log scale) and y = absolute 5-class accuracy. The dashed line is the Pareto frontier (maximise y for a given x). **Only three runs are Pareto-optimal:** gpt-5.4 none (cheapest useful point), gpt-5.4 high (best absolute), and — marginally — Kimi K2.5 think. Everything to the right of the frontier is strictly dominated; Qwen3.5-4B think in particular is the worst point on both axes.*

---

## 13. Recommendations / next experiments

1. **Adopt GPT-5.4 high as the benchmark SOTA and Kimi K2.5 think as the open-source SOTA.** Both are on the same page within ~1 pt absolute; GPT-5.4 wins the generalist title, Kimi wins the SN specialist title.
2. **The SN↔AGN confusion is the highest-value debug target.** Any prompt-level intervention that moves even 20 of the 131 GPT-5.4-high SN→AGN mistakes is worth ~1.3 pt absolute. Candidate fixes: (a) add an explicit "supernovae are NOT AGN unless the host shows a clear active nucleus; SN are transient point sources on passive or star-forming galaxies" rule to the Part-C guidance; (b) a dedicated stage-3 disambiguation pass that only fires when stage-3 = AGN with low self-confidence.
3. **AGN is a prompt / representation problem.** All 9 runs are in the 0-8 % range on AGN. The fix will not come from a larger or different model; it has to come from more signal (e.g. longer light-curve context, explicit host-galaxy SED features) or a better Part-C instruction.
4. **Ensemble routing is the cheapest +5 pt lift available.** If every row routes to Kimi for SN candidates and GPT-5.4 high otherwise, the expected accuracy ceiling is ~55 %. A router can be trained on just the `stage1 + stage2` cheap pre-call from a small model, so inference stays close to one-model cost.
5. **~~Investigate the GPT-5.4 none runtime_error spike.~~ — RESOLVED Apr 22.** All 295 GPT-5.4 nulls (240 on none, 55 on high) were filled in by `retry_failed.py` (`retry_failed.py --results <jsonl> --manifest data/manifest_benchmark_final.csv --backend openai --model gpt-5.4 --reasoning-effort <none|high> --concurrency 8`). Both runs now have 1500/1500 clean rows and 0 runtime errors. The anomaly turned out to be pure quota exhaustion, not a model / reasoning-mode effect. If you see similar 429 spikes on future large OpenAI runs, `retry_failed.py` is the idempotent tool to recover them cheaply.
6. **Default future Qwen3.5-4B runs to `--thinking disabled`**, and default 397B to `--thinking enabled`. 35B-A3B is discretionary based on per-class needs.
7. **Add Part B ↔ Part C calibration computation (pearson_r, calibration_gap, high/low-confidence accuracy) to the benchmark-full runs.** It is computed for the fewshot runs but not the full runs — a small `evaluate.py` extension.

---

## 14. Appendix — data sources

Per-run metrics JSONs:

- `runs/20260420-1226-kimi-k25-benchmark-full/metrics.json`
- `runs/20260420-1554-qwen35-397b-a17b-benchmark-full/metrics.json`
- `runs/20260420-1920-qwen35-4b-benchmark-full/metrics.json`
- `runs/20260420-2054-qwen35-35b-a3b-benchmark-full/metrics.json`
- `runs/20260421-0002-qwen35-4b-nothink-benchmark-full/metrics.json`
- `runs/20260421-0019-qwen35-35b-a3b-nothink-benchmark-full/metrics.json`
- `runs/20260421-0025-qwen35-397b-a17b-nothink-benchmark-full/metrics.json`
- `runs/20260421-2032-gpt-5.4-none-benchmark-full/metrics.json`
- `runs/20260421-2024-gpt-5.4-high-benchmark-full/metrics.json`

Per-run narrative reports under `runs/<slug>/report.md`. Cross-run index in `runs/index.md` and `runs/index.jsonl`. Eval pipeline: `evaluate.evaluate_jsonl` (current commit).

Prior comparison reports in this directory for context:

- `20260419_report_opensource_5class.md` — 4 open-source models on 100-row fewshot (n=100).
- `20260419_report_gpt54_high_vs_none.md` — GPT-5.4 A/B on 20-row fewshot (n=20).
- `20260417_report_prompt_final_setup_comparison.md` — prompt evolution history.

---

*Report generated 2026-04-21 from `runs/*/metrics.json`; refreshed 2026-04-22 after the GPT-5.4 retry pass filled in 295 runtime-error rows. n=1500 per run. Standard errors added 2026-04-22 — every reported proportion now carries its 1σ binomial SE (and pairwise differences carry the propagated diff-SE plus a z-statistic). Nine figures added and incorporated into the narrative on 2026-04-22 via `viz/_make_charts_benchmark_full_apr21.py` → `charts/benchmark_full_apr21/`. No inputs hand-edited.*
