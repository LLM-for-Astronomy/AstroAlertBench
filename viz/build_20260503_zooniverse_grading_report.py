"""Build figures + markdown report for Zooniverse LLM-response grading.

Merges `temporary_files/llm-for-astronomy-classifications (4).csv` and `(5).csv`
(deduplicated by `classification_id`), joins benchmark `run.jsonl` via
`viz.build_llm_example_grading.RUN_SPECS` (PNG index 1..13).

**§1 (ZTF26aargnnp):** Four Zooniverse lanes on workflow **(X)** plus **Matthew**’s 0–5
scores from `LLM Answer Grading ZTF26aargnnp.docx` (equal weight). Workflow **(D)** is a
separate alert (**ZTF25aaxmsns**, SN) and does not appear in §1.

**§2–3 (pooled):** Five gold OID surfaces — **ZTF19abfqvbg** (expert `.docx`), Zooniverse
**(A, B, C)**, and **ZTF25aaxmsns** from **LLM Response Grading (D)** (e.g. **theodlz**).
Workflow **(X)** remains §1-only on **ZTF26aargnnp**.

Run from repo root::

    python -m viz.build_20260503_zooniverse_grading_report

Writes figures under ``results_comparison/report/charts/<subdir>_May03/`` (PNG names ``20260503_*.png``) and
``results_comparison/report/20260503_report_zooniverse_llm_grading.md``.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluate import (  # noqa: E402
    normalize_stage1,
    normalize_stage2,
    normalize_stage3_label,
    stages_to_final_class,
)
from viz.build_llm_example_grading import RUN_SPECS  # noqa: E402
from viz._analyze_llm_grading_docx_highlights import (  # noqa: E402
    per_model_merged_fills_in_doc_order,
    per_model_your_grading_0_5,
)

RESULTS_DIR = PROJECT_ROOT / "results_comparison"
CHARTS_ROOT = RESULTS_DIR / "report" / "charts"
# Subfolder under charts/; name ends with May03 per report convention.
CHARTS_SUBDIR_NAME = "zooniverse_llm_grading_May03"
CHARTS_DIR = CHARTS_ROOT / CHARTS_SUBDIR_NAME
CHART_MD_PREFIX = f"charts/{CHARTS_SUBDIR_NAME}"
REPORT_PATH = RESULTS_DIR / "report" / "20260503_report_zooniverse_llm_grading.md"
CSV_PATHS: list[Path] = [
    PROJECT_ROOT / "temporary_files" / "llm-for-astronomy-classifications (4).csv",
    PROJECT_ROOT / "temporary_files" / "llm-for-astronomy-classifications (5).csv",
]
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifest_benchmark_final.csv"
DOCX_Z26_CANDIDATES = [
    PROJECT_ROOT / "temporary_files" / "LLM Answer Grading ZTF26aargnnp.docx",
    PROJECT_ROOT / "LLM Answer Grading ZTF26aargnnp.docx",
]
DOCX_Z19_CANDIDATES = [
    PROJECT_ROOT / "temporary_files" / "LLM Answer Grading ZTF19abfqvbg.docx",
    PROJECT_ROOT / "LLM Answer Grading ZTF19abfqvbg.docx",
]

WF_TO_OID = {
    "LLM Response Grading (X)": "ZTF26aargnnp",
    "LLM Response Grading (D)": "ZTF25aaxmsns",
    "LLM Response Grading (A)": "ZTF19aayhwvd",
    "LLM Response Grading (B)": "ZTF19abkdsaw",
    "LLM Response Grading (C)": "ZTF25aahvsli",
}

# Pooled self-score / human joins: workflow (D) → ZTF25aaxmsns (SN), not ZTF26.
SECTION2_OIDS: list[str] = [
    "ZTF19abfqvbg",
    "ZTF19aayhwvd",
    "ZTF19abkdsaw",
    "ZTF25aahvsli",
    "ZTF25aaxmsns",
]

MATTHEW_RATER_LABEL = "Matthew (expert .docx)"

Z26_RATER_ORDER = [
    "libai_astro",
    "lukehandley",
    "RickyN",
    "theodlz",
    MATTHEW_RATER_LABEL,
]

Z26_ZOONIVERSE_WF = "LLM Response Grading (X)"
SECTION2_D_WF = "LLM Response Grading (D)"
SECTION2_ZOON_WFS = frozenset(
    {"LLM Response Grading (A)", "LLM Response Grading (B)", "LLM Response Grading (C)"}
)

OID_PROFILE_LABELS = [
    "ZTF19abfqvbg\n(expert .docx)",
    "ZTF19aayhwvd\n(VS · Zoon. A)",
    "ZTF19abkdsaw\n(AGN · Zoon. B)",
    "ZTF25aahvsli\n(bogus · Zoon. C)",
    "ZTF25aaxmsns\n(SN · Zoon. D)",
]

MODEL_DISPLAY = [
    "Gemini 2.5 Pro high",
    "Gemini 2.5 Flash none",
    "GPT-5.4 high",
    "GPT-5.4 none",
    "Opus 4.7 think",
    "Opus 4.7 nothink",
    "Kimi K2.5 think",
    "Qwen3.5-4B think",
    "Qwen3.5-4B nothink",
    "Qwen3.5-35B think",
    "Qwen3.5-35B nothink",
    "Qwen3.5-397B think",
    "Qwen3.5-397B nothink",
]


def _final_class_from_parsed(parsed: dict) -> str | None:
    if not isinstance(parsed, dict):
        return None
    pc = parsed.get("Part C") or parsed.get("part_c")
    if not isinstance(pc, dict):
        return None
    s1 = normalize_stage1(pc.get("stage1"))
    s2 = normalize_stage2(pc.get("stage2"))
    s3 = normalize_stage3_label(pc.get("stage3"))
    if s1 is None or s2 is None or s3 is None:
        return None
    return stages_to_final_class(s1, s2, s3)


def _part_b_scores(parsed: dict) -> tuple[float | None, float | None, float | None]:
    if not isinstance(parsed, dict):
        return None, None, None
    pb = parsed.get("Part B") or parsed.get("part_b")
    if not isinstance(pb, dict):
        return None, None, None

    def g(key: str) -> float | None:
        v = pb.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    k = g("self_score_key_evidence")
    l_ = g("self_score_leading_interpretation_and_support")
    a = g("self_score_alternative_analysis")
    return k, l_, a


def build_run_features() -> pd.DataFrame:
    oids = list(SECTION2_OIDS)
    manifest = pd.read_csv(MANIFEST_PATH, dtype=str)
    gold = manifest.set_index("oid")["target_class"].to_dict()

    by_slug: dict[str, dict[str, dict]] = {}
    for slug, path, _tag in RUN_SPECS:
        idx: dict[str, dict] = {}
        with path.open(encoding="utf-8") as f:
            for line in f:
                o = json.loads(line)
                oid_k = o.get("oid")
                if oid_k:
                    idx[str(oid_k)] = o
        by_slug[slug] = idx

    rows: list[dict] = []
    for run_idx, (slug, _path, _tag) in enumerate(RUN_SPECS, start=1):
        blob = by_slug[slug]
        for oid in oids:
            line = blob.get(oid)
            if not line:
                continue
            target = str(gold.get(oid, ""))
            parsed = line.get("parsed")
            pred = _final_class_from_parsed(parsed) if isinstance(parsed, dict) else None
            ok = bool(pred is not None and target and pred == target)
            k, l_, a = _part_b_scores(parsed) if isinstance(parsed, dict) else (None, None, None)
            scores_3 = [x for x in (k, l_, a) if x is not None]
            mean_all = float(np.mean(scores_3)) if len(scores_3) == 3 else None
            pair = [x for x in (l_, a) if x is not None]
            mean_q23 = float(np.mean(pair)) if len(pair) == 2 else None
            rows.append(
                {
                    "oid": oid,
                    "run_idx": run_idx,
                    "model_slug": slug,
                    "model_label": MODEL_DISPLAY[run_idx - 1],
                    "target_class": target,
                    "pred_final": pred,
                    "is_correct": ok,
                    "self_key": k,
                    "self_lead": l_,
                    "self_alt": a,
                    "mean_self_all": mean_all,
                    "mean_self_q23": mean_q23,
                }
            )
    return pd.DataFrame(rows)


def _rater_label(row: pd.Series) -> str:
    """Single `theodlz` label on ZTF26 (workflow D is excluded from §1 tables)."""
    oid = str(row.get("oid", ""))
    user = str(row.get("user_name", ""))
    if oid == "ZTF26aargnnp" and user == "theodlz":
        return "theodlz"
    return user


def load_human_grades() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for p in CSV_PATHS:
        if not p.is_file():
            print(f"[WARN] missing {p.name}, skip", file=sys.stderr)
            continue
        frames.append(pd.read_csv(p, dtype=str, keep_default_na=False))
    if not frames:
        raise FileNotFoundError("no classification CSV found under temporary_files/")
    df = pd.concat(frames, ignore_index=True)
    df["classification_id"] = df["classification_id"].astype(str)
    df = df.drop_duplicates(subset=["classification_id"], keep="first")

    sub = df[df["workflow_name"].isin(WF_TO_OID)].copy()
    sub["oid"] = sub["workflow_name"].map(WF_TO_OID)

    def parse_grade(row) -> int | None:
        try:
            ann = json.loads(row["annotations"])
            return int(ann[0]["value"])
        except (json.JSONDecodeError, KeyError, ValueError, IndexError):
            return None

    def parse_idx_slug(row) -> tuple[str | None, str | None]:
        try:
            sd = json.loads(row["subject_data"])
            for _k, v in sd.items():
                fn = v.get("Filename", "")
                m = re.match(r"^(\d+)_(.+)_grading\.png$", fn)
                if m:
                    return int(m.group(1)), m.group(2)
        except (json.JSONDecodeError, AttributeError, KeyError):
            pass
        return None, None

    sub["human_grade"] = sub.apply(parse_grade, axis=1)
    idx_slug = sub.apply(parse_idx_slug, axis=1, result_type="expand")
    sub["run_idx"] = idx_slug[0]
    sub["model_slug"] = idx_slug[1]
    sub = sub.dropna(subset=["human_grade", "run_idx"])
    sub["human_grade"] = sub["human_grade"].astype(int)
    sub["run_idx"] = sub["run_idx"].astype(int)
    sub["rater_label"] = sub.apply(_rater_label, axis=1)
    return sub


def _parse_docx_grades_13(path: Path | None) -> list[int] | None:
    if path is None or not path.is_file():
        return None
    raw = per_model_your_grading_0_5(path)
    if len(raw) != 13 or any(x is None for x in raw):
        print(
            f"[WARN] expected 13 integer Your Grading lines in {path}, got {len(raw)} parses",
            file=sys.stderr,
        )
        return None
    return [int(x) for x in raw]


def _expert_docx_grade_rows(
    oid: str,
    grades: list[int],
    rater_label: str,
    workflow_name: str,
) -> pd.DataFrame:
    rows: list[dict] = []
    for i, g in enumerate(grades, start=1):
        rows.append(
            {
                "classification_id": f"synthetic_docx_{oid}_{i}",
                "workflow_name": workflow_name,
                "user_name": "Matthew",
                "oid": oid,
                "human_grade": g,
                "run_idx": i,
                "model_slug": "",
                "rater_label": rater_label,
            }
        )
    return pd.DataFrame(rows)


def cronbach_alpha(matrix: np.ndarray) -> float | None:
    """matrix: n_subjects × k_items (e.g. 13 models × k raters)."""
    if matrix.shape[1] < 2:
        return None
    item_vars = matrix.var(axis=0, ddof=1)
    total = matrix.sum(axis=1)
    total_var = total.var(ddof=1)
    if total_var <= 0:
        return None
    k = matrix.shape[1]
    return float((k / (k - 1)) * (1.0 - item_vars.sum() / total_var))


def fig_per_oid_profile_by_model(
    human: pd.DataFrame,
    path: Path,
    oids: list[str],
    bar_labels: list[str],
) -> None:
    """Grouped bars: per model index, mean human grade on each pooled §2 OID (typically five)."""
    g = human.groupby(["oid", "run_idx"], as_index=False)["human_grade"].mean()
    fig, ax = plt.subplots(figsize=(14, 4.6))
    x = np.arange(13)
    n_b = len(oids)
    w = min(0.18, 0.7 / max(n_b, 1))
    off = (n_b - 1) / 2.0
    for i, (oid, lab) in enumerate(zip(oids, bar_labels)):
        sub = g[g["oid"] == oid].set_index("run_idx")["human_grade"].reindex(range(1, 14))
        ax.bar(x + (i - off) * w, sub, width=w, label=lab, alpha=0.9, edgecolor="k", linewidth=0.2)
    ax.set_xticks(x)
    ax.set_xticklabels([str(i + 1) for i in range(13)])
    ax.set_xlabel("Model index (1 = Gemini Pro high … 13 = Qwen 397B nothink)")
    ax.set_ylabel("Mean human grade (0–5)")
    ax.set_title(
        "Per-model mean human grade by §2 alert "
        "(abfqvbg = expert .docx; A/B/C = Zooniverse; D = ZTF25aaxmsns SN)"
    )
    ax.legend(fontsize=7, ncol=2, loc="upper right")
    ax.set_ylim(0, 5.5)
    ax.axhline(2.5, color="gray", ls=":", lw=0.7, alpha=0.6)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def z26_full_scores_markdown(z26: pd.DataFrame) -> list[str]:
    wide = z26.pivot_table(
        index="run_idx", columns="rater_label", values="human_grade", aggfunc="first"
    ).reindex(range(1, 14))
    cols = [c for c in Z26_RATER_ORDER if c in wide.columns]
    if not cols:
        return ["*(No rater columns matched `Z26_RATER_ORDER`.)*"]
    wide = wide[cols].copy()
    wide["Mean"] = wide.mean(axis=1)
    wide["SD"] = wide.std(axis=1, ddof=1)
    lines = [
        "| Idx | Model | " + " | ".join(cols) + " | Mean | SD |",
        "| ---: | :--- | " + " | ".join(["---:"] * len(cols)) + " | ---: | ---: |",
    ]
    for i in range(1, 14):
        row = wide.loc[i]
        cells = [str(int(row[c])) if pd.notna(row[c]) else "—" for c in cols]
        lines.append(
            f"| {i} | {MODEL_DISPLAY[i - 1]} | "
            + " | ".join(cells)
            + f" | {row['Mean']:.2f} | {row['SD']:.2f} |"
        )
    return lines


def _find_ztf26_docx() -> Path | None:
    for p in DOCX_Z26_CANDIDATES:
        if p.is_file():
            return p
    return None


def _find_docx_z19() -> Path | None:
    for p in DOCX_Z19_CANDIDATES:
        if p.is_file():
            return p
    return None


def _docx_rgb_tone_by_run_idx(docx_path: Path) -> pd.DataFrame | None:
    """Per model block in .docx order → run_idx 1..13; tone = (green−red)/(R+Y+G)."""
    blocks = per_model_merged_fills_in_doc_order(docx_path)
    if not blocks:
        return None
    rows: list[dict] = []
    for i, c in enumerate(blocks, start=1):
        g = int(c.get("green", 0))
        y = int(c.get("yellow", 0))
        r = int(c.get("red", 0))
        u = int(c.get("unhighlighted", 0))
        rgb = g + y + r
        tot = rgb + u
        rows.append(
            {
                "run_idx": i,
                "pct_green_of_rgb": (100.0 * g / rgb) if rgb else np.nan,
                "tone_green_minus_red": ((g - r) / rgb) if rgb else np.nan,
                "rgb_chars": rgb,
            }
        )
    return pd.DataFrame(rows)


def fig_rater_heatmap(z26: pd.DataFrame, path: Path) -> None:
    pivot = z26.pivot_table(
        index="rater_label",
        columns="run_idx",
        values="human_grade",
        aggfunc="first",
    )
    pivot = pivot.reindex(Z26_RATER_ORDER)
    pivot = pivot.reindex(columns=list(range(1, 14)))
    fig, ax = plt.subplots(figsize=(14, 3.2))
    arr = pivot.to_numpy(dtype=float)
    im = ax.imshow(arr, aspect="auto", vmin=0, vmax=5, cmap="viridis")
    ax.set_xticks(np.arange(13))
    ax.set_xticklabels([f"{i+1}" for i in range(13)], fontsize=8)
    ax.set_yticks(np.arange(len(pivot)))
    ax.set_yticklabels(pivot.index, fontsize=9)
    ax.set_xlabel("Model index (see table: Gemini Pro … Qwen 397B nothink)")
    ax.set_ylabel("Rater (4 Zooniverse X + Matthew .docx)")
    ax.set_title("ZTF26aargnnp — human grades (0–5): five §1 graders × 13 models")
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, f"{arr[i, j]:.0f}", ha="center", va="center", color="w", fontsize=8)
    fig.colorbar(im, ax=ax, label="Grade", fraction=0.025, pad=0.02)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_mean_sd_bars(z26: pd.DataFrame, path: Path) -> None:
    g = z26.groupby("run_idx")["human_grade"].agg(["mean", "std", "count"]).reindex(
        range(1, 14)
    )
    x = np.arange(13)
    fig, ax = plt.subplots(figsize=(12, 4))
    means = g["mean"].to_numpy(dtype=float)
    errs = g["std"].replace({np.nan: 0}).to_numpy(dtype=float)
    rects = ax.bar(x, means, yerr=errs, capsize=4, color="steelblue", edgecolor="navy", alpha=0.85)
    ax.bar_label(
        rects,
        labels=[f"{v:.2f}" if not np.isnan(v) else "" for v in means],
        padding=2,
        fontsize=7,
        fontweight="bold",
    )
    ax.set_xticks(x)
    ax.set_xticklabels([f"{i+1}\n{MODEL_DISPLAY[i][:10]}…" for i in range(13)], fontsize=7)
    ax.set_ylabel("Mean human grade (±1 SD across §1 graders)")
    ax.set_title("ZTF26aargnnp — mean ± SD across five graders (values on bars = mean)")
    ax.set_ylim(0, 5.5)
    ax.axhline(2.5, color="gray", ls="--", lw=0.8, alpha=0.7)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_pairwise_raters(z26: pd.DataFrame, path: Path) -> None:
    """Pearson r between every pair of graders (13 models each)."""
    wide = z26.pivot_table(
        index="run_idx", columns="rater_label", values="human_grade", aggfunc="first"
    ).reindex(range(1, 14))
    cols = [c for c in Z26_RATER_ORDER if c in wide.columns]
    if len(cols) < 2:
        return
    wide = wide[cols]
    k = len(cols)
    R = np.eye(k)
    for i in range(k):
        for j in range(i + 1, k):
            a = wide[cols[i]].to_numpy(dtype=float)
            b = wide[cols[j]].to_numpy(dtype=float)
            if np.nanstd(a) < 1e-9 or np.nanstd(b) < 1e-9:
                r = np.nan
            else:
                r, _ = stats.pearsonr(a, b)
            R[i, j] = R[j, i] = float(r) if not np.isnan(r) else np.nan
    fig, ax = plt.subplots(figsize=(6.2, 5))
    im = ax.imshow(R, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(np.arange(k))
    ax.set_yticks(np.arange(k))
    ax.set_xticklabels(cols, rotation=35, ha="right", fontsize=7)
    ax.set_yticklabels(cols, fontsize=7)
    for i in range(k):
        for j in range(k):
            v = R[i, j]
            t = f"{v:.2f}" if not np.isnan(v) else "—"
            ax.text(j, i, t, ha="center", va="center", color="black", fontsize=8)
    ax.set_title("ZTF26aargnnp — Pearson r between graders (13 models)")
    fig.colorbar(im, ax=ax, fraction=0.046, label="Pearson r")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_scatter_self_human(merged: pd.DataFrame, ycol: str, title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 5))
    colors = {
        "ZTF19abfqvbg": "C0",
        "ZTF19aayhwvd": "C1",
        "ZTF19abkdsaw": "C2",
        "ZTF25aahvsli": "C3",
        "ZTF25aaxmsns": "C4",
    }
    pal = [plt.cm.tab10(i / 10.0) for i in range(10)]
    for i, (oid, sub) in enumerate(merged.groupby("oid")):
        col = colors.get(oid, pal[i % len(pal)])
        ax.scatter(
            sub[ycol],
            sub["human_mean"],
            label=oid,
            s=45,
            alpha=0.8,
            color=col,
            edgecolors="k",
            linewidths=0.35,
        )
    all_x = merged[ycol].to_numpy()
    all_y = merged["human_mean"].to_numpy()
    mask = ~(np.isnan(all_x) | np.isnan(all_y))
    if mask.sum() > 2:
        r, p = stats.pearsonr(all_x[mask], all_y[mask])
        coef = np.polyfit(all_x[mask], all_y[mask], 1)
        xs = np.linspace(all_x[mask].min(), all_x[mask].max(), 50)
        ax.plot(xs, np.poly1d(coef)(xs), color="gray", ls="--", label=f"OLS fit ( Pearson r={r:.2f}, p={p:.2e})")
    ax.set_xlabel(
        "Mean Part B self-score"
        + (" (key + lead + alt)" if ycol == "mean_self_all" else " (lead + alt only)")
    )
    ax.set_ylabel("Human grade (mean across raters when multiple)")
    ax.set_title(title)
    ax.legend(fontsize=7, loc="best")
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(-0.2, 5.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_correctness_violin(merged: pd.DataFrame, path: Path) -> None:
    correct = merged[merged["is_correct"]]["human_mean"].dropna()
    wrong = merged[~merged["is_correct"]]["human_mean"].dropna()
    if len(correct) == 0 or len(wrong) == 0:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.violinplot([correct, wrong], positions=[0, 1], showmeans=True, widths=0.55)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Part C correct", "Part C incorrect"])
    ax.set_ylabel("Human mean grade (0–5)")
    ax.set_title("Human reasoning grades vs benchmark correctness (§2 OIDs × 13 models)")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_correctness_by_model(merged: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 4))
    run_ids = list(range(1, 14))
    means_c: list[float] = []
    means_w: list[float] = []
    for r in run_ids:
        sl = merged[merged["run_idx"] == r]
        mc = sl[sl["is_correct"]]["human_mean"].mean()
        mw = sl[~sl["is_correct"]]["human_mean"].mean()
        means_c.append(float(mc) if not pd.isna(mc) else np.nan)
        means_w.append(float(mw) if not pd.isna(mw) else np.nan)
    x = np.arange(13)
    w = 0.35
    rc = ax.bar(x - w / 2, means_c, width=w, label="Correct", color="#2ca02c", alpha=0.85)
    rw = ax.bar(x + w / 2, means_w, width=w, label="Incorrect", color="#d62728", alpha=0.85)
    ax.bar_label(
        rc,
        labels=[f"{v:.2f}" if not np.isnan(v) else "" for v in means_c],
        padding=2,
        fontsize=6,
    )
    ax.bar_label(
        rw,
        labels=[f"{v:.2f}" if not np.isnan(v) else "" for v in means_w],
        padding=2,
        fontsize=6,
    )
    ax.set_xticks(x)
    ax.set_xticklabels([str(i + 1) for i in range(13)], fontsize=9)
    ax.set_xlabel("Model index (1 = Gemini Pro high … 13 = Qwen 397B nothink)")
    ax.set_ylabel("Mean human grade")
    ax.set_title("Mean human grade split by Part C correctness (§2 OIDs × 13 models)")
    ax.legend()
    ax.set_ylim(0, 5.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_per_model_correlation(merged: pd.DataFrame, path: Path) -> None:
    rs: list[float] = []
    ps: list[float] = []
    for r in range(1, 14):
        sl = merged[merged["run_idx"] == r].dropna(subset=["mean_self_all", "human_mean"])
        if len(sl) < 3:
            rs.append(np.nan)
            ps.append(np.nan)
            continue
        xa = sl["mean_self_all"].to_numpy(dtype=float)
        ya = sl["human_mean"].to_numpy(dtype=float)
        if np.nanstd(xa) < 1e-12 or np.nanstd(ya) < 1e-12:
            rs.append(np.nan)
            ps.append(np.nan)
            continue
        c, p = stats.pearsonr(xa, ya)
        rs.append(float(c))
        ps.append(float(p))
    fig, ax = plt.subplots(figsize=(11, 3.8))
    x = np.arange(13)
    rects = ax.bar(x, rs, color="teal", edgecolor="k", linewidth=0.4)
    ax.bar_label(
        rects,
        labels=[f"{v:.2f}" if not np.isnan(v) else "—" for v in rs],
        padding=2,
        fontsize=7,
        fontweight="bold",
    )
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([str(i + 1) for i in range(13)])
    ax.set_xlabel("Model index")
    ax.set_ylabel("Pearson r (§2 OIDs: self_all vs human mean)")
    ax.set_title("Per-model correlation: mean self-scores vs mean human grades (r on each bar)")
    ax.set_ylim(-1.05, 1.05)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_docx_tone_vs_zooniverse_mean(
    z26: pd.DataFrame,
    docx_path: Path,
    path: Path,
) -> tuple[float | None, float | None, int]:
    """Expert (green−red)/highlight vs mean Zooniverse grades; same 13 model order as .docx."""
    doc_df = _docx_rgb_tone_by_run_idx(docx_path)
    if doc_df is None or doc_df.empty:
        return None, None, 0
    zmean = z26.groupby("run_idx")["human_grade"].mean().reindex(range(1, 14))
    doc_df = doc_df[doc_df["run_idx"].between(1, 13)].copy()
    doc_df["human_mean_z"] = doc_df["run_idx"].map(zmean.to_dict())
    m = doc_df.dropna(subset=["tone_green_minus_red", "human_mean_z"])
    n = len(m)
    r = p = None
    if n > 2:
        r, p = stats.pearsonr(
            m["tone_green_minus_red"].to_numpy(dtype=float),
            m["human_mean_z"].to_numpy(dtype=float),
        )
        r, p = float(r), float(p)
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    sc = ax.scatter(
        m["tone_green_minus_red"],
        m["human_mean_z"],
        s=55,
        c=m["run_idx"],
        cmap="tab20",
        vmin=1,
        vmax=13,
        edgecolors="k",
        linewidths=0.35,
    )
    for _, row in m.iterrows():
        ax.annotate(
            f"{int(row['run_idx'])}",
            (row["tone_green_minus_red"], row["human_mean_z"]),
            textcoords="offset points",
            xytext=(3, 2),
            fontsize=7,
        )
    xs = m["tone_green_minus_red"].to_numpy(dtype=float)
    ys = m["human_mean_z"].to_numpy(dtype=float)
    if n > 2 and np.nanstd(xs) > 1e-9:
        coef = np.polyfit(xs, ys, 1)
        xline = np.linspace(xs.min(), xs.max(), 40)
        ax.plot(xline, np.poly1d(coef)(xline), ls="--", color="gray", lw=1)
    ax.axhline(2.5, color="lightgray", ls=":", lw=0.8)
    ax.set_xlabel("Expert highlight tone: (green − red) / (green + yellow + red) in .docx Q2+Q3")
    ax.set_ylabel("Mean grade — 4 Zooniverse (X) + Matthew .docx (0–5)")
    ttl = "ZTF26aargnnp — expert highlight tone vs blended §1 mean (per model)"
    if r is not None and p is not None:
        ttl += f"\nPearson r = {r:.2f}, p = {p:.2e}, n = {n}"
    ax.set_title(ttl, fontsize=10)
    ax.set_ylim(-0.2, 5.5)
    ax.set_xlim(-1.05, 1.05)
    cbar = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Model index")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return r, p, n


def fig_inter_rater_mae_heatmap(z26: pd.DataFrame, path: Path) -> None:
    cols = [c for c in Z26_RATER_ORDER if c in z26["rater_label"].unique()]
    if len(cols) < 2:
        return
    wide = z26.pivot_table(
        index="run_idx", columns="rater_label", values="human_grade", aggfunc="first"
    ).reindex(range(1, 14))
    wide = wide[cols]
    k = len(cols)
    mad = np.zeros((k, k))
    for i, a in enumerate(cols):
        for j, b in enumerate(cols):
            if i == j:
                mad[i, j] = 0.0
            else:
                mad[i, j] = float(np.mean(np.abs(wide[a].to_numpy() - wide[b].to_numpy())))
    fig, ax = plt.subplots(figsize=(5, 4.2))
    im = ax.imshow(mad, cmap="Oranges", vmin=0, vmax=max(2.5, mad.max() * 1.05))
    ax.set_xticks(np.arange(k))
    ax.set_yticks(np.arange(k))
    ax.set_xticklabels(cols, rotation=35, ha="right", fontsize=8)
    ax.set_yticklabels(cols, fontsize=8)
    ax.set_title("Mean |grade_i − grade_j| across 13 models\n(ZTF26 — §1 graders)")
    for i in range(k):
        for j in range(k):
            ax.text(j, i, f"{mad[i, j]:.2f}", ha="center", va="center", color="black", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Mean abs diff (0–5 scale)")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_correctness_counts(merged: pd.DataFrame, path: Path) -> None:
    c = int(merged[merged["is_correct"]].shape[0])
    w = int(merged[~merged["is_correct"]].shape[0])
    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    rects = ax.bar([0, 1], [c, w], color=["#2ca02c", "#d62728"], width=0.55, edgecolor="k")
    ax.bar_label(rects, labels=[str(c), str(w)], fontsize=12, fontweight="bold", padding=4)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Part C correct", "Part C incorrect"])
    ax.set_ylabel("Number of (OID × model) rows")
    ax.set_title("Sample sizes: §2 panel — 5 OIDs × 13 models (value on each bar = n)")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_per_oid_self_human_correlation(merged: pd.DataFrame, path: Path) -> list[str]:
    """Bar chart: Pearson r per OID (n=13 models); bar labels = r to 2 decimals."""
    present = set(merged["oid"].astype(str).unique())
    oids = [o for o in SECTION2_OIDS if o in present]
    for o in sorted(present):
        if o not in oids:
            oids.append(o)
    rs: list[float] = []
    for oid in oids:
        sl = merged[(merged["oid"] == oid)].dropna(subset=["mean_self_all", "human_mean"])
        if len(sl) < 3 or np.nanstd(sl["mean_self_all"]) < 1e-9 or np.nanstd(sl["human_mean"]) < 1e-9:
            rs.append(np.nan)
        else:
            r, _ = stats.pearsonr(sl["mean_self_all"], sl["human_mean"])
            rs.append(float(r))
    x = np.arange(len(oids))
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    rects = ax.bar(x, rs, color="slateblue", edgecolor="k", linewidth=0.4)
    ax.bar_label(rects, labels=[f"{v:.2f}" if not np.isnan(v) else "—" for v in rs], fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(oids, rotation=15, ha="right", fontsize=8)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_ylabel("Pearson r (13 models)")
    ax.set_title("Per-alert correlation: mean self (3 Part B fields) vs human mean")
    ax.set_ylim(-1.05, 1.05)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    lines = []
    for oid, r in zip(oids, rs):
        sl = merged[merged["oid"] == oid].dropna(subset=["mean_self_all", "human_mean"])
        lines.append(
            f"| {oid} | {len(sl)} | {r:.3f} |"
            if not np.isnan(r)
            else f"| {oid} | {len(sl)} | — |"
        )
    return lines


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "report").mkdir(parents=True, exist_ok=True)
    CHARTS_ROOT.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    human_csv = load_human_grades()
    feats = build_run_features()

    docx_path = _find_ztf26_docx()
    docx_z19_path = _find_docx_z19()
    gz26 = _parse_docx_grades_13(docx_path)
    gz19 = _parse_docx_grades_13(docx_z19_path)

    z26_zoo = human_csv[
        (human_csv["oid"] == "ZTF26aargnnp")
        & (human_csv["workflow_name"] == Z26_ZOONIVERSE_WF)
    ].copy()
    expert_z26_df = (
        _expert_docx_grade_rows(
            "ZTF26aargnnp",
            gz26,
            MATTHEW_RATER_LABEL,
            "Expert LLM Answer Grading (.docx ZTF26)",
        )
        if gz26
        else pd.DataFrame()
    )
    z26 = (
        pd.concat([z26_zoo, expert_z26_df], ignore_index=True)
        if not expert_z26_df.empty
        else z26_zoo.copy()
    )

    human_s2_zoo = human_csv[human_csv["workflow_name"].isin(SECTION2_ZOON_WFS)].copy()
    expert_ab_df = (
        _expert_docx_grade_rows(
            "ZTF19abfqvbg",
            gz19,
            MATTHEW_RATER_LABEL,
            "Expert LLM Answer Grading (.docx ZTF19abfqvbg)",
        )
        if gz19
        else pd.DataFrame()
    )
    human_s2_d = human_csv[human_csv["workflow_name"] == SECTION2_D_WF].copy()
    if human_s2_d.empty:
        print(
            "[WARN] no LLM Response Grading (D) rows — §2 omits ZTF25aaxmsns from pooled joins",
            file=sys.stderr,
        )
    parts: list[pd.DataFrame] = [human_s2_zoo]
    if not expert_ab_df.empty:
        parts.append(expert_ab_df)
    if not human_s2_d.empty:
        parts.append(human_s2_d)
    human_s2 = pd.concat(parts, ignore_index=True)

    hm = (
        human_s2.groupby(["oid", "run_idx"])
        .agg(
            human_mean=("human_grade", "mean"),
            human_sd=("human_grade", "std"),
            n_raters=("human_grade", "count"),
        )
        .reset_index()
    )
    merged = feats.merge(hm, on=["oid", "run_idx"], how="inner")

    wide26 = z26.pivot_table(
        index="run_idx", columns="rater_label", values="human_grade", aggfunc="first"
    ).reindex(range(1, 14))
    cols26 = [c for c in Z26_RATER_ORDER if c in wide26.columns]
    if len(cols26) < 2:
        alpha = None
    else:
        alpha = cronbach_alpha(wide26[cols26].to_numpy(dtype=float))

    pair_bits_list: list[str] = []
    if len(cols26) >= 2:
        for i in range(len(cols26)):
            for j in range(i + 1, len(cols26)):
                a = wide26[cols26[i]].to_numpy(dtype=float)
                b = wide26[cols26[j]].to_numpy(dtype=float)
                if np.nanstd(a) < 1e-9 or np.nanstd(b) < 1e-9:
                    continue
                r_ij, _ = stats.pearsonr(a, b)
                pair_bits_list.append(f"{cols26[i]} vs {cols26[j]} **{r_ij:.2f}**")
    pair_bits = "; ".join(pair_bits_list)

    z26_table_lines = z26_full_scores_markdown(z26)

    p1 = CHARTS_DIR / "20260503_01_ztf26_rater_heatmap.png"
    p2 = CHARTS_DIR / "20260503_02_ztf26_mean_sd_by_model.png"
    p3 = CHARTS_DIR / "20260503_03_rater_pairwise_scatter.png"
    p4 = CHARTS_DIR / "20260503_04_scatter_self_all_vs_human.png"
    p5 = CHARTS_DIR / "20260503_05_scatter_self_q23_vs_human.png"
    p6 = CHARTS_DIR / "20260503_06_violin_human_by_correctness.png"
    p7 = CHARTS_DIR / "20260503_07_bar_mean_human_correct_vs_wrong_by_model.png"
    p8 = CHARTS_DIR / "20260503_08_bar_per_model_correlation.png"
    p9 = CHARTS_DIR / "20260503_09_inter_rater_mae_heatmap.png"
    p10 = CHARTS_DIR / "20260503_10_docx_tone_vs_zooniverse_mean.png"
    p11 = CHARTS_DIR / "20260503_11_correctness_row_counts.png"
    p12 = CHARTS_DIR / "20260503_12_per_oid_pearson_self_vs_human.png"
    p13 = CHARTS_DIR / "20260503_13_per_model_profile_four_oid_means.png"

    fig_rater_heatmap(z26, p1)
    fig_mean_sd_bars(z26, p2)
    fig_pairwise_raters(z26, p3)
    fig_inter_rater_mae_heatmap(z26, p9)

    docx_r = docx_p = None
    docx_n = 0
    if docx_path is not None:
        docx_r, docx_p, docx_n = fig_docx_tone_vs_zooniverse_mean(z26, docx_path, p10)
    else:
        # Placeholder so markdown can skip broken image links
        pass

    fig_scatter_self_human(
        merged,
        "mean_self_all",
        "Human vs LLM mean self-score (3 Part B fields)",
        p4,
    )
    fig_scatter_self_human(
        merged,
        "mean_self_q23",
        "Human vs mean self-score (leading + alternative only)",
        p5,
    )
    fig_per_model_correlation(merged, p8)
    per_oid_table_rows = fig_per_oid_self_human_correlation(merged, p12)
    fig_correctness_violin(merged, p6)
    fig_correctness_by_model(merged, p7)
    fig_correctness_counts(merged, p11)
    fig_per_oid_profile_by_model(
        human_s2,
        p13,
        list(SECTION2_OIDS),
        list(OID_PROFILE_LABELS),
    )

    # Pooled correlations
    m = merged.dropna(subset=["mean_self_all", "human_mean"])
    r_all, p_all = stats.pearsonr(m["mean_self_all"], m["human_mean"]) if len(m) > 3 else (np.nan, np.nan)
    m2 = merged.dropna(subset=["mean_self_q23", "human_mean"])
    r_q23, p_q23 = (
        stats.pearsonr(m2["mean_self_q23"], m2["human_mean"]) if len(m2) > 3 else (np.nan, np.nan)
    )
    if len(m) > 2:
        tau_all, p_tau_all = stats.kendalltau(m["mean_self_all"], m["human_mean"])
        sp_all, p_sp_all = stats.spearmanr(m["mean_self_all"], m["human_mean"])
    else:
        tau_all = p_tau_all = sp_all = p_sp_all = np.nan
    if len(m2) > 2:
        tau_q23, p_tau_q23 = stats.kendalltau(m2["mean_self_q23"], m2["human_mean"])
        sp_q23, p_sp_q23 = stats.spearmanr(m2["mean_self_q23"], m2["human_mean"])
    else:
        tau_q23 = p_tau_q23 = sp_q23 = p_sp_q23 = np.nan
    bis_mask = merged["is_correct"].notna()
    correct_b = merged.loc[bis_mask, "is_correct"].astype(int).to_numpy()
    hg = merged.loc[bis_mask, "human_mean"].to_numpy()
    if len(correct_b) > 3 and np.unique(correct_b).size == 2:
        pb_r, pb_p = stats.pointbiserialr(correct_b, hg)
    else:
        pb_r, pb_p = np.nan, np.nan

    nc_pool = int(merged[merged["is_correct"]].shape[0])
    nw_pool = int(merged[~merged["is_correct"]].shape[0])
    mean_h_correct = merged.loc[merged["is_correct"], "human_mean"].mean()
    mean_h_wrong = merged.loc[~merged["is_correct"], "human_mean"].mean()

    miss = merged[merged["mean_self_all"].isna()]
    if len(miss):
        bits = ", ".join(
            f"`{r['oid']}` · model {r['run_idx']} ({r['model_label']})"
            for r in miss[["oid", "run_idx", "model_label"]].to_dict("records")
        )
        skip_note = (
            f"\nIncomplete Part B self-scores in some `run.jsonl` `parsed` blocks exclude "
            f"{len(miss)} row(s) from the Pearson summaries & scatter fits: {bits}.\n"
        )
    else:
        skip_note = ""

    n_rows = len(human_csv)
    zoo_users = sorted(z26_zoo["user_name"].unique())
    z26_wf_exclude = {Z26_ZOONIVERSE_WF, "LLM Response Grading (D)"}
    per_user_extra: list[str] = []
    for u in zoo_users:
        sub = human_csv[
            (human_csv["user_name"] == u) & (~human_csv["workflow_name"].isin(z26_wf_exclude))
        ]
        if sub.empty:
            continue
        wf = str(sub.iloc[0]["workflow_name"])
        oid_x = str(sub.iloc[0]["oid"])
        per_user_extra.append(f"- **{u}** also completed `{wf}` → `{oid_x}`.")
    rater_means = z26.groupby("rater_label")["human_grade"].mean()
    rater_mean_bits = ", ".join(
        f"**{lbl}** μ={rater_means[lbl]:.2f}"
        for lbl in Z26_RATER_ORDER
        if lbl in rater_means.index
    )

    docx_md_lines: list[str] = []
    if docx_path is None:
        docx_md_lines = [
            "*Expert .docx scatter was skipped (file not found under `temporary_files/` or repo root). "
            "Place `LLM Answer Grading ZTF26aargnnp.docx` to regenerate Fig 1c.*",
        ]
    elif docx_r is not None and docx_p is not None:
        docx_md_lines = [
            f"- **Expert highlight tone vs blended §1 mean** (four Zooniverse **(X)** scores + **Matthew** `.docx` **Your Grading** per model, equal weight): "
            f"Pearson r = **{docx_r:.3f}**, p = {docx_p:.2e}, n = {docx_n}. "
            "Tone = (green − red) / (R+Y+G) over Q2+Q3 highlight inventory (see Apr 30 highlight report for color semantics).",
        ]
    else:
        docx_md_lines = [
            "*Expert .docx present but overlap with Zooniverse rows was insufficient for correlation.*",
        ]

    pairwise_md: list[str] = []
    if pair_bits:
        pairwise_md = [
            "",
            f"- **Pairwise Pearson r** between grader columns (same 13 model vectors): {pair_bits}.",
        ]

    pooled_extra: list[str] = []
    if len(m) > 2 and not (np.isnan(sp_all) or np.isnan(p_sp_all)):
        pooled_extra.append(
            f"- **Pooled Spearman ρ** (n = {len(m)}): **ρ = {sp_all:.3f}**, p = {p_sp_all:.2e}"
        )
    if len(m) > 2 and not (np.isnan(tau_all) or np.isnan(p_tau_all)):
        pooled_extra.append(
            f"- **Pooled Kendall τ** (n = {len(m)}): **τ = {tau_all:.3f}**, p = {p_tau_all:.2e}"
        )
    pooled_q23: list[str] = []
    if len(m2) > 2 and not (np.isnan(sp_q23) or np.isnan(p_sp_q23)):
        pooled_q23.append(
            f"- **Pooled Spearman ρ** (n = {len(m2)}): **ρ = {sp_q23:.3f}**, p = {p_sp_q23:.2e}"
        )
    if len(m2) > 2 and not (np.isnan(tau_q23) or np.isnan(p_tau_q23)):
        pooled_q23.append(
            f"- **Pooled Kendall τ** (n = {len(m2)}): **τ = {tau_q23:.3f}**, p = {p_tau_q23:.2e}"
        )

    md_lines = [
        "# Zooniverse LLM response grading — ZTF26 §1 (X + Matthew); §2 includes **(D)** on ZTF25aaxmsns (3 May 2026)",
        "",
        "**Exports:** `temporary_files/llm-for-astronomy-classifications (4).csv` and `(5).csv`, "
        "concatenated and **deduplicated by `classification_id`**. "
        "**LLM Response Grading (D)** maps to **`ZTF25aaxmsns` (SN)**, not ZTF26. **(D)** is **excluded from §1** and **included in §2** (see table). "
        "Gold OIDs / PNG bundle: `human_samples/llm_example_grading_zooniverse/README.md`.",
        "",
        "| Workflow | OID | Role in this report |",
        "|---|---|---|",
        "| LLM Response Grading **(X)** | ZTF26aargnnp | **§1:** four Zooniverse raters (libai_astro, lukehandley, RickyN, theodlz). |",
        "| Expert `.docx` | ZTF26aargnnp | **§1:** **Matthew** **Your Grading:** 0–5 per model (**equal** weight). |",
        "| LLM Response Grading **(D)** | **ZTF25aaxmsns** (SN) | **§2** — Zooniverse grading lane (e.g. **theodlz**); **not** used in §1. |",
        "| **(A)** | ZTF19aayhwvd (VS) | **§2** pooled (Zooniverse). |",
        "| **(B)** | ZTF19abkdsaw (AGN) | **§2** pooled (Zooniverse). |",
        "| **(C)** | ZTF25aahvsli (bogus) | **§2** pooled (Zooniverse). |",
        "| Expert `.docx` | **ZTF19abfqvbg** (AGN) | **§2** pooled — **Matthew** **Your Grading** (not workflow **(X)**). |",
        "",
        "## Annotators",
        "",
        f"**§1** uses **five** numeric lanes on **ZTF26aargnnp**: four on workflow **(X)** plus **Matthew** from "
        f"`LLM Answer Grading ZTF26aargnnp.docx`. **(D)** is unrelated (SN alert **ZTF25aaxmsns**) and is excluded from §1. "
        f"**§2** pools **five OIDs** (`{', '.join(SECTION2_OIDS)}`): expert **ZTF19abfqvbg** + Zooniverse **(A,B,C)** + **ZTF25aaxmsns** via **(D)**. "
        f"Total **{n_rows}** CSV rows with Zooniverse 0–5 scores (expert rows for §1/§2 are injected from `.docx`).",
        "",
        *per_user_extra,
        "",
        f"**Mean on ZTF26 (§1)** by rater: {rater_mean_bits}.",
        "",
        "R/Y/G markup: [`20260430_report_llm_grading_docx_highlights.md`](20260430_report_llm_grading_docx_highlights.md).",
        "",
        "## 1. ZTF26aargnnp — Zooniverse **(X)** + Matthew `.docx`",
        "",
        "### 1.1 13 models × five graders",
        "",
        "**(D)** excluded. **Mean** / **SD** = unweighted over the five columns below.",
        "",
        *z26_table_lines,
        "",
        "### 1.2 Reliability",
        "",
        (
            f"- **Cronbach’s α** (13 models × **{len(cols26)}** columns): **{alpha:.3f}**"
            if alpha is not None
            else "- **Cronbach’s α**: (undefined — fewer than two rater columns)"
        ),
        *pairwise_md,
        "",
        f"![Heatmap]({CHART_MD_PREFIX}/20260503_01_ztf26_rater_heatmap.png)",
        "",
        "*Fig 1. Grades 0–5; rows = §1 raters; columns = model index.*",
        "",
        f"![Mean ± SD]({CHART_MD_PREFIX}/20260503_02_ztf26_mean_sd_by_model.png)",
        "",
        "*Fig 2. Mean ±1 SD across **five** §1 graders.*",
        "",
        f"![Rater correlation matrix]({CHART_MD_PREFIX}/20260503_03_rater_pairwise_scatter.png)",
        "",
        "*Fig 3. Pearson **r** matrix between grader columns (legacy filename).*",
        "",
        "### 1.3 Mean absolute pairwise disagreement",
        "",
        f"![Inter-rater MAE]({CHART_MD_PREFIX}/20260503_09_inter_rater_mae_heatmap.png)",
        "",
        "*Fig 1b. Off-diagonal mean |Δgrade|.*",
        "",
        "### 1.4 Highlight tone vs blended §1 mean",
        *docx_md_lines,
    ]
    if docx_path is not None:
        md_lines += [
            "",
            f"![Docx tone vs §1 mean]({CHART_MD_PREFIX}/20260503_10_docx_tone_vs_zooniverse_mean.png)",
            "",
            "*Fig 1c. **y** = §1 blended mean (4× Zoon **X** + Matthew `.docx` **Your Grading**).*",
            "",
        ]
    md_lines += [
        "### 1.5 Model index ↔ system",
        "",
        "| Idx | Model |",
        "|:---:|:---|",
    ]
    for i, name in enumerate(MODEL_DISPLAY, start=1):
        md_lines.append(f"| {i} | {name} |")
    md_lines += [
        "",
        "## 2. Five-alerts §2 panel (workflow **(D)** → **ZTF25aaxmsns**)",
        "",
        "**Streams:** expert **ZTF19abfqvbg** (`.docx`) plus Zooniverse **(A, B, C, D)**. "
        "**(X)** is **§1-only** on **ZTF26aargnnp**. **(D)** targets **`ZTF25aaxmsns` (SN)**, not ZTF26. "
        "Pooled plots use **five OIDs** × 13 models: "
        f"`{', '.join(SECTION2_OIDS)}`.",
        "",
        f"![Per-model profile]({CHART_MD_PREFIX}/20260503_13_per_model_profile_four_oid_means.png)",
        "",
        "*Fig 13. Mean human grade on each §2 OID (**D** = SN **ZTF25aaxmsns**).*",
        "",
        "## 3. Self-scores vs human grades (pooled and per-alert)",
        "",
        "(OID, model) rows join Part B self-scores to **`human_mean`** from §2. "
        "**ZTF25aaxmsns** comes from workflow **(D)** only. **ZTF26aargnnp** appears only in §1 (X + Matthew). "
        "**ZTF19abfqvbg** = expert `.docx`; **(A–C)** = Zooniverse.",
        skip_note,
        "",
        "### 3.1 Pooled linear and ordinal summaries",
        "",
        f"- **Pooled Pearson r** (n = {len(m)}): mean self (**key + lead + alt**) vs human mean → **r = {r_all:.3f}**, p = {p_all:.2e}",
        *pooled_extra,
        "",
        f"- **Pooled Pearson r** (n = {len(m2)}): mean self (**lead + alt only**) vs human mean → **r = {r_q23:.3f}**, p = {p_q23:.2e}",
        *pooled_q23,
        "",
        "Self-reported Part B scores use the same 1–5 rubric as the human task, but need not track external graders; "
        "weak pooled linear correlation can coexist with a strong correctness signal (§4).",
        "",
        f"![Scatter all self]({CHART_MD_PREFIX}/20260503_04_scatter_self_all_vs_human.png)",
        "",
        f"![Scatter q23]({CHART_MD_PREFIX}/20260503_05_scatter_self_q23_vs_human.png)",
        "",
        "*Fig 4–5. One point per (OID, model); colors = OID.*",
        "",
        "### 3.2 Per-model across-OID correlation (five OIDs per bar)",
        "",
        f"![Per-model r]({CHART_MD_PREFIX}/20260503_08_bar_per_model_correlation.png)",
        "",
        "*Fig 6. Pearson r between mean self (3 fields) and human mean; bars labeled.*",
        "",
        "### 3.3 Per-alert correlation (13 models per OID)",
        "",
        "| OID | n (models with complete self + human) | Pearson r (self all vs human) |",
        "|---|---:|---:|",
    ]
    md_lines.extend(per_oid_table_rows)
    md_lines += [
        "",
        f"![Per-OID r]({CHART_MD_PREFIX}/20260503_12_per_oid_pearson_self_vs_human.png)",
        "",
        "*Fig 6b. Same numbers as the table.*",
        "",
        "## 4. Benchmark correctness vs human grades",
        "",
        f"- **Point-biserial r** (correctness × human mean): **r = {pb_r:.3f}**, p = {pb_p:.2e}"
        if not np.isnan(pb_r)
        else "",
        f"- **Pooled mean human grade** when Part C is **correct** (n = {nc_pool}): **{mean_h_correct:.2f}**; "
        f"when **incorrect** (n = {nw_pool}): **{mean_h_wrong:.2f}** (same rows as Fig 7a).",
        "",
        f"![Row counts]({CHART_MD_PREFIX}/20260503_11_correctness_row_counts.png)",
        "",
        "*Fig 7a. Pooled row counts (OID × model) with Part C correct vs incorrect; **n** on each bar.*",
        "",
        f"![Violin correctness]({CHART_MD_PREFIX}/20260503_06_violin_human_by_correctness.png)",
        "",
        f"![By model split]({CHART_MD_PREFIX}/20260503_07_bar_mean_human_correct_vs_wrong_by_model.png)",
        "",
        "*Fig 7b–7c. Human grades are typically lower when Part C is incorrect.*",
        "",
        "## 5. Expert highlight documents (qualitative)",
        "",
        "Red / yellow / green markup for Part B reasoning is summarized in "
        "[`20260430_report_llm_grading_docx_highlights.md`](20260430_report_llm_grading_docx_highlights.md).",
        "",
        "## 6. Extensions",
        "",
        "- **ICC(2,1)** or many-facet Rasch if more subjects and raters are added.",
        "- **Per-field** human scores if the UI separates key vs lead vs alt.",
        "- **Alert difficulty**: separate calibration per `target_class`.",
        "- **Ordinal mixed-effects** with rater random intercepts.",
        "",
        "---",
        "",
        f"Regenerate: `python -m viz.build_20260503_zooniverse_grading_report`",
        "",
    ]

    REPORT_PATH.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
