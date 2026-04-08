"""
Ablation baseline prompt: original 11-field metadata (no PS1 mags, chi, sharpness,
deltajd, nmtchps).  Drop-in replacement for prompts.py — exports the same three
names: SYSTEM_PROMPT, build_user_prompt, manifest_row_to_metadata.

Usage:
  python run_tinker_benchmark.py --manifest data/manifest_fewshot.csv \
      --out results/fewshot_kimi_ablation.jsonl --prompts prompt_ablation --concurrency 64
"""

from __future__ import annotations

from typing import Any

import pandas as pd

SYSTEM_PROMPT = """You are an experienced astrophysicist. Your task is to classify astronomical transient candidates using three image cutouts (Science, Template, Image) and associated metadata.

Your task is to analyze a single first-detection astronomical alert using:
(1) a single tiled image containing three cutouts, and
(2) alert-level metadata.

You must classify the alert using only the provided evidence.
Do not assume any additional light-curve history, spectroscopy, catalog lookup,
or outside information beyond the input shown here.
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

Important image interpretation guide:
- The input image consists of three 63 x 63 pixel cutouts tiled horizontally 
  in the following order: Science (left), Reference (middle), and Difference (right). 
  Each panel has a text label in the top margin.
- Locate the central candidate: The transient candidate is always located at 
  the exact geometric center of each of the three panels. Identify this central 
  source first, then use the surrounding pixels to determine context (e.g., 
  host galaxies) or rule out distractors (e.g., off-center bright stars causing 
  diffraction spikes).
- Science image (left): the current observation.
- Reference image (middle): a historical baseline image of the same sky location.
- Image image (right): the change between the current and reference images.
- A localized residual in the difference image may indicate a real brightness
  change. Real sources typically appear as circular objects with only positive (white) 
  or only negative (black) flux.
- Be cautious about obvious artifacts: bad subtractions often show a dipole 
  "yin-yang" pattern (adjacent white and black pixels). Edge effects, striping, 
  streaks, crosses, or diffuse irregular residuals are typically bogus.
- Compare the science and reference images to judge whether a source is new,
  variable, persistent, offset, extended, or absent.
- Use the images together with the metadata. Do not rely on images alone when
  metadata provide important context.

Important metadata interpretation guide:
- Observation Time (Julian Date): time of the detection.
- Filter Band: observing band (g, r, or i).
- PSF Magnitude: brightness estimate from PSF-fit photometry; lower values
  mean brighter objects.
- Magnitude Uncertainty: 1-sigma uncertainty on the PSF magnitude.
- Flux Change Direction:
  - positive subtraction = brighter in science than reference
  - negative subtraction = fainter in science than reference
- FWHM: approximate image width / seeing-related measure of the detected source.
- Nearest-source Star/Galaxy Score: score for the nearest reference source;
  values near 1 are more star-like and values near 0 are more galaxy-like.
- Distance to Nearest Reference Source: angular distance to the nearest
  reference source.
- Star-classifier Score: source morphology score; values near 1 are more
  star-like.
- Historical Detections: number of prior detections associated with this source.
- Historical Coverages: number of prior images covering this sky position.

General reasoning instructions:
- First, read and interpret the metadata carefully.
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

{
  "Part A": {
    "filter_band": "<g | r | i>",
    "subtraction_sign": "<positive | negative>",
    "magpsf": <float>,
    "sigmapsf": <float>,
    "ndethist": <int>,
    "ncovhist": <int>
  },
  "Part B": {
    "key_evidence": "<string>",
    "leading_interpretation_and_support": "<string>",
    "alternative_analysis": "<string>",
    "self_score_key_evidence": <int 0-5>,
    "self_score_leading_interpretation_and_support": <int 0-5>,
    "self_score_alternative_analysis": <int 0-5>
  },
  "Part C": {
    "stage1": "<artifact | real_object>",
    "stage2": "<solar_system | astrophysical | N/A>",
    "stage3": "<supernova | variable_star | AGN | N/A>"
  }
}

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


def _fmt(val: Any, fallback: str = "N/A") -> str:
    """Format a value for prompt display: None / NaN → fallback."""
    if val is None:
        return fallback
    if isinstance(val, float):
        if pd.isna(val):
            return fallback
        return f"{val:.6g}"
    s = str(val)
    if s.lower() in ("nan", ""):
        return fallback
    return s


def _fmt_int(val: Any, fallback: str = "N/A") -> str:
    if val is None:
        return fallback
    try:
        v = float(val)
        if pd.isna(v):
            return fallback
        return str(int(v))
    except (ValueError, TypeError):
        return fallback


def manifest_row_to_metadata(row: Any) -> dict[str, Any]:
    """Extract the original 11 prompt-facing metadata fields (no PS1 mags)."""
    isdiffpos_raw = _cell(row, "isdiffpos")
    if isdiffpos_raw is not None:
        isdiffpos = "positive" if str(isdiffpos_raw).lower() in ("t", "1", "true") else "negative"
    else:
        isdiffpos = None

    ndethist = _cell(row, "alert_ndethist")
    if ndethist is None:
        ndethist = _cell(row, "ndethist")
    ncovhist = _cell(row, "alert_ncovhist")
    if ncovhist is None:
        ncovhist = _cell(row, "ncovhist")

    return {
        "band": _cell(row, "fid_band"),
        "magpsf": _cell(row, "magpsf"),
        "sigmapsf": _cell(row, "sigmapsf"),
        "sgscore1": _cell(row, "sgscore1"),
        "distpsnr1": _cell(row, "distpsnr1"),
        "classtar": _cell(row, "classtar"),
        "fwhm": _cell(row, "fwhm"),
        "isdiffpos": isdiffpos,
        "ndethist": ndethist,
        "ncovhist": ncovhist,
        "firstmjd": _cell(row, "firstmjd"),
    }


def build_user_prompt(
    oid: str,
    metadata: dict[str, Any],
) -> str:
    """
    Per-alert user message: identifiers + metadata values + task instruction.
    Field labels match the metadata interpretation guide in SYSTEM_PROMPT.
    """
    return f"""\
[ALERT IDENTIFIERS]
- Object ID: {oid}

[ALERT METADATA]
- Observation Time (MJD): {_fmt(metadata.get("firstmjd"))}
- Filter Band: {_fmt(metadata.get("band"))}
- PSF Magnitude: {_fmt(metadata.get("magpsf"))}
- Magnitude Uncertainty: {_fmt(metadata.get("sigmapsf"))}
- Flux Change Direction: {_fmt(metadata.get("isdiffpos"))}
- FWHM: {_fmt(metadata.get("fwhm"))}
- Nearest-source Star/Galaxy Score: {_fmt(metadata.get("sgscore1"))}
- Distance to Nearest Reference Source: {_fmt(metadata.get("distpsnr1"))}
- Star-classifier Score: {_fmt(metadata.get("classtar"))}
- Historical Detections: {_fmt_int(metadata.get("ndethist"))}
- Historical Coverages: {_fmt_int(metadata.get("ncovhist"))}

Analyze this alert and return the JSON response."""
