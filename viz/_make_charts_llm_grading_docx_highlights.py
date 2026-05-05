"""Figures for results_comparison/report/20260430_report_llm_grading_docx_highlights.md.

Looks for ``LLM Answer Grading *.docx`` in the **repo root** or **temporary_files/**.

Outputs include ``07_stacked_correct_vs_incorrect_per_alert_ztf26_only.png`` (ZTF26 columns only).

Run::

    python -m viz._make_charts_llm_grading_docx_highlights
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from viz._analyze_llm_grading_docx_highlights import analyze_docx

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results_comparison" / "report" / "charts" / "llm_grading_docx_highlights_apr30"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Basenames only — resolved under repo root and under ``temporary_files/`` (same layout as grading report).
_DOC_ENTRIES: tuple[tuple[str, str], ...] = (
    ("ZTF19abfqvbg", "LLM Answer Grading ZTF19abfqvbg.docx"),
    ("ZTF26aargnnp", "LLM Answer Grading ZTF26aargnnp.docx"),
)


def _resolve_grading_docx(filename: str) -> Path | None:
    for d in (ROOT, ROOT / "temporary_files"):
        p = d / filename
        if p.is_file():
            return p
    return None

# Stacking order: bottom → top
STACK_KEYS = ["green", "yellow", "red", "unhighlighted"]
STACK_LABELS = ["Green", "Yellow", "Red", "Unhighlighted"]
STACK_COLORS = ["#27ae60", "#f1c40f", "#c0392b", "#95a5a6"]

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.titlesize": 12,
        "figure.dpi": 140,
        "savefig.dpi": 140,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def _pct_map(counts: dict[str, int]) -> dict[str, float]:
    tot = sum(counts.values())
    if tot == 0:
        return {k: 0.0 for k in STACK_KEYS}
    return {k: 100.0 * counts.get(k, 0) / tot for k in STACK_KEYS}


def _annotate_stacked_pct_counts(
    ax,
    x: np.ndarray,
    bottom: np.ndarray,
    heights: list[float],
    counts: list[int],
    *,
    min_pct_dual: float = 3.0,
) -> None:
    """Label each stack segment with ``pct`` + ``(count)``; tiny slivers show count only."""
    hb = np.asarray(bottom, dtype=float)
    hh = np.asarray(heights, dtype=float)
    for xi in range(len(x)):
        h = float(hh[xi])
        c = int(counts[xi])
        if h <= 0 and c <= 0:
            continue
        y = float(hb[xi]) + h / 2.0
        xi_f = float(x[xi])
        if h >= min_pct_dual:
            ax.text(
                xi_f,
                y,
                f"{h:.1f}%\n({c:,})",
                ha="center",
                va="center",
                fontsize=6.5,
                clip_on=False,
            )
        elif c > 0:
            ax.text(
                xi_f,
                y,
                f"{h:.1f}% ({c:,})",
                ha="center",
                va="center",
                fontsize=6,
                clip_on=False,
            )


def _annotate_grouped_bar_values(ax, bars, values: list[int], *, fontsize: int = 7) -> None:
    """Place integer labels above each bar in a grouped or simple bar chart."""
    for bar, v in zip(bars, values):
        if v == 0:
            continue
        h = bar.get_height()
        ax.annotate(
            f"{int(v):,}",
            xy=(bar.get_x() + bar.get_width() / 2.0, h),
            xytext=(0, 2),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=fontsize,
        )


def fig01_stacked_per_alert(results: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    x = np.arange(len(results))
    width = 0.55
    bottom = np.zeros(len(results))
    for key, lab, col in zip(STACK_KEYS, STACK_LABELS, STACK_COLORS):
        heights = [r["pct_both"].get(key, 0.0) for r in results]
        cnts = [r["reasoning_both_parts_chars_by_fill"].get(key, 0) for r in results]
        ax.bar(
            x,
            heights,
            width,
            bottom=bottom,
            label=lab,
            color=col,
            edgecolor="white",
            linewidth=0.5,
        )
        _annotate_stacked_pct_counts(ax, x, bottom, heights, cnts)
        bottom += np.array(heights)
    short = [r["path"].replace("LLM Answer Grading ", "").replace(".docx", "") for r in results]
    ax.set_xticks(x, short, rotation=15, ha="right")
    ax.set_ylabel("Share of characters (%)")
    ax.set_title("Highlight mix — Part B Q2+Q3 (per alert)")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    fig.savefig(OUT_DIR / "01_stacked_pct_per_alert.png")
    plt.close(fig)


def fig02_pie_combined(combined_counts: dict[str, int]) -> None:
    sizes = [combined_counts.get(k, 0) for k in STACK_KEYS]
    if sum(sizes) == 0:
        return
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=STACK_LABELS,
        colors=STACK_COLORS,
        autopct=lambda p: f"{p:.1f}%\n({int(p * sum(sizes) / 100)})",
        startangle=90,
        textprops={"fontsize": 9},
    )
    for t in autotexts:
        t.set_fontsize(8)
    ax.set_title("Both alerts combined — character counts by highlight")
    fig.savefig(OUT_DIR / "02_pie_combined_both_alerts.png")
    plt.close(fig)


def fig03_q2_q3_grid(results: list[dict]) -> None:
    """Four 100% stacked columns: each alert × (Q2, Q3)."""
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    n = len(results) * 2
    x = np.arange(n)
    labels: list[str] = []
    for r in results:
        short = r["path"].replace("LLM Answer Grading ", "").replace(".docx", "")
        labels.append(f"{short}\nQ2")
        labels.append(f"{short}\nQ3")
    width = 0.72
    bottom = np.zeros(n)
    for key, lab, col in zip(STACK_KEYS, STACK_LABELS, STACK_COLORS):
        row: list[float] = []
        row_counts: list[int] = []
        for r in results:
            row.append(_pct_map(r["q2_leading_interpretation_chars_by_fill"])[key])
            row_counts.append(r["q2_leading_interpretation_chars_by_fill"].get(key, 0))
            row.append(_pct_map(r["q3_alternative_analysis_chars_by_fill"])[key])
            row_counts.append(r["q3_alternative_analysis_chars_by_fill"].get(key, 0))
        h = np.array(row)
        ax.bar(x, h, width, bottom=bottom, label=lab, color=col, edgecolor="white", linewidth=0.5)
        _annotate_stacked_pct_counts(ax, x, bottom, list(h), row_counts, min_pct_dual=4.0)
        bottom += h
    ax.set_xticks(x, labels, fontsize=8)
    ax.set_ylabel("Share of characters (%)")
    ax.set_title("Q2 vs Q3 — highlight mix within each alert")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    fig.savefig(OUT_DIR / "03_stacked_q2_q3_per_alert.png")
    plt.close(fig)


def fig04_grouped_counts_both_fields(results: list[dict]) -> None:
    """Side-by-side bars: raw character counts (not %) for both fields total."""
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    n = len(results)
    w = 0.2
    x = np.arange(n)
    for i, key in enumerate(STACK_KEYS):
        vals = [r["reasoning_both_parts_chars_by_fill"].get(key, 0) for r in results]
        ax.bar(x + (i - 1.5) * w, vals, w, label=STACK_LABELS[i], color=STACK_COLORS[i])
    short = [r["path"].replace("LLM Answer Grading ", "").replace(".docx", "") for r in results]
    ax.set_xticks(x, short)
    ax.set_ylabel("Characters (Q2 + Q3)")
    ax.set_title("Raw character counts by highlight color (per alert)")
    ax.legend(fontsize=8, ncol=2, loc="upper right")
    fig.savefig(OUT_DIR / "04_grouped_char_counts_per_alert.png")
    plt.close(fig)


def fig05_stacked_correct_vs_incorrect_pooled(results: list[dict]) -> None:
    """Pooled over both .docx: 100% stacks for correct vs incorrect predictions."""
    comb_c: dict[str, int] = {k: 0 for k in STACK_KEYS}
    comb_i: dict[str, int] = {k: 0 for k in STACK_KEYS}
    for r in results:
        bc = r.get("by_llm_correct_vs_gold") or {}
        for k in STACK_KEYS:
            comb_c[k] += (bc.get("correct_chars_by_fill") or {}).get(k, 0)
            comb_i[k] += (bc.get("incorrect_chars_by_fill") or {}).get(k, 0)

    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    x = np.arange(2)
    labels = ["LLM correct\n(vs gold)", "LLM incorrect"]
    width = 0.55
    bottom = np.zeros(2)
    pct_maps = [_pct_map(comb_c), _pct_map(comb_i)]
    for key, lab, col in zip(STACK_KEYS, STACK_LABELS, STACK_COLORS):
        heights = [pct_maps[0].get(key, 0.0), pct_maps[1].get(key, 0.0)]
        cnts = [comb_c.get(key, 0), comb_i.get(key, 0)]
        ax.bar(x, heights, width, bottom=bottom, label=lab, color=col, edgecolor="white", linewidth=0.5)
        _annotate_stacked_pct_counts(ax, x, bottom, heights, cnts)
        bottom += np.array(heights)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Share of characters (%)")
    ax.set_title("Pooled — highlight mix when prediction matches gold vs not")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    fig.savefig(OUT_DIR / "05_stacked_correct_vs_incorrect_pooled.png")
    plt.close(fig)


def fig06_grouped_counts_correct_vs_incorrect_pooled(results: list[dict]) -> None:
    comb_c: dict[str, int] = {k: 0 for k in STACK_KEYS}
    comb_i: dict[str, int] = {k: 0 for k in STACK_KEYS}
    for r in results:
        bc = r.get("by_llm_correct_vs_gold") or {}
        for k in STACK_KEYS:
            comb_c[k] += (bc.get("correct_chars_by_fill") or {}).get(k, 0)
            comb_i[k] += (bc.get("incorrect_chars_by_fill") or {}).get(k, 0)

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    x = np.arange(len(STACK_KEYS))
    w = 0.35
    cvals = [comb_c.get(k, 0) for k in STACK_KEYS]
    ivals = [comb_i.get(k, 0) for k in STACK_KEYS]
    b1 = ax.bar(x - w / 2, cvals, w, label="Correct vs gold", color="#3498db")
    b2 = ax.bar(x + w / 2, ivals, w, label="Incorrect vs gold", color="#e67e22")
    _annotate_grouped_bar_values(ax, b1, cvals)
    _annotate_grouped_bar_values(ax, b2, ivals)
    ax.set_xticks(x, STACK_LABELS)
    ax.set_ylabel("Characters (Q2 + Q3)")
    ax.set_title("Pooled — raw counts by highlight & prediction correctness")
    ax.legend(fontsize=9)
    fig.savefig(OUT_DIR / "06_grouped_counts_correct_vs_incorrect_pooled.png")
    plt.close(fig)


def _fig07_stacked_correct_vs_incorrect_per_alert_core(
    results: list[dict],
    out_filename: str,
    title: str,
    figsize: tuple[float, float],
    *,
    legend_outside_right: bool = False,
) -> None:
    """Build stacked bars: one docx → up to 2 columns (correct / incorrect)."""
    fig, ax = plt.subplots(figsize=figsize)
    cols: list[str] = []
    series: list[dict[str, int]] = []
    for r in results:
        short = r["path"].replace("LLM Answer Grading ", "").replace(".docx", "")
        bc = r.get("by_llm_correct_vs_gold") or {}
        cc = bc.get("correct_chars_by_fill") or {}
        ic = bc.get("incorrect_chars_by_fill") or {}
        if sum(cc.values()):
            cols.append(f"{short}\ncorrect")
            series.append(cc)
        if sum(ic.values()):
            cols.append(f"{short}\nincorrect")
            series.append(ic)
    if not series:
        plt.close(fig)
        return
    n = len(series)
    x = np.arange(n)
    width = 0.65
    bottom = np.zeros(n)
    for key, lab, col in zip(STACK_KEYS, STACK_LABELS, STACK_COLORS):
        heights = [_pct_map(s).get(key, 0.0) for s in series]
        cnts = [s.get(key, 0) for s in series]
        ax.bar(x, heights, width, bottom=bottom, label=lab, color=col, edgecolor="white", linewidth=0.5)
        _annotate_stacked_pct_counts(ax, x, bottom, heights, cnts, min_pct_dual=4.0)
        bottom += np.array(heights)
    ax.set_xticks(x, cols, fontsize=8)
    ax.set_ylabel("Share of characters (%)")
    ax.set_title(title)
    ax.set_ylim(0, 100)
    if legend_outside_right:
        ax.legend(
            loc="upper left",
            bbox_to_anchor=(1.02, 1.0),
            borderaxespad=0.0,
            fontsize=8,
            ncol=1,
            framealpha=0.95,
        )
        fig.subplots_adjust(right=0.68)
    else:
        ax.legend(loc="upper right", fontsize=8, ncol=2)
    fig.savefig(OUT_DIR / out_filename)
    plt.close(fig)


def fig07_stacked_correct_vs_incorrect_per_alert(results: list[dict]) -> None:
    """Two alerts × (correct / incorrect) → up to 4 columns if both splits exist."""
    _fig07_stacked_correct_vs_incorrect_per_alert_core(
        results,
        "07_stacked_correct_vs_incorrect_per_alert.png",
        "Per-alert — highlight mix for correct vs incorrect predictions",
        figsize=(8.0, 4.2),
    )


def fig07b_stacked_correct_vs_incorrect_ztf26_only(results: list[dict]) -> None:
    """ZTF26aargnnp docx only: correct vs incorrect (two columns)."""
    z26 = [r for r in results if "ZTF26aargnnp" in r["path"]]
    if not z26:
        print(
            "[WARN] Skipped 07_stacked_correct_vs_incorrect_per_alert_ztf26_only.png — "
            "no ZTF26aargnnp docx was loaded (place file in repo root or temporary_files/).",
            flush=True,
        )
        return
    _fig07_stacked_correct_vs_incorrect_per_alert_core(
        z26,
        "07_stacked_correct_vs_incorrect_per_alert_ztf26_only.png",
        "ZTF26aargnnp — highlight mix for correct vs incorrect predictions",
        figsize=(5.2, 4.2),
        legend_outside_right=True,
    )


def main() -> None:
    results: list[dict] = []
    for _slug, fn in _DOC_ENTRIES:
        p = _resolve_grading_docx(fn)
        if p is None:
            print("skip missing", fn, "(tried repo root and temporary_files/)")
            continue
        results.append(analyze_docx(p))
    if not results:
        print("no docx found")
        return
    combined: dict[str, int] = {k: 0 for k in STACK_KEYS}
    for r in results:
        for k in STACK_KEYS:
            combined[k] += r["reasoning_both_parts_chars_by_fill"].get(k, 0)

    fig01_stacked_per_alert(results)
    fig02_pie_combined(combined)
    fig03_q2_q3_grid(results)
    fig04_grouped_counts_both_fields(results)
    fig05_stacked_correct_vs_incorrect_pooled(results)
    fig06_grouped_counts_correct_vs_incorrect_pooled(results)
    fig07_stacked_correct_vs_incorrect_per_alert(results)
    fig07b_stacked_correct_vs_incorrect_ztf26_only(results)
    print("Wrote PNGs to", OUT_DIR)


if __name__ == "__main__":
    main()
