"""
Evaluation for AstroAlertBench-style JSON outputs (Parts A–C).

Metrics:
  - JSON validity rate
  - Stage-3 top-1 accuracy vs. manifest target_class (ALeRCE label)
  - Optional: stage1/stage2 consistency checks
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

VALID_STAGE3 = {"SN", "AGN", "VS", "asteroid", "bogus"}


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Parse first JSON object from model output (handles ```json fences)."""
    if not text or not text.strip():
        return None
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", s)
    if fence:
        s = fence.group(1).strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    # try last { ... } block
    start = s.rfind("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(s[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def normalize_stage3(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    # allow "SN | AGN | ..." instruction leakage: take first token-like
    for tok in VALID_STAGE3:
        if tok.upper() == s.upper() or tok.upper() == s.split()[0].upper():
            return tok
    low = s.lower()
    if "asteroid" in low:
        return "asteroid"
    if "bogus" in low and "non" not in low:
        return "bogus"
    if "agn" in low or "active galactic" in low:
        return "AGN"
    if "supernova" in low or s.upper() == "SN":
        return "SN"
    if "variable" in low or s.upper() == "VS":
        return "VS"
    return None


def evaluate_jsonl(
    predictions_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """
    predictions_jsonl: one JSON per line with keys oid, target_class (gold), raw_text, parsed (optional)
    """
    manifest = pd.read_csv(manifest_path)
    gold = manifest.set_index("oid")["target_class"].to_dict()

    rows = []
    with open(predictions_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    n = len(rows)
    json_ok = 0
    stage3_pred_ok = 0
    stage3_with_gold = 0
    per_class_total: Counter[str] = Counter()
    per_class_correct: Counter[str] = Counter()

    for r in rows:
        if r.get("error"):
            continue
        oid = r["oid"]
        g = gold.get(oid, r.get("target_class"))
        raw = r.get("raw_text", "")
        parsed = r.get("parsed")
        if parsed is None:
            parsed = extract_json_object(raw)
        if parsed is None:
            continue
        json_ok += 1
        part_c = parsed.get("Part C") or parsed.get("part_c")
        if not isinstance(part_c, dict):
            continue
        pred = normalize_stage3(part_c.get("stage3"))
        if pred is None:
            continue
        if g is None:
            continue
        stage3_with_gold += 1
        per_class_total[str(g)] += 1
        if pred == g:
            stage3_pred_ok += 1
            per_class_correct[str(g)] += 1

    acc = stage3_pred_ok / stage3_with_gold if stage3_with_gold else 0.0

    return {
        "n_examples": n,
        "json_parseable": json_ok,
        "json_valid_rate": json_ok / n if n else 0.0,
        "stage3_evaluable_with_gold": stage3_with_gold,
        "stage3_accuracy_vs_gold": acc,
        "per_class_total": dict(per_class_total),
        "per_class_correct": dict(per_class_correct),
    }


def print_report(metrics: dict[str, Any]) -> None:
    for k, v in metrics.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Evaluate JSONL predictions vs manifest")
    ap.add_argument("--predictions", type=Path, required=True, help="JSONL from run_tinker_benchmark.py")
    ap.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    args = ap.parse_args()
    m = evaluate_jsonl(args.predictions, args.manifest)
    print_report(m)
