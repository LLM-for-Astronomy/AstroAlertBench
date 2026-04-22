"""End-to-end orchestrator: jsonl + manifest -> runs/<timestamp>-<model>/ folder
with report.md, viz/, plots/, and run.jsonl.

Usage (as library):

    from viz.build_run_folder import build_run_folder
    build_run_folder(
        jsonl_path="results/fewshot_kimi_think_newparser.jsonl",
        manifest_path="data/manifest_fewshot.csv",
        model_name="moonshotai/Kimi-K2.5",
        prompts_module="prompts",
        runs_root="runs",
        run_timestamp=None,       # auto: from jsonl mtime
        slug_override=None,
        hypothesis=None,
        comparison=None,
        observations=None,
        extra_config=None,        # dict merged into the Configuration section
    )

Usage (CLI):
    python -m viz.build_run_folder --jsonl results/foo.jsonl \
        --manifest data/manifest_fewshot.csv \
        --model Qwen/Qwen3.5-35B-A3B \
        [--prompts prompts] [--timestamp 20260419-2047] [--slug qwen35-baseline]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluate import evaluate_jsonl  # noqa: E402

from viz.html_report import render_datapoint_html  # noqa: E402
from viz.plots import build_all_plots  # noqa: E402
from viz.enriched_report import write_enriched_report  # noqa: E402
from viz.index import append_jsonl_summary, regenerate_index  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify_model(model: str) -> str:
    return (model or "unknown").replace("/", "_").replace(" ", "_")


def _derive_timestamp_from_jsonl(jsonl_path: Path) -> str:
    mtime = _dt.datetime.fromtimestamp(jsonl_path.stat().st_mtime)
    return mtime.strftime("%Y%m%d-%H%M")


def _git_info() -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        out["commit"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, text=True
        ).strip()
    except Exception:
        out["commit"] = "unknown"
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True
        )
        dirty_lines = [l.strip() for l in status.splitlines() if l.strip()]
        out["dirty"] = bool(dirty_lines)
        out["dirty_files"] = [l.split()[-1] for l in dirty_lines[:20]]
    except Exception:
        out["dirty"] = False
        out["dirty_files"] = []
    return out


def _load_jsonl(path: Path) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _pick_top_10_per_class(
    manifest: pd.DataFrame,
    oids_in_run: set[str],
    n_per_class: int = 10,
) -> dict[str, list[str]]:
    """Return {class: [oid, ...]} picking top-N-by-probability within each class,
    restricted to oids that actually appear in the run's predictions."""
    mf = manifest[manifest["oid"].isin(oids_in_run)].copy()
    if mf.empty:
        return {}
    mf = mf.sort_values(["target_class", "probability"], ascending=[True, False])
    out: dict[str, list[str]] = {}
    for cls, grp in mf.groupby("target_class", sort=False):
        out[str(cls)] = grp.head(n_per_class)["oid"].tolist()
    return out


def _extract_config_from_rows(
    rows: list[dict],
    model_name: str | None,
    prompts_module: str,
    backend_hint: str | None = None,
) -> dict[str, Any]:
    """Infer run configuration from the first record."""
    if not rows:
        return {"model": model_name or "?", "prompt_module": prompts_module}

    r0 = rows[0]
    cfg: dict[str, Any] = {
        "model": model_name or r0.get("model") or "?",
        "prompt_module": prompts_module,
    }
    if "reasoning_effort" in r0:
        cfg["reasoning_effort"] = r0["reasoning_effort"]
        cfg["backend"] = backend_hint or "openai"
    else:
        cfg["backend"] = backend_hint or "tinker"
    if "max_tokens" in r0:
        cfg["max_tokens"] = r0["max_tokens"]
    # Renderer / reasoning mode: prefer what the runner recorded per row (new
    # runs carry these fields directly), fall back to model-name inference for
    # legacy JSONLs that pre-date the fields.
    if cfg["backend"] == "tinker":
        if "renderer" in r0:
            cfg["renderer"] = r0["renderer"]
        if "reasoning_mode" in r0:
            cfg["reasoning_mode"] = r0["reasoning_mode"]
        if "renderer" not in cfg or "reasoning_mode" not in cfg:
            mn = (cfg["model"] or "").lower()
            if "kimi" in mn and "k2.5" in mn:
                cfg.setdefault("renderer", "KimiK25Renderer")
                cfg.setdefault("reasoning_mode", "enabled")
            elif "qwen3.5" in mn or "qwen3_5" in mn or "qwen" in mn:
                cfg.setdefault("renderer", "Qwen3_5Renderer")
                cfg.setdefault("reasoning_mode", "enabled")
            else:
                cfg.setdefault("renderer", "(unknown — see api_tinker.get_renderer)")
                cfg.setdefault("reasoning_mode", "unknown")
    return cfg


