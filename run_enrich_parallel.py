"""
Run enrich_manifest_alerce.py in parallel: one subprocess per target_class (default: five
classes), then merge shards back into a single CSV in the original manifest row order.

Example:
  python run_enrich_parallel.py --in data/manifest.csv --out data/manifest_enriched.csv

Shards are written next to --out as manifest_enriched_SN.csv, manifest_enriched_AGN.csv, ...
(using the stem of --out). If the ALeRCE API rate-limits you, lower concurrency with
--jobs 2 or increase --sleep (per-process delay between rows).

Options:
  --jobs N      max concurrent enrichment processes (default: 5, capped by number of classes)
  --classes     comma-separated classes (default: SN,AGN,VS,asteroid,bogus)
  --merge-only  only run merge_enriched_manifests.py (expects shard files to exist)
  --no-merge    only launch enrich jobs; merge manually
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DEFAULT_CLASSES = ["SN", "AGN", "VS", "asteroid", "bogus"]


def shard_path(final_out: Path, class_name: str) -> Path:
    return final_out.parent / f"{final_out.stem}_{class_name}{final_out.suffix}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Parallel ALeRCE manifest enrichment by class")
    ap.add_argument("--in", dest="inp", type=Path, default=ROOT / "data" / "manifest.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "manifest_enriched.csv")
    ap.add_argument("--sleep", type=float, default=0.12)
    ap.add_argument("--limit", type=int, default=None, help="Passed to each enrich job (testing)")
    ap.add_argument("--jobs", type=int, default=5, help="Max concurrent enrichment processes")
    ap.add_argument(
        "--classes",
        type=str,
        default=None,
        help=f"Comma-separated target_class values (default: {','.join(DEFAULT_CLASSES)})",
    )
    ap.add_argument("--merge-only", action="store_true", help="Only merge existing shard CSVs into --out")
    ap.add_argument("--no-merge", action="store_true", help="Run enrich only; skip merge step")
    args = ap.parse_args()

    classes = DEFAULT_CLASSES if not args.classes else [c.strip() for c in args.classes.split(",") if c.strip()]
    if not classes:
        print("No classes to process.", file=sys.stderr)
        sys.exit(1)

    enrich_script = ROOT / "enrich_manifest_alerce.py"
    merge_script = ROOT / "merge_enriched_manifests.py"

    if args.merge_only:
        shards = [shard_path(args.out, c) for c in classes]
        cmd = [
            sys.executable,
            str(merge_script),
            "--reference",
            str(args.inp),
            "--out",
            str(args.out),
            "--shards",
            *[str(p) for p in shards],
        ]
        r = subprocess.run(cmd, cwd=ROOT)
        sys.exit(r.returncode)

    if not args.inp.is_file():
        print(f"Manifest not found: {args.inp}", file=sys.stderr)
        sys.exit(1)

    def run_enrich(class_name: str) -> tuple[str, int]:
        out = shard_path(args.out, class_name)
        cmd = [
            sys.executable,
            str(enrich_script),
            "--in",
            str(args.inp),
            "--out",
            str(out),
            "--target-class",
            class_name,
            "--sleep",
            str(args.sleep),
        ]
        if args.limit is not None:
            cmd.extend(["--limit", str(args.limit)])
        r = subprocess.run(cmd, cwd=ROOT)
        return class_name, r.returncode

    workers = max(1, min(args.jobs, len(classes)))
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(run_enrich, c): c for c in classes}
        for fut in as_completed(futures):
            cname, code = fut.result()
            if code != 0:
                failed.append(cname)
                print(f"FAILED class {cname} (exit {code})", file=sys.stderr)

    if failed:
        print(f"Stopping: {len(failed)} enrich job(s) failed: {failed}", file=sys.stderr)
        sys.exit(1)

    if args.no_merge:
        print("Skipping merge (--no-merge). Merge with:")
        shards = " ".join(str(shard_path(args.out, c)) for c in classes)
        print(
            f"  python merge_enriched_manifests.py --reference {args.inp} --out {args.out} --shards {shards}",
        )
        return

    shards = [shard_path(args.out, c) for c in classes]
    cmd = [
        sys.executable,
        str(merge_script),
        "--reference",
        str(args.inp),
        "--out",
        str(args.out),
        "--shards",
        *[str(p) for p in shards],
    ]
    r = subprocess.run(cmd, cwd=ROOT)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
