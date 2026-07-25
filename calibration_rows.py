"""Canonical per-row confidence/correctness extraction for calibration analysis.

This is the single source of truth for the row set behind every calibration
number we report. `evaluate.evaluate_jsonl` derives `bc_confidence` / `bc_correct`
internally but does not persist the per-row arrays, so anything that needs to
re-bin, re-weight, or bootstrap has to re-derive them from `run.jsonl`. Having
two copies of that linkage logic is how the submitted Table 14 ended up quoting
`json_parseable` in its `n_linked` column, so all consumers import from here.

A row is *linked* (and therefore eligible) when it satisfies all of:
  - no transport-level `error`
  - a gold `target_class`
  - a parseable JSON object
  - a Part B with all three rubric self-scores present
  - a Part C whose three stages normalize and compose into a 5-class label

which mirrors `evaluate.evaluate_jsonl` exactly.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluate import (  # noqa: E402
    GOLD_STAGES,
    extract_json_object,
    extract_self_scores,
    normalize_stage1,
    normalize_stage2,
    normalize_stage3_label,
    stages_to_final_class,
)

# The self-score rubric is 0-5 over three dimensions; dividing by this maps a
# rubric mean onto [0, 1] so it can be read as a correctness probability.
RUBRIC_MAX = 5.0


@dataclass(frozen=True)
class RunSpec:
    """One evaluated configuration: paper-facing label plus its run folder."""

    label: str
    folder: str
    family: str
    color: str
    marker: str


# The 13 configurations of the main benchmark table, in the paper's Table 1 order.
RUNS: tuple[RunSpec, ...] = (
    RunSpec("Claude Opus 4.7 think",    "runs/20260423-0942-opus47-think-benchmark-full",             "Claude", "tab:orange", "o"),
    RunSpec("GPT-5.4 high-think",       "runs/20260421-2024-gpt-5.4-high-benchmark-full",             "GPT",    "tab:blue",   "o"),
    RunSpec("Kimi K2.5 think",          "runs/20260420-1226-kimi-k25-benchmark-full",                 "Kimi",   "tab:purple", "o"),
    RunSpec("Claude Opus 4.7 nothink",  "runs/20260424-2324-opus47-nothink-benchmark-full",           "Claude", "tab:orange", "s"),
    RunSpec("Qwen3.5-397B-A17B think",  "runs/20260420-1554-qwen35-397b-a17b-benchmark-full",         "Qwen",   "tab:red",    "o"),
    RunSpec("GPT-5.4 no-think",         "runs/20260421-2032-gpt-5.4-none-benchmark-full",             "GPT",    "tab:blue",   "s"),
    RunSpec("Gemini 2.5 Pro high-think", "runs/20260424-1809-gemini25-pro-high-benchmark-full",       "Gemini", "tab:green",  "o"),
    RunSpec("Gemini 2.5 Flash no-think", "runs/20260423-2110-gemini25-flash-none-benchmark-full",     "Gemini", "tab:green",  "s"),
    RunSpec("Qwen3.5-397B-A17B nothink", "runs/20260421-0025-qwen35-397b-a17b-nothink-benchmark-full", "Qwen",  "tab:red",    "s"),
    RunSpec("Qwen3.5-35B-A3B think",    "runs/20260420-2054-qwen35-35b-a3b-benchmark-full",           "Qwen",   "tab:pink",   "o"),
    RunSpec("Qwen3.5-35B-A3B nothink",  "runs/20260421-0019-qwen35-35b-a3b-nothink-benchmark-full",   "Qwen",   "tab:pink",   "s"),
    RunSpec("Qwen3.5-4B nothink",       "runs/20260421-0002-qwen35-4b-nothink-benchmark-full",        "Qwen",   "tab:brown",  "s"),
    RunSpec("Qwen3.5-4B think",         "runs/20260420-1920-qwen35-4b-benchmark-full",                "Qwen",   "tab:brown",  "o"),
)

RUNS_BY_LABEL = {r.label: r for r in RUNS}


def load_conf_pairs(jsonl_path: Path) -> list[tuple[float, int]]:
    """Return (self_score_mean, is_correct) for every linked row in a run.jsonl."""
    out: list[tuple[float, int]] = []
    if not Path(jsonl_path).is_file():
        return out
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("error"):
                continue
            tc = r.get("target_class")
            if tc is None:
                continue
            parsed = r.get("parsed")
            if parsed is None:
                parsed = extract_json_object(r.get("answer_text") or r.get("raw_text") or "")
            if not isinstance(parsed, dict):
                continue
            part_b = parsed.get("Part B") or parsed.get("part_b")
            if not isinstance(part_b, dict):
                continue
            scores = extract_self_scores(part_b)
            if not all(s is not None for s in scores):
                continue
            self_mean = float(np.mean(scores))

            part_c = parsed.get("Part C") or parsed.get("part_c")
            if not isinstance(part_c, dict):
                continue
            gold_stages = GOLD_STAGES.get(str(tc))
            if gold_stages is None:
                continue
            s1 = normalize_stage1(part_c.get("stage1"))
            s2 = normalize_stage2(part_c.get("stage2"))
            s3 = normalize_stage3_label(part_c.get("stage3"))
            if s1 is None or s2 is None or s3 is None:
                continue
            pred_final = stages_to_final_class(s1, s2, s3)
            if pred_final is None:
                continue
            out.append((self_mean, int(pred_final == str(tc))))
    return out


def load_run_arrays(spec: RunSpec, project_root: Path | None = None
                    ) -> tuple[np.ndarray, np.ndarray]:
    """Return (confidence in [0,1], correctness in {0,1}) arrays for one run."""
    root = project_root or PROJECT_ROOT
    pairs = load_conf_pairs(root / spec.folder / "run.jsonl")
    if not pairs:
        return np.zeros(0), np.zeros(0, dtype=int)
    arr = np.asarray(pairs, dtype=float)
    return arr[:, 0] / RUBRIC_MAX, arr[:, 1].astype(int)
