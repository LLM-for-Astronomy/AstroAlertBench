"""Evaluate standalone class-probability calibration (P_correct vs Y).

This standalone experiment evaluates pure predictive class confidence against
actual binary correctness Y in {0,1}, cleanly separating classification
calibration from Part B rationale quality self-scores.

Reads a JSONL produced with ``--prompts prompts_class_probability_calibration``
and reports:

Calibration
  - ECE exact (one bin per distinct P value) / equal-width / equal-mass
  - MCE, signed ECE (mean conf - accuracy)
  - Brier score + Murphy decomposition (reliability / resolution / uncertainty)
  - Brier skill score vs constant base-rate forecast
  - Negative log-likelihood (NLL)
  - Adaptive Calibration Error (ACE = equal-mass ECE)
  - Overconfidence / underconfidence rates

Discrimination
  - AUROC (tie-aware), Somers' D, Kendall tau-b, Spearman rho, Pearson r
  - AUROC permutation p-value

Operational / selective prediction
  - accuracy at P >= {0.5, 0.7, 0.9}
  - coverage at those thresholds
  - risk-coverage curve points (mean risk when retaining top-k by confidence)

Usage::

    python -m evaluate.evaluate_class_probability \\
        --predictions results/classprob_gpt54_high_n300.jsonl \\
        --manifest data_class_probability_calibration/manifest_class_prob_300.csv \\
        --json results/classprob_gpt54_high_n300.metrics.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for _subdir in ("evaluate", "prompts"):
    _p = ROOT / _subdir
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from evaluate import (  # noqa: E402
    GOLD_STAGES,
    extract_json_object,
    normalize_stage1,
    normalize_stage2,
    normalize_stage3_label,
    stages_to_final_class,
)
from prompts_class_probability_calibration import extract_p_correct  # noqa: E402

# Reuse the calibration primitives already validated against Table 14.
from evaluate_calibration import (  # noqa: E402
    auroc,
    auroc_permutation_p,
    bin_stats,
    brier,
    brier_skill_score,
    ece_equal_mass,
    ece_equal_width,
    ece_exact,
    mce_exact,
    murphy_decomposition,
    pearson_r,
    signed_ece,
    somers_d,
)


def _pred_final(parsed: dict | None) -> str | None:
    if not isinstance(parsed, dict):
        return None
    part_c = parsed.get("Part C") or parsed.get("part_c")
    if not isinstance(part_c, dict):
        return None
    s1 = normalize_stage1(part_c.get("stage1"))
    s2 = normalize_stage2(part_c.get("stage2"))
    s3 = normalize_stage3_label(part_c.get("stage3"))
    if s1 is None or s2 is None or s3 is None:
        return None
    return stages_to_final_class(s1, s2, s3)


def load_pairs(predictions_path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Return (p, y, diagnostics) for every row with parseable Part C + P_correct."""
    p_list: list[float] = []
    y_list: list[int] = []
    n_rows = 0
    n_err = 0
    n_no_parse = 0
    n_no_p = 0
    n_no_label = 0
    by_class: dict[str, list[tuple[float, int]]] = {}

    with open(predictions_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n_rows += 1
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                n_no_parse += 1
                continue
            if r.get("error"):
                n_err += 1
                continue
            tc = r.get("target_class")
            if tc is None or str(tc) not in GOLD_STAGES:
                n_no_label += 1
                continue
            parsed = r.get("parsed")
            if parsed is None:
                parsed = extract_json_object(r.get("answer_text") or r.get("raw_text") or "")
            pred = _pred_final(parsed if isinstance(parsed, dict) else None)
            p_val = extract_p_correct(parsed if isinstance(parsed, dict) else None)
            if pred is None:
                n_no_parse += 1
                continue
            if p_val is None:
                n_no_p += 1
                continue
            y = int(pred == str(tc))
            p_list.append(p_val)
            y_list.append(y)
            by_class.setdefault(str(tc), []).append((p_val, y))

    diag = {
        "n_rows": n_rows,
        "n_transport_error": n_err,
        "n_unparseable_or_incomplete_part_c": n_no_parse,
        "n_missing_p_correct": n_no_p,
        "n_missing_gold": n_no_label,
        "n_linked": len(p_list),
        "per_class_n": {k: len(v) for k, v in by_class.items()},
    }
    return np.asarray(p_list, dtype=float), np.asarray(y_list, dtype=int), diag


def nll(p: np.ndarray, y: np.ndarray, eps: float = 1e-12) -> float:
    """Mean Bernoulli negative log-likelihood of the stated probabilities."""
    p_c = np.clip(p, eps, 1.0 - eps)
    return float(-np.mean(y * np.log(p_c) + (1 - y) * np.log(1 - p_c)))


def selective_stats(p: np.ndarray, y: np.ndarray, thresh: float) -> dict[str, float]:
    mask = p >= thresh
    n = int(mask.sum())
    if n == 0:
        return {"threshold": thresh, "n": 0, "coverage": 0.0, "accuracy": float("nan")}
    return {
        "threshold": thresh,
        "n": n,
        "coverage": float(n / len(p)),
        "accuracy": float(y[mask].mean()),
    }


def risk_coverage_curve(p: np.ndarray, y: np.ndarray,
                        coverages: list[float] | None = None) -> list[dict[str, float]]:
    """Mean error rate when retaining the top fraction of rows by confidence."""
    if coverages is None:
        coverages = [0.2, 0.4, 0.6, 0.8, 1.0]
    order = np.argsort(-p)
    y_sorted = y[order]
    out = []
    n = len(y)
    for c in coverages:
        k = max(1, int(round(c * n)))
        retained = y_sorted[:k]
        out.append({
            "coverage": float(c),
            "n": int(k),
            "accuracy": float(retained.mean()),
            "risk": float(1.0 - retained.mean()),
        })
    return out


def analyse(p: np.ndarray, y: np.ndarray, diag: dict[str, Any],
            n_perm: int = 5000) -> dict[str, Any]:
    if len(p) == 0:
        return {"error": "no linked rows", "diagnostics": diag}

    dec = murphy_decomposition(p, y)
    tau = stats.kendalltau(p, y)
    spear = stats.spearmanr(p, y)

    # Over/under-confidence: high-P wrong / low-P correct
    over_mask = (p >= 0.9) & (y == 0)
    under_mask = (p <= 0.3) & (y == 1)

    bins = [
        {"conf": v, "acc": acc, "n": cnt, "gap": abs(v - acc)}
        for v, acc, cnt in bin_stats(p, y)
    ]

    out: dict[str, Any] = {
        "note": (
            "This standalone experiment evaluates pure predictive class confidence "
            "against actual binary correctness Y in {0,1}, cleanly separating "
            "classification calibration from Part B rationale quality self-scores."
        ),
        "diagnostics": diag,
        "n_linked": int(len(p)),
        "accuracy": float(y.mean()),
        "mean_p_correct": float(p.mean()),
        "sd_p_correct": float(p.std(ddof=1)) if len(p) > 1 else 0.0,
        "n_distinct_p": int(len(np.unique(np.round(p, 6)))),
        "p_min": float(p.min()),
        "p_max": float(p.max()),
        "p_median": float(np.median(p)),
        "frac_p_ge_0_9": float((p >= 0.9).mean()),
        "frac_p_le_0_3": float((p <= 0.3).mean()),

        "signed_ece": signed_ece(p, y),
        "ece_exact": ece_exact(p, y),
        "ece_ew15": ece_equal_width(p, y, 15),
        "ece_ew10": ece_equal_width(p, y, 10),
        "ece_em10": ece_equal_mass(p, y, 10),  # aka ACE
        "ace_em10": ece_equal_mass(p, y, 10),
        "mce_exact": mce_exact(p, y, min_count=5),

        "brier": brier(p, y),
        "reliability": dec.reliability,
        "resolution": dec.resolution,
        "uncertainty": dec.uncertainty,
        "brier_skill": brier_skill_score(p, y),
        "nll": nll(p, y),

        "auroc": auroc(p, y),
        "somers_d": somers_d(p, y),
        "kendall_tau_b": float(tau.correlation) if tau.correlation is not None else float("nan"),
        "spearman_rho": float(spear.correlation) if spear.correlation is not None else float("nan"),
        "pearson_r": pearson_r(p, y),
        "auroc_perm_p": auroc_permutation_p(p, y, n_perm=n_perm),

        "overconfidence_rate_p90": float(over_mask.mean()),
        "overconfidence_n_p90": int(over_mask.sum()),
        "underconfidence_rate_p30": float(under_mask.mean()),
        "underconfidence_n_p30": int(under_mask.sum()),

        "selective": [
            selective_stats(p, y, t) for t in (0.5, 0.7, 0.8, 0.9)
        ],
        "risk_coverage": risk_coverage_curve(p, y),
        "bins": bins,
    }
    return out


def _print(m: dict[str, Any]) -> None:
    if "error" in m:
        print(m)
        return
    d = m["diagnostics"]
    print(f"n_rows={d['n_rows']}  n_linked={m['n_linked']}  "
          f"transport_err={d['n_transport_error']}  "
          f"no_P={d['n_missing_p_correct']}  incomplete={d['n_unparseable_or_incomplete_part_c']}")
    print(f"accuracy={m['accuracy']:.4f}  mean_P={m['mean_p_correct']:.4f}  "
          f"sd_P={m['sd_p_correct']:.4f}  n_distinct_P={m['n_distinct_p']}")
    print(f"ECE_exact={m['ece_exact']:.4f}  ECE_ew15={m['ece_ew15']:.4f}  "
          f"ACE_em10={m['ace_em10']:.4f}  signed_ECE={m['signed_ece']:+.4f}")
    print(f"Brier={m['brier']:.4f}  REL={m['reliability']:.4f}  "
          f"RES={m['resolution']:.4f}  BSS={m['brier_skill']:+.4f}  NLL={m['nll']:.4f}")
    print(f"AUROC={m['auroc']:.4f}  perm_p={m['auroc_perm_p']:.4g}  "
          f"SomersD={m['somers_d']:+.4f}  spearman={m['spearman_rho']:+.4f}")
    print("selective accuracy:")
    for s in m["selective"]:
        print(f"  P>={s['threshold']}: n={s['n']} cov={s['coverage']:.2f} "
              f"acc={s['accuracy']:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--predictions", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=None,
                    help="Optional; currently unused for scoring (gold is on JSONL rows).")
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--permutations", type=int, default=5000)
    args = ap.parse_args()
    _ = args.manifest  # reserved for future gold-from-manifest mode

    p, y, diag = load_pairs(args.predictions)
    metrics = analyse(p, y, diag, n_perm=args.permutations)
    metrics["predictions"] = str(args.predictions)
    _print(metrics)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
