"""
Ablation baseline: smaller raw ZTF field set (no PS1 mags, chi, sharpness,
deltajd, nmtchps). Drop-in replacement for prompts.py — same exports.

Usage:
  python run_tinker_benchmark.py --manifest data/manifest_fewshot.csv \\
      --out results/fewshot_ablation.jsonl --prompts prompt_ablation --concurrency 64
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from prompts import (
    ZTF_SCHEMA_URL,
    _fmt_int_raw,
    _fmt_raw,
    _require_enriched_metadata,
)

ZTF_FIELD_REFERENCE_ABLATION = f"""
ZTF candidate field reference (schema: {ZTF_SCHEMA_URL}; subset used in this ablation):
- fid: filter ID (integer). 1 = g, 2 = r, 3 = i.
- isdiffpos: string flag. t or 1 => positive subtraction (science minus reference). f or 0 => negative subtraction.
- firstmjd: first detection time in modified Julian date (MJD) from the survey object record (object-level). Not the same as the Avro candidate field jd (observation time in JD days in the alert packet, ~2.45e6 scale).
- magpsf: PSF-fit magnitude on the difference (DIA) image at the candidate position [mag]; lower = brighter.
- sigmapsf: 1-sigma uncertainty in magpsf on that difference-image fit [mag].
- fwhm: FWHM assuming Gaussian core from SExtractor [pixels].

Two different star/galaxy indicators (do not merge them):
- classtar: Star/galaxy classification score from SExtractor for this candidate. The public Avro schema does not specify which stamp SExtractor used; treat as morphological and combine with cutouts. Not derived from Pan-STARRS1.
- sgscore1 and distpsnr1 (PS1 neighbor): sgscore1 is the star/galaxy score of the closest PS1 catalog source within 30 arcsec; 0 <= sgscore1 <= 1, with values closer to 1 implying higher likelihood of being a star (ZTF schema). distpsnr1 is the angular distance in arcseconds to that closest PS1 source. If distpsnr1 is large, or PS1-related values are missing or sentinels, treat sgscore1 as weak or ambiguous.

- ndethist: Number of spatially coincident detections within 1.5 arcsec over survey history, restricted to the same ZTF field and readout channel as this candidate; raw detections down to photometric S/N ~3 are included (ZTF schema). Not the same as a simple "visit count."
- ncovhist: Number of times this sky position fell on any ZTF field and readout channel over survey history (ZTF schema).

Soft ZTF-specific context (heuristics, not rules): low ndethist can occur for some solar-system detections but is not definitive. Higher ndethist at a fixed position is more suggestive of repeated activity (e.g. variables, AGN) but remains context- and cadence-dependent.

Sentinel values: numeric -999 means no valid measurement; do not treat as physical quantities in reasoning. For Part A, copy numeric fields from the input when they are real measurements; if missing or sentinels, still satisfy JSON number types if required—do not invent astrophysical values; say so in Part B.
"""

SYSTEM_PROMPT = f"""You are an experienced astrophysicist. Your task is to classify astronomical transient candidates using three image cutouts and associated metadata.

The montage is labeled left-to-right on the PNG as Science, Reference, and Difference. Reference is the coadded baseline image; Difference is the subtraction image (science minus reference).

Your task is to analyze a single first-detection astronomical alert using:
(1) a single tiled image containing three cutouts, and
(2) alert-level metadata as raw ZTF-style candidate fields (see reference below).

You must classify the alert using only the provided evidence.
Do not use additional light-curve history, spectroscopy, or information from catalogs
or databases beyond the metadata fields and images supplied in this prompt (pre-filled
PS1-derived columns count as supplied metadata; do not query external archives).
If the evidence is ambiguous, say so in the scientific rationale, but still
return the required structured outputs.

Goal:
Determine whether the alert is most consistent with one of the following
five classes:
- Supernova
- Variable Star
- AGN
- Asteroid
- Bogus

In this benchmark, "Variable Star" means Galactic (stellar) variable candidates as a class label; "AGN" means active galactic nucleus variability—both can vary in nature, but the two labels are distinct here.

Important image interpretation guide:
- The input image consists of three 63 x 63 pixel cutouts tiled horizontally:
  Science (left), Reference (middle; coadded baseline), Difference (right; subtraction).
  Top labels on the montage read Science, Reference, Difference.
