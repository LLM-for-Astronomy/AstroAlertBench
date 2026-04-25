"""Generate calibration / confidence-quality charts for the Apr 23 cross-model
comparison report.

Reads `metrics.json` from every full-benchmark run folder and renders six PNGs
into `results_comparison/report/charts/calibration_apr23/`.

Charts:
  C1 — Calibration gap bar (sorted, 1σ SE on the gap)
  C2 — Pearson r bar (sorted, with sign)
  C3 — Calibration gap vs Pearson r scatter (with quadrant labels)
  C4 — Calibration gap vs absolute 5-class accuracy scatter
  C5 — High-vs-low confidence accuracy paired bars (high = self-mean ≥ 4)
  C5b — Same as C5 but at the midpoint threshold (high = self-mean ≥ 3.5).
  C5c — Same as C5 but at the strict threshold (high = self-mean ≥ 4.5).
        C5b/C5c are one-shot complementary views; default in metrics.json
        stays at 4.
  C6 — Confidence-bin distribution (high vs low) stacked bars
"""
from __future__ import annotations

import json
import math
import sys
import dataclasses
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
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
    # Raw per-row (self_mean, is_correct) pairs, populated from run.jsonl,
    # so we can re-bin at any threshold (one-shot need for this report —
    # default reporting threshold remains 4).
    conf_pairs: list[tuple[float, int]] = dataclasses.field(default_factory=list)

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


def _per_row_conf_correctness(jsonl_path: Path) -> list[tuple[float, int]]:
    """Walk a run.jsonl and return (self_mean, is_correct) for each parseable
    row that has a complete Part B (3 self-scores) AND a parseable Part C that
    yields a final 5-class label.

    Mirrors the linkage logic in evaluate.evaluate_jsonl that builds
    `bc_confidence` / `bc_correct`. We re-derive these per-row pairs so we can
    re-bin at thresholds other than the default 4.
    """
    out: list[tuple[float, int]] = []
    if not jsonl_path.is_file():
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
            gold_s = GOLD_STAGES.get(str(tc))
            if gold_s is None:
                continue
            ps1 = normalize_stage1(part_c.get("stage1"))
            ps2 = normalize_stage2(part_c.get("stage2"))
            ps3 = normalize_stage3_label(part_c.get("stage3"))
            if ps1 is None or ps2 is None or ps3 is None:
                continue
            pred_final = stages_to_final_class(ps1, ps2, ps3)
            if pred_final is None:
                continue
            is_correct = int(pred_final == str(tc))
            out.append((self_mean, is_correct))
    return out


def _bin_at_threshold(pairs: list[tuple[float, int]], thresh: float
                      ) -> tuple[float, int, float, int]:
    """Return (acc_high, n_high, acc_low, n_low) for self_mean >= thresh."""
    if not pairs:
        return float("nan"), 0, float("nan"), 0
    arr = np.array(pairs)
    conf = arr[:, 0]
    cor = arr[:, 1]
    high_mask = conf >= thresh
    low_mask = ~high_mask
    n_h = int(high_mask.sum())
    n_l = int(low_mask.sum())
    acc_h = float(cor[high_mask].mean()) if n_h > 0 else float("nan")
    acc_l = float(cor[low_mask].mean()) if n_l > 0 else float("nan")
    return acc_h, n_h, acc_l, n_l


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

    # Per-row pairs so we can re-bin at any threshold for the one-shot views.
    pairs = _per_row_conf_correctness(PROJECT_ROOT / folder / "run.jsonl")

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
        conf_pairs=pairs,
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


def _fmt_thresh(t: float) -> str:
    return f"{int(t)}" if float(t).is_integer() else f"{t:g}"


