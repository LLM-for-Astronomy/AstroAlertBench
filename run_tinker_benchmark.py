"""
Run zero-shot VLM evaluation on the manifest using Tinker (api_tinker.py).

Example (use manifest_enriched.csv after enrich_manifest_alerce.py for magpsf / sgscore1 / fid_band):
  set TINKER_API_KEY=...
  python run_tinker_benchmark.py --manifest data/manifest_enriched.csv --model moonshotai/Kimi-K2.5 --limit 10 --out results/kimi_zs.jsonl
  python evaluate.py --predictions results/kimi_zs.jsonl --manifest data/manifest_enriched.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from api_tinker import ROOT, DEFAULT_MODEL, run_one
from evaluate import extract_json_object


def main() -> None:
    ap = argparse.ArgumentParser(description="Run Tinker VLM on ZTF benchmark montages")
    ap.add_argument("--manifest", type=Path, default=ROOT / "data" / "manifest.csv")
    ap.add_argument("--out", type=Path, required=True, help="JSONL output path")
    ap.add_argument("--limit", type=int, default=None, help="Max rows to process")
    ap.add_argument("--model", type=str, default=None, help="Override TINKER_MODEL")
    ap.add_argument("--start", type=int, default=0, help="Row offset")
    args = ap.parse_args()

    if not args.manifest.is_file():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(args.manifest)
    if args.start:
        df = df.iloc[args.start :]
    if args.limit is not None:
        df = df.head(args.limit)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    model = args.model or DEFAULT_MODEL

    n_ok = 0
    n_err = 0
    with open(args.out, "w", encoding="utf-8") as fout:
        for _, row in df.iterrows():
            oid = str(row["oid"])
            tc = str(row["target_class"])
            try:
                rec = run_one(oid, tc, row, model_name=model)
                rec["parsed"] = extract_json_object(rec["raw_text"])
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fout.flush()
                n_ok += 1
                print(f"OK {oid} ({tc})")
            except Exception as e:
                n_err += 1
                err_rec = {"oid": oid, "target_class": tc, "error": str(e)}
                fout.write(json.dumps(err_rec, ensure_ascii=False) + "\n")
                fout.flush()
                print(f"FAIL {oid}: {e}", file=sys.stderr)

    print(f"Wrote {args.out}  ok={n_ok}  fail={n_err}")


if __name__ == "__main__":
    main()
