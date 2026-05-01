"""Compute stats for 20260430_report_human_baseline_examples.md (stdout JSON-ish)."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import math

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

LABEL_TO_GOLD = {
    "Variable Star": "VS",
    "Supernova": "SN",
    "Active Galactic Nucleus": "AGN",
    "Asteroid": "asteroid",
    "Artifact (bogus)": "bogus",
}
GOLD_LABELS = ("SN", "VS", "AGN", "asteroid", "bogus")


def se_prop(p: float, n: int) -> float:
    """Binomial SE for proportion p with denominator n (1σ)."""
    if n <= 0:
        return 0.0
    p = min(max(p, 0.0), 1.0)
    return math.sqrt(p * (1.0 - p) / n)


def oid_from_row(r: dict) -> str:
    sd = json.loads(r["subject_data"])
    for v in sd.values():
        fn = v.get("Filename", "")
        return fn.replace(".png", "").replace(".jpg", "").strip()
    return ""


def raw_t0_value(r: dict) -> str | None:
    for t in json.loads(r["annotations"]):
        if t.get("task") == "T0":
            return t.get("value")
    return None


def is_dk(r: dict) -> bool:
    return raw_t0_value(r) == "Don't Know"


def majority_pred_for_oid(rows: list[dict]) -> str | None:
    """Plurality with strict majority on 5 votes: need >=3 for one label.

    DK and unmapped values count as their own bucket; only a single physical
    class label (SN, VS, AGN, asteroid, bogus) with >=3 votes and strict
    plurality wins. Otherwise None (no collective label).
    """
    votes: list[str] = []
    for r in rows:
        val = raw_t0_value(r)
        if val == "Don't Know" or val is None:
            votes.append("DK")
        else:
            m = LABEL_TO_GOLD.get(val)
            votes.append(m if m is not None else "OTHER")
    ctr = Counter(votes)
    best = ctr.most_common()
    if not best:
        return None
    top_lab, top_n = best[0]
    if top_n < 3:
        return None
    if top_lab in ("DK", "OTHER"):
        return None
    if len(best) > 1 and best[1][1] == top_n:
        return None
    return top_lab


def macro_f1_nominal(
    golds: list[str],
    preds: list[str | None],
) -> float:
    """One-vs-rest macro-F1; `None` prediction yields no positive for any class."""
    f1s: list[float] = []
    for c in GOLD_LABELS:
        tp = fp = fn = 0
        for g, p in zip(golds, preds):
            if p is None:
                if g == c:
                    fn += 1
                continue
            if p == c and g == c:
                tp += 1
            elif p == c and g != c:
                fp += 1
            elif p != c and g == c:
                fn += 1
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        f1s.append(f1)
    return float(np.mean(f1s))


def compute_human_baseline_examples_stats(
    csv_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict:
    if csv_path is None:
        csv_path = ROOT / "llm-for-astronomy-classifications_human-baseline-final_filtered_with_is_correct.csv"
    if manifest_path is None:
        manifest_path = ROOT / "data" / "manifest_human_baselines_15.csv"

    manifest: dict[str, str] = {}
    with manifest_path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            manifest[r["oid"]] = r["target_class"]

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    by_oid: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_oid[oid_from_row(r)].append(r)

    k_dist = Counter()
    for oid in sorted(by_oid):
        k = sum(1 for x in by_oid[oid] if x["is_correct"] == "true")
        k_dist[k] += 1

    # per-user accuracy
    by_user: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        by_user[r["user_name"]].append(r["is_correct"] == "true")

    n = len(rows)
    n_dk = sum(1 for r in rows if is_dk(r))
    n_correct = sum(1 for r in rows if r["is_correct"] == "true")
    effective = n_correct / n if n else 0.0
    selective = n_correct / (n - n_dk) if (n - n_dk) else float("nan")

    # ensemble (majority over 5 experts; denominator 15 IDs)
    gold_list: list[str] = []
    pred_list: list[str | None] = []
    maj_ok = 0
    for oid in sorted(by_oid):
        g = manifest[oid]
        gold_list.append(g)
        pred = majority_pred_for_oid(by_oid[oid])
        pred_list.append(pred)
        if pred is not None and pred == g:
            maj_ok += 1

    maj_f1 = macro_f1_nominal(gold_list, pred_list)

    at_least_k = {}
    oid_k_list = []
    for oid in sorted(by_oid):
        kk = sum(1 for x in by_oid[oid] if x["is_correct"] == "true")
        oid_k_list.append(kk)
    for k in range(1, 6):
        at_least_k[k] = sum(1 for kk in oid_k_list if kk >= k) / 15.0

    none_preds = sum(1 for p in pred_list if p is None)

    n_ids = 15
    k_dist_frac = {k: k_dist.get(k, 0) / n_ids for k in range(0, 6)}
    k_dist_se = {k: se_prop(k_dist_frac[k], n_ids) for k in k_dist_frac}

    at_least_k_se = {}
    for k in range(1, 6):
        m = sum(1 for kk in oid_k_list if kk >= k)
        pk = m / n_ids
        at_least_k_se[k] = se_prop(pk, n_ids)

    per_user_out = {}
    for u in sorted(by_user):
        s = sum(by_user[u])
        pu = s / n_ids
        per_user_out[u] = {
            "n_correct": s,
            "acc": pu,
            "acc_se": se_prop(pu, n_ids),
        }

    p_ens = maj_ok / n_ids
    p_ref = n_dk / n if n else 0.0
    p_eff = effective
    n_sel = n - n_dk
    p_sel = selective if math.isfinite(selective) else 0.0

    return {
        "k_dist": dict(sorted(k_dist.items())),
        "k_dist_frac": k_dist_frac,
        "k_dist_se": k_dist_se,
        "at_least_k_frac": at_least_k,
        "at_least_k_se": at_least_k_se,
        "per_user": per_user_out,
        "n_rows": n,
        "n_dk": n_dk,
        "refusal_rate": p_ref,
        "refusal_rate_se": se_prop(p_ref, n),
        "effective_accuracy": p_eff,
        "effective_accuracy_se": se_prop(p_eff, n),
        "selective_accuracy": selective,
        "selective_accuracy_se": se_prop(p_sel, n_sel) if n_sel > 0 else 0.0,
        "ensemble_n_none": none_preds,
        "ensemble_correct": maj_ok,
        "ensemble_accuracy": p_ens,
        "ensemble_accuracy_se": se_prop(p_ens, n_ids),
        "ensemble_macro_f1": maj_f1,
    }


def main() -> None:
    o = compute_human_baseline_examples_stats()
    print("=== k_dist", o["k_dist"])
    print("=== at_least_k_frac", o["at_least_k_frac"])
    print("=== per_user (acc +/- 1*SE on p, n=15)")
    for u, d in o["per_user"].items():
        print(f"  {u} {d['n_correct']}/15 {d['acc']:.4f} +/- {d['acc_se']:.4f}")
    print("=== n", o["n_rows"], "n_dk", o["n_dk"])
    print(
        "=== refusal",
        o["refusal_rate"],
        "+/-",
        o["refusal_rate_se"],
    )
    print(
        "=== effective",
        o["effective_accuracy"],
        "+/-",
        o["effective_accuracy_se"],
    )
    print(
        "=== selective",
        o["selective_accuracy"],
        "+/-",
        o["selective_accuracy_se"],
    )
    print("=== ensemble_none_preds", o["ensemble_n_none"], "/15")
    print(
        "=== ensemble_maj",
        o["ensemble_correct"],
        "/15",
        o["ensemble_accuracy"],
        "+/-",
        o["ensemble_accuracy_se"],
    )
    print("=== ensemble_macro_f1", o["ensemble_macro_f1"])


if __name__ == "__main__":
    main()