def _chart_conf_bin_pairs(rows: list[RunRow], threshold: float, out_name: str,
                          title_suffix: str = "") -> None:
    """Generic high-vs-low confidence accuracy paired-bar chart.

    Bins each row's per-prediction (self_mean, is_correct) pairs at `threshold`
    (high = self_mean >= threshold, low = self_mean < threshold) and renders
    the resulting per-bin accuracies as paired bars, sorted by (high - low)
    descending so honest models land on the left.
    """
    binned: list[tuple[float, int, float, int]] = [
        _bin_at_threshold(r.conf_pairs, threshold) for r in rows
    ]

    combined = list(zip(rows, binned))
    combined.sort(
        key=lambda rp: (rp[1][0] - rp[1][2])
            if not (math.isnan(rp[1][0]) or math.isnan(rp[1][2]))
            else -1.0,
        reverse=True,
    )
    rows_s = [c[0] for c in combined]
    binned_s = [c[1] for c in combined]

    labels = [r.label for r in rows_s]
    high = [b[0] for b in binned_s]
    low = [b[2] for b in binned_s]
    n_high = [b[1] for b in binned_s]
    n_low = [b[3] for b in binned_s]

    tlabel = _fmt_thresh(threshold)
    x = np.arange(len(rows_s))
    width = 0.4
    fig, ax = plt.subplots(figsize=(12, 5.8))
    ax.bar(x - width/2, high, width, label=f"acc | high conf (>= {tlabel})",
           color="tab:green", alpha=0.8, edgecolor="black", linewidth=0.4)
    ax.bar(x + width/2, low, width, label=f"acc | low conf (< {tlabel})",
           color="tab:gray", alpha=0.8, edgecolor="black", linewidth=0.4)
    for i, (h, l, nh, nl) in enumerate(zip(high, low, n_high, n_low)):
        if not math.isnan(h):
            ax.text(i - width/2, h + 0.01, f"{h:.2f}\n(n={nh})", ha="center", va="bottom", fontsize=7)
        if not math.isnan(l):
            ax.text(i + width/2, l + 0.01, f"{l:.2f}\n(n={nl})", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("5-class accuracy on the bin")
    title = (f"Accuracy by confidence bin (high >= {tlabel} vs low < {tlabel} "
             "on the 1..5 ordinal)\n"
             "Sorted by (high - low) - the gap an honest model would maximise.")
    if title_suffix:
        title = f"{title_suffix} - " + title
    ax.set_title(title)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_ylim(0, 1.0)
    ax.legend(loc="upper right", fontsize=10)
    fig.tight_layout()
    out = OUT_DIR / out_name
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out.name}")


def chart_high_vs_low_conf_bars(rows: list[RunRow]) -> None:
    """C5 - Default threshold (high = self-mean >= 4)."""
    _chart_conf_bin_pairs(rows, threshold=4.0,
                          out_name="C5_high_vs_low_conf_bars.png",
                          title_suffix="C5")


def chart_high_vs_low_conf_bars_t35(rows: list[RunRow]) -> None:
    """C5b - One-shot complementary view at the midpoint threshold (>= 3.5)."""
    _chart_conf_bin_pairs(rows, threshold=3.5,
                          out_name="C5b_high_vs_low_conf_bars_thresh35.png",
                          title_suffix="C5b")


def chart_high_vs_low_conf_bars_t45(rows: list[RunRow]) -> None:
    """C5c - One-shot complementary view at the strict threshold (>= 4.5)."""
    _chart_conf_bin_pairs(rows, threshold=4.5,
                          out_name="C5c_high_vs_low_conf_bars_thresh45.png",
                          title_suffix="C5c")


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
    chart_high_vs_low_conf_bars_t35(rows)
    chart_high_vs_low_conf_bars_t45(rows)
    chart_conf_bin_distribution(rows)
    print("\ndone.")

    # ---- Sanity check: recomputed threshold=4 should match metrics.json ----
    print("\nSanity check (threshold=4 recompute vs metrics.json):")
    print(f"{'run':<26}  {'n_H json':>9}  {'n_H reco':>9}  {'acc_H json':>11}  {'acc_H reco':>11}")
    for r in rows:
        h_reco, n_h_reco, _l_reco, _n_l_reco = _bin_at_threshold(r.conf_pairs, 4.0)
        delta = (h_reco - r.acc_high_conf
                 if not (math.isnan(h_reco) or math.isnan(r.acc_high_conf))
                 else float("nan"))
        flag = "" if (not math.isnan(delta) and abs(delta) < 1e-3
                      and r.n_high_conf == n_h_reco) else "  <-- DIFFERS"
        print(f"{r.label:<26}  {r.n_high_conf:>9}  {n_h_reco:>9}  "
              f"{r.acc_high_conf*100:>10.2f}%  {h_reco*100:>10.2f}%{flag}")

    # ---- Per-threshold tables for the report writer ----
    for thr in (3.5, 4.5):
        print(f"\nThreshold={thr} split (one-shot, sorted by acc_H - acc_L desc):")
        print(f"{'run':<26}  {'n_H':>5}  {'n_L':>4}  {'acc|H':>6}  {'acc|L':>6}  {'gap':>7}")
        triples = [(r, *_bin_at_threshold(r.conf_pairs, thr)) for r in rows]
        triples.sort(
            key=lambda t: (t[1] - t[3])
                if not (math.isnan(t[1]) or math.isnan(t[3]))
                else -1.0,
            reverse=True,
        )
        for r, acc_h, n_h, acc_l, n_l in triples:
            h_pct = acc_h * 100 if not math.isnan(acc_h) else float("nan")
            l_pct = acc_l * 100 if not math.isnan(acc_l) else float("nan")
            gap = h_pct - l_pct if not (math.isnan(h_pct) or math.isnan(l_pct)) else float("nan")
            print(f"{r.label:<26}  {n_h:>5}  {n_l:>4}  "
                  f"{h_pct:>5.2f}%  {l_pct:>5.2f}%  {gap:>+6.2f}")

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