def _reconstruct_prompts(manifest_row: pd.Series, oid: str, prompts_module: str) -> tuple[str, str]:
    """Rebuild the system + user prompts that would have been sent to the model."""
    mod = importlib.import_module(prompts_module)
    system_prompt = getattr(mod, "SYSTEM_PROMPT", "(prompts module has no SYSTEM_PROMPT)")
    metadata = mod.manifest_row_to_metadata(manifest_row)
    user_prompt = mod.build_user_prompt(oid, metadata)
    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def build_run_folder(
    jsonl_path: str | Path,
    manifest_path: str | Path,
    model_name: str | None = None,
    prompts_module: str = "prompts",
    runs_root: str | Path = "runs",
    run_timestamp: str | None = None,
    slug_override: str | None = None,
    hypothesis: str | None = None,
    comparison: str | None = None,
    prompt_summary: str | None = None,
    observations: str | None = None,
    extra_config: dict[str, Any] | None = None,
    operator: str = "user",
    backend_hint: str | None = None,
    keep_original_jsonl: bool = True,
) -> Path:
    """Create `runs/<timestamp>-<slug>/` and populate report + viz + plots.

    Returns the created run folder path.
    """
    jsonl_path = Path(jsonl_path).resolve()
    manifest_path = Path(manifest_path).resolve()
    runs_root = (PROJECT_ROOT / runs_root).resolve()

    # 1. Load predictions + manifest
    rows = _load_jsonl(jsonl_path)
    manifest = pd.read_csv(manifest_path, low_memory=False)

    # 2. Compute run timestamp + slug
    ts = run_timestamp or _derive_timestamp_from_jsonl(jsonl_path)
    cfg = _extract_config_from_rows(rows, model_name, prompts_module, backend_hint)
    if extra_config:
        cfg.update(extra_config)
    slug = slug_override or _slugify_model(cfg["model"])
    folder_name = f"{ts}-{slug}"
    run_dir = runs_root / folder_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # 3. Copy JSONL (evaluate will also write error categories back into it)
    run_jsonl = run_dir / "run.jsonl"
    if keep_original_jsonl:
        shutil.copy2(jsonl_path, run_jsonl)
    else:
        shutil.move(str(jsonl_path), run_jsonl)

    # 4. Run evaluate on the in-run copy (writes error_category + value_errors back)
    metrics = evaluate_jsonl(
        predictions_path=run_jsonl,
        manifest_path=manifest_path,
        write_back_errors=True,
    )
    # Persist metrics as JSON for programmatic access.
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # 5. Reload rows with error_category annotations
    rows = _load_jsonl(run_jsonl)

    # 6. Pick top-10 per class by ALERCE probability, restricted to oids in the run
    oids_in_run = {r.get("oid") for r in rows if r.get("oid")}
    top_per_class = _pick_top_10_per_class(manifest, oids_in_run, n_per_class=10)

    # 7. Generate per-datapoint HTMLs
    oid_to_row = {r["oid"]: r for r in rows if r.get("oid")}
    manifest_by_oid = manifest.set_index("oid")
    viz_counts: dict[str, int] = {}
    viz_root = run_dir / "viz"
    for cls, oids in top_per_class.items():
        cls_dir = viz_root / cls
        cls_dir.mkdir(parents=True, exist_ok=True)
        n_written = 0
        for oid in oids:
            r = oid_to_row.get(oid)
            if r is None or oid not in manifest_by_oid.index:
                continue
            mrow = manifest_by_oid.loc[oid]
            try:
                sys_p, usr_p = _reconstruct_prompts(mrow, oid, prompts_module)
            except Exception as e:
                sys_p, usr_p = f"(prompt reconstruction failed: {e})", ""
            try:
                render_datapoint_html(
                    row=r,
                    manifest_row=mrow,
                    system_prompt=sys_p,
                    user_prompt=usr_p,
                    out_path=cls_dir / f"{oid}.html",
                )
                n_written += 1
            except Exception as e:
                print(f"[viz] {oid} failed: {e}")
        viz_counts[cls] = n_written

    # 8. Generate plots
    plot_names = build_all_plots(metrics=metrics, rows=rows, out_dir=run_dir / "plots")

    # 9. Metadata block
    git = _git_info()
    class_dist = dict(Counter(r.get("target_class", "?") for r in rows))
    meta = {
        "run_folder": folder_name,
        "run_timestamp": ts,
        "slug": slug,
        "status": "complete",
        "operator": operator,
        "commit": git["commit"],
        "dirty": git["dirty"],
        "dirty_files": git["dirty_files"],
        "manifest_path": str(manifest_path.relative_to(PROJECT_ROOT)) if PROJECT_ROOT in manifest_path.parents else str(manifest_path),
        "n_records": len(rows),
        "class_distribution": class_dist,
        "model_label": cfg["model"],
        "original_jsonl": str(jsonl_path.relative_to(PROJECT_ROOT)) if PROJECT_ROOT in jsonl_path.parents else str(jsonl_path),
    }

    # 10. Write enriched report
    write_enriched_report(
        out_path=run_dir / "report.md",
        meta=meta,
        config=cfg,
        metrics=metrics,
        plot_names=plot_names,
        viz_counts=viz_counts,
        hypothesis=hypothesis,
        comparison=comparison,
        prompt_summary=prompt_summary,
        observations=observations,
    )

    # 11. Update running index
    regenerate_index(runs_root)
    append_jsonl_summary(runs_root, folder_name, metrics)

    return run_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def rebuild_viz_only(
    run_folder: str | Path,
    manifest_path: str | Path,
    prompts_module: str = "prompts",
) -> int:
    """Regenerate only the per-datapoint HTMLs inside an existing run folder.

    Use after changing the HTML layout in `viz.html_report` to refresh every
    existing run without re-running evaluate or regenerating plots.

    Returns the number of HTML files written.
    """
    run_folder = Path(run_folder).resolve()
    manifest_path = Path(manifest_path).resolve()
    run_jsonl = run_folder / "run.jsonl"
    if not run_jsonl.exists():
        print(f"[rebuild] skip: {run_folder} (no run.jsonl)")
        return 0

    rows = _load_jsonl(run_jsonl)
    manifest = pd.read_csv(manifest_path, low_memory=False)
    oids_in_run = {r.get("oid") for r in rows if r.get("oid")}
    top_per_class = _pick_top_10_per_class(manifest, oids_in_run, n_per_class=10)

    oid_to_row = {r["oid"]: r for r in rows if r.get("oid")}
    manifest_by_oid = manifest.set_index("oid")

    viz_root = run_folder / "viz"
    if viz_root.exists():
        shutil.rmtree(viz_root)

    n_written = 0
    for cls, oids in top_per_class.items():
        cls_dir = viz_root / cls
        cls_dir.mkdir(parents=True, exist_ok=True)
        for oid in oids:
            r = oid_to_row.get(oid)
            if r is None or oid not in manifest_by_oid.index:
                continue
            mrow = manifest_by_oid.loc[oid]
            try:
                sys_p, usr_p = _reconstruct_prompts(mrow, oid, prompts_module)
            except Exception as e:
                sys_p, usr_p = f"(prompt reconstruction failed: {e})", ""
            try:
                render_datapoint_html(
                    row=r,
                    manifest_row=mrow,
                    system_prompt=sys_p,
                    user_prompt=usr_p,
                    out_path=cls_dir / f"{oid}.html",
                )
                n_written += 1
            except Exception as e:
                print(f"[rebuild] {run_folder.name}/{oid} failed: {e}")
    print(f"[rebuild] {run_folder.name}: {n_written} HTMLs")
    return n_written


def _cli() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--jsonl", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--model", default=None)
    ap.add_argument("--prompts", default="prompts")
    ap.add_argument("--runs-root", default="runs")
    ap.add_argument("--timestamp", default=None, help="Format YYYYMMDD-HHMM; auto from mtime if omitted.")
    ap.add_argument("--slug", default=None, help="Override slug (default: model name slugified)")
    ap.add_argument("--backend", default=None, choices=[None, "tinker", "openai"])
    ap.add_argument("--hypothesis", default=None)
    ap.add_argument("--comparison", default=None)
    ap.add_argument("--observations", default=None)
    args = ap.parse_args()

    run_dir = build_run_folder(
        jsonl_path=args.jsonl,
        manifest_path=args.manifest,
        model_name=args.model,
        prompts_module=args.prompts,
        runs_root=args.runs_root,
        run_timestamp=args.timestamp,
        slug_override=args.slug,
        hypothesis=args.hypothesis,
        comparison=args.comparison,
        observations=args.observations,
        backend_hint=args.backend,
    )
    print(f"run folder written to: {run_dir}")


if __name__ == "__main__":
    _cli()
