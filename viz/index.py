"""Maintain `runs/index.md` — a running table of every run folder.

The index is regenerated from scratch each time (reading every run's `report.md`
for a small header block) so it stays in sync even if folders are renamed or
backfilled out-of-order.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _extract_metric_summary(report_md: str) -> dict[str, str]:
    """Pull a handful of key metrics out of the enriched report for the index."""
    out: dict[str, str] = {}

    def _grab(pattern: str) -> str | None:
        m = re.search(pattern, report_md)
        return m.group(1).strip() if m else None

    out["5class"] = _grab(r"\*\*Final 5-class accuracy\*\*\s*\|\s*\*\*([^|*]+)\*\*") or "—"
    out["parse"] = _grab(r"json_valid_rate\s*\|\s*([0-9.]+\s*%?)") or "—"
    out["n"] = _grab(r"n_examples\s*\|\s*([0-9]+)") or "—"
    out["trunc"] = _grab(r"truncated_rate\s*\|\s*([0-9.]+\s*%?)") or "—"
    out["msrs"] = _grab(r"MSRS \(mean self-rated score\):\*\*\s*([0-9.]+)") or "—"
    out["wallclock"] = _grab(r"\*\*Wall-clock runtime:\*\*\s*([^\n]+)") or "—"
    return out


def _parse_folder_name(name: str) -> tuple[str, str]:
    """runs/20260420-1855-kimi-k25 → ('20260420-1855', 'kimi-k25')."""
    parts = name.split("-", 2)
    if len(parts) >= 3:
        return f"{parts[0]}-{parts[1]}", parts[2]
    return name, ""


def regenerate_index(runs_root: Path) -> None:
    """Rewrite `runs/index.md`."""
    runs_root = Path(runs_root)
    if not runs_root.exists():
        return

    entries: list[dict[str, str]] = []
    for p in sorted(runs_root.iterdir()):
        if not p.is_dir():
            continue
        report = p / "report.md"
        if not report.exists():
            continue
        try:
            md = report.read_text(encoding="utf-8")
        except OSError:
            continue
        ts, slug = _parse_folder_name(p.name)
        metrics = _extract_metric_summary(md)
        entries.append({
            "folder": p.name,
            "ts": ts,
            "slug": slug,
            **metrics,
        })

    # Sort newest first by folder name (format sorts lexicographically)
    entries.sort(key=lambda e: e["folder"], reverse=True)

    lines = [
        "# Runs index",
        "",
        f"_{len(entries)} run(s) logged. Regenerated automatically; do not hand-edit._",
        "",
        "| Run folder | Timestamp | Slug / model | n | Parse rate | 5-class acc | Truncated | MSRS | Wall-clock |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        lines.append(
            f"| [`{e['folder']}`](./{e['folder']}/report.md) | {e['ts']} | {e['slug']} | "
            f"{e['n']} | {e['parse']} | {e['5class']} | {e['trunc']} | {e['msrs']} | {e['wallclock']} |"
        )
    lines.append("")

    (runs_root / "index.md").write_text("\n".join(lines), encoding="utf-8")


def regenerate_jsonl_index(runs_root: Path) -> None:
    """Rewrite runs/index.jsonl by scanning every run's metrics.json (de-duped)."""
    runs_root = Path(runs_root)
    if not runs_root.exists():
        return
    entries: list[dict] = []
    for p in sorted(runs_root.iterdir()):
        if not p.is_dir():
            continue
        mj = p / "metrics.json"
        if not mj.exists():
            continue
        try:
            metrics = json.loads(mj.read_text(encoding="utf-8"))
        except Exception:
            continue
        wc = metrics.get("wall_clock") or {}
        entries.append({
            "folder": p.name,
            "n_examples": metrics.get("n_examples"),
            "json_valid_rate": metrics.get("json_valid_rate"),
            "final_5class_accuracy": metrics.get("part_c_final_5class_accuracy"),
            "part_b_msrs": metrics.get("part_b_msrs"),
            "truncated_rate": metrics.get("truncated_rate"),
            "wall_clock_seconds_total": wc.get("wall_clock_seconds_total"),
            "wall_clock_human": wc.get("wall_clock_human"),
            "wall_clock_estimated": wc.get("estimated"),
            "wall_clock_n_passes": wc.get("n_passes"),
        })
    path = runs_root / "index.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


# Kept as an alias for the old name.
append_jsonl_summary = lambda runs_root, folder_name, metrics: regenerate_jsonl_index(runs_root)  # noqa: E731
