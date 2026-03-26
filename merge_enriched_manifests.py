"""
Combine per-class enriched CSV shards into one file in the reference manifest row order.

Use after parallel runs of enrich_manifest_alerce.py --target-class <CLASS>.

Example:
  python merge_enriched_manifests.py --reference data/manifest.csv \\
    --shards data/manifest_enriched_SN.csv data/manifest_enriched_AGN.csv ... \\
    --out data/manifest_enriched.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def merge_shards(reference: Path, shard_paths: list[Path], out: Path) -> None:
    _cols = pd.read_csv(reference, nrows=0).columns.tolist()
    _dtype = {"candid_used": "string"} if "candid_used" in _cols else {}
    ref = pd.read_csv(reference, dtype=_dtype, low_memory=False)

    parts: list[pd.DataFrame] = []
    for p in shard_paths:
        if not p.is_file():
            raise FileNotFoundError(f"Missing shard: {p}")
        parts.append(pd.read_csv(p, dtype=_dtype, low_memory=False))

    big = pd.concat(parts, ignore_index=True)
    dup = big[big.duplicated(subset=["oid"], keep=False)]
    if len(dup) > 0:
        raise ValueError(
            "Duplicate oid values across shards:\n" + "\n".join(dup["oid"].astype(str).unique()[:20].tolist())
        )

    ref_oids = ref["oid"].astype(str)
    have = set(big["oid"].astype(str))
    missing = set(ref_oids) - have
    if missing:
        print(
            f"Warning: {len(missing)} reference oids are missing from shards "
            "(those rows keep manifest columns only; enrichment columns stay NaN).",
            file=sys.stderr,
        )

    # Start from reference rows/order; overlay shard rows so missing oids keep manifest fields.
    ref_idx = ref.set_index("oid")
    big_idx = big.set_index("oid")
    ordered = ref_idx.reindex(ref_oids)
    for c in big_idx.columns:
        if c not in ordered.columns:
            ordered[c] = np.nan
    ordered.update(big_idx.reindex(ordered.index))

    ordered = ordered.reset_index()
    extra = [c for c in ordered.columns if c not in set(ref.columns)]
    final_cols = [c for c in ref.columns if c in ordered.columns] + extra
    ordered = ordered[final_cols]

    out.parent.mkdir(parents=True, exist_ok=True)
    ordered.to_csv(out, index=False)
    print(f"Wrote {out} ({len(ordered)} rows)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Merge enriched manifest shards in reference order")
    ap.add_argument("--reference", type=Path, required=True, help="Original manifest (defines row order and oid set)")
    ap.add_argument("--shards", type=Path, nargs="+", required=True, help="Enriched CSV paths (one or more)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    merge_shards(args.reference, list(args.shards), args.out)


if __name__ == "__main__":
    main()
