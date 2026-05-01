"""Figures for results_comparison/report/20260430_report_human_baseline_examples.md.

Regenerate:

    python -m viz._make_charts_human_baseline_examples_apr30
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from viz._compute_human_baseline_examples_stats import compute_human_baseline_examples_stats, se_prop

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results_comparison" / "report" / "charts" / "human_baseline_examples_apr30"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Same 13 sweep as human_baselines_15_apr29 (short_label, metrics_json)
RUNS = [
    ("Opus 4.7 think", "runs/20260428-2356-opus47-think-human-baselines-15/metrics.json"),
    ("gpt-5.4 high", "runs/20260428-2358-gpt-5.4-high-human-baselines-15/metrics.json"),
    ("Kimi K2.5 think", "runs/20260428-2349-kimi-k25-human-baselines-15/metrics.json"),
    ("Opus 4.7 nothink", "runs/20260428-2357-opus47-nothink-human-baselines-15/metrics.json"),
    ("Qwen3.5-397B think", "runs/20260428-2348-qwen35-397b-a17b-human-baselines-15/metrics.json"),
    ("gpt-5.4 none", "runs/20260428-2359-gpt-5.4-none-human-baselines-15/metrics.json"),
    ("Gemini 2.5 Pro high", "runs/20260428-2356-gemini25-pro-high-human-baselines-15/metrics.json"),
    ("Gemini 2.5 Flash none", "runs/20260429-0042-gemini25-flash-none-human-baselines-15/metrics.json"),
    ("Qwen3.5-397B nothink", "runs/20260428-2330-qwen35-397b-a17b-nothink-human-baselines-15/metrics.json"),
    ("Qwen3.5-35B think", "runs/20260429-0019-qwen35-35b-a3b-human-baselines-15/metrics.json"),
    ("Qwen3.5-35B nothink", "runs/20260428-2357-qwen35-35b-a3b-nothink-human-baselines-15/metrics.json"),
    ("Qwen3.5-4B nothink", "runs/20260428-2356-qwen35-4b-nothink-human-baselines-15/metrics.json"),
    ("Qwen3.5-4B think", "runs/20260429-0026-qwen35-4b-human-baselines-15/metrics.json"),
]

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.titlesize": 12,
        "figure.dpi": 140,
        "savefig.dpi": 140,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
    }
)


def _absolute_accuracy(m: dict) -> float:
    return float(m.get("json_valid_rate", 0.0) * m.get("part_c_final_5class_accuracy", 0.0))


def load_llm_points() -> list[tuple[str, float, int, float]]:
    """(label, absolute_accuracy, n_examples, se_absolute_fraction)."""
    out = []
    for label, rel in RUNS:
        path = ROOT / rel
        if not path.is_file():
            continue
        m = json.loads(path.read_text(encoding="utf-8"))
        p = round(_absolute_accuracy(m), 4)
        ntot = int(m.get("n_examples", 15))
        se = se_prop(p, ntot)
        out.append((label, p, ntot, se))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def fig01_k_distribution(h: dict) -> None:
    ks = list(range(0, 6))
    counts = [h["k_dist"].get(k, 0) for k in ks]
    n_ids = 15
    errs = [n_ids * h["k_dist_se"][k] for k in ks]
    colors = ["#c0392b" if k == 0 else "#2980b9" for k in ks]
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    xpos = np.arange(len(ks))
    bars = ax.bar(xpos, counts, color=colors, edgecolor="white", yerr=errs, capsize=4, ecolor="#2c3e50")
    ax.set_xticks(xpos, [str(k) for k in ks])
    ax.set_xlabel("k = experts correct (same alert ID)")
    ax.set_ylabel("Count of alert IDs (of 15)")
    ax.set_title("Expert agreement versus manifest gold (±1σ on count)")
    for b, c, err in zip(bars, counts, errs):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + err + 0.12, str(c), ha="center", va="bottom", fontsize=9)
    fig.savefig(OUT_DIR / "01_expert_agreement_per_datapoint.png")
    plt.close(fig)


def fig02_refusal_pie(h: dict) -> None:
    dk = h["n_dk"]
    committed = h["n_rows"] - dk
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    ax.pie(
        [dk, committed],
        labels=[f"Don't Know ({dk})", f"Committed class ({committed})"],
        autopct="%1.1f%%",
        colors=["#e67e22", "#3498db"],
        startangle=90,
    )
    ax.set_title("75 individual responses: refusal vs committed label")
    fig.savefig(OUT_DIR / "02_refusal_pie_75.png")
    plt.close(fig)


def fig03_human_modes(h: dict) -> None:
    labels = ["Effective\n(DK wrong)", "Selective\n(non-DK only)", "Ensemble\n(majority, 15 IDs)"]
    vals = [
        h["effective_accuracy"],
        h["selective_accuracy"],
        h["ensemble_accuracy"],
    ]
    colors = ["#34495e", "#16a085", "#c0392b"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(len(labels))
    heights = [100 * v for v in vals]
    yerr = [
        100 * h["effective_accuracy_se"],
        100 * h["selective_accuracy_se"],
        100 * h["ensemble_accuracy_se"],
    ]
    ax.bar(x, heights, color=colors, edgecolor="white", yerr=yerr, capsize=4, ecolor="#2c3e50")
    ax.set_xticks(x, labels, fontsize=9)
    ax.set_ylabel("Percent")
    ax.set_ylim(0, max([hi + ei for hi, ei in zip(heights, yerr)] + [55.0]) * 1.15)
    ax.set_title("Human baselines: accuracy definitions (±1σ binomial)")
    for xi, v, e in zip(x, vals, yerr):
        ax.text(xi, 100 * v + e + 1.5, f"{100 * v:.1f}%", ha="center", fontsize=9)
    fig.savefig(OUT_DIR / "03_human_accuracy_modes.png")
    plt.close(fig)


def fig04_llm_vs_human(h: dict) -> None:
    llm = load_llm_points()
    if not llm:
        return
    labels = [x[0] for x in llm]
    vals = [100 * x[1] for x in llm]
    xerrs = [100 * x[3] for x in llm]
    fig, ax = plt.subplots(figsize=(8.4, 5.6))
    y = np.arange(len(labels))
    ax.barh(y, vals, color="#7f8c8d", height=0.7, xerr=xerrs, capsize=2, ecolor="#34495e")
    ax.set_yticks(y, labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Absolute 5-class accuracy (%) ±1σ — same 13 configs as Apr 29 report")
    ens = 100 * h["ensemble_accuracy"]
    ens_e = 100 * h["ensemble_accuracy_se"]
    eff = 100 * h["effective_accuracy"]
    eff_e = 100 * h["effective_accuracy_se"]
    best_u = max(h["per_user"].values(), key=lambda d: d["acc"])
    best_pct = 100 * best_u["acc"]
    best_e = 100 * best_u["acc_se"]
    ax.axvline(ens, color="#c0392b", ls="--", lw=1.5, label=f"Ensemble {ens:.1f}±{ens_e:.1f}%")
    ax.axvline(eff, color="#2c3e50", ls=":", lw=1.5, label=f"Effective {eff:.1f}±{eff_e:.1f}%")
    ax.axvline(best_pct, color="#8e44ad", ls="-.", lw=1.5, label=f"Best expert {best_pct:.1f}±{best_e:.1f}%")
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("Frontier models vs human references (n≈15 per model)")
    fig.savefig(OUT_DIR / "04_llm_vs_human_absolute.png")
    plt.close(fig)


def fig06_per_expert(h: dict) -> None:
    users = sorted(h["per_user"].keys())
    vals = [100 * h["per_user"][u]["acc"] for u in users]
    errs = [100 * h["per_user"][u]["acc_se"] for u in users]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    x = np.arange(len(users))
    ax.bar(x, vals, color="#9b59b6", edgecolor="white", yerr=errs, capsize=4, ecolor="#2c3e50")
    ax.set_xticks(x, users, rotation=25, ha="right")
    ax.set_ylabel("Accuracy vs manifest (%)")
    ax.set_title("Single-expert accuracy (±1σ, n = 15 each)")
    for xi, v, e in zip(x, vals, errs):
        ax.text(xi, v + e + 1.2, f"{v:.1f}%", ha="center", fontsize=9)
    mx = max((v + e for v, e in zip(vals, errs)), default=0.0)
    ax.set_ylim(0, mx * 1.18 if mx else 60.0)
    fig.savefig(OUT_DIR / "06_per_expert_accuracy.png")
    plt.close(fig)


def fig05_at_least_k(h: dict) -> None:
    ks = [1, 2, 3, 4, 5]
    fracs = [100 * h["at_least_k_frac"][k] for k in ks]
    errs = [100 * h["at_least_k_se"][k] for k in ks]
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.errorbar(ks, fracs, yerr=errs, fmt="o-", color="#2980b9", lw=2, markersize=8, capsize=4, ecolor="#2c3e50")
    ax.set_xticks(ks)
    ax.set_xlabel("k (minimum experts correct on the same alert ID)")
    ax.set_ylabel("Percent of 15 alert IDs")
    ax.set_ylim(0, 100)
    ax.set_title("At least k experts match gold (±1σ, n = 15 IDs)")
    for k, f, e in zip(ks, fracs, errs):
        ax.text(k, min(f + e + 6, 96), f"{f:.0f}%", ha="center", fontsize=9)
    fig.savefig(OUT_DIR / "05_at_least_k_experts.png")
    plt.close(fig)


def main() -> None:
    h = compute_human_baseline_examples_stats()
    fig01_k_distribution(h)
    fig02_refusal_pie(h)
    fig03_human_modes(h)
    fig04_llm_vs_human(h)
    fig05_at_least_k(h)
    fig06_per_expert(h)
    print("Wrote figures to", OUT_DIR)


if __name__ == "__main__":
    main()
