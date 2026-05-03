"""Build figures + markdown report for Zooniverse LLM-response grading (workflows X/A/B/C).

Reads `temporary_files/llm-for-astronomy-classifications (4).csv`, joins to benchmark
`run.jsonl` via `viz.build_llm_example_grading.RUN_SPECS` (PNG index 1..13).

Run from repo root::

    python -m viz.build_20260503_zooniverse_grading_report

Writes figures under ``results_comparison/report/charts/`` (names ``20260503_*.png``) and
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

RESULTS_DIR = PROJECT_ROOT / "results_comparison"
CHARTS_DIR = RESULTS_DIR / "report" / "charts"
REPORT_PATH = RESULTS_DIR / "report" / "20260503_report_zooniverse_llm_grading.md"
CSV_PATH = PROJECT_ROOT / "temporary_files" / "llm-for-astronomy-classifications (4).csv"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifest_benchmark_final.csv"

WF_TO_OID = {
    "LLM Response Grading (X)": "ZTF26aargnnp",
    "LLM Response Grading (A)": "ZTF19aayhwvd",
    "LLM Response Grading (B)": "ZTF19abkdsaw",
    "LLM Response Grading (C)": "ZTF25aahvsli",
}

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
    oids = sorted(set(WF_TO_OID.values()))
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


def load_human_grades() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)
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
    return sub


def cronbach_alpha(matrix: np.ndarray) -> float | None:
    """matrix: n_subjects × k_items (e.g. 13 models × 3 raters)."""
    if matrix.shape[1] < 2:
        return None
    item_vars = matrix.var(axis=0, ddof=1)
    total = matrix.sum(axis=1)
    total_var = total.var(ddof=1)
    if total_var <= 0:
        return None
    k = matrix.shape[1]
    return float((k / (k - 1)) * (1.0 - item_vars.sum() / total_var))


def fig_rater_heatmap(z26: pd.DataFrame, path: Path) -> None:
    pivot = z26.pivot_table(
        index="user_name",
        columns="run_idx",
        values="human_grade",
        aggfunc="first",
    )
    pivot = pivot.reindex(columns=list(range(1, 14)))
    fig, ax = plt.subplots(figsize=(14, 3.2))
    arr = pivot.to_numpy(dtype=float)
    im = ax.imshow(arr, aspect="auto", vmin=0, vmax=5, cmap="viridis")
    ax.set_xticks(np.arange(13))
    ax.set_xticklabels([f"{i+1}" for i in range(13)], fontsize=8)
    ax.set_yticks(np.arange(len(pivot)))
    ax.set_yticklabels(pivot.index, fontsize=9)
    ax.set_xlabel("Model index (see table: Gemini Pro … Qwen 397B nothink)")
    ax.set_ylabel("Zooniverse user")
    ax.set_title("ZTF26aargnnp — human grades (0–5) by rater × model")
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
    ax.bar(x, g["mean"], yerr=g["std"], capsize=4, color="steelblue", edgecolor="navy", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{i+1}\n{MODEL_DISPLAY[i][:10]}…" for i in range(13)], fontsize=7)
    ax.set_ylabel("Mean human grade (±1 SD across 3 raters)")
    ax.set_ylim(0, 5.5)
    ax.axhline(2.5, color="gray", ls="--", lw=0.8, alpha=0.7)
    ax.set_title("ZTF26aargnnp — consensus across three Zooniverse raters")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_pairwise_raters(z26: pd.DataFrame, path: Path) -> None:
    users = sorted(z26["user_name"].unique())
    if len(users) != 3:
        return
    wide = z26.pivot_table(
        index="run_idx", columns="user_name", values="human_grade", aggfunc="first"
    ).reindex(range(1, 14))
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
    pairs = [(users[0], users[1]), (users[0], users[2]), (users[1], users[2])]
    for ax, (a, b) in zip(axes, pairs):
        xa = wide[a].to_numpy()
        xb = wide[b].to_numpy()
        ax.scatter(xa, xb, s=40, alpha=0.85, edgecolors="k", linewidths=0.3)
        ax.plot([0, 5], [0, 5], ls="--", color="gray", lw=0.9)
        ax.set_xlabel(a)
        ax.set_ylabel(b)
        r, _p = stats.pearsonr(xa, xb)
        ax.set_title(f"r = {r:.2f}")
        ax.set_xlim(-0.3, 5.3)
        ax.set_ylim(-0.3, 5.3)
    fig.suptitle("ZTF26aargnnp — pairwise agreement (Pearson r)", y=1.02)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_scatter_self_human(merged: pd.DataFrame, ycol: str, title: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 5))
    colors = {"ZTF26aargnnp": "C0", "ZTF19aayhwvd": "C1", "ZTF19abkdsaw": "C2", "ZTF25aahvsli": "C3"}
    for oid, sub in merged.groupby("oid"):
        ax.scatter(
            sub[ycol],
            sub["human_mean"],
            label=oid,
            s=45,
            alpha=0.8,
            c=colors.get(oid, "k"),
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
    ax.set_title("Human reasoning grades vs benchmark correctness (all OIDs, 13 models)")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_correctness_by_model(merged: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 4))
    run_ids = list(range(1, 14))
    means_c = []
    means_w = []
    for r in run_ids:
        sl = merged[merged["run_idx"] == r]
        mc = sl[sl["is_correct"]]["human_mean"].mean()
        mw = sl[~sl["is_correct"]]["human_mean"].mean()
        means_c.append(mc if not pd.isna(mc) else np.nan)
        means_w.append(mw if not pd.isna(mw) else np.nan)
    x = np.arange(13)
    w = 0.35
    ax.bar(x - w / 2, means_c, width=w, label="Correct", color="#2ca02c", alpha=0.85)
    ax.bar(x + w / 2, means_w, width=w, label="Incorrect", color="#d62728", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([str(i + 1) for i in range(13)], fontsize=9)
    ax.set_xlabel("Model index (1 = Gemini Pro high … 13 = Qwen 397B nothink)")
    ax.set_ylabel("Mean human grade")
    ax.set_title("Mean human grade split by Part C correctness (4 OIDs × correct/incorrect subset)")
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
    ax.bar(x, rs, color="teal", edgecolor="k", linewidth=0.4)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([str(i + 1) for i in range(13)])
    ax.set_xlabel("Model index")
    ax.set_ylabel("Pearson r (4 OIDs: self_all vs human mean)")
    ax.set_title("Per-model correlation: mean self-scores vs mean human grades")
    ax.set_ylim(-1.05, 1.05)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "report").mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    human = load_human_grades()
    feats = build_run_features()

    hm = (
        human.groupby(["oid", "run_idx"])
        .agg(
            human_mean=("human_grade", "mean"),
            human_sd=("human_grade", "std"),
            n_raters=("human_grade", "count"),
        )
        .reset_index()
    )
    merged = feats.merge(hm, on=["oid", "run_idx"], how="inner")

    z26 = human[human["oid"] == "ZTF26aargnnp"].copy()
    mat = z26.pivot_table(
        index="run_idx", columns="user_name", values="human_grade", aggfunc="first"
    ).reindex(range(1, 14))
    alpha = cronbach_alpha(mat.to_numpy(dtype=float))

    r12 = r13 = r23 = None
    users = sorted(z26["user_name"].unique())
    if len(users) == 3:
        w = mat.copy()
        u1, u2, u3 = users
        r12, _ = stats.pearsonr(w[u1], w[u2])
        r13, _ = stats.pearsonr(w[u1], w[u3])
        r23, _ = stats.pearsonr(w[u2], w[u3])

    p1 = CHARTS_DIR / "20260503_01_ztf26_rater_heatmap.png"
    p2 = CHARTS_DIR / "20260503_02_ztf26_mean_sd_by_model.png"
    p3 = CHARTS_DIR / "20260503_03_rater_pairwise_scatter.png"
    p4 = CHARTS_DIR / "20260503_04_scatter_self_all_vs_human.png"
    p5 = CHARTS_DIR / "20260503_05_scatter_self_q23_vs_human.png"
    p6 = CHARTS_DIR / "20260503_06_violin_human_by_correctness.png"
    p7 = CHARTS_DIR / "20260503_07_bar_mean_human_correct_vs_wrong_by_model.png"
    p8 = CHARTS_DIR / "20260503_08_bar_per_model_correlation.png"

    fig_rater_heatmap(z26, p1)
    fig_mean_sd_bars(z26, p2)
    fig_pairwise_raters(z26, p3)
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
    fig_correctness_violin(merged, p6)
    fig_correctness_by_model(merged, p7)
    fig_per_model_correlation(merged, p8)

    # Pooled correlations
    m = merged.dropna(subset=["mean_self_all", "human_mean"])
    r_all, p_all = stats.pearsonr(m["mean_self_all"], m["human_mean"]) if len(m) > 3 else (np.nan, np.nan)
    m2 = merged.dropna(subset=["mean_self_q23", "human_mean"])
    r_q23, p_q23 = (
        stats.pearsonr(m2["mean_self_q23"], m2["human_mean"]) if len(m2) > 3 else (np.nan, np.nan)
    )
    bis_mask = merged["is_correct"].notna()
    correct_b = merged.loc[bis_mask, "is_correct"].astype(int).to_numpy()
    hg = merged.loc[bis_mask, "human_mean"].to_numpy()
    if len(correct_b) > 3 and np.unique(correct_b).size == 2:
        pb_r, pb_p = stats.pointbiserialr(correct_b, hg)
    else:
        pb_r, pb_p = np.nan, np.nan

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

    md_lines = [
        "# Zooniverse LLM response grading — cross-check with benchmark self-scores (3 May 2026)",
        "",
        "Source export: `temporary_files/llm-for-astronomy-classifications (4).csv`. "
        "Workflow labels map to gold OIDs (Zooniverse bundle under `human_samples/llm_example_grading_zooniverse/`):",
        "",
        "| Workflow | OID | `target_class` (manifest) |",
        "|---|---|---|",
        "| LLM Response Grading (X) | ZTF26aargnnp | asteroid |",
        "| LLM Response Grading (A) | ZTF19aayhwvd | VS |",
        "| LLM Response Grading (B) | ZTF19abkdsaw | AGN |",
        "| LLM Response Grading (C) | ZTF25aahvsli | bogus |",
        "",
        "## Annotators",
        "",
        "Three Zooniverse users each grade **all 13 model snapshots** on **ZTF26aargnnp** (workflow X), "
        "and each also grades one **other** OID alone: **lukehandley** → (A), **libai_astro** → (B), **RickyN** → (C). "
        "That yields 39 + 13 + 13 + 13 = **78** classification rows with a numeric 0–5 score in the annotations.",
        "",
        "A **fourth** layer of human feedback on ZTF26aargnnp is the expert-highlighted `.docx` "
        "(`temporary_files/LLM Answer Grading ZTF26aargnnp.docx`). "
        "That document does not add another 0–5 column here; see the highlight analysis in "
        "[`20260430_report_llm_grading_docx_highlights.md`](20260430_report_llm_grading_docx_highlights.md). "
        "The same report covers `LLM Answer Grading ZTF19abfqvbg.docx` (OID **ZTF19abfqvbg** is a separate AGN calibration example, not part of this A/B/C/X PNG bundle).",
        "",
        "## 1. ZTF26aargnnp — three independent raters",
        "",
        f"- **Cronbach’s α** (13 models × 3 raters): **{alpha:.3f}**" if alpha is not None else "- **Cronbach’s α**: (undefined)",
        "",
    ]
    if r12 is not None:
        md_lines.append(
            f"- **Pairwise Pearson r** between raters: {users[0]} vs {users[1]} **{r12:.2f}**, "
            f"{users[0]} vs {users[2]} **{r13:.2f}**, {users[1]} vs {users[2]} **{r23:.2f}**."
        )
    md_lines += [
        "",
        f"![Heatmap](charts/20260503_01_ztf26_rater_heatmap.png)",
        "",
        "*Fig 1. Grades (0–5) for each rater (row) and model index (column). Order 1–13 matches `viz/build_llm_example_grading.py` `RUN_SPECS` and the zooniverse README.*",
        "",
        f"![Mean ± SD](charts/20260503_02_ztf26_mean_sd_by_model.png)",
        "",
        "*Fig 2. Mean human score ±1 SD across the three raters, by model index.*",
        "",
        f"![Pairwise](charts/20260503_03_rater_pairwise_scatter.png)",
        "",
        "*Fig 3. Pairwise scatter plots (same 13 points per panel). The dashed line is y = x.*",
        "",
        "### Model index ↔ system",
        "",
        "| Idx | Model |",
        "|:---:|:---|",
    ]
    for i, name in enumerate(MODEL_DISPLAY, start=1):
        md_lines.append(f"| {i} | {name} |")
    md_lines += [
        "",
        "## 2. Self-scores vs human grades",
        "",
        "For each (OID, model) we join benchmark `run.jsonl` **Part B** numeric self-scores with the **mean human** grade "
        "(for ZTF26 that is the mean of three raters; for other OIDs a single rater).",
        skip_note,
        "",
        f"- **Pooled Pearson r** (n = {len(m)}): mean self (**key + lead + alt**) vs human mean → **r = {r_all:.3f}**, p = {p_all:.2e}",
        f"- **Pooled Pearson r** (n = {len(m2)}): mean self (**lead + alt only**) vs human mean → **r = {r_q23:.3f}**, p = {p_q23:.2e}",
        "",
        f"![Scatter all self](charts/20260503_04_scatter_self_all_vs_human.png)",
        "",
        f"![Scatter q23](charts/20260503_05_scatter_self_q23_vs_human.png)",
        "",
        "*Fig 4–5. One point per (OID, model). Colors distinguish OIDs.*",
        "",
        "With only **four** OIDs per model, per-model correlation is very noisy; the bar summary is still useful to spot sign consistency:",
        "",
        f"![Per-model r](charts/20260503_08_bar_per_model_correlation.png)",
        "",
        "*Fig 6. Pearson r between mean self (3 fields) and human mean, using the four OID points per model.*",
        "",
        "## 3. Benchmark correctness vs human grades",
        "",
        f"- **Point-biserial r** (correctness × human mean): **r = {pb_r:.3f}**, p = {pb_p:.2e}"
        if not np.isnan(pb_r)
        else "",
        "",
        f"![Violin correctness](charts/20260503_06_violin_human_by_correctness.png)",
        "",
        f"![By model split](charts/20260503_07_bar_mean_human_correct_vs_wrong_by_model.png)",
        "",
        "*Fig 7–8. Human grades tend to be **lower** when Part C is incorrect (violins), with a per-model breakdown.*",
        "",
        "## 4. Expert highlight documents",
        "",
        "Qualitative markup (red / yellow / green) for reasoning paragraphs is summarized in "
        "[`20260430_report_llm_grading_docx_highlights.md`](20260430_report_llm_grading_docx_highlights.md). "
        "It complements the numeric Zooniverse scores on ZTF26aargnnp.",
        "",
        "## 5. Extra metrics worth tracking later",
        "",
        "- **Reliability growth**: add more raters or duplicate subjects to stabilize ICC/α.",
        "- **Ordinal treatment**: treat 0–5 as ordered and use Kendall’s τ or proportional-odds models (here Pearson is a quick linear summary).",
        "- **Per-field human scores**: if the UI later separates key vs lead vs alt, test which field drives disagreement.",
        "- **Alert difficulty**: bogus vs asteroid vs AGN may anchor graders differently; separate calibration curves per `target_class`.",
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
