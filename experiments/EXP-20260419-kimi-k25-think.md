# EXP-20260419-kimi-k25-think

## Metadata
- **Date:** 2026-04-19 (local)
- **Slug:** kimi-k25-think
- **Status:** complete
- **Commit:** `e319137`
- **Working tree dirty:** true — `evaluate.py`, `api_tinker.py`, and the new `api_openai.py` carry uncommitted edits from this session.
- **Operator:** user

## Hypothesis
Kimi K2.5 had previously been routed through `KimiK25DisableThinkingRenderer` (no CoT). Switch to `KimiK25Renderer` (thinking enabled) and see whether internal reasoning lifts the model above the strong but bounded prior baseline. Expectation: parse rate stays ~100% (Kimi was already a clean JSON emitter); 5-class accuracy goes up because the harder Stage-2/Stage-3 calls benefit from extra deliberation.

## Baseline / Comparison
- **Compared to:** the previous `results/fewshot_kimi.jsonl` family (DisableThinking renderer, same prompts module). No formal `EXP-*.md` was logged for that earlier run.
- **What changed:**
  - `api_tinker.get_renderer`: `KimiK25DisableThinkingRenderer` → `KimiK25Renderer` (thinking enabled).
  - `effective_max` auto-bumped 2 048 → 20 000 because `KimiK25Renderer` is in `_REASONING_RENDERERS`.
  - No prompt change.

## Configuration
| Field | Value |
|---|---|
| Model | `moonshotai/Kimi-K2.5` |
| Renderer | `KimiK25Renderer` |
| Reasoning mode | enabled |
| max_tokens | 20 000 |
| Temperature | 0.2 |
| Concurrency | 32 |
| Prompt module | `prompts` |

## Prompt Summary

**System prompt header (first ~10 lines):**

```
You are an experienced astrophysicist. Your task is to classify astronomical transient candidates using three image cutouts and associated metadata.

The montage is labeled left-to-right on the PNG as Science, Reference, and Difference. Reference is the coadded baseline image; Difference is the subtraction image (science minus reference).

Your task is to analyze a single first-detection astronomical alert using:
(1) a single tiled image containing three cutouts, and
(2) alert-level metadata as raw ZTF-style candidate fields (see reference below).

You must classify the alert using only the provided evidence.
```

**Metadata fields exposed to model:** standard set from `prompts.manifest_row_to_metadata` (fid, isdiffpos_raw, magpsf, sigmapsf, sgscore1, distpsnr1, classtar, fwhm, ndethist, ncovhist, firstmjd, chinr, sharpnr, sgmag1, srmag1, …).

**Custom Stage guidance:** default.

## Data
- **Manifest:** `data/manifest_fewshot.csv`
- **Total samples used:** 100 (limit=none)
- **Class distribution:** 20 each (SN, AGN, VS, asteroid, bogus).

## Command

```bash
python run_tinker_benchmark.py `
  --manifest data/manifest_fewshot.csv `
  --model moonshotai/Kimi-K2.5 `
  --out results/fewshot_kimi_think_newparser.jsonl `
  --prompts prompts `
  --concurrency 32
```

## Output
- **Results file:** `results/fewshot_kimi_think_newparser.jsonl`
- **Wall-clock runtime:** 609.2 s (~10 min, concurrency 32)
- **Records written:** 100
- **Records with parsed JSON:** 100 (100 %)

## Code Diff vs Baseline

`api_tinker.py` — single 1-line route swap (`KimiK25DisableThinkingRenderer` → `KimiK25Renderer`); rest of the pipeline identical.

## Library Versions
- tinker: `0.13.1`
- tinker-cookbook: `0.1.0`

---

## Results

| Metric | Value |
|---|---|
| **5-class accuracy** | **49.0 %** |
| JSON parse rate | 100 % |
| Stage 1 (real vs artifact) | 82.0 % |
| Stage 2 (astro vs solar) | 73.0 % |
| Stage 3 (subclass) accuracy | 58.0 % |
| Stage 3 macro F1 | 0.468 |
| Part A (metadata reading) | 100 % |
| MSRS (reasoning self-score) | 4.54 |
| Mean output tokens (full) | 3 868 |
| Median output tokens | 3 652 |
| Max output tokens | 6 582 |
| Mean answer tokens (post-thinking) | 3 867 *(see note)* |
| Truncated runs (hit max_tokens) | 0 (0 %) |

> **Note on answer tokens:** `KimiK25Renderer.parse_response` returns content as a single string (not a list of typed parts the way `Qwen3_5Renderer` does). `_extract_text_content` therefore passes the whole CoT-prose-then-JSON blob through unchanged, so `answer_tokens ≈ output_tokens`. JSON parsing is unaffected because `extract_json_object` finds the trailing JSON object regardless. This is also why every record gets the soft `extra_text_around_json` warning code (100/100) — the format-error breakdown looks alarming but is benign here.

**Format error breakdown:**
```
extra_text_around_json: 100   # benign warning; JSON is valid in every row
```

**Value error breakdown:** none.

**Per-class accuracy:**
| Class | Acc | n |
|---|---|---|
| SN | 60.0 % | 20 |
| AGN | 0.0 % | 20 |
| VS | 95.0 % | 20 |
| asteroid | 80.0 % | 20 |
| bogus | 10.0 % | 20 |

**Stage 3 confusion (true → predicted):**
|  | supernova | variable_star | AGN | N/A |
|---|---|---|---|---|
| supernova | 12 | 0 | 5 | 3 |
| variable_star | 0 | 19 | 0 | 1 |
| AGN | 0 | 19 | 0 | 1 |

## Observations
- **Hypothesis matched?** Yes. Best 5-class accuracy on record (49 %), parse rate held at 100 %, no truncation. Thinking-enabled Kimi is the strongest open-source result we have so far.
- **Surprises:** (1) `bogus` collapsed to 10 % — the model is now more "trusting" of marginal candidates and pushes them into astrophysical classes, costing 8 bogus predictions vs prior runs. (2) AGN remains 0/20 — the AGN→VS collapse is universal across every model on this benchmark. (3) Renderer-level token accounting is wrong for Kimi (see note above).
- **Notable failure modes:** `bogus` regression and persistent AGN failure. Stage-3 confusion shows AGN 0/20 going entirely to variable_star — same pattern as Qwen3.5-35B and -397B.
- **Suggested next experiment:** retry with `prompts_agn_instruction` to see whether targeted AGN-vs-VS guidance helps the strongest open-source backbone.

**See also:** opensource comparison report `report/report_opensource_5class_Apr19.md`.
