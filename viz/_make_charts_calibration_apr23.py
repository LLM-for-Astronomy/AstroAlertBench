"""Generate calibration / confidence-quality charts for the Apr 23 cross-model
comparison report.

Reads `metrics.json` from every full-benchmark run folder and renders six PNGs
into `results_comparison/report/charts/calibration_apr23/`.

Charts:
  C1 — Calibration gap bar (sorted, 1σ SE on the gap)
  C2 — Pearson r bar (sorted, with sign)
  C3 — Calibration gap vs Pearson r scatter (with quadrant labels)
  C4 — Calibration gap vs absolute 5-class accuracy scatter
  C5 — High-vs-low confidence accuracy paired bars
  C6 — Confidence-bin distribution (high vs low) stacked bars
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUT_DIR = PROJECT_ROOT / "results_comparison" / "report" / "charts" / "calibration_apr23"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Each entry: (label, run_folder, color_family, marker)
# color_family is used for grouping the bar-chart fill: blue=GPT, green=Gemini,
# orange=Claude, purple=Kimi, red=Qwen.
RUNS = [
    ("GPT-5.4 high",            "runs/20260421-2024-gpt-5.4-high-benchmark-full",                "tab:blue",   "o"),
    ("GPT-5.4 none",            "runs/20260421-2032-gpt-5.4-none-benchmark-full",                "tab:blue",   "s"),
    ("Claude Opus 4.7 think",   "runs/20260423-0942-opus47-think-benchmark-full",                "tab:orange", "o"),
    ("Claude Opus 4.7 nothink", "runs/20260423-1200-opus47-nothink-benchmark-full",              "tab:orange", "s"),
    ("Gemini 2.5 Pro high",     "runs/20260424-1809-gemini25-pro-high-benchmark-full",           "tab:green",  "o"),
    ("Gemini 2.5 Flash none",   "runs/20260423-2110-gemini25-flash-none-benchmark-full",         "tab:green",  "s"),
    ("Kimi K2.5 think",         "runs/20260420-1226-kimi-k25-benchmark-full",                    "tab:purple", "o"),
    ("Qwen3.5-397B think",      "runs/20260420-1554-qwen35-397b-a17b-benchmark-full",            "tab:red",    "o"),
    ("Qwen3.5-397B nothink",    "runs/20260421-0025-qwen35-397b-a17b-nothink-benchmark-full",    "tab:red",    "s"),
    ("Qwen3.5-35B think",       "runs/20260420-2054-qwen35-35b-a3b-benchmark-full",              "tab:pink",   "o"),
    ("Qwen3.5-35B nothink",     "runs/20260421-0019-qwen35-35b-a3b-nothink-benchmark-full",      "tab:pink",   "s"),
    ("Qwen3.5-4B think",        "runs/20260420-1920-qwen35-4b-benchmark-full",                   "tab:brown",  "o"),
    ("Qwen3.5-4B nothink",      "runs/20260421-0002-qwen35-4b-nothink-benchmark-full",           "tab:brown",  "s"),
]


@dataclass
class RunRow:
    label: str
    color: str
    marker: str
    n_total: int
    n_parsed: int
    five_class_acc: float
    parse_rate: float
    abs_5class: float
    msrs: float
    n_linked: int
    mean_correct: float
    mean_incorrect: float
    calibration_gap: float
    pearson_r: float
    acc_high_conf: float
    n_high_conf: int
    acc_low_conf: float
    n_low_conf: int

    @property
    def cal_gap_se(self) -> float:
        # SE on (mean_correct - mean_incorrect): treat as difference of two
        # independent group means with unknown population SD. Confidence is on
        # a 1..5 ordinal; without per-row data we can't compute exact pooled
        # SE, so we approximate using sd ~= range/4 = 1.0 and the per-bin
        # counts: SE_diff = sqrt(sd^2/n_correct + sd^2/n_incorrect).
        n_correct = round(self.n_linked * self.five_class_acc)
        n_incorrect = max(self.n_linked - n_correct, 1)
        sd = 1.0
        return math.sqrt(sd ** 2 / max(n_correct, 1) + sd ** 2 / n_incorrect)

    @property
    def pearson_r_se(self) -> float:
        # Fisher SE on Pearson r given n: 1/sqrt(n-3).
        n = max(self.n_linked - 3, 1)
        return 1.0 / math.sqrt(n)


def load_run(label: str, folder: str, color: str, marker: str) -> RunRow | None:
    path = PROJECT_ROOT / folder / "metrics.json"
    if not path.is_file():
        print(f"  !! missing {path}")
        return None
    m = json.loads(path.read_text(encoding="utf-8"))
    cb = m.get("part_bc_confidence_accuracy", {})
    n_total = m.get("n_examples", 0) or 0
    n_parsed = m.get("json_parseable", 0) or 0
    parse_rate = (n_parsed / n_total) if n_total else 0.0
    five = m.get("part_c_final_5class_accuracy", 0.0) or 0.0
    return RunRow(
        label=label,
        color=color,
        marker=marker,
        n_total=n_total,
        n_parsed=n_parsed,
        five_class_acc=five,
        parse_rate=parse_rate,
        abs_5class=parse_rate * five,
        msrs=m.get("part_b_msrs", 0.0) or 0.0,
        n_linked=cb.get("n_linked", 0) or 0,
        mean_correct=cb.get("mean_confidence_correct", float("nan")),
        mean_incorrect=cb.get("mean_confidence_incorrect", float("nan")),
        calibration_gap=cb.get("calibration_gap", float("nan")),
        pearson_r=cb.get("pearson_r", float("nan")),
        acc_high_conf=cb.get("accuracy_high_confidence", float("nan")),
        n_high_conf=cb.get("n_high_confidence", 0) or 0,
        acc_low_conf=cb.get("accuracy_low_confidence", float("nan")),
        n_low_conf=cb.get("n_low_confidence", 0) or 0,
    )


def _annotate_bars(ax, bars, fmt="{:.4f}", offset=0.0, fontsize=7):
    for b in bars:
        h = b.get_height()
        ax.text(
            b.get_x() + b.get_width() / 2.0,
            h + offset,
            fmt.format(h),
            ha="center", va="bottom", fontsize=fontsize,
        )


def chart_calibration_gap_bar(rows: list[RunRow]) -> None:
    """C1 — Calibration gap bar chart, sorted ascending (smaller = better)."""
    rows = sorted(rows, key=lambda r: r.calibration_gap)
    labels = [r.label for r in rows]
    gaps = [r.calibration_gap for r in rows]
    ses = [r.cal_gap_se for r in rows]
    colors = [r.color for r in rows]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(rows))
    bars = ax.bar(x, gaps, yerr=ses, color=colors, edgecolor="black",
                  linewidth=0.5, capsize=3, alpha=0.85)
    for i, r in enumerate(rows):
        ax.text(i, r.calibration_gap + r.cal_gap_se + 0.005,
                f"{r.calibration_gap:.3f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("Calibration gap  (mean conf when correct − mean conf when incorrect)")
    ax.set_title("C1 — Calibration gap across full-benchmark runs (smaller is better)\n"
                 "* Claude Opus 4.7 nothink is partial (n_parsed=879 / 1500).")
    ax.axhline(0.0, color="gray", linewidth=0.6)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    fig.tight_layout()
    out = OUT_DIR / "C1_calibration_gap_bar.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")


def chart_pearson_r_bar(rows: list[RunRow]) -> None:
    """C2 — Pearson r between confidence and correctness, sorted descending."""
    rows = sorted(rows, key=lambda r: r.pearson_r, reverse=True)
    labels = [r.label for r in rows]
    rs = [r.pearson_r for r in rows]
    ses = [r.pearson_r_se for r in rows]
    colors = [r.color for r in rows]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(rows))
    bars = ax.bar(x, rs, yerr=ses, color=colors, edgecolor="black",
                  linewidth=0.5, capsize=3, alpha=0.85)
    for i, r in enumerate(rows):
        y = r.pearson_r
        ax.text(i, y + (0.005 if y >= 0 else -0.012),
                f"{y:.3f}", ha="center",
                va="bottom" if y >= 0 else "top", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("Pearson r  (per-row confidence vs correctness 0/1)")
    ax.set_title("C2 — Confidence–correctness Pearson r (larger is better)\n"
                 "Error bars: 1/√(n−3). Most runs are ≤ 0.2 — confidence is "
                 "barely informative on this benchmark.")
    ax.axhline(0.0, color="gray", linewidth=0.6)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    fig.tight_layout()
    out = OUT_DIR / "C2_pearson_r_bar.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")


def chart_gap_vs_r_scatter(rows: list[RunRow]) -> None:
    """C3 — Calibration gap (x) vs Pearson r (y) scatter."""
    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    for r in rows:
        ax.scatter(r.calibration_gap, r.pearson_r,
                   s=110, color=r.color, marker=r.marker, edgecolor="black",
                   linewidth=0.6, alpha=0.9)
        ax.annotate(r.label, (r.calibration_gap, r.pearson_r),
                    xytext=(6, 4), textcoords="offset points", fontsize=8)
    ax.axhline(0.0, color="gray", linewidth=0.6)
    ax.axvline(0.0, color="gray", linewidth=0.6)
    ax.set_xlabel("Calibration gap (correct conf − incorrect conf)")
    ax.set_ylabel("Pearson r (confidence vs correctness)")
    ax.set_title("C3 — Calibration gap vs Pearson r\n"
                 "Top-right = honestly confident; bottom-left = miscalibrated AND uninformative.")
    ax.grid(linestyle=":", alpha=0.4)
    # Quadrant annotations
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    ax.text(xmax * 0.97, ymax * 0.97, "honest +\ninformative", ha="right", va="top",
            color="darkgreen", fontsize=9, alpha=0.7)
    ax.text(xmin * 0.97 if xmin < 0 else 0.001, ymin * 0.97 if ymin < 0 else 0.001,
            "miscalibrated +\nuninformative", ha="left", va="bottom",
            color="darkred", fontsize=9, alpha=0.7)
    fig.tight_layout()
    out = OUT_DIR / "C3_gap_vs_pearson_scatter.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")


def chart_gap_vs_acc_scatter(rows: list[RunRow]) -> None:
    """C4 — Calibration gap (x) vs absolute 5-class accuracy (y)."""
    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    xs, ys = [], []
    for r in rows:
        ax.scatter(r.calibration_gap, r.abs_5class,
                   s=110, color=r.color, marker=r.marker, edgecolor="black",
                   linewidth=0.6, alpha=0.9)
        ax.annotate(r.label, (r.calibration_gap, r.abs_5class),
                    xytext=(6, 4), textcoords="offset points", fontsize=8)
        xs.append(r.calibration_gap)
        ys.append(r.abs_5class)
    # OLS line
    if len(xs) >= 3:
        m, b = np.polyfit(xs, ys, 1)
        xline = np.linspace(min(xs), max(xs), 50)
        ax.plot(xline, m * xline + b, color="black", linewidth=0.7, linestyle="--", alpha=0.7,
                label=f"OLS  y = {m:.3f}·x + {b:.3f}")
        # Pearson r between gap and accuracy
        r_corr = np.corrcoef(xs, ys)[0, 1]
        ax.text(0.02, 0.98, f"corr(gap, abs_5class) = {r_corr:+.3f}",
                transform=ax.transAxes, fontsize=10, va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.8))
        ax.legend(loc="lower right", fontsize=9)
    ax.set_xlabel("Calibration gap (correct − incorrect mean confidence)")
    ax.set_ylabel("Absolute 5-class accuracy over all 1500 rows")
    ax.set_title("C4 — Calibration gap vs absolute 5-class accuracy")
    ax.grid(linestyle=":", alpha=0.4)
    fig.tight_layout()
    out = OUT_DIR / "C4_gap_vs_accuracy_scatter.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")


def chart_high_vs_low_conf_bars(rows: list[RunRow]) -> None:
    """C5 — High-vs-low confidence accuracy paired bars per model."""
    rows = sorted(rows, key=lambda r: r.acc_high_conf - r.acc_low_conf, reverse=True)
    labels = [r.label for r in rows]
    high = [r.acc_high_conf for r in rows]
    low = [r.acc_low_conf for r in rows]
    n_high = [r.n_high_conf for r in rows]
    n_low = [r.n_low_conf for r in rows]

    x = np.arange(len(rows))
    width = 0.4
    fig, ax = plt.subplots(figsize=(12, 5.8))
    b1 = ax.bar(x - width/2, high, width, label="acc | high conf", color="tab:green", alpha=0.8, edgecolor="black", linewidth=0.4)
    b2 = ax.bar(x + width/2, low, width, label="acc | low conf",  color="tab:gray",  alpha=0.8, edgecolor="black", linewidth=0.4)
    for i, (h, l, nh, nl) in enumerate(zip(high, low, n_high, n_low)):
        ax.text(i - width/2, h + 0.01, f"{h:.2f}\n(n={nh})", ha="center", va="bottom", fontsize=7)
        ax.text(i + width/2, l + 0.01, f"{l:.2f}\n(n={nl})", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("5-class accuracy on the bin")
    ax.set_title("C5 — Accuracy by confidence bin (high ≥ 4 vs low < 4 on the 1..5 ordinal)\n"
                 "Sorted by (high − low) — the gap an honest model would maximise.")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_ylim(0, 1.0)
    ax.legend(loc="upper right", fontsize=10)
    fig.tight_layout()
    out = OUT_DIR / "C5_high_vs_low_conf_bars.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")


def chart_conf_bin_distribution(rows: list[RunRow]) -> None:
    """C6 — Stacked bars: how many predictions are in each confidence bin."""
    rows = sorted(rows, key=lambda r: r.n_high_conf / max(r.n_linked, 1), reverse=True)
    labels = [r.label for r in rows]
    high = [r.n_high_conf for r in rows]
    low = [r.n_low_conf for r in rows]
    high_pct = [h / max(r.n_linked, 1) for h, r in zip(high, rows)]
    low_pct = [l / max(r.n_linked, 1) for l, r in zip(low, rows)]

    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(12, 5.4))
    ax.bar(x, high_pct, label="high conf (≥4)", color="tab:green", alpha=0.85, edgecolor="black", linewidth=0.4)
    ax.bar(x, low_pct, bottom=high_pct, label="low conf (<4)", color="tab:gray", alpha=0.85, edgecolor="black", linewidth=0.4)
    for i, (hp, lp, h, l) in enumerate(zip(high_pct, low_pct, high, low)):
        ax.text(i, hp / 2, f"{hp*100:.1f}%\nn={h}", ha="center", va="center", fontsize=7, color="white")
        ax.text(i, hp + lp / 2, f"{lp*100:.1f}%\nn={l}", ha="center", va="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Fraction of parsed predictions in bin")
    ax.set_title("C6 — Confidence-bin distribution per model\n"
                 "Most models park >85% of predictions in the high-confidence bin — "
                 "concentrated mass that calibration must police.")
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    fig.tight_layout()
    out = OUT_DIR / "C6_conf_bin_distribution.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")


def main() -> None:
    print(f"Loading {len(RUNS)} runs from {PROJECT_ROOT / 'runs'} ...")
    rows: list[RunRow] = []
    for label, folder, color, marker in RUNS:
        rr = load_run(label, folder, color, marker)
        if rr is not None:
            rows.append(rr)
    print(f"Loaded {len(rows)} runs.")
    print(f"\nWriting charts to {OUT_DIR} ...")
    chart_calibration_gap_bar(rows)
    chart_pearson_r_bar(rows)
    chart_gap_vs_r_scatter(rows)
    chart_gap_vs_acc_scatter(rows)
    chart_high_vs_low_conf_bars(rows)
    chart_conf_bin_distribution(rows)
    print("\ndone.")

    # Print a quick text table for the report writer to reference.
    rows_sorted = sorted(rows, key=lambda r: r.calibration_gap)
    print("\nCalibration table (sorted by calibration_gap, ascending):")
    print(f"{'run':<26}  {'n_link':>6}  {'5cls':>6}  {'gap':>7}  {'gap_SE':>7}  "
          f"{'pears r':>8}  {'r_SE':>6}  {'acc|H':>6}  {'acc|L':>6}  {'n_H':>5}  {'n_L':>4}")
    for r in rows_sorted:
        print(f"{r.label:<26}  {r.n_linked:>6}  {r.five_class_acc*100:>5.2f}%  "
              f"{r.calibration_gap:>7.4f}  {r.cal_gap_se:>7.4f}  "
              f"{r.pearson_r:>+8.4f}  {r.pearson_r_se:>6.4f}  "
              f"{r.acc_high_conf*100:>5.2f}%  {r.acc_low_conf*100:>5.2f}%  "
              f"{r.n_high_conf:>5}  {r.n_low_conf:>4}")


if __name__ == "__main__":
    main()
