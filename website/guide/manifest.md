# Manifest columns

Manifests are CSV tables keyed by **`oid`**. Exact columns evolve with enrichment, but conceptually they hold:

## Identity & label

- **`oid`** — ALeRCE / ZTF object identifier; joins to stamp folders and JSONL rows.
- **`target_class`** (or equivalent) — five-way gold label used by `evaluate.py` when scoring Part C / final class.

## Broker / candidate features

Typical prompt-facing and scoring-related fields include (names may vary slightly by CSV version):

- photometry: `magpsf`, `sigmapsf`, `diffmaglim`, …
- astrometry / star-galaxy: `sgscore1`, `distpsnr1`, …
- filter / position semantics: `fid`, `isdiffpos`, derived `fid_band`
- variability context: `ndethist`, `ncovhist`, …

**Part A** asks models to extract a **subset** of these as JSON; **gold** is derived from the manifest with numeric tolerances (`FLOAT_TOLERANCE` in `evaluate.py`).

## Paths

Stamp locations may appear as relative paths or be implied by `oid` + class folder conventions. The runner resolves the montage file that `prompts.py` expects (usually `montage.png`).

## Where to look in code

- `enrich_manifest_alerce.py` — what gets fetched from ALeRCE.
- `prompts.py` — which keys are serialized into the user message.
- `evaluate.py` — which columns define gold for Part A and Part C.
