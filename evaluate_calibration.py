"""Standard calibration metrics (ECE, Brier) for Part B self-scores.

Motivation: the submitted paper summarises within-run calibration with two
bespoke scalars, a mean-difference "calibration gap" and a point-biserial
Pearson r. Reviewer 2005 asked for standard metrics instead. This module adds
them without discarding the originals.

Confidence mapping. The rubric mean c in [0, 5] is mapped to a correctness
probability p = c / 5. That is an interpretive choice: the rubric asks the model
to grade its *reasoning quality*, not to state a probability that its Part C
label is right. Metrics are therefore split into two groups:

  mapping-dependent   ECE variants, Brier, Brier skill score
  mapping-invariant   AUROC, Somers' D, Kendall tau-b, Spearman rho, and any
                      cross-validated recalibration result

The invariant group depends only on the *ordering* of the scores, so those
numbers are unchanged under any monotone re-mapping of the rubric and can carry
conclusions that the p = c/5 assumption cannot.

Binning. The self-scores take only 3-7 distinct values per run (three integer
sub-scores averaged), so `ece_exact` uses one bin per observed value: an ECE
with no binning degrees of freedom at all. Equal-width and equal-mass variants
are reported alongside purely for comparability with the wider literature.

Usage:
    python evaluate_calibration.py                       # table to stdout
    python evaluate_calibration.py --json out.json       # + machine-readable
    python evaluate_calibration.py --bootstrap 2000      # CIs (default 2000)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from calibration_rows import RUBRIC_MAX, RUNS, RunSpec, load_run_arrays  # noqa: E402


# --------------------------------------------------------------------------- #
# Calibration (mapping-dependent)
# --------------------------------------------------------------------------- #

def bin_stats(p: np.ndarray, y: np.ndarray) -> list[tuple[float, float, int]]:
    """Group rows by distinct forecast value.

    Returns (forecast, empirical accuracy, count) per distinct value, ascending.
    These are the natural bins for a discrete forecaster: no bin-count choice is
    involved, so the resulting ECE has no tuning knob.
    """
    out: list[tuple[float, float, int]] = []
    for v in np.unique(p):
        m = p == v
        out.append((float(v), float(y[m].mean()), int(m.sum())))
    return out


def ece_exact(p: np.ndarray, y: np.ndarray) -> float:
    """Expected calibration error over per-distinct-value bins."""
    n = len(p)
    return float(sum(cnt / n * abs(v - acc) for v, acc, cnt in bin_stats(p, y)))


def mce_exact(p: np.ndarray, y: np.ndarray, min_count: int = 10) -> float:
    """Worst-bin calibration error, ignoring bins too small to estimate."""
    gaps = [abs(v - acc) for v, acc, cnt in bin_stats(p, y) if cnt >= min_count]
    return float(max(gaps)) if gaps else float("nan")


def ece_equal_width(p: np.ndarray, y: np.ndarray, n_bins: int = 15) -> float:
    """Classic Guo et al. ECE with equal-width bins on [0, 1]."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1], right=True), 0, n_bins - 1)
    n = len(p)
    total = 0.0
    for b in range(n_bins):
        m = idx == b
        if not m.any():
            continue
        total += m.sum() / n * abs(p[m].mean() - y[m].mean())
    return float(total)


def ece_equal_mass(p: np.ndarray, y: np.ndarray, n_bins: int = 10) -> float:
    """Equal-mass (adaptive) ECE.

    Ties must not be split across bins or the bin boundaries would encode
    nothing, so distinct values are merged greedily towards a target occupancy
    of n / n_bins. With only a handful of distinct values the realised bin count
    is usually below `n_bins`; that is a property of the data, not a bug.
    """
    groups = bin_stats(p, y)
    n = len(p)
    target = max(n / n_bins, 1.0)
    total, cur_n, cur_p, cur_pos = 0.0, 0, 0.0, 0.0
    for v, acc, cnt in groups:
        cur_n += cnt
        cur_p += v * cnt
        cur_pos += acc * cnt
        if cur_n >= target:
            total += cur_n / n * abs(cur_p / cur_n - cur_pos / cur_n)
            cur_n, cur_p, cur_pos = 0, 0.0, 0.0
    if cur_n:
        total += cur_n / n * abs(cur_p / cur_n - cur_pos / cur_n)
    return float(total)