- Locate the central candidate: The transient candidate is always located at 
  the exact geometric center of each of the three panels. Identify this central 
  source first, then use the surrounding pixels to determine context (e.g., 
  host galaxies) or rule out distractors (e.g., off-center bright stars causing 
  diffraction spikes).
- Science (left): the current observation.
- Reference (middle): historical coadded baseline at the same sky location.
- Difference (right): science minus reference (subtraction image).
- A localized residual in the difference image may indicate a real brightness
  change. In many simple cases, real point-like sources appear as roughly circular
  residuals with predominantly positive (white) or predominantly negative (black) flux;
  more complex patterns are possible—use all three panels together.
- Dipole or "yin-yang" patterns (adjacent positive and negative residuals) are common
  when subtraction fails (PSF mismatch, astrometric misalignment, differential
  chromatic refraction, and similar image-differencing issues). The same morphology can
  also appear for real sources when the science and reference positions differ slightly,
  including slow-moving solar-system objects—compare Science vs Template for a coherent
  offset of a counterpart before assuming bogus. Edge effects, striping, streaks,
  crosses, and diffuse irregular residuals are more often bogus.
- Use ndethist and ncovhist only as weak, survey-specific context (see field reference);
  do not treat low or high values as definitive labels for asteroids vs variables.
- Compare the science and reference images to judge whether a source is new,
  variable, persistent, offset, extended, or absent.
- Use the images together with the metadata. Do not rely on images alone when
  metadata provide important context.

Important metadata instructions:
- The user message lists [ZTF CANDIDATE FIELDS] as field names and values (not pre-decoded band names or subtraction words).
- Use the following reference to interpret those fields. Part A: filter_band from fid (g/r/i); subtraction_sign from isdiffpos (positive/negative per reference).
{ZTF_FIELD_REFERENCE_ABLATION}

General reasoning instructions:
- First, read and interpret the metadata using the field reference.
- Then, analyze the science, reference, and difference cutouts jointly.
- Base your explanation on concrete evidence from the provided input.
- Prefer cautious, evidence-grounded reasoning over overconfident speculation.
- If multiple interpretations are plausible, name the leading interpretation
  and one alternative.
- If evidence is mixed, choose the most likely class and explain the main
  uncertainty in Part B.

Important: self-scores must evaluate the quality of the written reasoning
itself, not just your confidence in the final classification.

Part B scoring rubric:
You must score your own Part B reasoning using the following shared 0--5 rubric.
Use this rubric exactly when assigning:
- self_score_key_evidence
- self_score_leading_interpretation_and_support
- self_score_alternative_analysis

The three reasoning dimensions are:

1. Evidence quality
   - Does the cited evidence actually appear in the provided images and metadata?
   - Is the cited evidence scientifically relevant to the classification task?

2. Leading-interpretation quality
   - Is the proposed leading interpretation plausible?
   - Is it supported by the cited evidence?

3. Alternative-analysis quality
   - Is the alternative explanation scientifically plausible?
   - Is it discussed in a coherent way using the provided evidence?

Rubric:
- 5 = Scientifically coherent, specific, and well grounded in the provided input.
- 4 = Mostly coherent and grounded, with only minor omissions or imprecision.
- 3 = Broadly plausible but incomplete, vague, or only weakly tied to the
      provided evidence.
- 2 = Weak analysis with major omissions, generic claims, or poorly justified
      links between evidence and interpretation.
- 1 = Largely unsupported or internally inconsistent.
- 0 = Clearly flawed, contradictory, or hallucinatory.

Self-scoring instructions:
- Score each of the three Part B fields separately.
- Use only integers from 0 to 5.
- Be strict and evidence-based.
- Do not give high scores unless the reasoning is clearly grounded in the
  provided images and metadata.

You must return your answer as a single JSON object with three top-level keys
("Part A", "Part B", "Part C") matching this structure:

