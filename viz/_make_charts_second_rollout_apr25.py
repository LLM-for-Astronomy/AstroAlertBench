"""Generate matplotlib figures for the second-rollout low-confidence ablation.

Reads ``results/second_rollout_<slug>_n35.metrics.json`` for each of five models
and writes PNGs under ``results_comparison/report/charts/second_rollout_apr25/``.

Run from repo root::

    python -m viz._make_charts_second_rollout_apr25
"""
from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

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


def _bar_top_labels(
    ax: plt.Axes,
    rects: Iterable,
    labels: list[str],
    y_pad: float = 0.02,
    fs: int = 7,
) -> None:
    """Place one preformatted string above each bar (heights from rects)."""
    for rect, t in zip(rects, labels):
        h = float(rect.get_height())
        if not t:
            continue
        ax.text(
            float(rect.get_x() + rect.get_width() / 2.0),
            h + y_pad,
            t,
            ha="center",
            va="bottom",
            fontsize=fs,
        )


def _label_stacked_cell(
    ax: plt.Axes,
    x_center: float,
    base: float,
    height: float,
    count: int,
    share: float,
    fs: int = 6,
    min_h: float = 0.04,
) -> None:
    if height < 1e-6:
        return
    if height < min_h:
        ax.text(
            x_center,
            base + height + 0.01,
            f"{count}",
            ha="center",
            va="bottom",
            fontsize=fs - 1,
            color="0.4",
        )
        return
    y = base + max(height * 0.5, 0.015)
    ax.text(
        x_center,
        y,
        f"{count}\n({share:.0%})",
        ha="center",
        va="center",
        fontsize=fs,
        color="0.15" if share > 0.1 else "0.35",
    )


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
    b_corr = ax.bar(
        x - w, corr, width=w, label="Correction rate (W→C′)", color="#2ca02c"
    )
    b_dmg = ax.bar(x, dmg, width=w, label="Damage rate (C→W)", color="#d62728")
    b_per = ax.bar(x + w, per, width=w, label="Persistence (W→W)", color="#7f7f7f")
    _bar_top_labels(ax, b_corr, [f"{c:.0%}" for c in corr], y_pad=0.01, fs=6)
    _bar_top_labels(ax, b_dmg, [f"{d:.0%}" for d in dmg], y_pad=0.01, fs=6)
    _bar_top_labels(ax, b_per, [f"{p:.0%}" for p in per], y_pad=0.01, fs=6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.set_ylabel("Fraction")
    ax.set_ylim(0, 1.12)
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
    b_a1 = ax.bar(x - 0.2, a1, 0.4, label="First pass", color="#aec7e8")
    b_a2 = ax.bar(x + 0.2, a2, 0.4, label="Second pass", color="#1f77b4")
    _bar_top_labels(ax, b_a1, [f"{v * 100:.1f}%" for v in a1], y_pad=0.012, fs=6)
    _bar_top_labels(ax, b_a2, [f"{v * 100:.1f}%" for v in a2], y_pad=0.012, fs=6)
    for i, r in enumerate(rows):
        dpp = float(r[2]["net_accuracy_delta"]) * 100.0
        ax.annotate(
            f"Δ{dpp:+.1f} %",
            (x[i], max(a1[i], a2[i]) + 0.045),
            ha="center",
            fontsize=8,
            fontweight="bold",
        )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.set_ylabel("5-class accuracy")
    ax.set_ylim(0, 1.1)
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
    ax.set_ylabel(
        r"$-\log_{10}(p)$" + "\n(McNemar exact, two-sided; height capped at 5)"
    )
    for i, p in enumerate(ps):
        h_bar = min(neglog[i], 5)
        mcp = (rows[i][2].get("mcnemar_discordant_pairs") or {})
        w_c = int(mcp.get("wrong_to_correct", 0))
        c_w = int(mcp.get("correct_to_wrong", 0))
        ax.text(
            x[i],
            h_bar + 0.1,
            f"p={p:.3g}\nW→C′={w_c}, C→W={c_w}",
            ha="center",
            fontsize=6.5,
            linespacing=1.12,
        )
    ax.legend(loc="upper right")
    ax.set_title("Paired significance of accuracy change (discordant pairs only)")
    # Room for 2-line annotation above bar (capped at −log10 p = 5)
    ax.set_ylim(0, 5.9)
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
    for i, xi in enumerate(x):
        b0, b1, b2, b3 = 0.0, cc_n[i], cc_n[i] + cw_n[i], cc_n[i] + cw_n[i] + wc_n[i]
        _label_stacked_cell(
            ax, float(xi), b0, cc_n[i], int(cc[i]), float(cc_n[i])
        )
        _label_stacked_cell(
            ax, float(xi), b1, cw_n[i], int(cw[i]), float(cw_n[i])
        )
        _label_stacked_cell(
            ax, float(xi), b2, wc_n[i], int(wc[i]), float(wc_n[i])
        )
        _label_stacked_cell(
            ax, float(xi), b3, ww_n[i], int(ww[i]), float(ww_n[i])
        )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.set_ylabel("Share of n=35")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Paired outcome composition (first vs second 5-class correctness)")
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "04_contingency_stacked.png", dpi=150)
    plt.close(fig)

    # --- Fig 5: MSRS — 2D scatter (joint “decoupling” view) + paired horizontal bars
    # Twin-y column charts mix ΔMSRS with a 0‒1 rate on different scales. Here: one scatter
    # puts both on meaningful x/y; size encodes 2nd-pass accuracy. Bottom row: same metrics as h-bars.
    dms = [float(r[2]["msrs_mean_delta"] or 0) for r in rows]
    ge4 = [float(r[2]["second_pass_msrs_ge4_rate"] or 0) for r in rows]
    acc2 = [float(r[2]["accuracy_second"] or 0) for r in rows]
    y_b = np.arange(len(labels), dtype=float)
    ann_y = [
        "GPT-5.4 high",
        "GPT-5.4 none",
        "Gemini 2.5 F",
        "Opus 4.7 think",
        "Opus 4.7 nothink",
    ]
    ann_sc = ["GPT-5.4h", "GPT-5.4n", "Gem 2.5F", "Opus T", "Opus N"]
    s_mark = 90.0 + 2350.0 * np.array(acc2, dtype=float)

    fig = plt.figure(figsize=(12, 6.8), layout="constrained")
    gs = fig.add_gridspec(
        2,
        2,
        height_ratios=[1.2, 1.0],
        width_ratios=[1.0, 1.02],
    )
    ax0 = fig.add_subplot(gs[0, :])
    for i in range(len(rows)):
        ax0.scatter(
            dms[i],
            ge4[i],
            s=s_mark[i],
            c=RUNS[i][2],
            edgecolors="0.2",
            linewidth=0.75,
            marker=RUNS[i][3],
            zorder=3,
        )
    ax0.axvline(0.0, color="0.45", ls="--", lw=0.95, zorder=1, alpha=0.88)
    ax0.axhline(0.5, color="0.45", ls=":", lw=0.95, zorder=1, alpha=0.88)
    ax0.set_xlabel("Mean ΔMSRS (second − first, Part B 3 self-scores)")
    ax0.set_ylabel("P(second pass MSRS ≥ 4)")
    rngx = max(float(np.ptp(dms)), 0.08)
    ax0.set_xlim(
        float(np.min(dms)) - 0.12 * rngx - 0.02,
        float(np.max(dms)) + 0.2 * rngx + 0.04,
    )
    ax0.set_ylim(-0.04, min(1.0, float(np.max(ge4)) + 0.12))
    ax0.grid(True, alpha=0.28, zorder=0)
    off_xy = [(9, 11), (-88, 6), (10, -16), (11, 9), (-98, -12)]
    for i in range(len(rows)):
        ax0.annotate(
            ann_sc[i],
            (dms[i], ge4[i]),
            xytext=off_xy[i],
            textcoords="offset points",
            fontsize=7.5,
            ha="left",
            arrowprops=dict(arrowstyle="-", color="0.45", lw=0.45, alpha=0.65),
            zorder=4,
        )
    ax0.text(
        0.02,
        0.98,
        "Marker area ∝ 2nd-pass 5-class accuracy (same 35 OIDs). "
        "Dashed: ΔMSRS = 0. Dotted: P(≥4) = 0.5.",
        transform=ax0.transAxes,
        ha="left",
        va="top",
        fontsize=7,
        color="0.35",
    )
    leg_el = [
        Line2D(
            [0],
            [0],
            marker=RUNS[i][3],
            linestyle="None",
            color="none",
            markerfacecolor=RUNS[i][2],
            markeredgecolor="0.25",
            markeredgewidth=0.5,
            markersize=7.0,
            label=labels[i],
        )
        for i in range(len(RUNS))
    ]
    ax0.legend(handles=leg_el, loc="lower right", fontsize=6.5, framealpha=0.95, title=None)
    ax0.set_title("A. Joint view (two comparable axes; no twin-y)")

    ax_d = fig.add_subplot(gs[1, 0])
    ax_g = fig.add_subplot(gs[1, 1], sharey=ax_d)
    ax_d.barh(
        y_b, dms, height=0.55, color="#8c564b", edgecolor="0.2", linewidth=0.3, zorder=2
    )
    ax_d.axvline(0, color="k", lw=0.75, zorder=1)
    d_lo = min(0.0, float(np.min(dms)) * 1.12 - 0.04)
    d_hi = max(0.0, float(np.max(dms)) * 1.12 + 0.05)
    if d_lo == d_hi:
        d_lo, d_hi = d_lo - 0.1, d_hi + 0.1
    span = d_hi - d_lo
    ax_d.set_xlim(d_lo, d_hi)
    for yi, v in zip(y_b, dms):
        tx = v + 0.015 * span * (1.0 if v >= 0 else -1.0)
        ax_d.text(
            tx,
            yi,
            f"{v:+.3f}",
            va="center",
            ha="left" if v >= 0 else "right",
            fontsize=7,
            color="0.2",
        )
    ax_d.set_xlabel("Mean ΔMSRS")
    ax_d.set_yticks(y_b)
    ax_d.set_yticklabels(ann_y, fontsize=7.5)
    ax_d.set_title("B. ΔMSRS (detail)")
    ax_d.invert_yaxis()

    ax_g.barh(
        y_b,
        ge4,
        height=0.55,
        color="#e377c2",
        edgecolor="0.2",
        linewidth=0.3,
        alpha=0.9,
        zorder=2,
    )
    ax_g.set_xlabel("P(second pass MSRS ≥ 4)")
    ax_g.set_xlim(0, 1.0)
    for yi, v in zip(y_b, ge4):
        ax_g.text(
            v + 0.02,
            yi,
            f"{v:.0%}",
            va="center",
            ha="left",
            fontsize=7,
            color="0.2",
        )
    ax_g.set_title("C. High self-grade rate (detail)")
    plt.setp(ax_g.get_yticklabels(), visible=False)
    fig.suptitle(
        "MSRS: mean shift vs. high self-grade on the second pass (n = 35 per model)",
        fontsize=11,
    )
    fig.savefig(CHART_DIR / "05_msrs_delta_and_highconf_second.png", dpi=150)
    plt.close(fig)

    # --- Fig 6: token ratio + prior-reference proxy ---
    tr = [r[2]["token_ratio_output_mean"] or 0 for r in rows]
    pr = [r[2]["prior_reference_rate"] or 0 for r in rows]
    fig, ax = plt.subplots(figsize=(11, 5))
    b_tr = ax.bar(
        x - 0.2, tr, 0.4, label="Mean output tokens (2nd / 1st)", color="#7f7f7f"
    )
    b_pr = ax.bar(
        x + 0.2, pr, 0.4, label="Prior-reference rate (regex proxy)", color="#ffbb78"
    )
    _bar_top_labels(
        ax, b_tr, [f"{t:.2f}×" if t else "—" for t in tr], y_pad=0.04, fs=6
    )
    _bar_top_labels(ax, b_pr, [f"{p:.0%}" for p in pr], y_pad=0.04, fs=6)
    ax.axhline(1.0, color="k", linestyle=":", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=18, ha="right")
    ax.legend()
    ax.set_ylabel("Ratio / rate")
    ymax = max(
        1.05,
        max((float(v) for v in tr), default=0) * 1.12,
        max((float(v) for v in pr), default=0) * 1.12,
    )
    ax.set_ylim(0, ymax)
    ax.set_title("Token overhead vs explicit self-review language (second pass)")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "06_token_ratio_prior_ref.png", dpi=150)
    plt.close(fig)

    print(f"Wrote charts to {CHART_DIR}")


if __name__ == "__main__":
    main()
