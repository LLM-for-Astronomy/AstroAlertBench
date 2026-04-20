"""Per-run matplotlib charts.

Inputs:
    metrics : dict returned by evaluate.evaluate_jsonl(...)
    rows    : list of raw JSONL records (with error_category + value_errors written back)
    out_dir : target directory (will be created)

Outputs PNGs:
    per_class_accuracy.png      — bar chart, 5-class accuracy
    stage3_confusion.png        — heatmap, true vs predicted stage-3 label
    five_class_confusion.png    — heatmap, true vs predicted 5-class
    token_distribution.png      — histogram of n_output_tokens, max_tokens line
    error_breakdown.png         — horizontal bars, format codes
    calibration.png             — scatter of self-confidence vs correctness (if available)

Also writes a plots/README.md describing each plot.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

import matplotlib

matplotlib.use("Agg")  # non-interactive
import matplotlib.pyplot as plt  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluate import (  # noqa: E402
    CLASSES_5,
    GOLD_STAGES,
    normalize_stage1,
    normalize_stage2,
    normalize_stage3_label,
)

PLOT_DESCRIPTIONS: dict[str, str] = {
    "per_class_accuracy.png": (
        "Bar chart of accuracy within each of the five ground-truth classes. "
        "Horizontal dashed line at 20 % marks random-guess baseline. Overlays "
        "the per-class sample count as grey text."
    ),
    "five_class_confusion.png": (
        "End-to-end 5-class confusion matrix (SN / AGN / VS / asteroid / bogus / N-A). "
        "Rows are gold labels, columns are predicted 5-class labels derived from the "
        "staged Part-C output. Unparseable rows land in N-A. Values are raw counts."
    ),
    "stage3_confusion.png": (
        "Stage-3 subclass confusion restricted to rows that reached Stage 3. "
        "Rows are gold astrophysical classes (SN / VS / AGN), columns are the model's "
        "Stage-3 prediction (supernova / variable_star / AGN / N-A)."
    ),
    "token_distribution.png": (
        "Histogram of n_output_tokens per row (full generation including thinking). "
        "Red dashed line at the max_tokens budget shows how close the model came to "
        "the token ceiling. Truncated runs are rows at or near that line."
    ),
    "error_breakdown.png": (
        "Counts of each format-error category (mutually exclusive per row). Includes "
        "'ok' for cleanly parsed rows. Useful for spotting runs dominated by "
        "truncation vs malformed JSON vs schema issues."
    ),
    "calibration.png": (
        "Scatter of self-reported MSRS (mean of three Part-B self-scores) vs binary "
        "correctness of the final 5-class prediction. Correct = 1, wrong = 0. If the "
        "model is well calibrated, high-confidence predictions should be correct. "
        "Generated only when >= 5 linked records exist."
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_5class(s1: str | None, s2: str | None, s3: str | None) -> str:
    if s1 == "artifact":
        return "bogus"
    if s1 == "real_object":
        if s2 == "solar_system":
            return "asteroid"
        if s2 == "astrophysical":
            if s3 == "supernova":
                return "SN"
            if s3 == "AGN":
                return "AGN"
            if s3 == "variable_star":
                return "VS"
    return "N-A"


def _build_5class_preds(rows: list[dict]) -> list[tuple[str, str]]:
    """Return list of (gold_5class, pred_5class) pairs."""
    out = []
    for r in rows:
        gold = r.get("target_class") or "?"
        parsed = r.get("parsed") or {}
        pc = parsed.get("Part C") or parsed.get("part_c") or {}
        pred = _to_5class(
            normalize_stage1(pc.get("stage1")),
            normalize_stage2(pc.get("stage2")),
            normalize_stage3_label(pc.get("stage3")),
        )
        out.append((gold, pred))
    return out


def _savefig(path: Path, fig: plt.Figure) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Individual plot generators
# ---------------------------------------------------------------------------


def plot_per_class_accuracy(metrics: dict, out_path: Path) -> bool:
    per_cls = metrics.get("per_class_accuracy") or {}
    per_tot = metrics.get("per_class_total") or {}
    if not per_cls:
        return False
    classes = [c for c in CLASSES_5 if c in per_cls or c in per_tot]
    vals = [per_cls.get(c, 0.0) for c in classes]
    tots = [per_tot.get(c, 0) for c in classes]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(classes, vals, color=["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#9467bd"])
    ax.axhline(0.2, linestyle="--", color="gray", linewidth=0.8, label="random (20 %)")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("accuracy")
    ax.set_title("Per-class 5-class accuracy")
    for b, v, n in zip(bars, vals, tots):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
        ax.text(b.get_x() + b.get_width() / 2, 0.02, f"n={n}", ha="center", fontsize=8, color="white")
    ax.legend(loc="upper right")
    _savefig(out_path, fig)
    return True


def plot_five_class_confusion(rows: list[dict], out_path: Path) -> bool:
    pairs = _build_5class_preds(rows)
    if not pairs:
        return False
    labels_row = CLASSES_5
    labels_col = CLASSES_5 + ["N-A"]
    cm = np.zeros((len(labels_row), len(labels_col)), dtype=int)
    for gold, pred in pairs:
        if gold not in labels_row:
            continue
        i = labels_row.index(gold)
        j = labels_col.index(pred) if pred in labels_col else labels_col.index("N-A")
        cm[i, j] += 1
    fig, ax = plt.subplots(figsize=(6.5, 5))
    im = ax.imshow(cm, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(labels_col)))
    ax.set_xticklabels(labels_col, rotation=30, ha="right")
    ax.set_yticks(range(len(labels_row)))
    ax.set_yticklabels(labels_row)
    ax.set_xlabel("predicted 5-class")
    ax.set_ylabel("gold 5-class")
    ax.set_title("End-to-end 5-class confusion matrix")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            if cm[i, j] > 0:
                color = "white" if cm[i, j] > cm.max() * 0.6 else "black"
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", color=color, fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.7)
    _savefig(out_path, fig)
    return True


def plot_stage3_confusion(metrics: dict, out_path: Path) -> bool:
    cm_dict = metrics.get("part_c_stage3_confusion_matrix")
    if not cm_dict:
        return False
    row_labels = ["supernova", "variable_star", "AGN"]
    col_labels = ["supernova", "variable_star", "AGN", "N/A"]
    cm = np.zeros((len(row_labels), len(col_labels)), dtype=int)
    for i, r in enumerate(row_labels):
        for j, c in enumerate(col_labels):
            cm[i, j] = cm_dict.get(r, {}).get(c, 0)
    fig, ax = plt.subplots(figsize=(5.5, 4))
    im = ax.imshow(cm, cmap="Oranges", aspect="auto")
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=20, ha="right")
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels)
    ax.set_xlabel("predicted stage-3")
    ax.set_ylabel("gold stage-3")
    ax.set_title("Stage-3 subclass confusion")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            if cm[i, j] > 0:
                color = "white" if cm[i, j] > cm.max() * 0.6 else "black"
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", color=color, fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.7)
    _savefig(out_path, fig)
    return True


def plot_token_distribution(rows: list[dict], out_path: Path) -> bool:
    toks = [r["n_output_tokens"] for r in rows if isinstance(r.get("n_output_tokens"), int)]
    if not toks:
        return False
    max_tok = max((r.get("max_tokens") or 0) for r in rows) or None
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(toks, bins=30, color="#4c72b0", edgecolor="black", alpha=0.85)
    if max_tok:
        ax.axvline(max_tok, color="red", linestyle="--", linewidth=1.2, label=f"max_tokens={max_tok}")
        ax.legend()
    ax.set_xlabel("n_output_tokens (full generation incl. thinking)")
    ax.set_ylabel("rows")
    ax.set_title("Output-token distribution per row")
    _savefig(out_path, fig)
    return True


def plot_error_breakdown(metrics: dict, out_path: Path) -> bool:
    fmt = (metrics.get("error_breakdown") or {}).get("format") or {}
    if not fmt:
        return False
    items = sorted(fmt.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.45 * len(labels))))
    colors = ["#2ca02c" if lbl == "ok" else "#d62728" for lbl in labels]
    ax.barh(labels, vals, color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("row count")
    ax.set_title("Format error breakdown")
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.01, i, str(v), va="center", fontsize=9)
    _savefig(out_path, fig)
    return True


def plot_calibration(metrics: dict, rows: list[dict], out_path: Path) -> bool:
    # Uses the per-row B/C linkage data. We re-derive because metrics only has aggregates.
    from evaluate import extract_self_scores

    xs: list[float] = []
    ys: list[int] = []
    for r in rows:
        parsed = r.get("parsed") or {}
        pb = parsed.get("Part B") or parsed.get("part_b")
        if not isinstance(pb, dict):
            continue
        scores = extract_self_scores(pb)
        if any(s is None for s in scores):
            continue
        gold = r.get("target_class")
        pc = parsed.get("Part C") or parsed.get("part_c") or {}
        pred = _to_5class(
            normalize_stage1(pc.get("stage1")),
            normalize_stage2(pc.get("stage2")),
            normalize_stage3_label(pc.get("stage3")),
        )
        xs.append(float(np.mean(scores)))
        ys.append(1 if pred == gold else 0)
    if len(xs) < 5:
        return False
    xs_arr = np.array(xs)
    ys_arr = np.array(ys)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    jitter = (np.random.default_rng(42).random(len(ys_arr)) - 0.5) * 0.06
    ax.scatter(xs_arr, ys_arr + jitter, alpha=0.5, s=30)
    # Bucket means
    bucket_edges = np.linspace(1, 5, 9)
    bucket_centers = 0.5 * (bucket_edges[:-1] + bucket_edges[1:])
    bucket_means = []
    for lo, hi in zip(bucket_edges[:-1], bucket_edges[1:]):
        mask = (xs_arr >= lo) & (xs_arr < hi)
        bucket_means.append(ys_arr[mask].mean() if mask.any() else np.nan)
    ax.plot(bucket_centers, bucket_means, marker="o", color="red", label="bucket mean accuracy")
    ax.set_xlim(1, 5)
    ax.set_ylim(-0.1, 1.1)
    ax.set_xlabel("self-rated MSRS (mean of 3 Part-B self-scores)")
    ax.set_ylabel("correct? (0 = wrong, 1 = right)")
    ax.set_title(f"Calibration: self-confidence vs correctness  (n = {len(xs_arr)})")
    ax.legend()
    _savefig(out_path, fig)
    return True


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def build_all_plots(metrics: dict, rows: list[dict], out_dir: Path) -> list[str]:
    """Generate every plot that has enough data. Returns list of generated filenames."""
    out_dir.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    for name, fn in [
        ("per_class_accuracy.png", lambda: plot_per_class_accuracy(metrics, out_dir / "per_class_accuracy.png")),
        ("five_class_confusion.png", lambda: plot_five_class_confusion(rows, out_dir / "five_class_confusion.png")),
        ("stage3_confusion.png", lambda: plot_stage3_confusion(metrics, out_dir / "stage3_confusion.png")),
        ("token_distribution.png", lambda: plot_token_distribution(rows, out_dir / "token_distribution.png")),
        ("error_breakdown.png", lambda: plot_error_breakdown(metrics, out_dir / "error_breakdown.png")),
        ("calibration.png", lambda: plot_calibration(metrics, rows, out_dir / "calibration.png")),
    ]:
        try:
            ok = fn()
            if ok:
                generated.append(name)
        except Exception as e:
            print(f"[plots] {name} failed: {e}")

    # Write a README.md with descriptions + inline previews
    readme = [f"# Plots for this run\n"]
    for name in generated:
        readme.append(f"## `{name}`\n")
        readme.append(PLOT_DESCRIPTIONS.get(name, "(no description)"))
        readme.append(f"\n\n![{name}](./{name})\n")
    (out_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")

    return generated
