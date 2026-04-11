"""
AstroAlertBench-style prompts: Parts A–C + strict JSON (zero-shot).
Used by api_tinker.py and run_tinker_benchmark.py.

User messages show raw ZTF-style candidate field names (e.g. fid, isdiffpos) plus
definitions in SYSTEM_PROMPT. Requires enriched manifest columns fid and isdiffpos.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

ZTF_SCHEMA_URL = "https://zwickytransientfacility.github.io/ztf-avro-alert/schema.html"

# Field definitions for ztf.alert.candidate-aligned names (subset used in the user prompt).
ZTF_FIELD_REFERENCE = f"""
ZTF candidate field reference (schema: {ZTF_SCHEMA_URL}):
- fid: filter ID (integer). 1 = g, 2 = r, 3 = i.
- isdiffpos: string flag. t or 1 => positive subtraction (science minus reference), i.e. brighter in science than reference.
  f or 0 => negative subtraction (reference minus science), i.e. fainter in science than reference.
- firstmjd: first detection time as modified Julian date from the survey object record (object-level; not the Avro field jd).
- magpsf: PSF-fit magnitude [mag]; lower = brighter.
- sigmapsf: 1-sigma uncertainty on magpsf [mag].
- fwhm: FWHM assuming Gaussian core from SExtractor [pixels].
- classtar: SExtractor star/galaxy classification score (~1 star-like).
- sgscore1: PS1 nearest neighbor star/galaxy score (0–1, ~1 star-like).
- distpsnr1: distance to nearest PS1 source [arcsec].
- chinr: DAOPhot chi of nearest source in reference image PSF catalog.
- sharpnr: DAOPhot sharpness of nearest reference source (~0 point-like).
- ndethist: number of spatially coincident detections (ZTF candidate definition; values here match alert-level history for this candidate).
- ncovhist: number of times the position was covered on any field/channel (ZTF candidate definition).
- sgmag1, srmag1, simag1, szmag1: PS1 PSF magnitudes of nearest match in g,r,i,z [mag].
- nmtchps: number of PS1 matches within 30 arcsec.
- deltajd: time span in days between first and last detection for this object (object-level).

Sentinel values: numeric -999 (and similar schema null sentinels) means no valid measurement. Do not interpret -999 as a physical magnitude, distance, or flux; do not use it as numeric evidence in Part B or Part C. For Part A, report physically meaningful floats for magpsf/sigmapsf when the input is a real measurement; if the only values provided are sentinels, use your best consistent interpretation of the JSON schema constraints.
"""

SYSTEM_PROMPT = f"""You are an experienced astrophysicist. Your task is to classify astronomical transient candidates using three image cutouts (Science, Template, Image) and associated metadata.

Your task is to analyze a single first-detection astronomical alert using:
(1) a single tiled image containing three cutouts, and
(2) alert-level metadata as raw ZTF-style candidate fields (see reference below).

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

Important metadata instructions:
- The user message lists [ZTF CANDIDATE FIELDS] as field names and values exactly as in the benchmark extract (not pre-decoded band names or subtraction words).
- Use the following reference to interpret those fields. Part A asks for decoded quantities: filter_band must be g, r, or i (derive from fid), and subtraction_sign must be positive or negative (derive from isdiffpos using the reference).
{ZTF_FIELD_REFERENCE}

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


_SENTINEL = -999


def _fmt(val: Any, fallback: str = "N/A") -> str:
    """Format a value for prompt display: None / NaN / -999 sentinel → fallback."""
    if val is None:
        return fallback
    if isinstance(val, (int, float)):
        if pd.isna(val) or val == _SENTINEL:
            return fallback
        return f"{val:.6g}"
    s = str(val).strip()
    if s.lower() in ("nan", "", "-999", "-999.0"):
        return fallback
    return s


def _fmt_int(val: Any, fallback: str = "N/A") -> str:
    if val is None:
        return fallback
    try:
        v = float(val)
        if pd.isna(v) or v == _SENTINEL:
            return fallback
        return str(int(v))
    except (ValueError, TypeError):
        return fallback


def _fmt_raw(val: Any, fallback: str = "N/A") -> str:
    """Like _fmt but preserves literal -999; only None/NaN/empty → N/A."""
    if val is None:
        return fallback
    if isinstance(val, float) and pd.isna(val):
        return fallback
    if isinstance(val, (int, float)):
        return f"{val:.6g}"
    s = str(val).strip()
    if s.lower() in ("nan", ""):
        return fallback
    return s


def _fmt_int_raw(val: Any, fallback: str = "N/A") -> str:
    """Integer-ish display; preserves -999; None/NaN → N/A."""
    if val is None:
        return fallback
    try:
        v = float(val)
        if pd.isna(v):
            return fallback
        if v == int(v):
            return str(int(v))
        return f"{v:.6g}"
    except (ValueError, TypeError):
        s = str(val).strip()
        return s if s and s.lower() != "nan" else fallback


def _require_enriched_metadata(oid: str, metadata: dict[str, Any]) -> None:
    """Enriched manifest must supply fid and raw isdiffpos for Part A grounding."""
    if metadata.get("fid") is None:
        raise ValueError(
            f"Missing fid for object {oid!r}. Re-run enrich_manifest_alerce.py "
            "and use manifest_enriched.csv (or ensure the manifest has a fid column)."
        )
    raw = metadata.get("isdiffpos_raw")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise ValueError(
            f"Missing isdiffpos for object {oid!r}. Re-run enrich_manifest_alerce.py "
            "and use manifest_enriched.csv (or ensure the manifest has isdiffpos)."
        )


def manifest_row_to_metadata(row: Any) -> dict[str, Any]:
    """Extract prompt-facing metadata from a manifest_enriched.csv row."""
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
        "chinr": _cell(row, "chinr"),
        "sharpnr": _cell(row, "sharpnr"),
        "sgmag1": _cell(row, "sgmag1"),
        "srmag1": _cell(row, "srmag1"),
        "simag1": _cell(row, "simag1"),
        "szmag1": _cell(row, "szmag1"),
        "nmtchps": _cell(row, "nmtchps"),
        "deltajd": _cell(row, "deltajd"),
    }


def build_user_prompt(
    oid: str,
    metadata: dict[str, Any],
) -> str:
    """
    Per-alert user message: identifiers + raw ZTF-style fields + task instruction.
    Definitions and sentinel rules are in SYSTEM_PROMPT.
    """
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
        f"- chinr: {_fmt_raw(m.get('chinr'))}",
        f"- sharpnr: {_fmt_raw(m.get('sharpnr'))}",
        f"- ndethist: {_fmt_int_raw(m.get('ndethist'))}",
        f"- ncovhist: {_fmt_int_raw(m.get('ncovhist'))}",
        f"- sgmag1: {_fmt_raw(m.get('sgmag1'))}",
        f"- srmag1: {_fmt_raw(m.get('srmag1'))}",
        f"- simag1: {_fmt_raw(m.get('simag1'))}",
        f"- szmag1: {_fmt_raw(m.get('szmag1'))}",
        f"- nmtchps: {_fmt_int_raw(m.get('nmtchps'))}",
        f"- deltajd: {_fmt_raw(m.get('deltajd'))}",
        "",
        "Field definitions and sentinel rules are in the system message.",
        "",
        "Analyze this alert and return the JSON response.",
    ]
    return "\n".join(lines)


def required_manifest_columns() -> frozenset[str]:
    """Columns that must exist on the manifest for prompt construction."""
    return frozenset(
        {
            "fid",
            "isdiffpos",
            "oid",
        }
    )
