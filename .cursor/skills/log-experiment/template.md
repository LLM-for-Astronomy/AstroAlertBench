# EXP-{YYYYMMDD}-{slug}

## Metadata
- **Date:** {YYYY-MM-DD HH:MM local}
- **Slug:** {slug}
- **Status:** {planned | running | complete | failed}
- **Commit:** `{short-hash}` ({last commit subject})
- **Working tree dirty:** {true | false} {if true, list modified files}
- **Operator:** {name or "user"}

## Hypothesis
{1-3 sentences: what are we testing, why, what do we expect to see?}

## Baseline / Comparison
- **Compared to:** `EXP-{YYYYMMDD}-{slug}` ({one-line summary of that run})
- **What changed since baseline:**
  - {e.g. "switched Qwen3.5 renderer from DisableThinking to Renderer (thinking enabled)"}
  - {e.g. "added Stage-2 AGN-vs-VS guidance in prompts.py"}
  - {e.g. "max_tokens 2048 → 16384 for reasoning models"}

## Configuration
| Field | Value |
|---|---|
| Model | `{HF model id}` |
| Renderer | `{renderer class name from api_tinker.py}` |
| Reasoning mode | {enabled | disabled} |
| max_tokens | {effective value} |
| Temperature | {value} |
| Concurrency | {N} |
| Prompt module | `{module name}` |

## Prompt Summary

**System prompt header (first ~10 lines):**

```
{paste verbatim}
```

**Metadata fields exposed to model:**
{comma-separated list returned by manifest_row_to_metadata}

**Custom Stage guidance (if any):**
{1-2 lines summarizing Stage 1/2/3 hints, or "default"}

## Data
- **Manifest:** `{path}`
- **Total samples used:** {N} (limit={--limit value or "none"})
- **Class distribution:**
  | Class | Count |
  |---|---|
  | SN | {n} |
  | AGN | {n} |
  | VS | {n} |
  | asteroid | {n} |
  | bogus | {n} |

## Command

```bash
{exact CLI used to launch the run, including env vars if non-default}
```

## Output
- **Results file:** `{path to .jsonl}`
- **Wall-clock runtime:** {HH:MM:SS or "TBD"}
- **Records written:** {n}
- **Records with parsed JSON:** {n} ({pct}%)

## Code Diff vs Baseline

`git diff --stat {baseline_commit}..HEAD -- prompts.py api_tinker.py evaluate.py run_tinker_benchmark.py`

```
{paste output, or "no changes"}
```

## Library Versions
- tinker: `{version}`
- tinker-cookbook: `{version}`
- {other relevant: pandas, transformers, etc.}

---

## Results
*(fill after `evaluate.py` completes)*

| Metric | Value |
|---|---|
| 5-class accuracy | {pct} |
| JSON parse rate | {pct} |
| Stage 1 (real vs bogus) | {pct} |
| Stage 2 (astro vs artifact) | {pct} |
| Stage 3 (astro subclass) macro F1 | {value} |
| Part A (metadata reading) | {pct} |
| MSRS (reasoning self-score) | {value} |
| Mean output tokens (full) | {value} |
| Median output tokens (full) | {value} |
| Max output tokens (full) | {value} |
| Mean answer tokens (post-thinking) | {value} |
| Truncated runs (hit max_tokens) | {n} ({pct}%) |

**Per-class accuracy:**
| Class | Acc | n |
|---|---|---|
| SN | {pct} | {n} |
| AGN | {pct} | {n} |
| VS | {pct} | {n} |
| asteroid | {pct} | {n} |
| bogus | {pct} | {n} |

**Stage 3 confusion matrix (true → predicted):**
|  | SN | AGN | VS | asteroid | bogus | N/A |
|---|---|---|---|---|---|---|
| SN | | | | | | |
| AGN | | | | | | |
| VS | | | | | | |
| asteroid | | | | | | |
| bogus | | | | | | |

## Observations
- **Hypothesis matched?** {yes / partially / no, 1-line why}
- **Surprises:** {e.g. "VS over-prediction collapsed AGN to 0%"}
- **Notable failure modes:** {e.g. "model truncates JSON when thinking exceeds 14k tokens"}
- **Suggested next experiment:** {one sentence}
