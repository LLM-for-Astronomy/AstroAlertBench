"""
Retry failed rows in an existing JSONL benchmark result file and merge the
new successful rows back into the same file (preserving original row order).

A record is considered "failed" if it has an "error" key (e.g., from a 429
insufficient_quota or other API exception during the original run) and no
"raw_text"/"parsed" output.

Usage (GPT-5.4 high / none, backend=openai):
  python retry_failed.py --results results/benchmark_gpt54_high.jsonl \
      --manifest data/manifest_benchmark_final.csv \
      --backend openai --model gpt-5.4 --reasoning-effort high --concurrency 8

  python retry_failed.py --results results/benchmark_gpt54_none.jsonl \
      --manifest data/manifest_benchmark_final.csv \
      --backend openai --model gpt-5.4 --reasoning-effort none --concurrency 8

A .bak copy is written alongside the results file before modification, and a
.retry.jsonl file with only the newly fetched rows is also written for audit.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

import api_tinker
from evaluate import extract_json_object


def _is_failed(rec: dict) -> bool:
    if "error" in rec and rec.get("raw_text") is None:
        return True
    if rec.get("raw_text") is None and rec.get("parsed") is None and rec.get("model") is None:
        return True
    return False


def _process_row(oid, tc, row, model, backend_module, extra_kwargs):
    rec = backend_module.run_one(oid, tc, row, model_name=model, **extra_kwargs)
    rec["parsed"] = extract_json_object(rec.get("answer_text") or rec["raw_text"])
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description="Retry failed JSONL rows and merge in-place.")
    ap.add_argument("--results", type=Path, required=True,
                    help="Existing JSONL file produced by run_tinker_benchmark.py")
    ap.add_argument("--manifest", type=Path, required=True,
                    help="Manifest CSV matching the original run (e.g. data/manifest_benchmark_final.csv)")
    ap.add_argument("--backend", choices=["tinker", "openai"], default="openai")
    ap.add_argument("--model", type=str, required=True)
    ap.add_argument("--reasoning-effort", type=str, default=None,
                    choices=["none", "low", "medium", "high", "xhigh"])
    ap.add_argument("--thinking", choices=["enabled", "disabled"], default="enabled")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true",
                    help="Only report how many rows would be retried; do not call the API.")
    args = ap.parse_args()

    if not args.results.is_file():
        print(f"Results file not found: {args.results}", file=sys.stderr)
        sys.exit(1)
    if not args.manifest.is_file():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    existing: list[dict] = []
    for line in args.results.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        existing.append(json.loads(line))

    failed_oids = [r["oid"] for r in existing if _is_failed(r)]
    print(f"Loaded {len(existing)} rows from {args.results}")
    print(f"Found {len(failed_oids)} failed rows to retry")
    if not failed_oids:
        print("Nothing to do.")
        return
    if args.dry_run:
        sample = ", ".join(failed_oids[:10])
        more = f" (+{len(failed_oids)-10} more)" if len(failed_oids) > 10 else ""
        print(f"First failed OIDs: {sample}{more}")
        return

    df = pd.read_csv(args.manifest)
    df_by_oid = {str(r["oid"]): r for _, r in df.iterrows()}
    missing = [oid for oid in failed_oids if oid not in df_by_oid]
    if missing:
        print(f"ERROR: {len(missing)} failed OIDs not present in manifest; aborting.", file=sys.stderr)
        print(f"  examples: {missing[:5]}", file=sys.stderr)
        sys.exit(2)

    if args.backend == "openai":
        import api_openai
        backend_module = api_openai
    else:
        backend_module = api_tinker

    extra_kwargs: dict = {}
    if args.backend == "openai" and args.reasoning_effort is not None:
        extra_kwargs["reasoning_effort"] = args.reasoning_effort
    if args.backend == "tinker":
        extra_kwargs["thinking"] = args.thinking == "enabled"

    bak = args.results.with_suffix(args.results.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(args.results, bak)
        print(f"Backup written: {bak}")
    else:
        print(f"Backup already exists (not overwriting): {bak}")

    retry_out = args.results.with_suffix(".retry.jsonl")
    new_by_oid: dict[str, dict] = {}
    still_failed: list[tuple[str, str]] = []
    total = len(failed_oids)
    write_lock = threading.Lock()
    t0 = time.perf_counter()

    with open(retry_out, "w", encoding="utf-8") as fout:
        futures = {}
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            for oid in failed_oids:
                row = df_by_oid[oid]
                tc = str(row["target_class"])
                fut = pool.submit(_process_row, oid, tc, row, args.model, backend_module, extra_kwargs)
                futures[fut] = (oid, tc)

            for done_idx, fut in enumerate(as_completed(futures), 1):
                oid, tc = futures[fut]
                try:
                    rec = fut.result()
                    with write_lock:
                        new_by_oid[oid] = rec
                        fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        fout.flush()
                    print(f"[{done_idx}/{total}] OK {oid} ({tc})")
                except Exception as e:
                    err_rec = {"oid": oid, "target_class": tc, "error": str(e)}
                    with write_lock:
                        still_failed.append((oid, str(e)))
                        fout.write(json.dumps(err_rec, ensure_ascii=False) + "\n")
                        fout.flush()
                    print(f"[{done_idx}/{total}] FAIL {oid}: {e}", file=sys.stderr)

    elapsed = time.perf_counter() - t0
    print(f"\nRetry pass finished: ok={len(new_by_oid)}  fail={len(still_failed)}  elapsed={elapsed:.1f}s")
    print(f"Retry-only log: {retry_out}")

    merged = []
    for rec in existing:
        oid = rec.get("oid")
        if oid in new_by_oid:
            merged.append(new_by_oid[oid])
        else:
            merged.append(rec)

    tmp = args.results.with_suffix(args.results.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fout:
        for rec in merged:
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(args.results)

    remaining_fail = sum(1 for r in merged if _is_failed(r))
    print(f"Merged results written to: {args.results}")
    print(f"  total rows  = {len(merged)}")
    print(f"  ok rows     = {len(merged) - remaining_fail}")
    print(f"  failed rows = {remaining_fail}")
    if still_failed:
        print("\nOIDs that still failed after retry:")
        for oid, msg in still_failed[:20]:
            print(f"  - {oid}: {msg[:120]}")
        if len(still_failed) > 20:
            print(f"  ... (+{len(still_failed) - 20} more)")


if __name__ == "__main__":
    main()
