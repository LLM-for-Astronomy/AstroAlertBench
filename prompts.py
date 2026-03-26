"""
AstroAlertBench-style prompts: Parts A–C + strict JSON (zero-shot).
Used by api_tinker.py and run_tinker_benchmark.py.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

SYSTEM_PROMPT = """You are an experienced astrophysicist. Your task is to classify astronomical transient candidates using three image cutouts (Science, Template, Difference) and associated metadata.

You must analyze the images and metadata carefully and produce a structured response divided into three parts:

Part A: Metadata Grounding
Extract and restate the key metadata fields and relevant observable properties.

Part B: Scientific Interpretation
Provide a concise scientific interpretation of the candidate based on the images and metadata.

Part C: Staged Classification
Make a step-by-step classification decision:
- Stage 1: Determine whether the detection is a real astrophysical object or bogus
- Stage 2: Determine whether it is astrophysical or non_astrophysical
- Stage 3: Assign one of the five classes: SN, AGN, VS, asteroid, or bogus

Your final answer must follow the required JSON format exactly."""

OUTPUT_JSON_SCHEMA_DOC = """
{
  "Part A": {
    "band": "...",
    "magnitude": "...",
    "sgscore": "...",
    "key_features": "..."
  },
  "Part B": {
    "interpretation": "..."
  },
  "Part C": {
    "stage1": "real_object | bogus",
    "stage2": "astrophysical | non_astrophysical",
    "stage3": "SN | AGN | VS | asteroid | bogus",
    "confidence": 0.0
  }
}
"""


def build_user_prompt(
    oid: str,
    metadata: dict[str, Any],
) -> str:
    """
    Serialize one benchmark example into the user prompt.
    `metadata` should include prompt-facing fields; use \"N/A\" for missing AVRO fields.
    """
    band = metadata.get("band") or metadata.get("fid_band") or "N/A"
    magpsf = metadata.get("magpsf", "N/A")
    sgscore1 = metadata.get("sgscore1", "N/A")
    extra = metadata.get("extra_lines", "")
    if isinstance(extra, list):
        extra = "\n".join(f"    - {line}" for line in extra)
    if extra:
        extra = "\n" + str(extra)

    # NOTE: not an f-string — OUTPUT_JSON_SCHEMA_DOC contains literal { } for JSON.
    return (
        f"""Alert ID: {oid}

Images:
- Science image: recent observation
- Template image: reference observation
- Difference image: Science minus Template

Metadata:
- Band: {band}
- Magnitude (magpsf): {magpsf}
- sgscore1: {sgscore1}
- Detection statistics and additional fields as provided{extra}

Task: Analyze the image triplet and metadata, then complete Parts A--C.

Class Definitions:
- SN (Supernova): Transient event not present in template, often point-like and located near a host galaxy
- AGN: Persistent or variably bright source associated with a galaxy nucleus
- VS (Variable Star): Stellar variability, typically present in both Science and Template images
- Asteroid: Moving object, may show positional shift or streak-like morphology
- Bogus: Artifacts such as noise, cosmic rays, subtraction errors, or misalignment

Instructions:
1. Focus on the central object in the images
2. Compare Science, Template, and Difference images
3. Use metadata to support your reasoning
4. Follow the staged classification process

Output Format (strict JSON):
"""
        + OUTPUT_JSON_SCHEMA_DOC
    )


def _cell(row: Any, key: str) -> Any:
    if hasattr(row, "index") and key in row.index:
        v = row[key]
        if pd.isna(v):
            return None
        return v
    return None


def manifest_row_to_metadata(row: Any) -> dict[str, Any]:
    """Build metadata dict from a pandas Series / manifest row (CSV may lack AVRO fields)."""
    extra_lines: list[str] = []
    for col, label in [
        ("ndet", "ndet"),
        ("meanra", "mean RA (deg)"),
        ("meandec", "mean Dec (deg)"),
        ("firstmjd", "first MJD"),
        ("lastmjd", "last MJD"),
        ("deltajd", "delta MJD"),
        ("stellar", "stellar flag"),
        ("probability", "ALeRCE stamp probability"),
    ]:
        v = _cell(row, col)
        if v is not None and str(v) != "nan":
            extra_lines.append(f"{label}: {v}")
    return {
        "band": _cell(row, "fid_band"),
        "magpsf": _cell(row, "magpsf"),
        "sgscore1": _cell(row, "sgscore1"),
        "extra_lines": extra_lines,
    }