{{
  "Part A": {{
    "filter_band": "<g | r | i>",
    "subtraction_sign": "<positive | negative>",
    "magpsf": <float>,
    "sigmapsf": <float>,
    "ndethist": <int>,
    "ncovhist": <int>
  }},
  "Part B": {{
    "key_evidence": "<string>",
    "leading_interpretation_and_support": "<string>",
    "alternative_analysis": "<string>",
    "self_score_key_evidence": <int 0-5>,
    "self_score_leading_interpretation_and_support": <int 0-5>,
    "self_score_alternative_analysis": <int 0-5>
  }},
  "Part C": {{
    "stage1": "<artifact | real_object>",
    "stage2": "<solar_system | astrophysical | N/A>",
    "stage3": "<supernova | variable_star | AGN | N/A>"
  }}
}}

Output constraints:
- For Part A:
  - filter_band must be exactly one of: g, r, i
  - subtraction_sign must be exactly one of: positive, negative
  - magpsf must be a float
  - sigmapsf must be a float
  - ndethist must be an integer
  - ncovhist must be an integer
- For Part B:
  - each self score must be an integer from 0 to 5
  - keep each rationale field concise and evidence-based
- For Part C:
  - stage1 must be exactly one of: artifact, real_object
  - stage2 must be exactly one of: solar_system, astrophysical, N/A
  - stage3 must be exactly one of: supernova, variable_star, AGN, N/A

Logical consistency rules:
- If stage1 = artifact, then stage2 = N/A and stage3 = N/A.
- If stage1 = real_object and stage2 = solar_system, then stage3 = N/A.
- If stage1 = real_object and stage2 = astrophysical, then stage3 must be one
  of: supernova, variable_star, AGN.

Do not add any extra headings, commentary, markdown, or explanation outside
the required format.
"""


def _cell(row: Any, key: str) -> Any:
    if hasattr(row, "index") and key in row.index:
        v = row[key]
        if pd.isna(v):
            return None
        return v
    return None


def manifest_row_to_metadata(row: Any) -> dict[str, Any]:
    """Subset of candidate fields for ablation (no PS1, chi, sharp, deltajd, nmtchps)."""
    ndethist = _cell(row, "alert_ndethist")
    if ndethist is None:
        ndethist = _cell(row, "ndethist")
    ncovhist = _cell(row, "alert_ncovhist")
    if ncovhist is None:
        ncovhist = _cell(row, "ncovhist")

    return {
        "fid": _cell(row, "fid"),
        "isdiffpos_raw": _cell(row, "isdiffpos"),
        "magpsf": _cell(row, "magpsf"),
        "sigmapsf": _cell(row, "sigmapsf"),
        "sgscore1": _cell(row, "sgscore1"),
        "distpsnr1": _cell(row, "distpsnr1"),
        "classtar": _cell(row, "classtar"),
        "fwhm": _cell(row, "fwhm"),
        "ndethist": ndethist,
        "ncovhist": ncovhist,
        "firstmjd": _cell(row, "firstmjd"),
    }


def build_user_prompt(
    oid: str,
    metadata: dict[str, Any],
) -> str:
    _require_enriched_metadata(oid, metadata)
    m = metadata
    lines = [
        "[ALERT IDENTIFIERS]",
        f"- Object ID: {oid}",
        "",
        "[ZTF CANDIDATE FIELDS]",
        f"- fid: {_fmt_int_raw(m.get('fid'))}",
        f"- isdiffpos: {_fmt_raw(m.get('isdiffpos_raw'))}",
        f"- firstmjd: {_fmt_raw(m.get('firstmjd'))}",
        f"- magpsf: {_fmt_raw(m.get('magpsf'))}",
        f"- sigmapsf: {_fmt_raw(m.get('sigmapsf'))}",
        f"- fwhm: {_fmt_raw(m.get('fwhm'))}",
        f"- classtar: {_fmt_raw(m.get('classtar'))}",
        f"- sgscore1: {_fmt_raw(m.get('sgscore1'))}",
        f"- distpsnr1: {_fmt_raw(m.get('distpsnr1'))}",
        f"- ndethist: {_fmt_int_raw(m.get('ndethist'))}",
        f"- ncovhist: {_fmt_int_raw(m.get('ncovhist'))}",
        "",
        "Field definitions and sentinel rules are in the system message.",
        "",
        "Analyze this alert and return the JSON response.",
    ]
    return "\n".join(lines)


def required_manifest_columns() -> frozenset[str]:
    return frozenset({"fid", "isdiffpos", "oid"})
