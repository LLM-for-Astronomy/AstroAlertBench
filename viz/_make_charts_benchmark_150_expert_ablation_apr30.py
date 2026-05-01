"""Generate chart suite for results_comparison/report/20260430_report_expert_example_ablation.md.

Seven runs × n=150 on manifest_benchmark_150.csv. Output:
  results_comparison/report/charts/benchmark_150_expert_ablation_apr30/*.png
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results_comparison" / "report" / "charts" / "benchmark_150_expert_ablation_apr30"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Ordered by descending absolute 5-class (approximate — charts re-sort anyway)
RUNS = [
    ("Qwen3.5-397B think", "runs/20260429-2118-qwen35-397b-a17b-think-benchmark-150/metrics.json", "#1f77b4", "Qwen397", "think"),
    ("Kimi K2.5 think", "runs/20260429-2037-kimi-k25-think-benchmark-150/metrics.json", "#9467bd", "Kimi", "think"),
    ("Qwen3.5-397B nothink", "runs/20260429-2031-qwen35-397b-a17b-nothink-benchmark-150/metrics.json", "#2ca02c", "Qwen397", "nothink"),
    ("Qwen3.5-4B nothink", "runs/20260429-2028-qwen35-4b-nothink-benchmark-150/metrics.json", "#8c564b", "Qwen4", "nothink"),
    ("Qwen3.5-35B nothink", "runs/20260429-2017-qwen35-35b-a3b-nothink-benchmark-150/metrics.json", "#bcbd22", "Qwen35", "nothink"),
    ("Qwen3.5-35B think", "runs/20260429-2145-qwen35-35b-a3b-think-benchmark-150/metrics.json", "#17becf", "Qwen35", "think"),
    ("Qwen3.5-4B think", "runs/20260429-2145-qwen35-4b-think-benchmark-150/metrics.json", "#e377c2", "Qwen4", "think"),
]

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 140,
    "savefig.dpi": 140,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
})


def se_prop(p: float, n: int) -> float:
    if n <= 0:
        return 0.0
    return math.sqrt(p * (1.0 - p) / n)


def ols_slope_stderr(x: list[float], y: list[float]) -> tuple[float, float]:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    n = int(xa.size)
    if n < 3:
        return float("nan"), float("nan")
    xm = float(xa.mean())
    ym = float(ya.mean())
    sxx = float(np.sum((xa - xm) ** 2))
    if sxx <= 0:
        return float("nan"), float("nan")
    sxy = float(np.sum((xa - xm) * (ya - ym)))
    m = sxy / sxx
    resid = ya - (m * xa + (ym - m * xm))
    rss = float(np.sum(resid ** 2))
    df = n - 2
    mse = rss / df
    se_m = math.sqrt(mse / sxx)
    return m, se_m


def load_all() -> list[dict]:
    out = []
    for label, path, color, family, reasoning in RUNS:
        m = json.loads((ROOT / path).read_text(encoding="utf-8"))
        n_total = int(m["n_examples"])
        parse_rate = float(m["json_valid_rate"])
        p_on_parsed = float(m["part_c_final_5class_accuracy"])
        p_abs = parse_rate * p_on_parsed
        out.append({
            "label": label,
            "color": color,
            "family": family,
            "reasoning": reasoning,
            "m": m,
            "n_total": n_total,
            "n_parsed": int(m.get("part_c_n_evaluable", m["json_parseable"])),
            "parse_rate": parse_rate,
            "p_abs": p_abs,
            "se_abs": se_prop(p_abs, n_total),
            "p_parsed": p_on_parsed,
            "se_parsed": se_prop(p_on_parsed, int(m.get("part_c_n_evaluable", m["json_parseable"]))),
            "stage1": float(m["part_c_stage1_accuracy"]),
            "stage2": float(m["part_c_stage2_accuracy"]),
            "stage3": float(m["part_c_stage3_accuracy"]),
            "stage3c": float(m["part_c_stage3_conditional_accuracy"]),
            "per_class_acc": m["per_class_accuracy"],
            "per_class_total": m["per_class_total"],
            "per_class_correct": m["per_class_correct"],
            "macro_f1": float(m["part_c_stage3_macro_f1"]),
            "msrs": float(m["part_b_msrs"]),
            "self_pass": float(m["part_b_self_pass_rate"]),
            "mean_out_tokens": float(m["output_tokens"]["mean"]),
            "median_out_tokens": float(m["output_tokens"]["median"]),
            "p95_out_tokens": float(m["output_tokens"]["p95"]),
            "max_out_tokens": float(m["output_tokens"]["max"]),
            "cm": m["part_c_stage3_confusion_matrix"],
            "err": m["error_breakdown"]["format"],
        })
    return out


def chart_01_absolute_ranked(runs):
    ordered = sorted(runs, key=lambda r: r["p_abs"], reverse=True)
    labels = [r["label"] for r in ordered]
    vals = [r["p_abs"] * 100 for r in ordered]
    errs = [r["se_abs"] * 100 for r in ordered]
    colors = [r["color"] for r in ordered]

    fig, ax = plt.subplots(figsize=(9.0, 5.8))
    y = np.arange(len(labels))
    ax.barh(y, vals, xerr=errs, color=colors, edgecolor="black",
            linewidth=0.5, capsize=3, ecolor="#333333")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Absolute 5-class accuracy over all 150 rows  (% ± 1σ SE)")
    ax.set_title("Headline: absolute 5-class accuracy, ranked  (7 runs, n=150)")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_xlim(0, min(100, max(vals) * 1.28 + max(errs)))
    fig.tight_layout()
    fig.savefig(OUT_DIR / "01_absolute_5class_ranked.png")
    plt.close(fig)


def chart_02_per_class_heatmap(runs):
    classes = ["SN", "AGN", "VS", "asteroid", "bogus"]
    ordered = sorted(runs, key=lambda r: r["p_abs"], reverse=True)
    mat = np.array([[r["per_class_acc"].get(c, 0.0) * 100 for c in classes]
                    for r in ordered])
    labels_row = [r["label"] for r in ordered]

    fig, ax = plt.subplots(figsize=(8, 5.2))
    im = ax.imshow(mat, cmap="YlGnBu", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(classes)))
    ax.set_xticklabels(classes)
    ax.set_yticks(range(len(labels_row)))
    ax.set_yticklabels(labels_row)
    ax.set_title("Per-class accuracy (%), ordered by absolute 5-class")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            txt_color = "white" if v > 55 else "black"
            ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                    fontsize=8.5, color=txt_color)
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label("Accuracy (%)")
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "02_per_class_heatmap.png")
    plt.close(fig)


def chart_03_stagewise_cascade(runs):
    ordered = sorted(runs, key=lambda r: r["p_abs"], reverse=True)
    labels = [r["label"] for r in ordered]
    s1 = [r["stage1"] * 100 for r in ordered]
    s2 = [r["stage2"] * 100 for r in ordered]
    s3 = [r["stage3"] * 100 for r in ordered]
    s3c = [r["stage3c"] * 100 for r in ordered]

    x = np.arange(len(labels))
    width = 0.2
    fig, ax = plt.subplots(figsize=(12.5, 5.2))
    ax.bar(x - 1.5*width, s1, width, label="Stage-1 (real/artifact)", color="#4c72b0")
    ax.bar(x - 0.5*width, s2, width, label="Stage-2 (astro/solar)", color="#55a868")
    ax.bar(x + 0.5*width, s3, width, label="Stage-3 (subclass)", color="#c44e52")
    ax.bar(x + 1.5*width, s3c, width, label="Stage-3 conditional", color="#8172b2")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=28, ha="right")
    ax.set_ylabel("Accuracy (%, on n_parsed)")
    ax.set_title("Stage-wise cascade accuracy (Part C), n=150 benchmark")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "03_stagewise_cascade.png")
    plt.close(fig)


def chart_04_agn_collapse_pie(runs):
    ordered = sorted(runs, key=lambda r: r["p_abs"], reverse=True)[:4]
    fig, axes = plt.subplots(1, 4, figsize=(13.5, 4.6))
    parts = ["AGN", "variable_star", "supernova", "N/A"]
    legend_labels = ["AGN (correct)", "variable_star", "supernova", "N/A / other"]
    colors = ["#55a868", "#c44e52", "#4c72b0", "#bbbbbb"]

    for ax, r in zip(axes, ordered):
        agn_row = r["cm"].get("AGN", {})
        vals = [int(agn_row.get(p, 0)) for p in parts]
        total = sum(vals)

        def autopct(p):
            return f"{p:.1f}%" if p >= 5 else ""

        ax.pie(
            vals, labels=None, colors=colors, autopct=autopct,
            startangle=90, pctdistance=0.72,
            wedgeprops={"edgecolor": "white", "linewidth": 1},
            textprops={"fontsize": 9, "color": "white", "fontweight": "bold"},
        )
        counts_txt = "   ".join(f"{legend_labels[i].split(' ')[0]}: {vals[i]}" for i in range(len(vals)))
        ax.text(0, -1.35, counts_txt, ha="center", va="top", fontsize=8.5, transform=ax.transData)
        ax.set_title(f"{r['label']}\n(n = {total} true AGN)", fontsize=9.5)

    fig.legend(legend_labels, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("True AGN rows: predicted-class distribution (top 4 runs by absolute 5-class)", y=1.02, fontsize=12)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT_DIR / "04_agn_collapse_pie.png")
    plt.close(fig)


def chart_05_token_economy(runs):
    ordered = sorted(runs, key=lambda r: r["mean_out_tokens"])
    labels = [r["label"] for r in ordered]
    means = [r["mean_out_tokens"] for r in ordered]
    p95 = [r["p95_out_tokens"] for r in ordered]
    max_ = [r["max_out_tokens"] for r in ordered]

    fig, ax = plt.subplots(figsize=(9.0, 5.8))
    y = np.arange(len(labels))
    ax.barh(y, means, color="#4c72b0", label="Mean", edgecolor="black", linewidth=0.5)
    ax.scatter(p95, y, color="#dd8452", s=56, label="p95", zorder=3, marker="D", edgecolor="black", linewidth=0.5)
    ax.scatter(max_, y, color="#c44e52", s=56, label="Max", zorder=3, marker="s", edgecolor="black", linewidth=0.5)
    ax.axvline(20000, color="black", linestyle="--", linewidth=0.8, alpha=0.6, label="20 000-token cap")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Output tokens per row")
    ax.set_title("Token economy: mean / p95 / max output tokens")
    ax.legend(loc="lower right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "05_token_economy.png")
    plt.close(fig)


def chart_06_error_breakdown(runs):
    order = ["ok", "truncated_no_json", "truncated_partial_json",
             "parse_failed", "extra_text_around_json",
             "schema_missing_top_level", "runtime_error"]
    display = {
        "ok": "ok",
        "truncated_no_json": "truncated (no JSON)",
        "truncated_partial_json": "truncated (partial)",
        "parse_failed": "parse_failed",
        "extra_text_around_json": "extra text around JSON",
        "schema_missing_top_level": "schema missing",
        "runtime_error": "runtime_error",
    }
    colors = ["#55a868", "#c44e52", "#dd8452", "#8172b2",
              "#9467bd", "#7f7f7f", "#bcbd22"]

    ordered = sorted(runs, key=lambda r: r["p_abs"], reverse=True)
    labels = [r["label"] for r in ordered]
    ntot = ordered[0]["n_total"]
    mat = np.zeros((len(order), len(labels)))
    for j, r in enumerate(ordered):
        for i, k in enumerate(order):
            mat[i, j] = r["err"].get(k, 0)

    fig, ax = plt.subplots(figsize=(12.5, 5.0))
    x = np.arange(len(labels))
    bottoms = np.zeros(len(labels))
    for i, k in enumerate(order):
        vals = mat[i]
        if vals.sum() == 0:
            continue
        ax.bar(x, vals, bottom=bottoms, color=colors[i], label=display[k],
               edgecolor="white", linewidth=0.5)
        bottoms += vals
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=28, ha="right")
    ax.set_ylabel(f"Row count (out of {ntot})")
    ax.set_title("Format / transport breakdown per run (stacked)")
    ax.set_ylim(0, ntot)
    ax.legend(loc="lower right", framealpha=0.95, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "06_error_breakdown_stacked.png")
    plt.close(fig)


def chart_07_msrs_vs_accuracy(runs):
    xs = [r["msrs"] for r in runs]
    ys = [r["p_abs"] * 100 for r in runs]
    errs = [r["se_abs"] * 100 for r in runs]
    colors = [r["color"] for r in runs]
    labels = [r["label"] for r in runs]

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.errorbar(xs, ys, yerr=errs, fmt="none", ecolor="#aaaaaa", capsize=3, linewidth=0.8, zorder=1)
    ax.scatter(xs, ys, c=colors, s=110, edgecolor="black", linewidth=0.6, zorder=2)

    m, se_m = ols_slope_stderr(xs, ys)
    b = float(np.mean(ys) - m * np.mean(xs))
    xr = np.linspace(min(xs) - 0.06, max(xs) + 0.06, 50)
    ax.plot(xr, m * xr + b, linestyle="--", color="#555555",
            label=f"OLS: slope = {m:.1f} ± {se_m:.1f} (SE) pt / MSRS")

    for x, y, lab in zip(xs, ys, labels):
        ax.annotate(lab, (x, y), xytext=(5, 3), textcoords="offset points", fontsize=7.5)

    ax.set_xlabel("MSRS (Part B mean self-rating, 1–5)")
    ax.set_ylabel("Absolute 5-class accuracy (%)")
    ax.set_title("MSRS vs absolute 5-class accuracy (n=150 sweep)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.legend(loc="upper right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "07_msrs_vs_accuracy.png")
    plt.close(fig)


def chart_08_think_vs_nothink_qwen_only(runs):
    pairs = [
        ("Qwen3.5-4B", "Qwen4"),
        ("Qwen3.5-35B-A3B", "Qwen35"),
        ("Qwen3.5-397B-A17B", "Qwen397"),
    ]
    by_family: dict[str, dict[str, dict]] = {}
    for r in runs:
        by_family.setdefault(r["family"], {})[r["reasoning"]] = r

    labels = [p[0] for p in pairs]
    think = [by_family[p[1]]["think"]["p_abs"] * 100 for p in pairs]
    nothink = [by_family[p[1]]["nothink"]["p_abs"] * 100 for p in pairs]
    th_err = [by_family[p[1]]["think"]["se_abs"] * 100 for p in pairs]
    no_err = [by_family[p[1]]["nothink"]["se_abs"] * 100 for p in pairs]

    x = np.arange(len(labels))
    w = 0.35
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    ax.bar(x - w/2, think, w, yerr=th_err, capsize=3, color="#4c72b0",
           edgecolor="black", linewidth=0.5, label="think / reasoning enabled")
    ax.bar(x + w/2, nothink, w, yerr=no_err, capsize=3, color="#dd8452",
           edgecolor="black", linewidth=0.5, label="nothink / disabled")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Absolute 5-class accuracy (% ± 1σ)")
    ax.set_title("Think vs nothink: Qwen3.5 family only (n = 150 each)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_ylim(0, 52)
    ax.legend(loc="upper left", framealpha=0.95)

    for i, (_, key) in enumerate(pairs):
        t = by_family[key]["think"]
        n = by_family[key]["nothink"]
        delta = (t["p_abs"] - n["p_abs"]) * 100
        se_d = math.sqrt(t["se_abs"] ** 2 + n["se_abs"] ** 2) * 100
        z = abs(delta) / se_d if se_d else float("nan")
        top = max(think[i] + th_err[i], nothink[i] + no_err[i]) + 2
        sign = "+" if delta >= 0 else "−"
        stars = "***" if z >= 3 else ("**" if z >= 2 else ("*" if z >= 1 else "n.s."))
        ax.text(i, top, f"Δ = {sign}{abs(delta):.2f} pt\n(z = {z:.2f}, {stars})",
                ha="center", va="bottom", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "08_think_vs_nothink.png")
    plt.close(fig)


def chart_09_compute_pareto(runs):
    xs = [r["mean_out_tokens"] for r in runs]
    ys = [r["p_abs"] * 100 for r in runs]
    errs = [r["se_abs"] * 100 for r in runs]
    colors = [r["color"] for r in runs]
    labels = [r["label"] for r in runs]

    idx_sorted = sorted(range(len(xs)), key=lambda i: xs[i])
    frontier = []
    best_y = -1.0
    for i in idx_sorted:
        if ys[i] > best_y:
            frontier.append(i)
            best_y = ys[i]

    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    ax.errorbar(xs, ys, yerr=errs, fmt="none", ecolor="#aaaaaa", capsize=3, linewidth=0.8, zorder=1)
    ax.scatter(xs, ys, c=colors, s=120, edgecolor="black", linewidth=0.6, zorder=2)
    fx = [xs[i] for i in frontier]
    fy = [ys[i] for i in frontier]
    ax.plot(fx, fy, "--", color="#555555", linewidth=1.2, zorder=1, label="Pareto frontier")

    for x, y, lab in zip(xs, ys, labels):
        ax.annotate(lab, (x, y), xytext=(5, 3), textcoords="offset points", fontsize=7.5)

    ax.set_xscale("log")
    ax.set_xlabel("Mean output tokens per row (log scale)")
    ax.set_ylabel("Absolute 5-class accuracy (%)")
    ax.set_title("Compute-accuracy trade-off (150-row benchmark)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.xaxis.set_major_formatter(mticker.ScalarFormatter())
    ax.xaxis.get_major_formatter().set_scientific(False)
    ax.legend(loc="lower right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "09_compute_pareto.png")
    plt.close(fig)


def main() -> None:
    runs = load_all()
    print(f"loaded {len(runs)} runs; output dir = {OUT_DIR}")
    chart_01_absolute_ranked(runs)
    chart_02_per_class_heatmap(runs)
    chart_03_stagewise_cascade(runs)
    chart_04_agn_collapse_pie(runs)
    chart_05_token_economy(runs)
    chart_06_error_breakdown(runs)
    chart_07_msrs_vs_accuracy(runs)
    chart_08_think_vs_nothink_qwen_only(runs)
    chart_09_compute_pareto(runs)
    for p in sorted(OUT_DIR.glob("*.png")):
        print(f"  wrote {p.relative_to(ROOT)}  ({p.stat().st_size:,} B)")


if __name__ == "__main__":
    main()
