"""
Run zero-shot VLM evaluation on the manifest using Tinker (api_tinker.py).

Example (use manifest_enriched.csv after enrich_manifest_alerce.py — required for fid / isdiffpos and other candidate fields):
  set TINKER_API_KEY=...
  python run_tinker_benchmark.py --manifest data/manifest_enriched.csv --model moonshotai/Kimi-K2.5 --limit 10 --out results/kimi_zs.jsonl
  python evaluate.py --predictions results/kimi_zs.jsonl --manifest data/manifest_enriched.csv

Parallel execution (default concurrency=1 for backward compat):
  python run_tinker_benchmark.py --manifest data/manifest_fewshot.csv --out results/fewshot.jsonl --concurrency 64

Ablation (fewer raw ZTF fields, same JSON schema):
  python run_tinker_benchmark.py --manifest data/manifest_enriched.csv --out results/fewshot_ablation.jsonl --prompts prompt_ablation --concurrency 64

Full metadata + extra Part B/C guidance for AGN vs variable_star:
  python run_tinker_benchmark.py --manifest data/manifest_enriched.csv --out results/run_agn_prompt.jsonl --prompts prompts_agn_instruction
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

import api_tinker
from api_tinker import ROOT, DEFAULT_MODEL, run_one
from evaluate import extract_json_object


def _process_row(
    oid: str, tc: str, row: "pd.Series", model: str
) -> dict:
    rec = run_one(oid, tc, row, model_name=model)
    rec["parsed"] = extract_json_object(rec.get("answer_text") or rec["raw_text"])
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description="Run Tinker VLM on ZTF benchmark montages")
    ap.add_argument("--manifest", type=Path, default=ROOT / "data" / "manifest.csv")
    ap.add_argument("--out", type=Path, required=True, help="JSONL output path")
    ap.add_argument("--limit", type=int, default=None, help="Max rows to process")
    ap.add_argument("--model", type=str, default=None, help="Override TINKER_MODEL")
    ap.add_argument("--start", type=int, default=0, help="Row offset")
    ap.add_argument(
        "--concurrency", type=int, default=1,
        help="Number of parallel API calls (default: 1, try 32-64 for speed)",
    )
    ap.add_argument(
        "--prompts", type=str, default="prompts",
        help="Prompt module name (default: prompts). Use 'prompts_agn_instruction' for full fields + AGN vs VS guidance.",
    )
    args = ap.parse_args()

    prompt_mod = importlib.import_module(args.prompts)
    if args.prompts != "prompts":
        api_tinker.SYSTEM_PROMPT = prompt_mod.SYSTEM_PROMPT
        api_tinker.build_user_prompt = prompt_mod.build_user_prompt
        api_tinker.manifest_row_to_metadata = prompt_mod.manifest_row_to_metadata
        print(f"Using prompt module: {args.prompts}")

    if not args.manifest.is_file():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(args.manifest)
    req_cols = getattr(prompt_mod, "required_manifest_columns", None)
    if callable(req_cols):
        missing = req_cols() - frozenset(df.columns)
        if missing:
            print(
                f"Manifest missing required columns for --prompts {args.prompts!r}: "
                f"{sorted(missing)}. Use manifest_enriched.csv or run enrich_manifest_alerce.py.",
                file=sys.stderr,
            )
            sys.exit(1)
    if args.start:
        df = df.iloc[args.start :]
    if args.limit is not None:
        df = df.head(args.limit)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    model = args.model or DEFAULT_MODEL
    total = len(df)

    n_ok = 0
    n_err = 0
    write_lock = threading.Lock()
    t0 = time.perf_counter()

    with open(args.out, "w", encoding="utf-8") as fout:
        if args.concurrency <= 1:
            for idx, (_, row) in enumerate(df.iterrows(), 1):
                oid = str(row["oid"])
                tc = str(row["target_class"])
                try:
                    rec = _process_row(oid, tc, row, model)
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fout.flush()
                    n_ok += 1
                    print(f"[{idx}/{total}] OK {oid} ({tc})")
                except Exception as e:
                    n_err += 1
                    err_rec = {"oid": oid, "target_class": tc, "error": str(e)}
                    fout.write(json.dumps(err_rec, ensure_ascii=False) + "\n")
                    fout.flush()
                    print(f"[{idx}/{total}] FAIL {oid}: {e}", file=sys.stderr)
        else:
            futures = {}
            with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                for _, row in df.iterrows():
                    oid = str(row["oid"])
                    tc = str(row["target_class"])
                    fut = pool.submit(_process_row, oid, tc, row, model)
                    futures[fut] = (oid, tc)

                for done_idx, fut in enumerate(as_completed(futures), 1):
                    oid, tc = futures[fut]
                    try:
                        rec = fut.result()
                        with write_lock:
                            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                            fout.flush()
                            n_ok += 1
                        print(f"[{done_idx}/{total}] OK {oid} ({tc})")
                    except Exception as e:
                        with write_lock:
                            n_err += 1
                            err_rec = {"oid": oid, "target_class": tc, "error": str(e)}
                            fout.write(json.dumps(err_rec, ensure_ascii=False) + "\n")
                            fout.flush()
                        print(f"[{done_idx}/{total}] FAIL {oid}: {e}", file=sys.stderr)

    elapsed = time.perf_counter() - t0
    print(f"Wrote {args.out}  ok={n_ok}  fail={n_err}  elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    main()
