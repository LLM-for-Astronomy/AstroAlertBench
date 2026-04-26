"""Generate matplotlib figures for the second-rollout low-confidence ablation.

Reads ``results/second_rollout_<slug>_n35.metrics.json`` for each of five models
and writes PNGs under ``results_comparison/report/charts/second_rollout_apr25/``.

Run from repo root::

    python -m viz._make_charts_second_rollout_apr25
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RUNS = [
    ("gpt54_high", "GPT-5.4 high", "#2ca02c", "o"),
    ("gpt54_none", "GPT-5.4 none", "#98df8a", "s"),
    ("gemini25_flash_none", "Gemini 2.5 Flash", "#1f77b4", "^"),
    ("opus47_think", "Opus 4.7 think", "#9467bd", "D"),
    ("opus47_nothink", "Opus 4.7 nothink", "#ff7f0e", "v"),
]

CHART_DIR = PROJECT_ROOT / "results_comparison" / "report" / "charts" / "second_rollout_apr25"


def _load_metrics(slug: str) -> dict:
    p = PROJECT_ROOT / "results" / f"second_rollout_{slug}_n35.metrics.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _safe_log10_p(p: float | None) -> float:
    if p is None or p <= 0:
        return 0.0
    return float(-np.log10(max(p, 1e-10)))


def main() -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    rows = [(slug, label, _load_metrics(slug)) for slug, label, _, _ in RUNS]
    labels = [r[1] for r in rows]
    x = np.arange(len(labels))

    # --- Fig 1: correction vs damage vs persistence (grouped bars) ---
    corr = [r[2]["correction_rate"] or 0 for r in rows]
    dmg = [r[2]["damage_rate"] or 0 for r in rows]
    per = [r[2]["persistence_rate"] or 0 for r in rows]
    w = 0.25
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - w, corr, width=w, label="Correction rate (W→C′)", color="#2ca02c")
    ax.bar(x, dmg, width=w, label="Damage rate (C→W)", color="#d62728")
    ax.bar(x + w, per, width=w, label="Persistence (W→W)", color="#7f7f7f")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.set_ylabel("Fraction")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("Second rollout: correction flow (n=35 per model, low-conf subset)")
    ax.axhline(0, color="k", linewidth=0.3)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "01_correction_flow_grouped.png", dpi=150)
    plt.close(fig)

    # --- Fig 2: accuracy first vs second + delta annotation ---
    a1 = [r[2]["accuracy_first"] for r in rows]
    a2 = [r[2]["accuracy_second"] for r in rows]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - 0.2, a1, 0.4, label="First pass (subset)", color="#aec7e8")
    ax.bar(x + 0.2, a2, 0.4, label="Second pass", color="#1f77b4")
    for i, r in enumerate(rows):
        d = r[2]["net_accuracy_delta"]
        ax.annotate(f"Δ{d:+.2f}", (x[i], max(a1[i], a2[i]) + 0.03), ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.set_ylabel("5-class accuracy (same 35 OIDs)")
    ax.set_ylim(0, 1.0)
    ax.legend()
    ax.set_title("First vs second pass accuracy on the stratified low-confidence cohort")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "02_accuracy_first_vs_second.png", dpi=150)
    plt.close(fig)

    # --- Fig 3: McNemar -log10(p); cap display for p=1 ---
    ps = [r[2]["mcnemar_exact_two_sided_p_value"] for r in rows]
    neglog = [_safe_log10_p(p) for p in ps]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    colors = ["#7f7f7f" if p >= 0.05 else "#2ca02c" for p in ps]
    ax.bar(x, [min(v, 5) for v in neglog], color=colors, edgecolor="k", linewidth=0.3)
    ax.axhline(-np.log10(0.05), color="r", linestyle="--", linewidth=1, label="p=0.05")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.set_ylabel("-log10(p)  (McNemar exact two-sided; capped at 5 for display)")
    for i, p in enumerate(ps):
        ax.text(x[i], min(neglog[i], 5) + 0.08, f"p={p:.4g}", ha="center", fontsize=7)
    ax.legend(loc="upper right")
    ax.set_title("Paired significance of accuracy change (discordant pairs only)")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "03_mcnemar_neglog10p.png", dpi=150)
    plt.close(fig)

    # --- Fig 4: stacked normalized contingency ---
    fig, ax = plt.subplots(figsize=(10, 5))
    cc = np.array([r[2]["contingency"]["n_cc"] for r in rows], dtype=float)
    cw = np.array([r[2]["contingency"]["n_cw"] for r in rows], dtype=float)
    wc = np.array([r[2]["contingency"]["n_wc"] for r in rows], dtype=float)
    ww = np.array([r[2]["contingency"]["n_ww"] for r in rows], dtype=float)
    tot = cc + cw + wc + ww
    cc_n, cw_n, wc_n, ww_n = cc / tot, cw / tot, wc / tot, ww / tot
    ax.bar(x, cc_n, label="C→C (stable correct)", color="#2ca02c")
    ax.bar(x, cw_n, bottom=cc_n, label="C→W (damage)", color="#d62728")
    ax.bar(x, wc_n, bottom=cc_n + cw_n, label="W→C′ (correction)", color="#17becf")
    ax.bar(x, ww_n, bottom=cc_n + cw_n + wc_n, label="W→W (persist)", color="#bcbd22")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.set_ylabel("Share of n=35")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Paired outcome composition (first vs second 5-class correctness)")
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "04_contingency_stacked.png", dpi=150)
    plt.close(fig)

    # --- Fig 5: MSRS mean delta + second-pass high-MSRS rate ---
    dms = [r[2]["msrs_mean_delta"] or 0 for r in rows]
    ge4 = [r[2]["second_pass_msrs_ge4_rate"] or 0 for r in rows]
    fig, ax1 = plt.subplots(figsize=(11, 5))
    b1 = ax1.bar(x - 0.2, dms, 0.4, color="#8c564b", label="Mean Δ MSRS (3 self-scores)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=18, ha="right")
    ax1.axhline(0, color="k", linewidth=0.5)
    ax1.set_ylabel("Delta MSRS")
    ax2 = ax1.twinx()
    ax2.bar(x + 0.2, ge4, 0.4, color="#e377c2", alpha=0.85, label="Second pass: frac MSRS≥4")
    ax2.set_ylabel("Fraction MSRS ≥ 4 (second)")
    ax2.set_ylim(0, 1.05)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
    ax1.set_title("Self-score shift vs second-pass high-confidence rate")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "05_msrs_delta_and_highconf_second.png", dpi=150)
    plt.close(fig)

    # --- Fig 6: token ratio + prior-reference proxy ---
    tr = [r[2]["token_ratio_output_mean"] or 0 for r in rows]
    pr = [r[2]["prior_reference_rate"] or 0 for r in rows]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - 0.2, tr, 0.4, label="Mean output tokens (2nd / 1st)", color="#7f7f7f")
    ax.bar(x + 0.2, pr, 0.4, label="Prior-reference rate (regex proxy)", color="#ffbb78")
    ax.axhline(1.0, color="k", linestyle=":", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.legend()
    ax.set_ylabel("Ratio / rate")
    ax.set_title("Token overhead vs explicit self-review language (second pass)")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "06_token_ratio_prior_ref.png", dpi=150)
    plt.close(fig)

    print(f"Wrote charts to {CHART_DIR}")


if __name__ == "__main__":
    main()