def signed_ece(p: np.ndarray, y: np.ndarray) -> float:
    """Calibration-in-the-large: mean confidence minus accuracy.

    Positive means overconfident. Unlike ECE this keeps its sign, which is what
    makes it readable as an honesty statement rather than an error magnitude.
    """
    return float(p.mean() - y.mean())


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


@dataclass
class MurphyDecomposition:
    """Brier = reliability - resolution + uncertainty, over the natural bins.

    reliability   how far each bin's forecast sits from its own accuracy
                  (the miscalibration the reviewer wants measured)
    resolution    how far bin accuracies spread around the base rate
                  (the discrimination the paper's 5.2 claim is actually about)
    uncertainty   base-rate variance, the Brier of a constant forecaster
    """

    reliability: float
    resolution: float
    uncertainty: float

    @property
    def brier_from_terms(self) -> float:
        return self.reliability - self.resolution + self.uncertainty


def murphy_decomposition(p: np.ndarray, y: np.ndarray) -> MurphyDecomposition:
    n = len(p)
    ybar = float(y.mean())
    rel = res = 0.0
    for v, acc, cnt in bin_stats(p, y):
        w = cnt / n
        rel += w * (v - acc) ** 2
        res += w * (acc - ybar) ** 2
    return MurphyDecomposition(rel, res, ybar * (1.0 - ybar))


def brier_skill_score(p: np.ndarray, y: np.ndarray) -> float:
    """Skill relative to always forecasting the run's own accuracy.

    BSS > 0 means the self-score beats a forecaster that knows only the run's
    overall accuracy; BSS < 0 means it is actively worse than that baseline.
    This is the single number that answers "is the confidence dial worth
    reading at all", and it is unaffected by the ceiling effect.
    """
    unc = float(y.mean() * (1.0 - y.mean()))
    return float(1.0 - brier(p, y) / unc) if unc > 0 else float("nan")


# --------------------------------------------------------------------------- #
# Discrimination (mapping-invariant)
# --------------------------------------------------------------------------- #

def auroc(p: np.ndarray, y: np.ndarray) -> float:
    """Tie-aware c-statistic via midranks (Mann-Whitney U / n_pos n_neg).

    0.5 means the score cannot order a correct answer above an incorrect one.
    Heavy ties are handled by midranks, which is why this survives a 3-value
    score distribution where Pearson r is attenuated by coarseness.
    """
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = stats.rankdata(p)
    u = ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def somers_d(p: np.ndarray, y: np.ndarray) -> float:
    a = auroc(p, y)
    return float(2.0 * a - 1.0) if not math.isnan(a) else float("nan")


def pearson_r(p: np.ndarray, y: np.ndarray) -> float:
    """Point-biserial r, i.e. the paper's existing Table 14 column."""
    if p.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(p, y)[0, 1])


def pearson_r_max(p: np.ndarray, y: np.ndarray) -> float:
    """Largest r attainable given this score multiset and base rate.

    Obtained by handing every correct answer to the highest scores. Reporting
    r / r_max separates "the dial carries no signal" from "the dial is too coarse
    to express the signal", which is the legitimate half of the reviewer's
    range-restriction concern.
    """
    n_pos = int(y.sum())
    if n_pos == 0 or n_pos == len(y):
        return float("nan")
    order = np.argsort(-p, kind="stable")
    y_best = np.zeros_like(y)
    y_best[order[:n_pos]] = 1
    return pearson_r(p, y_best)


def auroc_permutation_p(p: np.ndarray, y: np.ndarray, n_perm: int = 2000,
                        seed: int = 0) -> float:
    """Two-sided permutation p-value for AUROC = 0.5."""
    obs = abs(auroc(p, y) - 0.5)
    if math.isnan(obs):
        return float("nan")
    rng = np.random.default_rng(seed)
    y_shuf = y.copy()
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(y_shuf)
        if abs(auroc(p, y_shuf) - 0.5) >= obs:
            hits += 1
    return float((hits + 1) / (n_perm + 1))


# --------------------------------------------------------------------------- #
# Recalibration residuals
# --------------------------------------------------------------------------- #

