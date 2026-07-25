# Open-source 5-class benchmark — Apr 19 2026

Comparison of four open-source VLMs on the same 100-row balanced fewshot manifest (`data/manifest_fewshot.csv`, 20 SN / 20 AGN / 20 VS / 20 asteroid / 20 bogus). All runs share the same prompts module (`prompts`), the same renderer family, the same 20 000-token budget, the same `evaluate.py` parser, and the same temperature (0.2). The only changing axis is the model id and (for Kimi) the renderer choice.

| Run | Result file | Run report |
|---|---|---|
| Qwen3.5-4B | `results/fewshot_qwen35_4b_newparser.jsonl` | [`runs/20260419-2230-qwen35-4b/report.md`](../../runs/20260419-2230-qwen35-4b/report.md) |
| Qwen3.5-35B-A3B | `results/fewshot_qwen35_newparser.jsonl` | [`runs/20260419-2047-qwen35-35b-a3b-baseline/report.md`](../../runs/20260419-2047-qwen35-35b-a3b-baseline/report.md) |
| Qwen3.5-397B-A17B | `results/fewshot_qwen35_397b_newparser.jsonl` | [`runs/20260419-2230-qwen35-397b-a17b/report.md`](../../runs/20260419-2230-qwen35-397b-a17b/report.md) |
| Kimi K2.5 (think) | `results/fewshot_kimi_think_newparser.jsonl` | [`runs/20260419-2230-kimi-k25-think/report.md`](../../runs/20260419-2230-kimi-k25-think/report.md) |

---

## Headline numbers

| Model | 5-class acc | Parse rate | Truncation | Stage 3 macro F1 | MSRS |
|---|---:|---:|---:|---:|---:|
| Qwen3.5-4B | 23.8 % | **22 %** | **77 %** | 0.175 | 4.83 |
| Qwen3.5-35B-A3B | 33.8 % | 72 % | 25 % | 0.249 | 4.71 |
| Qwen3.5-397B-A17B | 48.5 % | 99 % | 0 % | 0.365 | 4.74 |
| **Kimi K2.5 (think)** | **49.0 %** | **100 %** | **0 %** | **0.468** | 4.54 |

**Ranking is monotonic with model scale within Qwen3.5**, and Kimi K2.5 (thinking) edges out Qwen3.5-397B by 0.5 pp at the 5-class level while leading meaningfully on Stage 3 macro F1 (0.468 vs 0.365).

---

## Token economy — compactness of CoT

| Model | mean output | median output | max output | mean answer | truncation |
|---|---:|---:|---:|---:|---:|
| Qwen3.5-4B | 16 615 | **20 000** | 20 000 | 15 498 | 77 % |
| Qwen3.5-35B-A3B | 10 956 | 8 790 | 20 000 | 5 345 | 25 % |
| Qwen3.5-397B-A17B | **5 139** | **4 825** | 10 434 | 459 | 0 % |
| Kimi K2.5 (think) | 3 868 | 3 652 | 6 582 | 3 867 *(see note)* | 0 % |

> **Note on Kimi answer tokens:** `KimiK25Renderer.parse_response` returns content as a single string rather than typed parts, so `_extract_text_content` cannot strip the thinking. `n_answer_tokens` therefore equals `n_output_tokens` for Kimi only — it is not directly comparable to the Qwen `n_answer_tokens`. The visible Kimi *answer JSON* itself is comparable in length to the Qwen-397B answer (~450–500 tokens).

**Take-away.** Larger models think more *efficiently*, not just more capably. The 4B variant burns through the entire 20 k budget on >50 % of inputs, the 35B saturates 25 % of rows, and the 397B is decisive in 0 %. Kimi K2.5 (think) is the most compact thinker overall.

---

## Format error breakdown (per 100 rows)

| Error code | 4B | 35B | 397B | Kimi-think |
|---|---:|---:|---:|---:|
| `ok` | 22 | 71 | **99** | 0\* |
| `truncated_no_json` | **77** | 23 | 0 | 0 |
| `truncated_partial_json` | 0 | 1 | 0 | 0 |
| `parse_failed` | 1 | 4 | 1 | 0 |
| `schema_missing_top_level` | 0 | 1 | 0 | 0 |
| `extra_text_around_json` | 0 | 0 | 0 | 100\* |

\* Kimi's "extra_text_around_json" code is benign — see Kimi token note above. JSON parses cleanly for all 100 rows.

**Pattern.** Smaller models fail by *running out of budget* (truncation), not by emitting malformed JSON when they do finish. The 397B and Kimi-think have effectively eliminated format errors entirely.

---

