# GPT-5.4 reasoning A/B — Apr 19 2026

A/B comparison of OpenAI's `gpt-5.4` with reasoning enabled (`high`) vs disabled (`none`) on a 20-row balanced subset (`data/manifest_fewshot_20.csv`, 4 per class). Both runs use the new `api_openai.py` backend, the same `prompts` module, the same `max_output_tokens=20000`, and the same concurrency. The only changing axis is the `--reasoning-effort` flag.

| Run | Result file | Run report |
|---|---|---|
| gpt-5.4 high | `results/fewshot20_gpt54_high.jsonl` | [`runs/20260419-2230-gpt-5.4-high/report.md`](../../runs/20260419-2230-gpt-5.4-high/report.md) |
| gpt-5.4 none | `results/fewshot20_gpt54_none.jsonl` | [`runs/20260419-2230-gpt-5.4-none/report.md`](../../runs/20260419-2230-gpt-5.4-none/report.md) |

> **Caveat up-front:** n = 20 (4 per class). One swung row = 25 pp of per-class accuracy. The directional findings below are interesting but not statistically conclusive; treat them as smoke signals warranting a 100-row rerun.

---

## Headline numbers

| Metric | high | none | Δ (high − none) |
|---|---:|---:|---:|
| **5-class accuracy** | 40.0 % | **50.0 %** | **−10.0 pp** |
| JSON parse rate | 100 % | 100 % | 0 |
| Truncation rate | 0 % | 0 % | 0 |
| Stage 1 (real / artifact) | 80.0 % | 80.0 % | 0 |
| Stage 2 (astro / solar) | 80.0 % | 75.0 % | +5.0 pp |
| Stage 3 (subclass) acc | 55.0 % | 55.0 % | 0 |
| Stage 3 macro F1 | 0.222 | **0.356** | −0.134 |
| Part A (metadata reading) | 100 % | 100 % | 0 |
| MSRS | 4.25 | 4.25 | 0 |

**Headline finding:** at this sample size, GPT-5.4 with `reasoning_effort: none` *outperformed* `high` on end-to-end 5-class accuracy by 10 pp (10/20 vs 8/20). Reasoning-on did move the needle on Stage 2 (+5 pp), but lost it back at Stage 3.

---

## Token economy

| Metric | high | none | high / none |
|---|---:|---:|---:|
| Mean output tokens | 2 130 | 463 | **4.6 ×** |
| Median output tokens | 2 132 | 463 | 4.6 × |
| Max output tokens | 3 872 | 495 | 7.8 × |
| Mean answer (visible) tokens | 437 | 463 | 0.94 × |
| Mean reasoning (hidden CoT) tokens | 1 694 | 0 | — |
| Median reasoning tokens | 1 660 | 0 | — |
| Max reasoning tokens | 3 448 | 0 | — |
| Mean prompt tokens | ~3 372 | ~3 372 | 1.0 × |

**Take-away.** The `high` variant burns roughly **4× more billable output tokens per row** without producing a longer or richer visible answer — the entire delta lives in the (charged) hidden reasoning trace. For this task, that delta is currently buying *negative* accuracy.

---

## Format quality

Both runs: `format_breakdown = {"ok": 20}`, no value errors, no truncation, 100 % JSON parse rate, 100 % Part A correctness. The OpenAI backend is producing perfectly clean records — there is no schema or parsing slack to recover.

---

## Per-class accuracy (4 records each)

| Class | high | none | swing |
|---|---|---|---|
| SN | 0 / 4 | **1 / 4** | none gains 1 |
| AGN | 0 / 4 | 0 / 4 | tied |
| VS | 4 / 4 | 4 / 4 | tied |
| asteroid | 3 / 4 | **4 / 4** | none gains 1 |
| bogus | 1 / 4 | 1 / 4 | tied |
| **Total** | **8 / 20** | **10 / 20** | **none +2** |

The 10-pp gap is exactly two records: one SN that `none` got right and `high` did not, and one asteroid that `none` got right and `high` did not.

---

## Stage 3 confusion (true → predicted)

**gpt-5.4 high:**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | 0 | 0 | **4** | 0 |
| variable_star | 0 | 4 | 0 | 0 |
| AGN | 0 | 4 | 0 | 0 |

**gpt-5.4 none:**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | **1** | 0 | 1 | 2 |
| variable_star | 0 | 4 | 0 | 0 |
| AGN | 0 | 4 | 0 | 0 |

**Pattern.** With reasoning on, every supernova is confidently classified as AGN. With reasoning off, the model is humbler: 1 SN correct, 1 wrong-as-AGN, 2 abstained as N/A. The high-reasoning model is *over-deliberating its way into a wrong-but-decisive AGN call* on every SN it sees — exactly the pathology that "thinking" is supposed to prevent.

The AGN→VS collapse (4/4) is identical in both runs and matches the universal pattern seen across every open-source model in `20260419_report_opensource_5class.md`. This is a problem with the prompt or the data presentation, not with the reasoning dial.

---

## Calibration (self-confidence vs correctness)

| Metric | high | none |
|---|---:|---:|
| n linked | 20 | 20 |
| mean self-confidence (correct preds) | 4.21 | 4.23 |
| mean self-confidence (incorrect preds) | 4.28 | 4.27 |
| calibration gap (correct − incorrect) | **−0.07** | **−0.03** |
| Pearson r (confidence ↔ correctness) | −0.10 | −0.05 |

Both variants are slightly *anti-calibrated*: they are marginally more confident in wrong answers than right ones. The reasoning-on variant is *more* anti-calibrated, not less. Reasoning is not buying calibration here either.

---

## Cross-reference with open-source

For context against the four open-source runs (which used a 100-row manifest):

| Model | Subset | n | 5-class | Output tokens (mean) |
|---|---|---:|---:|---:|
| Qwen3.5-4B | 100-row | 100 | 23.8 % | 16 615 |
| Qwen3.5-35B-A3B | 100-row | 100 | 33.8 % | 10 956 |
| Qwen3.5-397B-A17B | 100-row | 100 | 48.5 % | 5 139 |
| Kimi K2.5 (think) | 100-row | 100 | **49.0 %** | 3 868 |
| gpt-5.4 high | 20-row | 20 | 40.0 % | 2 130 |
| gpt-5.4 none | 20-row | 20 | **50.0 %** | 463 |

GPT-5.4 numbers are not directly comparable to the open-source 100-row runs because of the different sample size. The 20-row stratified slice should be roughly balanced but a single misclassification swings 5 % of the headline number.

---

## Recommendations / next steps

1. **Rerun both GPT-5.4 conditions on the full 100-row `manifest_fewshot.csv`** before drawing the "reasoning hurts" conclusion publicly. The current 20-row result is suggestive but underpowered.
2. **Default to `reasoning_effort: none` for cost-controlled smoke tests.** It is ~4–5× cheaper and (on this slice) at least as accurate.
3. **The SN→AGN collapse under reasoning is the most concrete finding.** When the 100-row rerun lands, look at the `key_evidence` text on SN rows in the `high` run vs the `none` run — the model is reasoning itself into a particular AGN-favoring narrative. This is exactly the kind of failure mode the new `prompts_token_limit_instruction` and a future "stop iterating, commit" prompt should target.
4. **AGN→VS is identical in both conditions** and matches the open-source pattern. Treat AGN as a prompt/data problem, not a model-capacity problem.

---

*Inputs to this report:* `results/fewshot20_gpt54_{high,none}.jsonl` (run 2026-04-19). *Eval pipeline:* `evaluate.py` at commit `e319137`. *Run folders:* `runs/20260419-2230-gpt-5.4-{high,none}/`.