def _out_of_fold(p: np.ndarray, y: np.ndarray, kind: str, n_splits: int = 5,
                 seed: int = 0) -> np.ndarray | None:
    """Cross-validated recalibrated forecasts.

    In-sample isotonic on a discrete forecaster drives ECE to exactly zero by
    construction (it just relabels each bin with its own accuracy), so an
    in-sample number would be meaningless. Cross-validation keeps the question
    honest: does a monotone re-mapping learned on other rows transfer?
    """
    n_pos, n_neg = int(y.sum()), int(len(y) - y.sum())
    if min(n_pos, n_neg) < n_splits:
        return None
    oof = np.zeros(len(p), dtype=float)
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for tr, te in skf.split(p.reshape(-1, 1), y):
        if kind == "isotonic":
            model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            model.fit(p[tr], y[tr])
            oof[te] = model.predict(p[te])
        else:
            model = LogisticRegression(solver="lbfgs")
            model.fit(p[tr].reshape(-1, 1), y[tr])
            oof[te] = model.predict_proba(p[te].reshape(-1, 1))[:, 1]
    return np.clip(oof, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# Per-run assembly
# --------------------------------------------------------------------------- #

@dataclass
class RunCalibration:
    label: str
    family: str
    n_linked: int
    accuracy: float
    mean_conf: float
    sd_conf_rubric: float
    n_distinct: int

    signed_ece: float
    ece_exact: float
    ece_ew15: float
    ece_ew10: float
    ece_em10: float
    mce_exact: float

    brier: float
    reliability: float
    resolution: float
    uncertainty: float
    brier_skill: float

    auroc: float
    somers_d: float
    kendall_tau_b: float
    spearman_rho: float
    pearson_r: float
    pearson_r_max: float
    pearson_r_ratio: float
    auroc_perm_p: float

    brier_isotonic_cv: float
    ece_isotonic_cv: float
    brier_skill_isotonic_cv: float
    brier_platt_cv: float

    ci: dict[str, list[float]] = field(default_factory=dict)
    bins: list[dict[str, float]] = field(default_factory=list)


_BOOTSTRAP_METRICS = {
    "ece_exact": ece_exact,
    "signed_ece": signed_ece,
    "brier": brier,
    "brier_skill": brier_skill_score,
    "auroc": auroc,
}


def _bootstrap_cis(p: np.ndarray, y: np.ndarray, n_boot: int, seed: int = 0
                   ) -> dict[str, list[float]]:
    """Percentile CIs from a stratified bootstrap (resample within each class).

    Stratifying holds the base rate fixed across resamples, so the interval
    reflects uncertainty in the confidence-correctness relationship rather than
    uncertainty in the run's overall accuracy.
    """
    if n_boot <= 0:
        return {}
    idx_pos = np.flatnonzero(y == 1)
    idx_neg = np.flatnonzero(y == 0)
    if len(idx_pos) == 0 or len(idx_neg) == 0:
        return {}
    rng = np.random.default_rng(seed)
    draws: dict[str, list[float]] = {k: [] for k in _BOOTSTRAP_METRICS}
    for _ in range(n_boot):
        take = np.concatenate([
            rng.choice(idx_pos, len(idx_pos), replace=True),
            rng.choice(idx_neg, len(idx_neg), replace=True),
        ])
        pb, yb = p[take], y[take]
        for name, fn in _BOOTSTRAP_METRICS.items():
            draws[name].append(fn(pb, yb))
    return {
        name: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]
        for name, v in draws.items()
    }