## Stage-by-stage accuracy

| Stage | 4B | 35B | 397B | Kimi-think |
|---|---:|---:|---:|---:|
| Part A (metadata reading) | 100 % | 100 % | 100 % | 100 % |
| Stage 1 (real / artifact) | 95 %\* | 81 % | 84 % | 82 % |
| Stage 2 (astro / solar) | 67 %\* | 71 % | 78 % | 73 % |
| Stage 3 (subclass) | 24 %\* | 47 % | 58 % | 58 % |
| End-to-end 5-class | 23.8 % | 33.8 % | 48.5 % | **49.0 %** |

\* 4B percentages are computed over the 21 parsed rows only; n is too small to compare directly with the others.

**Observation.** Once the 4B is excluded, scale primarily moves the *Stage 3 (subclass)* needle. Stage 1 is already near-saturated for any model that produces JSON; Stage 2 moves modestly with scale; Stage 3 is where the bulk of the lift comes from.

---

## Per-class accuracy

| Class | 4B | 35B | 397B | Kimi-think |
|---|---:|---:|---:|---:|
| SN | 0 % (n=4) | 25 % | 36.8 % (n=19) | **60 %** |
| AGN | 0 % (n=8) | **0 %** | **0 %** | **0 %** |
| VS | 100 % (n=5) | 70 % | 75 % | **95 %** |
| asteroid | 0 % (n=3) | 50 % | 85 % | 80 % |
| bogus | 0 % (n=1) | 25 % | **45 %** | 10 % |

**The AGN result is universal across every open-source model tested**: 0/20 in every run that produced parsed predictions. AGN is being absorbed into VS at every scale.

---

## Stage-3 confusion (true → predicted), open-source comparison

Combining the three runs that produced enough parsed rows to be meaningful (35B, 397B, Kimi-think). Each cell is the count of true rows of that class predicted as the column class.

**Kimi K2.5 (think):**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | 12 | 0 | 5 | 3 |
| variable_star | 0 | 19 | 0 | 1 |
| AGN | 0 | 19 | 0 | 1 |

**Qwen3.5-397B-A17B:**

|  | supernova | variable_star | AGN | N/A |
|---|---:|---:|---:|---:|
| supernova | 7 | 0 | 10 | 2 |
| variable_star | 0 | 15 | 0 | 5 |
| AGN | 0 | 19 | 0 | 1 |

**Common failure modes:**
- **AGN → VS** (19/20 in both 397B and Kimi-think) is the dominant residual error on the open-source side.
- **SN labelling** is the swing axis: Kimi resolves 60 % of SNe correctly; 397B confuses SN with AGN (10/19 → AGN) instead. The two strongest models make almost orthogonal SN errors.

---

## Reasoning self-score (MSRS) vs accuracy

| Model | MSRS | 5-class acc |
|---|---:|---:|
| Qwen3.5-4B | 4.83 | 23.8 % |
| Qwen3.5-35B-A3B | 4.71 | 33.8 % |
| Qwen3.5-397B-A17B | 4.74 | 48.5 % |
| Kimi K2.5 (think) | 4.54 | **49.0 %** |

**MSRS is anti-correlated with accuracy** in this batch: the smallest, weakest model is the most confident in its own reasoning, and the strongest is the most humble. The model self-score is not a useful proxy for downstream correctness.

---

## Recommendations / next steps

1. **AGN→VS is now the single highest-value class to debug.** Every open-source model — independent of scale, family, and reasoning style — collapses AGN into variable_star. Worth running Kimi-think and 397B with `prompts_agn_instruction` to test whether targeted guidance moves this needle.
2. **Drop Qwen3.5-4B from the comparison set.** It cannot reliably emit JSON within 20 k tokens; numbers from it are misleading even when they look high (Stage 1 = 95 % is only 21 rows).
3. **Treat Kimi K2.5 (think) as the open-source reference model going forward.** Best 5-class accuracy, best Stage 3 macro F1, perfect parse rate, smallest token budget. The Qwen-397B is a near-tie on accuracy but ~33 % more expensive in output tokens.
4. **Fix Kimi's renderer-level token accounting** if it matters for downstream cost analysis: `_extract_text_content` should detect Kimi's string-only response and split thinking from JSON manually before counting answer tokens.

---

*Inputs to this report:* `results/fewshot_*_newparser.jsonl` files dated 2026-04-19. *Eval pipeline:* `evaluate.py` (commit `e319137`). *Run folders:* the four `runs/20260419-*` paths linked in the table above (plus token-limit A/B: `runs/20260419-2047-qwen35-35b-a3b-tokenlimit/`).
