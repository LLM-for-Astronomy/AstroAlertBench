"""One-shot back-fill of wall-clock runtime metadata for the four most recent
benchmark runs (Opus 4.7 think / nothink, Gemini 2.5 Pro / Flash).

Sources (from `terminals/` PowerShell scrollback):
  - 45.txt:1004  Opus 4.7 think     elapsed=10790.7s, single sweep, conc=2
  - 49.txt:1003  Gemini 2.5 Flash   elapsed=1021.4s,  single sweep, conc=8
  - 47.txt:824   Opus 4.7 nothink   retry elapsed=5548.1s, conc=2  (621/621 ok)
  - 48.txt:554   Gemini 2.5 Pro     retry elapsed=2562.5s, conc=8  (498/498 ok)

The original sweeps for Opus nothink and Gemini Pro got rolled out of the
terminal buffer.  We extrapolate them from the retry throughput
(seconds/row * rows-attempted-in-original-sweep) and mark estimated=True.

For each run we:
  1. Write `<run_folder>/runmeta.json`.
  2. Inject a `wall_clock` block into `<run_folder>/metrics.json`.
  3. Insert a `Wall-clock runtime:` bullet into the Output section of
     `<run_folder>/report.md` (idempotent).

After this, the regenerated `runs/index.md` will include the new column.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from viz._runmeta import format_wallclock_line, summarize  # noqa: E402
from viz.index import regenerate_index, regenerate_jsonl_index  # noqa: E402


def _iso(dt: _dt.datetime) -> str:
    return dt.astimezone().isoformat(timespec="seconds")


def _make_pass(
    *, kind: str, finished_at_local: str, elapsed: float,
    rows_attempted: int, rows_ok: int, rows_fail: int,
    concurrency: int, command: str, estimated: bool = False,
) -> dict:
    finished = _dt.datetime.fromisoformat(finished_at_local)
    started = finished - _dt.timedelta(seconds=elapsed)
    return {
        "kind": kind,
        "started_at": _iso(started),
        "finished_at": _iso(finished),
        "elapsed_seconds": round(float(elapsed), 1),
        "rows_attempted": int(rows_attempted),
        "rows_ok": int(rows_ok),
        "rows_fail": int(rows_fail),
        "concurrency": int(concurrency),
        "command": command,
        "estimated": bool(estimated),
    }


# Apr-25 back-fill numbers (see top-of-file source comments).
RUNS: list[dict] = [
    {
        "folder": "runs/20260423-0942-opus47-think-benchmark-full",
        "passes": [
            _make_pass(
                kind="initial",
                finished_at_local="2026-04-23T09:43:00",
                elapsed=10790.7,
                rows_attempted=1500, rows_ok=1500, rows_fail=0,
                concurrency=2,
                command=("python run_tinker_benchmark.py --backend anthropic "
                        "--manifest data/manifest_benchmark_final.csv "
                        "--model claude-opus-4-7 --reasoning-effort high "
                        "--out results/benchmark_opus47_think.jsonl --concurrency 2"),
            ),
        ],
    },
    {
        "folder": "runs/20260423-2110-gemini25-flash-none-benchmark-full",
        "passes": [
            _make_pass(
                kind="initial",
                finished_at_local="2026-04-23T21:10:20",
                elapsed=1021.4,
                rows_attempted=1500, rows_ok=1500, rows_fail=0,
                concurrency=8,
                command=("python run_tinker_benchmark.py --backend google "
                        "--manifest data/manifest_benchmark_final.csv "
                        "--model gemini-2.5-flash --reasoning-effort none "
                        "--out results/benchmark_gemini25_flash_none.jsonl --concurrency 8"),
            ),
        ],
    },
    {
        "folder": "runs/20260424-2324-opus47-nothink-benchmark-full",
        "passes": [
            # Original sweep: terminal scrollback rolled off.  After the run
            # 879 rows were OK and 621 still needed retry, so attempts ~1500.
            # Retry pace = 5548.1s / 621 = 8.93 s/row at concurrency 2.
            # Estimated elapsed for the original sweep = 879 * 8.93 ~= 7850s.
            _make_pass(
                kind="initial",
                finished_at_local="2026-04-23T14:11:00",   # ~12:00 + ~2h11m
                elapsed=7850.0,
                rows_attempted=1500, rows_ok=879, rows_fail=621,
                concurrency=2,
                command=("python run_tinker_benchmark.py --backend anthropic "
                        "--manifest data/manifest_benchmark_final.csv "
                        "--model claude-opus-4-7 --reasoning-effort none "
                        "--out results/benchmark_opus47_nothink.jsonl --concurrency 2"),
                estimated=True,
            ),
            _make_pass(
                kind="retry",
                finished_at_local="2026-04-24T23:24:28",
                elapsed=5548.1,
                rows_attempted=621, rows_ok=621, rows_fail=0,
                concurrency=2,
                command=("python retry_failed.py --results results/benchmark_opus47_nothink.jsonl "
                        "--manifest data/manifest_benchmark_final.csv "
                        "--backend anthropic --model claude-opus-4-7 "
                        "--reasoning-effort none --concurrency 2"),
            ),
        ],
    },
    {
        "folder": "runs/20260424-1809-gemini25-pro-high-benchmark-full",
        "passes": [
            # Original sweep: hit the per-day 1000-request quota partway,
            # leaving 1002 OK and 498 to retry.  Retry pace = 2562.5/498
            # = 5.146 s/row at concurrency 8.  Estimated original sweep
            # compute = 1002 * 5.146 ~= 5160s (excludes the long quota stall).
            _make_pass(
                kind="initial",
                finished_at_local="2026-04-23T23:30:00",   # ~22:04 + ~1h26m
                elapsed=5160.0,
                rows_attempted=1500, rows_ok=1002, rows_fail=498,
                concurrency=8,
                command=("python run_tinker_benchmark.py --backend google "
                        "--manifest data/manifest_benchmark_final.csv "
                        "--model gemini-2.5-pro --reasoning-effort high "
                        "--out results/benchmark_gemini25_pro_high.jsonl --concurrency 8"),
                estimated=True,
            ),
            _make_pass(
                kind="retry",
                finished_at_local="2026-04-24T18:09:56",
                elapsed=2562.5,
                rows_attempted=498, rows_ok=498, rows_fail=0,
                concurrency=8,
                command=("python retry_failed.py --results results/benchmark_gemini25_pro_high.jsonl "
                        "--manifest data/manifest_benchmark_final.csv "
                        "--backend google --model gemini-2.5-pro "
                        "--reasoning-effort high --concurrency 8"),
            ),
        ],
    },
]


def _patch_report_with_wallclock(report_path: Path, line: str) -> None:
    """Insert / refresh the `Wall-clock runtime:` bullet inside the Output
    section of report.md.  Idempotent."""
    md = report_path.read_text(encoding="utf-8")
    new_bullet = f"- **Wall-clock runtime:** {line}"

    # Already there?  Replace in-place.
    pat = re.compile(r"^- \*\*Wall-clock runtime:\*\*[^\n]*$", re.MULTILINE)
    if pat.search(md):
        md = pat.sub(new_bullet, md, count=1)
        report_path.write_text(md, encoding="utf-8")
        return

    # Otherwise insert right after the "Records written:" line.
    insert_pat = re.compile(r"(- \*\*Records written:\*\*[^\n]*\n)")
    m = insert_pat.search(md)
    if m:
        md = md[: m.end()] + new_bullet + "\n" + md[m.end():]
        report_path.write_text(md, encoding="utf-8")
        return

    # Fallback: append a new Output bullet after the Output heading.
    out_pat = re.compile(r"(## Output\s*\n)", re.MULTILINE)
    m = out_pat.search(md)
    if m:
        md = md[: m.end()] + new_bullet + "\n" + md[m.end():]
        report_path.write_text(md, encoding="utf-8")
        return

    print(f"  !! could not locate Output section in {report_path}; skipping report patch.")


def _patch_metrics_with_wallclock(metrics_path: Path, summary: dict) -> None:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["wall_clock"] = summary
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def main() -> None:
    for entry in RUNS:
        run_dir = (PROJECT_ROOT / entry["folder"]).resolve()
        if not run_dir.is_dir():
            print(f"!! missing run folder: {run_dir}")
            continue
        runmeta = {"passes": entry["passes"]}
        (run_dir / "runmeta.json").write_text(
            json.dumps(runmeta, indent=2), encoding="utf-8"
        )
        summary = summarize(runmeta)
        line = format_wallclock_line(summary)
        _patch_metrics_with_wallclock(run_dir / "metrics.json", summary)
        if (run_dir / "report.md").exists():
            _patch_report_with_wallclock(run_dir / "report.md", line)
        print(f"OK  {run_dir.name}")
        print(f"    -> {line}")

    # Refresh runs/index.md and runs/index.jsonl so the new column populates.
    runs_root = PROJECT_ROOT / "runs"
    regenerate_index(runs_root)
    regenerate_jsonl_index(runs_root)
    print("Regenerated runs/index.md and runs/index.jsonl.")


if __name__ == "__main__":
    main()
