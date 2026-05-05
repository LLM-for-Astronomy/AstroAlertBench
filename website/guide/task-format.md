# JSON contract (Parts A–C)

Models must answer with a **single JSON object** (details enforced by parsing in `evaluate.py` and the prompt schema in `prompts.py`).

## Part A — metadata extraction

Structured fields aligned with broker numbers but in “human” decoding where needed, e.g.:

- `filter_band` (g / r / i)
- `subtraction_sign` (positive / negative)
- photometry: `magpsf`, `sigmapsf`
- history: `ndethist`, `ncovhist`

Scores are **per-field** and **exact-match on six fields** variants, with float tolerance for numerics.

## Part B — self-reported reasoning quality

The model rates its own reasoning on a rubric (typically 1–5 in three dimensions). Aggregates include **MSRS** (mean self-reasoning score) and **self-pass rate** (mean ≥ threshold). These are **not** gold labels; they are used for **calibration analysis** vs Part C correctness.

## Part C — cascade & five-way class

Part C expresses a **three-stage** decision:

1. **Real vs bogus** (survey artifact / junk bucket)
2. Among real: **astrophysical vs non-astrophysical**
3. Among astrophysical: **supernova vs variable_star vs AGN** (stage-3 taxonomy)

The pipeline maps stages to a **single five-way label** (the SN / AGN / VS / asteroid / bogus taxonomy used in the benchmark).

Evaluation reports:

- per-stage accuracies (including **conditional** variants),
- end-to-end staged accuracy,
- final **5-class accuracy** vs `target_class`,
- **per-class** stats and confusion matrices on stage 3.

## Prompt modules

- **`prompts.py`** — default benchmark text and schema instructions.
- **`prompts_agn_instruction.py`** — adds extra guidance for **AGN vs variable_star** using colors and star-galaxy features.

Swap modules with the runner’s `--prompts` flag so JSON keys stay aligned.