def analyse_run(spec: RunSpec, n_boot: int = 2000, n_perm: int = 2000
                ) -> RunCalibration | None:
    p, y = load_run_arrays(spec)
    if len(p) == 0:
        print(f"  !! no linked rows for {spec.label}", file=sys.stderr)
        return None

    dec = murphy_decomposition(p, y)
    r = pearson_r(p, y)
    r_max = pearson_r_max(p, y)

    iso = _out_of_fold(p, y, "isotonic")
    platt = _out_of_fold(p, y, "platt")
    unc = dec.uncertainty

    return RunCalibration(
        label=spec.label,
        family=spec.family,
        n_linked=len(p),
        accuracy=float(y.mean()),
        mean_conf=float(p.mean()),
        sd_conf_rubric=float(p.std(ddof=1) * RUBRIC_MAX),
        n_distinct=int(len(np.unique(p))),

        signed_ece=signed_ece(p, y),
        ece_exact=ece_exact(p, y),
        ece_ew15=ece_equal_width(p, y, 15),
        ece_ew10=ece_equal_width(p, y, 10),
        ece_em10=ece_equal_mass(p, y, 10),
        mce_exact=mce_exact(p, y),

        brier=brier(p, y),
        reliability=dec.reliability,
        resolution=dec.resolution,
        uncertainty=unc,
        brier_skill=brier_skill_score(p, y),

        auroc=auroc(p, y),
        somers_d=somers_d(p, y),
        kendall_tau_b=float(stats.kendalltau(p, y).correlation),
        spearman_rho=float(stats.spearmanr(p, y).correlation),
        pearson_r=r,
        pearson_r_max=r_max,
        pearson_r_ratio=float(r / r_max) if r_max and not math.isnan(r_max) else float("nan"),
        auroc_perm_p=auroc_permutation_p(p, y, n_perm),

        brier_isotonic_cv=brier(iso, y) if iso is not None else float("nan"),
        ece_isotonic_cv=ece_exact(iso, y) if iso is not None else float("nan"),
        brier_skill_isotonic_cv=(
            float(1.0 - brier(iso, y) / unc) if iso is not None and unc > 0 else float("nan")
        ),
        brier_platt_cv=brier(platt, y) if platt is not None else float("nan"),

        ci=_bootstrap_cis(p, y, n_boot),
        bins=[
            {"conf": v, "acc": acc, "n": cnt, "conf_rubric": v * RUBRIC_MAX}
            for v, acc, cnt in bin_stats(p, y)
        ],
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _print_table(rows: list[RunCalibration]) -> None:
    print("\n=== Calibration (mapping-dependent; p = self_mean / 5) ===")
    hdr = (f"{'Run':<27}{'n':>6}{'acc':>7}{'conf':>7}{'sECE':>8}"
           f"{'ECE':>7}{'EW15':>7}{'EM10':>7}{'Brier':>7}{'REL':>7}{'RES':>7}{'BSS':>8}")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(rows, key=lambda x: -x.ece_exact):
        print(f"{r.label:<27}{r.n_linked:>6}{r.accuracy:>7.3f}{r.mean_conf:>7.3f}"
              f"{r.signed_ece:>+8.3f}{r.ece_exact:>7.3f}{r.ece_ew15:>7.3f}"
              f"{r.ece_em10:>7.3f}{r.brier:>7.3f}{r.reliability:>7.3f}"
              f"{r.resolution:>7.4f}{r.brier_skill:>+8.3f}")

    print("\n=== Discrimination (mapping-invariant) ===")
    hdr2 = (f"{'Run':<27}{'AUROC':>8}{'95% CI':>17}{'permp':>8}{'SomersD':>9}"
            f"{'tau_b':>8}{'r':>8}{'r_max':>8}{'r/rmax':>8}{'BSS_iso':>9}")
    print(hdr2)
    print("-" * len(hdr2))
    for r in sorted(rows, key=lambda x: -(x.auroc if not math.isnan(x.auroc) else 0)):
        lo, hi = r.ci.get("auroc", [float("nan")] * 2)
        print(f"{r.label:<27}{r.auroc:>8.4f}  [{lo:>6.3f},{hi:>6.3f}]{r.auroc_perm_p:>8.4f}"
              f"{r.somers_d:>+9.4f}{r.kendall_tau_b:>+8.4f}{r.pearson_r:>+8.4f}"
              f"{r.pearson_r_max:>8.4f}{r.pearson_r_ratio:>8.3f}"
              f"{r.brier_skill_isotonic_cv:>+9.4f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=None,
                    help="write the full per-run metric dump here")
    ap.add_argument("--bootstrap", type=int, default=2000,
                    help="bootstrap resamples for CIs (0 to skip)")
    ap.add_argument("--permutations", type=int, default=2000,
                    help="permutations for the AUROC p-value (0 to skip)")
    args = ap.parse_args()

    rows: list[RunCalibration] = []
    for spec in RUNS:
        print(f"analysing {spec.label} ...", file=sys.stderr)
        r = analyse_run(spec, n_boot=args.bootstrap, n_perm=args.permutations)
        if r is not None:
            rows.append(r)

    _print_table(rows)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps([asdict(r) for r in rows], indent=2), encoding="utf-8"
        )
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
